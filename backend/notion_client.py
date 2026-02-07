"""
Notion API interactions – image uploads, block building, page management.
"""

import os
import logging
import mimetypes
from typing import Any, Dict, List

import aiohttp
from notion_client import Client as NotionClient
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type



logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 50
_RETRY_ATTEMPTS = 3
_RETRY_WAIT_SECONDS = 2  # base for exponential back-off


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def chunked(xs: List[Any], n: int) -> List[List[Any]]:
    """Split a list into chunks of at most *n* items."""
    return [xs[i : i + n] for i in range(0, len(xs), n)]


# ---------------------------------------------------------------------------
# Image upload
# ---------------------------------------------------------------------------

_RETRY = dict(
    stop=stop_after_attempt(_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=_RETRY_WAIT_SECONDS, min=1, max=30),
    retry=retry_if_exception_type(Exception),
    reraise=True,
    before_sleep=lambda rs: logger.warning(
        "Notion call failed (attempt %s), retrying…", rs.attempt_number
    ),
)


def create_image_block(file_upload_id: str) -> Dict[str, Any]:
    """Create a Notion image block from a file_upload_id."""
    return {
        "object": "block",
        "type": "image",
        "image": {
            "type": "file_upload",
            "file_upload": {"id": file_upload_id},
        },
    }


@retry(**_RETRY)
async def upload_image_to_notion_async(api_key: str, image_path: str) -> str:
    """Upload an image to Notion and return the file_upload_id."""
    filename = os.path.basename(image_path)
    mime, _ = mimetypes.guess_type(image_path)
    if mime is None:
        mime = "application/octet-stream"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
    }

    async with aiohttp.ClientSession() as session:
        # Step 1 — create file upload object
        async with session.post(
            "https://api.notion.com/v1/file_uploads",
            json={"filename": filename, "content_type": mime},
            headers={**headers, "accept": "application/json", "content-type": "application/json"},
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"File upload creation failed: {resp.status} {text}")
            data = await resp.json()
            file_upload_id = data["id"]

        # Step 2 — upload the file bytes
        with open(image_path, "rb") as f:
            file_data = f.read()

        form = aiohttp.FormData()
        form.add_field("file", file_data, filename=filename, content_type=mime)

        async with session.post(
            f"https://api.notion.com/v1/file_uploads/{file_upload_id}/send",
            headers=headers,
            data=form,
        ) as resp:
            if resp.status != 200:
                text = await resp.text()
                raise Exception(f"File upload failed: {resp.status} {text}")

    return file_upload_id


# ---------------------------------------------------------------------------
# Append blocks to a page
# ---------------------------------------------------------------------------


@retry(**_RETRY)
async def append_children_to_notion_async(
    api_key: str,
    page_id: str,
    children: List[Dict[str, Any]],
    chunk_size: int = _CHUNK_SIZE,
) -> None:
    """Append children blocks to a Notion page (chunked to stay under limits)."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        for batch in chunked(children, chunk_size):
            async with session.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers,
                json={"children": batch},
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"Append failed: {resp.status} {text}")


# ---------------------------------------------------------------------------
# Page management
# ---------------------------------------------------------------------------


def create_child_page(notion: NotionClient, parent_page_id: str, title: str) -> str:
    """Create a new child page under *parent_page_id* and return its ID."""
    new_page = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": {
                "title": [{"text": {"content": title}}]
            }
        },
    )
    return new_page["id"]


# ---------------------------------------------------------------------------
# Inline spacing normalization
# ---------------------------------------------------------------------------


def normalize_inlines_spacing(inlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add natural spacing around inline math:
    - Space before math if preceding text doesn't end with space/opening bracket
    - Space after math if following text doesn't start with space/punctuation
    """
    if len(inlines) < 2:
        return inlines

    result = [dict(i) for i in inlines]
    punctuation = {",", ".", ";", ":", "!", "?", ")", "]", "}"}
    openers = {"(", "[", "{"}

    for i in range(len(result) - 1):
        current = result[i]
        next_inline = result[i + 1]

        if current["kind"] == "text" and next_inline["kind"] == "math":
            text = current.get("text", "")
            if text and not text.endswith(" ") and not text.endswith(tuple(openers)):
                current["text"] = text + " "

        if current["kind"] == "math" and next_inline["kind"] == "text":
            text = next_inline.get("text", "")
            if text and not text.startswith(" ") and text[0] not in punctuation:
                next_inline["text"] = " " + text

    return result


# ---------------------------------------------------------------------------
# Rich-text conversion
# ---------------------------------------------------------------------------


def inlines_to_rich_text(inlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert inline AST objects to Notion rich_text array."""
    rich_text: List[Dict[str, Any]] = []
    for inline in inlines:
        if inline["kind"] == "text":
            t = inline.get("text", "")
            if t:
                rich_text.append({"type": "text", "text": {"content": t}})
        elif inline["kind"] == "math":
            latex = inline.get("latex", "")
            if latex:
                rich_text.append({"type": "equation", "equation": {"expression": latex}})
    return rich_text


# ---------------------------------------------------------------------------
# AST → Notion blocks
# ---------------------------------------------------------------------------


def ast_to_notion_children(ast: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a semantic AST to a list of Notion block children.

    - heading   → heading_3
    - paragraph → paragraph
    - math_block → equation
    - bullets   → bulleted_list_item (one per item)
    - numbered  → numbered_list_item (one per item)
    """
    children: List[Dict[str, Any]] = []

    for block in ast.get("blocks", []):
        kind = block.get("kind")

        match kind:
            case "heading":
                inlines = normalize_inlines_spacing(block.get("inlines", []))
                rich_text = inlines_to_rich_text(inlines)
                if rich_text:
                    children.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {"rich_text": rich_text},
                    })

            case "paragraph":
                inlines = normalize_inlines_spacing(block.get("inlines", []))
                rich_text = inlines_to_rich_text(inlines)
                if rich_text:
                    children.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": rich_text},
                    })

            case "math_block":
                latex = block.get("latex", "").strip()
                if latex:
                    children.append({
                        "object": "block",
                        "type": "equation",
                        "equation": {"expression": latex},
                    })

            case "bullets":
                for item_inlines in block.get("items", []):
                    inlines = normalize_inlines_spacing(item_inlines)
                    rich_text = inlines_to_rich_text(inlines)
                    if rich_text:
                        children.append({
                            "object": "block",
                            "type": "bulleted_list_item",
                            "bulleted_list_item": {"rich_text": rich_text},
                        })

            case "numbered":
                for item_inlines in block.get("items", []):
                    inlines = normalize_inlines_spacing(item_inlines)
                    rich_text = inlines_to_rich_text(inlines)
                    if rich_text:
                        children.append({
                            "object": "block",
                            "type": "numbered_list_item",
                            "numbered_list_item": {"rich_text": rich_text},
                        })

    return children
