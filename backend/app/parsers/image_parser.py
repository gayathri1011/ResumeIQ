"""Image resume parser using RapidOCR (PNG/JPG/JPEG/WEBP)."""

from __future__ import annotations

from pathlib import Path

from app.core.upload_errors import CorruptedFileError, EmptyResumeError, ExtractionFailedError
from app.parsers.base import ParsedDocument, ResumeParser
from app.parsers.text_parser import normalize_lines


def _ocr_image(file_path: Path) -> str:
    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise ExtractionFailedError(
            "Image resume support is not installed on the server. "
            "Please upload a PDF, DOCX, or contact support.",
        ) from exc

    try:
        engine = RapidOCR()
        result, _ = engine(str(file_path))
    except Exception as exc:
        raise CorruptedFileError(
            "The image could not be read. Please upload a clear PNG, JPG, or WEBP resume.",
        ) from exc

    if not result:
        return ""

    # RapidOCR returns rows of [box, text, confidence]
    lines: list[str] = []
    for row in result:
        if not row or len(row) < 2:
            continue
        text = str(row[1]).strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


class ImageResumeParser(ResumeParser):
    """Extract resume text from scanned or photographed resume images."""

    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            raw_text = _ocr_image(file_path)
        except (CorruptedFileError, EmptyResumeError, ExtractionFailedError):
            raise
        except Exception as exc:
            raise CorruptedFileError(
                "The image resume could not be processed.",
            ) from exc

        if not raw_text.strip():
            raise EmptyResumeError(
                "No readable text found in this image. "
                "Try a clearer photo or upload a PDF/DOCX instead.",
            )

        lines = normalize_lines(raw_text)
        # Image OCR has no font sizes; treat short ALL-CAPS lines as headings.
        heading_flags = [
            bool(line.isupper() and 2 <= len(line.split()) <= 6) for line in lines
        ]
        return self._build_document(raw_text, lines, heading_flags)
