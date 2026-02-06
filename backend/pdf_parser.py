"""
PDF parsing – extract pages as images.
"""

import os
from typing import Generator

import fitz  # PyMuPDF

from config import PDF_ZOOM


def extract_pdf_pages_as_images(
    pdf_path: str,
    zoom: float = PDF_ZOOM,
) -> Generator[str, None, None]:
    """
    Yield temporary image paths for each page in a PDF.

    Images are saved to a temp directory and cleaned up after iteration.
    """
    import tempfile

    doc = fitz.open(pdf_path)
    matrix = fitz.Matrix(zoom, zoom)

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix)
            image_path = os.path.join(tmpdir, f"page_{i + 1}.jpg")
            pix.save(image_path)
            yield image_path

    doc.close()


def get_pdf_page_count(pdf_path: str) -> int:
    """Return the number of pages in a PDF."""
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def extract_pdf_pages_to_dir(
    pdf_path: str,
    output_dir: str,
    zoom: float = PDF_ZOOM,
) -> list[str]:
    """
    Extract all PDF pages as images into *output_dir*.

    Returns a list of image paths. Caller is responsible for cleanup.
    """
    doc = fitz.open(pdf_path)
    matrix = fitz.Matrix(zoom, zoom)
    image_paths: list[str] = []

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        image_path = os.path.join(output_dir, f"page_{i + 1}.jpg")
        pix.save(image_path)
        image_paths.append(image_path)

    doc.close()
    return image_paths
