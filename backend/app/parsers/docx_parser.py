"""DOCX resume parser using python-docx."""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.core.upload_errors import CorruptedFileError, EmptyResumeError
from app.parsers.base import ResumeParser, ParsedDocument
from app.parsers.text_parser import TextLine


class DocxResumeParser(ResumeParser):
    def parse(self, file_path: Path) -> ParsedDocument:
        try:
            document = Document(file_path)
        except Exception as exc:
            raise CorruptedFileError("The DOCX file could not be opened.") from exc

        text_lines: list[TextLine] = []
        for paragraph in document.paragraphs:
            line_text = paragraph.text.strip()
            if not line_text:
                continue

            style_name = paragraph.style.name.lower() if paragraph.style else ""
            is_heading = style_name.startswith("heading") or (
                paragraph.runs and all(run.bold for run in paragraph.runs if run.text.strip())
                and len(line_text) < 80
            )
            text_lines.append(TextLine(text=line_text, is_heading=is_heading))

        if not text_lines:
            raise EmptyResumeError()

        lines = [line.text for line in text_lines]
        heading_flags = [line.is_heading for line in text_lines]
        raw_text = "\n".join(lines)

        return self._build_document(raw_text, lines, heading_flags)
