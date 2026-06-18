"""Repository for job application documents."""

from beanie import PydanticObjectId

from core.models.job_application import JobApplication

from .base_repository import BeanieRepository


class JobApplicationRepository(BeanieRepository[JobApplication]):
    """Repository for JobApplication documents."""

    def __init__(self) -> None:
        super().__init__(JobApplication)

    async def list_by_user(
        self,
        user_id: PydanticObjectId,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[JobApplication]:
        query: dict[str, object] = {"user_id": user_id}
        if status is not None:
            query["status"] = status
        return (
            await JobApplication.find(query)
            .sort("-updated_at")
            .skip(skip)
            .limit(limit)
            .to_list()
        )

    async def count_by_user(
        self, user_id: PydanticObjectId, *, status: str | None = None
    ) -> int:
        query: dict[str, object] = {"user_id": user_id}
        if status is not None:
            query["status"] = status
        return await JobApplication.find(query).count()
