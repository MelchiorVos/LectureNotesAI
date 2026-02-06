"""
Orchestration pipeline – process a PDF end-to-end and push to Notion.
"""

import asyncio
import logging
import tempfile
from typing import Dict, Any, List, Tuple

from openai import AsyncOpenAI
from tqdm import tqdm

from config import ASTNode, PipelineContext
from backend.openai_client import (
    analyze_image_structured_async,
    generate_lecture_summary_async,
    generate_exam_questions_async,
)
from backend.notion_client import (
    upload_image_to_notion_async,
    create_image_block,
    ast_to_notion_children,
    append_children_to_notion_async,
)
from backend.pdf_parser import get_pdf_page_count, extract_pdf_pages_to_dir

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Single-slide processing
# ---------------------------------------------------------------------------


async def _process_single_slide(
    image_path: str,
    instruction: str,
    openai_client: AsyncOpenAI,
    notion_api_key: str,
    page_num: int,
    conversation_id: str,
    course_name: str,
) -> Tuple[int, List[Dict[str, Any]]]:
    """Process one slide: upload image + analyse via OpenAI in parallel."""
    upload_task = upload_image_to_notion_async(notion_api_key, image_path)
    analyze_task = analyze_image_structured_async(
        openai_client,
        image_path,
        instruction,
        conversation_id=conversation_id,
        course_name=course_name,
    )

    file_upload_id, ast = await asyncio.gather(upload_task, analyze_task)

    explanation_children = ast_to_notion_children(ast)
    image_block = create_image_block(file_upload_id)
    divider = {"object": "block", "type": "divider", "divider": {}}
    spacer = {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
    children = [image_block] + explanation_children + [divider, spacer]

    return (page_num, children)


async def _upload_slide_only(
    image_path: str,
    notion_api_key: str,
    page_num: int,
) -> Tuple[int, List[Dict[str, Any]]]:
    """Upload a slide image without OpenAI analysis (excluded slides)."""
    file_upload_id = await upload_image_to_notion_async(notion_api_key, image_path)
    image_block = create_image_block(file_upload_id)
    divider = {"object": "block", "type": "divider", "divider": {}}
    spacer = {"object": "block", "type": "paragraph", "paragraph": {"rich_text": []}}
    return (page_num, [image_block, divider, spacer])


# ---------------------------------------------------------------------------
# Full PDF pipeline
# ---------------------------------------------------------------------------


async def process_pdf(
    ctx: PipelineContext,
    openai_client: AsyncOpenAI,
) -> None:
    """
    Process every page of a PDF sequentially (conversation context requires
    ordering), then generate summary + exam questions and push to Notion.
    """
    total_pages = get_pdf_page_count(ctx.pdf_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        image_paths = extract_pdf_pages_to_dir(ctx.pdf_path, tmpdir)

        results: List[Tuple[int, List[Dict[str, Any]]]] = []

        with tqdm(total=total_pages, desc="Processing slides", unit="slide") as pbar:
            for i, image_path in enumerate(image_paths):
                page_num = i + 1

                if page_num in ctx.excluded_pages:
                    result = await _upload_slide_only(
                        image_path, ctx.notion_api_key, page_num
                    )
                else:
                    result = await _process_single_slide(
                        image_path,
                        ctx.instruction,
                        openai_client,
                        ctx.notion_api_key,
                        page_num,
                        ctx.conversation_id,
                        ctx.course_name,
                    )

                results.append(result)
                pbar.update(1)

    # Combine children in order
    all_children: List[Dict[str, Any]] = []
    for _, children in results:
        all_children.extend(children)

    # Lecture summary
    logger.info("Generating lecture summary…")
    summary_ast = await generate_lecture_summary_async(
        openai_client,
        ctx.conversation_id,
        ctx.course_name,
    )
    summary_title = {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": "📝 Lecture Summary"}}]
        },
    }
    all_children.extend([summary_title] + ast_to_notion_children(summary_ast))

    # Exam questions
    logger.info("Generating exam questions…")
    questions_ast = await generate_exam_questions_async(
        openai_client,
        ctx.conversation_id,
        ctx.course_name,
    )
    questions_title = {
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [{"type": "text", "text": {"content": "❓ Practice Questions"}}]
        },
    }
    all_children.extend([questions_title] + ast_to_notion_children(questions_ast))

    # Push to Notion
    logger.info("Appending %d blocks to Notion…", len(all_children))
    await append_children_to_notion_async(
        ctx.notion_api_key, ctx.notion_page_id, all_children
    )
    logger.info("All slides added to Notion.")
