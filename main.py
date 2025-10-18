"""Command line entry point for the exam checker pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Iterable, List

from exam_checker import (
    ColumnDetector,
    KnowledgeBaseBuilder,
    OCRProcessor,
    PDFPageImageConverter,
    PDFPageTextExtractor,
    RAGPipeline,
    ReportFormatter,
    SystemConfig,
)
from exam_checker.knowledge_base import KnowledgeBase, persist_knowledge_base
from exam_checker.report import PageReport

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class Pipeline:
    """High level orchestrator that wires together all building blocks."""

    def __init__(self, config: SystemConfig):
        self.config = config
        self.text_extractor = PDFPageTextExtractor()
        self.image_converter = PDFPageImageConverter(dpi=config.dpi)
        self.column_detector = ColumnDetector()
        self.ocr = OCRProcessor(language=config.language)
        self.report_formatter = ReportFormatter()
        self.knowledge_base: KnowledgeBase | None = None

    def build_knowledge_base(self) -> KnowledgeBase:
        logger.info("Building knowledge base from %s", self.config.law_pdf_path)
        pages = self.text_extractor.extract(self.config.law_pdf_path)
        builder = KnowledgeBaseBuilder(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            stopwords=self.config.extra_stopwords,
        )
        knowledge_base = builder.build_from_pages(pages)
        persist_knowledge_base(knowledge_base, self.config.cache_dir)
        self.knowledge_base = knowledge_base
        return knowledge_base

    def load_or_build_knowledge_base(self) -> KnowledgeBase:
        cache_path = self.config.cache_dir / "knowledge_base.json"
        if cache_path.exists():
            logger.info("Loading cached knowledge base from %s", cache_path)
            self.knowledge_base = KnowledgeBase.load(cache_path)
            return self.knowledge_base
        return self.build_knowledge_base()

    def process_exam(self) -> ReportFormatter:
        self.config.ensure_output_dir()
        knowledge_base = self.load_or_build_knowledge_base()
        rag_pipeline = RAGPipeline(config=self.config, knowledge_base=knowledge_base)

        logger.info("Starting inspection of %s", self.config.exam_pdf_path)
        page_texts = self._extract_page_texts()

        for page_number, page_text in enumerate(page_texts, start=1):
            logger.debug("Processing page %s", page_number)
            page_report = rag_pipeline.generate_page_report(page_text)
            self.report_formatter.add_page_report(PageReport(page_number=page_number, content=page_report))

        markdown_output = self.config.output_directory / "inspection_report.md"
        json_output = self.config.output_directory / "inspection_report.json"
        self.report_formatter.save_markdown(markdown_output)
        self.report_formatter.save_json(json_output)
        logger.info("Reports saved to %s and %s", markdown_output, json_output)
        return self.report_formatter

    def _extract_page_texts(self) -> List[str]:
        pdf_text_pages = self.text_extractor.extract(self.config.exam_pdf_path)
        try:
            images = list(self.image_converter.convert(self.config.exam_pdf_path))
        except Exception as error:
            logger.warning("Failed to render exam PDF to images: %s. Falling back to text extraction only.", error)
            return pdf_text_pages

        page_texts: List[str] = []
        for page_index, (image, fallback_text) in enumerate(zip(images, pdf_text_pages), start=1):
            if self.config.keep_debug_images:
                debug_path = self.config.output_directory / f"page_{page_index:04d}.png"
                image.save(debug_path)
            columns = self.column_detector.detect(image)
            column_images = self.column_detector.split_columns(image, columns)
            try:
                column_texts = self.ocr.run(column_images)
                page_text = "\n\n".join(text for text in column_texts if text).strip()
            except Exception as error:
                logger.warning("OCR failed on page %s: %s. Using fallback text extracted directly from the PDF.", page_index, error)
                page_text = fallback_text
            if not page_text:
                page_text = fallback_text
            page_texts.append(page_text)

        if len(images) > len(pdf_text_pages):
            logger.info(
                "Rendered %s pages but only %s text pages were extracted. Remaining pages will rely solely on OCR results.",
                len(images),
                len(pdf_text_pages),
            )
            for extra_index, image in enumerate(images[len(pdf_text_pages):], start=len(pdf_text_pages) + 1):
                if self.config.keep_debug_images:
                    debug_path = self.config.output_directory / f"page_{extra_index:04d}.png"
                    image.save(debug_path)
                columns = self.column_detector.detect(image)
                column_images = self.column_detector.split_columns(image, columns)
                try:
                    column_texts = self.ocr.run(column_images)
                    page_text = "\n\n".join(text for text in column_texts if text).strip()
                except Exception as error:
                    logger.warning(
                        "OCR failed on extra page %s: %s. The resulting text will be empty for this page.",
                        extra_index,
                        error,
                    )
                    page_text = ""
                page_texts.append(page_text)

        if len(images) < len(pdf_text_pages):
            logger.info(
                "Only %s pages could be rendered to images out of %s total pages. Remaining pages will use fallback text.",
                len(images),
                len(pdf_text_pages),
            )
            page_texts.extend(pdf_text_pages[len(images):])
        return page_texts


def parse_args(args: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="다단 편집 수험서 자동 검수 프로그램")
    parser.add_argument("law_pdf", type=Path, help="법령 PDF 파일 경로")
    parser.add_argument("exam_pdf", type=Path, help="검수할 수험서 PDF 파일 경로")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="보고서를 저장할 출력 디렉터리",
    )
    parser.add_argument("--dpi", type=int, default=300, help="PDF 페이지를 렌더링할 해상도")
    parser.add_argument("--top-k", type=int, default=5, help="검색할 법령 청크 개수")
    parser.add_argument("--chunk-size", type=int, default=1200, help="법령 텍스트 분할 크기")
    parser.add_argument("--chunk-overlap", type=int, default=200, help="법령 청크 간 오버랩 크기")
    parser.add_argument("--language", type=str, default="kor+eng", help="OCR 언어 설정")
    parser.add_argument(
        "--stopwords",
        type=str,
        nargs="*",
        default=[],
        help="추가로 제거할 불용어 목록",
    )
    return parser.parse_args(args=args)


def main(argv: Iterable[str] | None = None) -> None:
    arguments = parse_args(argv)
    config = SystemConfig(
        law_pdf_path=arguments.law_pdf,
        exam_pdf_path=arguments.exam_pdf,
        output_directory=arguments.output,
        dpi=arguments.dpi,
        top_k=arguments.top_k,
        chunk_size=arguments.chunk_size,
        chunk_overlap=arguments.chunk_overlap,
        language=arguments.language,
        extra_stopwords=arguments.stopwords,
    )
    pipeline = Pipeline(config)
    pipeline.process_exam()


if __name__ == "__main__":
    main()
