"""Structured resume schema produced by deterministic parsers."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ParsedResumeMeta(BaseModel):
    file_size_bytes: int | None = None
    sections_found: list[str] = Field(default_factory=list)
    sections_missing: list[str] = Field(default_factory=list)
    parser_version: str = "1.0"


class ParsedResumeStructure(BaseModel):
    personal_information: dict[str, Any] | None = None
    professional_summary: str | None = None
    education: list[dict[str, Any]] | None = None
    experience: list[dict[str, Any]] | None = None
    projects: list[dict[str, Any]] | None = None
    skills: list[str] | None = None
    certifications: list[dict[str, Any]] | None = None
    achievements: list[str] | None = None
    links: list[dict[str, str]] | None = None
    meta: ParsedResumeMeta = Field(default_factory=ParsedResumeMeta, alias="_meta")

    model_config = {"populate_by_name": True}

    def to_storage_dict(self) -> dict[str, Any]:
        data = self.model_dump(by_alias=True)
        return data

    @classmethod
    def empty(cls) -> ParsedResumeStructure:
        all_sections = [
            "personal_information",
            "professional_summary",
            "education",
            "experience",
            "projects",
            "skills",
            "certifications",
            "achievements",
            "links",
        ]
        return cls(
            meta=ParsedResumeMeta(sections_found=[], sections_missing=all_sections),
        )


CANONICAL_SECTIONS = [
    "personal_information",
    "professional_summary",
    "education",
    "experience",
    "projects",
    "skills",
    "certifications",
    "achievements",
    "links",
]
