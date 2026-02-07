"""
Tutor – thin entry point that wires frontend, backend, and pipeline together.
"""

import asyncio
import logging
import os
import tempfile

from openai import AsyncOpenAI
from notion_client import Client as NotionClient
from dotenv import load_dotenv

from backend.orchestrator import PipelineContext, process_pdf
from frontend.launcher import launch
from frontend.slide_selector import select_slides_to_exclude
from backend.notion_client import create_child_page
from backend.pdf_parser import extract_pdf_pages_to_dir
from prompts.system import INSTRUCTION

logger = logging.getLogger(__name__)


async def main_async() -> None:
    """Collect user input, build pipeline context, and run."""
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("notion_client").setLevel(logging.WARNING)

    # ---- GUI: collect inputs ----
    launcher_result = launch()
    if launcher_result is None:
        logger.info("Aborted by user.")
        return

    pdf_path = launcher_result.pdf_path
    course_name = launcher_result.course_name
    model = launcher_result.model
    select_slides = launcher_result.select_slides

    # ---- Resolve env / clients ----
    notion_api_key = os.environ["NOTION_API_KEY"]
    openai_client = AsyncOpenAI()
    notion = NotionClient(auth=notion_api_key)

    # Map course name to page ID
    course_key = f"NOTION_PAGE_{course_name.upper().replace(' ', '_')}"
    page_id = os.environ.get(course_key)
    if not page_id:
        logger.error(
            "No Notion page ID for course '%s'. Add %s=<id> to .env",
            course_name,
            course_key,
        )
        return

    # ---- Slide exclusion (optional) ----
    excluded_pages: set[int] = set()
    if select_slides:
        with tempfile.TemporaryDirectory() as tmpdir:
            image_paths = extract_pdf_pages_to_dir(pdf_path, tmpdir)
            result = select_slides_to_exclude(image_paths)

        if result is None:
            logger.info("Aborted by user.")
            return

        excluded_pages = result
        if excluded_pages:
            logger.info("Excluding slides: %s", sorted(excluded_pages))

    # ---- Create Notion page ----
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    logger.info("Creating new page for: %s", pdf_name)
    child_page_id = create_child_page(notion, page_id, pdf_name)
    logger.info("Created page ID: %s", child_page_id)

    # ---- Stateful OpenAI conversation ----
    conversation = await openai_client.conversations.create()
    logger.info("Conversation ID: %s", conversation.id)

    # ---- Run pipeline ----
    ctx = PipelineContext(
        pdf_path=pdf_path,
        course_name=course_name,
        instruction=INSTRUCTION,
        notion_api_key=notion_api_key,
        notion_page_id=child_page_id,
        conversation_id=conversation.id,
        excluded_pages=excluded_pages,
        model=model,
    )

    await process_pdf(ctx, openai_client)
    logger.info("Success!")


def main() -> None:
    """Entry point – runs the async main function."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()