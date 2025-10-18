"""Configuration objects for the exam checker pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class SystemConfig:
    """Container for user configurable settings.

    Attributes
    ----------
    law_pdf_path:
        Path to the reference law PDF that is used as the ground truth knowledge base.
    exam_pdf_path:
        Path to the exam book that should be validated.
    chunk_size:
        Approximate size (in characters) of each chunk when splitting the law text.
    chunk_overlap:
        Number of characters that should overlap between consecutive chunks. This helps
        keeping context continuity across chunks.
    top_k:
        Number of relevant law chunks to retrieve for every exam page.
    output_directory:
        Directory where intermediate artefacts (such as rendered page images) and
        generated reports will be stored.
    dpi:
        Resolution that will be used when rendering PDF pages to images.
    language:
        Language hint for the OCR engine.
    """

    law_pdf_path: Path
    exam_pdf_path: Path
    output_directory: Path
    chunk_size: int = 1200
    chunk_overlap: int = 200
    top_k: int = 5
    dpi: int = 300
    language: str = "kor+eng"
    keep_debug_images: bool = False
    extra_stopwords: List[str] = field(default_factory=list)

    def ensure_output_dir(self) -> None:
        """Create the output directory if it does not yet exist."""

        self.output_directory.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        """Return a sub-directory that can be used for cached artefacts."""

        cache = self.output_directory / "cache"
        cache.mkdir(parents=True, exist_ok=True)
        return cache
