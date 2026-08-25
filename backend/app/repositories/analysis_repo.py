import uuid
from typing import Any

from beanie.operators import In

from app.core.database import MongoSession
from app.models.analysis import AIAnalysisResult, Recommendation, ResumeAnalysis
from app.models.enums import AIResultType, AIServiceName, AnalysisStatus
from app.repositories.base import BaseRepository


class ResumeAnalysisRepository(BaseRepository[ResumeAnalysis]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, ResumeAnalysis)

    async def list_by_resume(
        self,
        resume_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ResumeAnalysis]:
        return (
            await ResumeAnalysis.find(ResumeAnalysis.resume_id == resume_id)
            .sort("-created_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def _list_completed_for_resumes(
        self,
        resume_ids: list[uuid.UUID],
    ) -> list[ResumeAnalysis]:
        return (
            await ResumeAnalysis.find(
                In(ResumeAnalysis.resume_id, resume_ids),
                ResumeAnalysis.status == AnalysisStatus.COMPLETED,
            )
            .sort([("resume_id", 1), ("created_at", -1)])
            .to_list()
        )

    async def get_latest_completed_for_resumes(
        self,
        resume_ids: list[uuid.UUID],
    ) -> dict[uuid.UUID, ResumeAnalysis]:
        if not resume_ids:
            return {}

        latest: dict[uuid.UUID, ResumeAnalysis] = {}
        for analysis in await self._list_completed_for_resumes(resume_ids):
            if analysis.resume_id not in latest:
                latest[analysis.resume_id] = analysis
        return latest

    async def delete_by_resume_version_id(self, version_id: uuid.UUID) -> None:
        await ResumeAnalysis.find(ResumeAnalysis.resume_version_id == version_id).delete()

    async def get_latest_by_resume(self, resume_id: uuid.UUID) -> ResumeAnalysis | None:
        return (
            await ResumeAnalysis.find(ResumeAnalysis.resume_id == resume_id)
            .sort("-created_at")
            .first_or_none()
        )


class RecommendationRepository(BaseRepository[Recommendation]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, Recommendation)

    async def list_by_resume(
        self,
        resume_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Recommendation]:
        return (
            await Recommendation.find(Recommendation.resume_id == resume_id)
            .sort("priority")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def delete_by_job_match_category(self, job_match_id: uuid.UUID, category: str) -> None:
        await Recommendation.find(
            Recommendation.job_match_id == job_match_id,
            Recommendation.category == category,
        ).delete()

    async def delete_by_job_match_ids(self, match_ids: list[uuid.UUID]) -> None:
        if not match_ids:
            return
        await Recommendation.find(In(Recommendation.job_match_id, match_ids)).delete()


class AIAnalysisResultRepository(BaseRepository[AIAnalysisResult]):
    def __init__(self, session: MongoSession) -> None:
        super().__init__(session, AIAnalysisResult)

    async def get_by_input_hash(self, input_hash: str) -> AIAnalysisResult | None:
        return await AIAnalysisResult.find_one(AIAnalysisResult.input_hash == input_hash)

    async def get_by_input_hash_and_service(
        self,
        input_hash: str,
        service_name: Any,
    ) -> AIAnalysisResult | None:
        return (
            await AIAnalysisResult.find(
                AIAnalysisResult.input_hash == input_hash,
                AIAnalysisResult.service_name == service_name,
            )
            .sort("-created_at")
            .first_or_none()
        )

    async def get_latest_optimization_for_resume(
        self,
        resume_id: uuid.UUID,
    ) -> AIAnalysisResult | None:
        return (
            await AIAnalysisResult.find(
                AIAnalysisResult.resume_id == resume_id,
                AIAnalysisResult.service_name == AIServiceName.RESUME_OPTIMIZER,
                AIAnalysisResult.result_type == AIResultType.OPTIMIZATION,
            )
            .sort("-created_at")
            .first_or_none()
        )

    async def get_by_resume_analysis_id(self, analysis_id: uuid.UUID) -> AIAnalysisResult | None:
        return await AIAnalysisResult.find_one(
            AIAnalysisResult.resume_analysis_id == analysis_id
        )

    async def get_by_resume_analysis_ids(
        self, analysis_ids: list[uuid.UUID]
    ) -> list[AIAnalysisResult]:
        if not analysis_ids:
            return []
        return await AIAnalysisResult.find(
            In(AIAnalysisResult.resume_analysis_id, analysis_ids)
        ).to_list()

    async def delete_by_resume_version_id(self, version_id: uuid.UUID) -> None:
        await AIAnalysisResult.find(AIAnalysisResult.resume_version_id == version_id).delete()
