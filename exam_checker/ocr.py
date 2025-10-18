"""OCR utilities using pytesseract."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List

try:  # pragma: no cover - optional dependency
    from PIL import Image
except Exception:  # pragma: no cover - handled gracefully
    Image = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import pytesseract
except Exception:  # pragma: no cover - handled gracefully
    pytesseract = None  # type: ignore[assignment]


@dataclass
class OCRProcessor:
    """Run OCR over the provided images."""

    language: str = "kor+eng"

    def run(self, column_images: Iterable[Image.Image]) -> List[str]:
        texts: List[str] = []
        for index, image in enumerate(column_images):
            if pytesseract is None:  # pragma: no cover - optional dependency
                raise RuntimeError("pytesseract is required to perform OCR.")
            if Image is None:  # pragma: no cover - optional dependency
                raise RuntimeError("Pillow is required to supply image objects to the OCR engine.")
            logger.debug("Running OCR on column %s", index)
            text = pytesseract.image_to_string(image, lang=self.language)
            texts.append(text.strip())
        return texts
