"""Column detection utilities for multi-column pages."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable, List, Tuple

try:  # pragma: no cover - optional dependency
    import numpy as np
except Exception:  # pragma: no cover - handled gracefully
    np = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from PIL import Image
except Exception:  # pragma: no cover - handled gracefully
    Image = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import cv2
except Exception:  # pragma: no cover - handled gracefully
    cv2 = None  # type: ignore[assignment]


@dataclass
class ColumnRegion:
    """Represents a detected column inside a page image."""

    bounds: Tuple[int, int, int, int]
    index: int

    @property
    def box(self) -> Tuple[int, int, int, int]:
        return self.bounds


class ColumnDetector:
    """Detect columns in a page using OpenCV."""

    def __init__(self, min_column_width: int = 200):
        self.min_column_width = min_column_width

    def detect(self, image: Image.Image) -> List[ColumnRegion]:
        if Image is None:  # pragma: no cover - optional dependency
            raise RuntimeError("Pillow is required for column detection.")
        if cv2 is None:  # pragma: no cover - optional dependency
            logger.warning("OpenCV is not installed, returning a single column covering the full page.")
            width, height = image.size
            return [ColumnRegion(bounds=(0, 0, width, height), index=0)]

        if np is None:  # pragma: no cover - optional dependency
            raise RuntimeError("NumPy is required for column detection when OpenCV is available.")
        gray = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))
        detected = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
        contours, _ = cv2.findContours(detected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        columns: List[ColumnRegion] = []
        width = image.width
        height = image.height
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w < self.min_column_width or h < height * 0.3:
                continue
            columns.append(ColumnRegion(bounds=(x, y, x + w, y + h), index=len(columns)))

        if not columns:
            logger.info("Falling back to heuristic equal-width columns.")
            columns = self._fallback_columns(width, height)
        else:
            columns.sort(key=lambda column: column.bounds[0])
        return columns

    def _fallback_columns(self, width: int, height: int, num_columns: int = 2) -> List[ColumnRegion]:
        column_width = width // num_columns
        columns: List[ColumnRegion] = []
        for index in range(num_columns):
            x0 = index * column_width
            x1 = width if index == num_columns - 1 else (index + 1) * column_width
            columns.append(ColumnRegion(bounds=(x0, 0, x1, height), index=index))
        return columns

    def split_columns(self, image: Image.Image, columns: Iterable[ColumnRegion]) -> List[Image.Image]:
        if Image is None:  # pragma: no cover - optional dependency
            raise RuntimeError("Pillow is required for column slicing.")
        slices: List[Image.Image] = []
        for column in columns:
            x0, y0, x1, y1 = column.bounds
            cropped = image.crop((x0, y0, x1, y1))
            slices.append(cropped)
        return slices
