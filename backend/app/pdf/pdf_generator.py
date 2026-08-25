"""Convert resume HTML into a PDF byte stream."""

from __future__ import annotations

import io
from typing import Any

import pymupdf as fitz

from app.core.exceptions import AppError
from app.pdf.html_renderer import render_resume_html

# US Letter with 0.75" margins — content stays in the body, not headers/footers.
_PAGE_RECT = fitz.paper_rect("letter")
_CONTENT_RECT = _PAGE_RECT + (54, 54, -54, -54)


def generate_resume_pdf(content: dict[str, Any]) -> bytes:
    """Deterministically render stored resume content to PDF bytes."""
    try:
        html = render_resume_html(content)
        story = fitz.Story(html=html)
        buffer = io.BytesIO()
        writer = fitz.DocumentWriter(buffer)

        more = True
        while more:
            device = writer.begin_page(_PAGE_RECT)
            more, _ = story.place(_CONTENT_RECT)
            story.draw(device)
            writer.end_page()

        writer.close()
        pdf_bytes = buffer.getvalue()
    except AppError:
        raise
    except Exception as exc:
        raise AppError(
            "Failed to generate resume PDF.",
            code="pdf_generation_failed",
            status_code=500,
        ) from exc

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF"):
        raise AppError(
            "PDF generation produced an invalid document.",
            code="pdf_generation_failed",
            status_code=500,
        )

    return pdf_bytes
