"""Resume file parsers — PDF, DOCX, and image extraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.core.upload_errors import CorruptedFileError, EmptyResumeError, ExtractionFailedError
from app.parsers.schema import ParsedResumeStructure
from app.parsers.text_parser import (
    SectionBlock,
    build_structured_resume,
    normalize_lines,
    split_into_sections,
)


@dataclass
class ParsedDocument:
    raw_text: str
    structured: ParsedResumeStructure
    metadata: dict[str, str] = field(default_factory=dict)


class ResumeParser(ABC):
    """Format-specific resume parser interface."""

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        """Extract raw text and structured content from a resume file."""

    def _build_document(self, raw_text: str, lines: list[str], heading_flags: list[bool]) -> ParsedDocument:
        if not raw_text.strip():
            raise EmptyResumeError()

        blocks = split_into_sections(lines, heading_flags)
        structured = build_structured_resume(blocks)

        if not blocks:
            raise ExtractionFailedError()

        return ParsedDocument(raw_text=raw_text.strip(), structured=structured)
