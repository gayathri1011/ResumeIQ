"""PDF resume parser using PyMuPDF."""

from __future__ import annotations

from pathlib import Path

import fitz

from app.core.upload_errors import CorruptedFileError, EmptyResumeError
from app.parsers.base import ResumeParser, ParsedDocument
from app.parsers.text_parser import TextLine


class PdfResumeParser(ResumeParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        doc = None
        try:
            doc = fitz.open(file_path)
        except Exception as exc:
            raise CorruptedFileError("The PDF file could not be opened.") from exc

        try:
            if doc.page_count == 0:
                raise EmptyResumeError()

            text_lines: list[TextLine] = []
            for page in doc:
                blocks = page.get_text("dict").get("blocks", [])
                for block in blocks:
                    if block.get("type") != 0:
                        continue
                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        if not spans:
                            continue
                        line_text = "".join(span.get("text", "") for span in spans).strip()
                        if not line_text:
                            continue
                        max_size = max(span.get("size", 0) for span in spans)
                        text_lines.append(TextLine(text=line_text, font_size=max_size))

            if not text_lines:
                raise EmptyResumeError()

            body_sizes = sorted(line.font_size or 0 for line in text_lines if line.font_size)
            median_size = body_sizes[len(body_sizes) // 2] if body_sizes else 11.0
            heading_threshold = median_size + 1.5

            lines = [line.text for line in text_lines]
            heading_flags = [
                (line.font_size or 0) >= heading_threshold for line in text_lines
            ]
            raw_text = "\n".join(lines)

            return self._build_document(raw_text, lines, heading_flags)
        finally:
            if doc is not None:
                doc.close()
