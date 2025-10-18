"""PDF related helper classes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

try:  # pragma: no cover - optional dependency
    from PIL import Image
except Exception:  # pragma: no cover - handled gracefully
    Image = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from pdf2image import convert_from_path
except Exception:  # pragma: no cover - handled gracefully
    convert_from_path = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from pdfminer.high_level import extract_text as pdfminer_extract_text
except Exception:  # pragma: no cover - handled gracefully
    pdfminer_extract_text = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from PyPDF2 import PdfReader
except Exception:  # pragma: no cover - handled gracefully
    PdfReader = None  # type: ignore[assignment]


@dataclass
class PDFPageTextExtractor:
    """Extract plain text for each page of a PDF file."""

    def extract(self, pdf_path: Path) -> List[str]:
        logger.info("Extracting text from %s", pdf_path)
        if pdfminer_extract_text:
            text = pdfminer_extract_text(str(pdf_path))
            pages = text.split("\f")
            return [page.strip() for page in pages if page.strip()]
        if PdfReader is None:
            raise RuntimeError(
                "Neither pdfminer.six nor PyPDF2 is installed. Install one of them to extract text."
            )
        reader = PdfReader(str(pdf_path))
        pages: List[str] = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return pages


@dataclass
class PDFPageImageConverter:
    """Render each PDF page to an image using pdf2image."""

    dpi: int = 300

    def convert(self, pdf_path: Path) -> Iterable[Image.Image]:
        if Image is None:  # pragma: no cover - optional dependency
            raise RuntimeError("Pillow is required to render PDF pages to images.")
        if convert_from_path is None:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "pdf2image is required to render PDF pages to images. Install pdf2image and poppler."
            )
        logger.info("Rendering %s into images at %s dpi", pdf_path, self.dpi)
        images = convert_from_path(str(pdf_path), dpi=self.dpi)
        for image in images:
            yield image
