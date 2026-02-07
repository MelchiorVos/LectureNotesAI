"""
OpenAI API interactions – image analysis, summaries, exam questions.
"""

import json
import base64
import logging
import mimetypes
from typing import Any, Dict

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from prompts.system import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Retry policy (internal)
# ---------------------------------------------------------------------------

_RETRY_ATTEMPTS = 3
_RETRY_WAIT_SECONDS = 2  # base for exponential back-off

# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------


def image_path_to_data_url(image_path: str) -> str:
    """Convert a local image file to a base-64 data URL."""
    mime, _ = mimetypes.guess_type(image_path)
    if mime is None:
        mime = "application/octet-stream"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------


def get_system_prompt(course_name: str) -> str:
    """Return the system prompt with the course name interpolated."""
    return SYSTEM_PROMPT.replace('[COURSE_NAME]', course_name)


# ---------------------------------------------------------------------------
# AST JSON Schema
# ---------------------------------------------------------------------------


def build_ast_schema() -> Dict[str, Any]:
    """
    Semantic AST schema used for structured OpenAI output.

    - title: string
    - blocks: array of block objects
      - kind: heading | paragraph | math_block | bullets | numbered
    """
    inline_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "kind": {"type": "string", "enum": ["text", "math"]},
            "text": {"type": "string"},
            "latex": {"type": "string"},
        },
        "required": ["kind", "text", "latex"],
    }

    block_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "kind": {
                "type": "string",
                "enum": ["heading", "paragraph", "math_block", "bullets", "numbered"],
            },
            "inlines": {"type": "array", "items": inline_schema},
            "latex": {"type": "string"},
            "items": {
                "type": "array",
                "items": {"type": "array", "items": inline_schema},
            },
        },
        "required": ["kind", "inlines", "latex", "items"],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "blocks": {"type": "array", "items": block_schema},
        },
        "required": ["title", "blocks"],
    }


# ---------------------------------------------------------------------------
# Retry-wrapped OpenAI helpers
# ---------------------------------------------------------------------------

_RETRY = dict(
    stop=stop_after_attempt(_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=_RETRY_WAIT_SECONDS, min=1, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "OpenAI call failed (attempt %s), retrying…", rs.attempt_number
    ),
)


@retry(**_RETRY)
async def analyze_image_structured_async(
    client: AsyncOpenAI,
    image_path: str,
    instruction: str,
    conversation_id: str,
    course_name: str,
    model: str = "gpt-5.2",
) -> Dict[str, Any]:
    """Analyze a slide image and return a structured AST."""
    data_url = image_path_to_data_url(image_path)
    schema = build_ast_schema()

    user_message = {
        "role": "user",
        "content": [
            {"type": "input_text", "text": instruction},
            {"type": "input_image", "image_url": data_url},
        ],
    }

    logger.debug("Sending slide to OpenAI (%s)", model)

    resp = await client.responses.create(
        model=model,
        input=[user_message],
        conversation=conversation_id,
        instructions=get_system_prompt(course_name),
        text={
            "format": {
                "type": "json_schema",
                "name": "semantic_ast",
                "strict": True,
                "schema": schema,
            }
        },
    )

    logger.debug("Received response (%d chars)", len(resp.output_text))
    return json.loads(resp.output_text)


@retry(**_RETRY)
async def generate_lecture_summary_async(
    client: AsyncOpenAI,
    conversation_id: str,
    course_name: str,
    model: str = "gpt-5.2",
) -> Dict[str, Any]:
    """Generate a lecture summary using the conversation history."""
    schema = build_ast_schema()

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": (
                    "Now that we've gone through the entire lecture, provide a "
                    "comprehensive summary. Make sure you mention the most important "
                    "concepts, formulas, and insights that were covered."
                ),
            },
        ],
    }

    resp = await client.responses.create(
        model=model,
        input=[user_message],
        conversation=conversation_id,
        instructions=get_system_prompt(course_name),
        text={
            "format": {
                "type": "json_schema",
                "name": "semantic_ast",
                "strict": True,
                "schema": schema,
            }
        },
    )

    return json.loads(resp.output_text)


@retry(**_RETRY)
async def generate_exam_questions_async(
    client: AsyncOpenAI,
    conversation_id: str,
    course_name: str,
    model: str = "gpt-5.2",
) -> Dict[str, Any]:
    """Generate exam-style questions from the lecture conversation."""
    schema = build_ast_schema()

    user_message = {
        "role": "user",
        "content": [
            {
                "type": "input_text",
                "text": (
                    "Based on the lecture content we've covered, generate 5 exam-style "
                    "questions. Format each question as a numbered list item. Make the "
                    "questions challenging but fair based on the lecture material. Also "
                    "include the correct answer for each question after the question itself."
                ),
            },
        ],
    }

    resp = await client.responses.create(
        model=model,
        input=[user_message],
        conversation=conversation_id,
        instructions=get_system_prompt(course_name),
        text={
            "format": {
                "type": "json_schema",
                "name": "semantic_ast",
                "strict": True,
                "schema": schema,
            }
        },
    )

    return json.loads(resp.output_text)
