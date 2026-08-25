"""Dispatch resume parsing to the correct format-specific parser."""

from __future__ import annotations

from pathlib import Path

from app.core.upload_errors import InvalidFileTypeError
from app.parsers.base import ParsedDocument, ResumeParser
from app.parsers.docx_parser import DocxResumeParser
from app.parsers.image_parser import ImageResumeParser
from app.parsers.pdf_parser import PdfResumeParser

MIME_TO_PARSER: dict[str, type[ResumeParser]] = {
    "application/pdf": PdfResumeParser,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxResumeParser,
    "image/png": ImageResumeParser,
    "image/jpeg": ImageResumeParser,
    "image/jpg": ImageResumeParser,
    "image/webp": ImageResumeParser,
    "image/gif": ImageResumeParser,
}

EXTENSION_TO_PARSER: dict[str, type[ResumeParser]] = {
    ".pdf": PdfResumeParser,
    ".docx": DocxResumeParser,
    ".png": ImageResumeParser,
    ".jpg": ImageResumeParser,
    ".jpeg": ImageResumeParser,
    ".webp": ImageResumeParser,
    ".gif": ImageResumeParser,
}


def get_parser_for_file(filename: str, mime_type: str | None) -> ResumeParser:
    ext = Path(filename).suffix.lower()
    parser_cls = EXTENSION_TO_PARSER.get(ext)

    if parser_cls is None and mime_type:
        parser_cls = MIME_TO_PARSER.get(mime_type.lower())

    if parser_cls is None:
        raise InvalidFileTypeError()

    return parser_cls()


def parse_resume_file(file_path: Path, filename: str, mime_type: str | None) -> ParsedDocument:
    parser = get_parser_for_file(filename, mime_type)
    return parser.parse(file_path)
