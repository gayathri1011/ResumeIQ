"""Tests for AI resume optimization."""

from __future__ import annotations

import copy
import json
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.ai.client import AIService
from app.ai.errors import AIOutputValidationError
from app.ai.providers.mock_provider import MockAIProvider, _build_valid_resume_optimize_output
from app.ai.providers.types import CompletionResult
from app.ai.schemas.optimize_output import (
    ResumeOptimizationAIOutput,
    validate_no_fabricated_content,
    validate_structural_facts_preserved,
)
from app.ai.tasks.resume_optimizer import ResumeOptimizer
from app.core.database import get_async_session
from app.main import app
from app.models.enums import ResumeVersionSource, ResumeVersionStatus
from app.repositories import ResumeRepository, ResumeVersionRepository
from tests.test_job_matching import SAMPLE_RESUME_PARSED


def test_resume_optimization_output_schema_validation() -> None:
    output = ResumeOptimizationAIOutput.model_validate(_build_valid_resume_optimize_output())
    assert "skills" in output.optimized_content or output.optimized_content.get("experience")


def test_structural_facts_preserved_detects_title_change() -> None:
    original = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized["experience"][0]["title"] = "Principal Engineer"
    violations = validate_structural_facts_preserved(original, optimized)
    assert any("title" in item for item in violations)


def test_structural_facts_preserved_detects_invented_skill() -> None:
    original = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized["skills"] = ["Python", "SQL", "REST APIs", "Kubernetes"]
    violations = validate_structural_facts_preserved(original, optimized)
    assert any("introduced skill" in item for item in violations)


def test_no_fabrication_guard_detects_fake_metric() -> None:
    original = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized = copy.deepcopy(SAMPLE_RESUME_PARSED)
    optimized["experience"][0]["description"] = (
        "Built backend services with Python, improving throughput by 40%."
    )
    violations = validate_no_fabricated_content(original, optimized)
    assert any("introduced metrics" in item for item in violations)


@pytest.mark.asyncio
async def test_optimizer_rejects_fabricated_metrics(db_session) -> None:
    class FabricatingProvider(MockAIProvider):
        async def complete(self, messages, **kwargs):
            payload = _build_valid_resume_optimize_output(messages)
            payload = dict(payload)
            payload["optimized_content"] = copy.deepcopy(SAMPLE_RESUME_PARSED)
            payload["optimized_content"]["experience"][0]["description"] = (
                "Built backend services with Python, improving throughput by 40%."
            )
            payload["changes"] = [
                {
                    "section": "experience",
                    "field_path": "experience[0].description",
                    "before": SAMPLE_RESUME_PARSED["experience"][0]["description"],
                    "after": payload["optimized_content"]["experience"][0]["description"],
                    "why": "Fabricated metric for test.",
                }
            ]
            return CompletionResult(
                content=json.dumps(payload),
                model_used="fabricate-mock",
                token_usage={"input": 1, "output": 1, "total": 2},
            )

    resume_repo = ResumeRepository(db_session)
    resume = await resume_repo.create(
        title="Optimize Fabrication Test",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="Engineer resume",
    )
    await db_session.flush()

    optimizer = ResumeOptimizer(AIService(provider=FabricatingProvider()), db_session)
    with pytest.raises(AIOutputValidationError):
        await optimizer.optimize(resume.id, target_role="Backend Engineer")


@pytest.mark.asyncio
async def test_optimizer_generates_changes_for_modified_sections(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    resume = await resume_repo.create(
        title="Optimize Changes Test",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="Engineer resume",
    )
    await db_session.flush()

    optimizer = ResumeOptimizer(AIService(provider=MockAIProvider()), db_session)
    result = await optimizer.optimize(resume.id, target_role="Backend Engineer")

    changed_sections = {change["section"] for change in result["changes"]}
    assert "skills" in changed_sections or "experience" in changed_sections
    for change in result["changes"]:
        assert change["why"].strip()
    assert result["optimization_mode"] == "target_role_only"


@pytest.mark.asyncio
async def test_optimizer_target_role_only_without_job(db_session) -> None:
    resume_repo = ResumeRepository(db_session)
    resume = await resume_repo.create(
        title="Optimize Role Only",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="Engineer resume",
    )
    await db_session.flush()

    optimizer = ResumeOptimizer(AIService(provider=MockAIProvider()), db_session)
    result = await optimizer.optimize(resume.id, target_role="Software Engineer")

    assert result["job_description_id"] is None
    assert result["optimization_mode"] == "target_role_only"
    assert result["optimized_content"]["experience"][0]["organization"] == "Tech Co"
    assert result["optimized_content"]["experience"][0]["title"] == "Software Engineer"


@pytest.mark.asyncio
async def test_optimize_endpoint_persists_draft_version(db_session) -> None:
    async def override_session():
        yield db_session

    app.dependency_overrides[get_async_session] = override_session

    resume_repo = ResumeRepository(db_session)
    version_repo = ResumeVersionRepository(db_session)
    resume = await resume_repo.create(
        title="Optimize Endpoint",
        parsed_structure=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="Engineer resume",
    )
    await version_repo.create(
        resume_id=resume.id,
        version_number=1,
        content_snapshot=copy.deepcopy(SAMPLE_RESUME_PARSED),
        raw_text="Engineer resume",
        source=ResumeVersionSource.UPLOAD,
        status=ResumeVersionStatus.ACTIVE,
    )
    await db_session.flush()

    with patch("app.services.optimizer_service.get_ai_service") as mock_get:
        mock_get.return_value = AIService(provider=MockAIProvider())
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/resumes/{resume.id}/optimize",
                json={"target_role": "Backend Engineer"},
            )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "draft"
    assert data["draft_version_id"]
    assert data["changes"]
    assert data["optimized_content"]
    assert data["original_content"]

    live_resume = await resume_repo.get_by_id(resume.id)
    assert live_resume.parsed_structure["experience"][0]["organization"] == "Tech Co"

    draft = await version_repo.get_by_id(data["draft_version_id"])
    assert draft is not None
    assert draft.status == ResumeVersionStatus.DRAFT
    assert draft.source == ResumeVersionSource.OPTIMIZATION
    assert draft.content_snapshot != live_resume.parsed_structure
