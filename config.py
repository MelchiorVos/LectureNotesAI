"""
Centralized configuration for the Tutor application.

All settings, model names, API defaults, and constants live here.
"""

import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Set

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = ROOT_DIR / "prompts"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger for the whole application."""
    logging.basicConfig(format=LOG_FORMAT, level=level)
    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("notion_client").setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# OpenAI model
# ---------------------------------------------------------------------------

OPENAI_MODEL = "gpt-5.2"

# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

PDF_ZOOM = 2.0

# ---------------------------------------------------------------------------
# Notion
# ---------------------------------------------------------------------------

NOTION_CHUNK_SIZE = 50

# ---------------------------------------------------------------------------
# Retry policy
# ---------------------------------------------------------------------------

RETRY_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 2  # base for exponential back-off

# ---------------------------------------------------------------------------
# AST type alias
# ---------------------------------------------------------------------------

from typing import Any, Dict

ASTNode = Dict[str, Any]

# ---------------------------------------------------------------------------
# Pipeline context
# ---------------------------------------------------------------------------


@dataclass
class PipelineContext:
    """Bundles all runtime state needed by the processing pipeline."""

    pdf_path: str
    course_name: str
    instruction: str
    notion_api_key: str
    notion_page_id: str
    conversation_id: str
    excluded_pages: Set[int] = field(default_factory=set)
    model: str = OPENAI_MODEL


# ---------------------------------------------------------------------------
# Environment helpers
# ---------------------------------------------------------------------------


def load_env() -> None:
    """Load .env once at startup."""
    load_dotenv()


def get_notion_api_key() -> str:
    return os.environ["NOTION_API_KEY"]


def get_notion_page_id(course_name: str) -> str | None:
    """Map a human-readable course name to its NOTION_PAGE_ env var."""
    key = f"NOTION_PAGE_{course_name.upper().replace(' ', '_')}"
    return os.environ.get(key)


def discover_courses() -> list[str]:
    """Return sorted course names derived from NOTION_PAGE_* env vars."""
    courses = []
    for key in os.environ:
        if key.startswith("NOTION_PAGE_"):
            name = key.removeprefix("NOTION_PAGE_").replace("_", " ").title()
            courses.append(name)
    return sorted(courses)
