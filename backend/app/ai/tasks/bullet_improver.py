"""AI-powered single bullet improvement."""

from __future__ import annotations

import logging
from typing import Any

from app.ai.client import AIService
from app.ai.errors import AIOutputValidationError
from app.ai.prompts.loader import load_prompt
from app.ai.schemas.bullet_output import (
    BulletImprovementOutput,
    find_fabricated_metrics,
)
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

PROMPT_FILE = "bullet_improve_v1.yaml"
PROMPT_VERSION = "bullet_improve_v1"


class BulletPointImprover:
    """Improves resume bullet points without fabricating metrics."""

    def __init__(self, ai_service: AIService) -> None:
        self.ai_service = ai_service

    async def improve(
        self,
        bullet_text: str,
        *,
        resume_context: str | None = None,
        target_role: str | None = None,
        regenerate: bool = False,
        previous_improved_text: str | None = None,
    ) -> dict[str, Any]:
        stripped = bullet_text.strip()
        if not stripped:
            raise AppError(
                "Bullet text cannot be empty.",
                code="bullet_empty",
                status_code=422,
            )

        context = resume_context or ""
        regenerate_instruction = ""
        if regenerate:
            regenerate_instruction = (
                "Provide a DIFFERENT variation from any prior rewrite. "
                "Vary the action verb, sentence structure, or emphasis while staying factual."
            )
            if previous_improved_text:
                regenerate_instruction += (
                    f"\nDo NOT repeat this prior rewrite:\n{previous_improved_text}"
                )

        output, completion = await self._call_ai(
            bullet_text=stripped,
            resume_context=context[:6000],
            target_role=target_role or "Not specified",
            regenerate=regenerate,
            regenerate_instruction=regenerate_instruction,
        )

        fabricated = find_fabricated_metrics(
            stripped,
            output.improved_text,
            resume_context=context,
        )
        if fabricated:
            raise AIOutputValidationError(
                "Improved bullet contained metrics not present in the original. "
                "Please try again."
            )

        return {
            "original_text": stripped,
            "improved_text": output.improved_text,
            "changes_summary": output.changes_summary,
            "metric_placeholder_used": output.metric_placeholder_used,
            "suggested_metric_prompt": output.suggested_metric_prompt,
            "regenerate": regenerate,
            "prompt_version": PROMPT_VERSION,
            "model_used": completion.model_used,
        }

    async def _call_ai(
        self,
        *,
        bullet_text: str,
        resume_context: str,
        target_role: str,
        regenerate: bool,
        regenerate_instruction: str,
    ) -> tuple[BulletImprovementOutput, Any]:
        prompt_data = load_prompt(PROMPT_FILE)
        user_prompt = prompt_data["user_template"].format(
            bullet_text=bullet_text,
            resume_context=resume_context or "No additional context provided.",
            target_role=target_role,
            regenerate=str(regenerate).lower(),
            regenerate_instruction=regenerate_instruction or "None",
        )

        return await self.ai_service.complete_structured(
            prompt=user_prompt,
            system_prompt=prompt_data["system"],
            output_schema=BulletImprovementOutput,
            prompt_version=PROMPT_VERSION,
        )
