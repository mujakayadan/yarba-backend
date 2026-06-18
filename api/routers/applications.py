"""Job application tracking and autofill API."""

from typing import Annotated

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.dependencies.auth import require_scopes
from api.dependencies.services import (
    get_application_profile_service,
    get_job_application_service,
)
from api.schemas.application import (
    ApplicationPrepareRequest,
    ApplicationPrepareResponse,
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    PaginatedJobApplicationResponse,
)
from config.logging_config import get_logger
from core.exceptions.base import NotFoundException
from core.models.job_application import JobApplication
from core.models.user import AuthenticatedUser
from core.schemas.application_schemas import ApplicationProfile
from core.services.application_profile_service import ApplicationProfileService
from core.services.job_application_service import JobApplicationService
from core.utils.object_id import require_object_id

router = APIRouter()
logger = get_logger(__name__)


def _scopes_from_request(request: Request) -> set[str] | None:
    token_type = getattr(request.state, "auth_token_type", "jwt")
    if token_type != "pat":
        return None
    raw = getattr(request.state, "auth_scopes", None)
    return set(raw) if raw else set()


def _to_response(record: JobApplication) -> JobApplicationResponse:
    return JobApplicationResponse(
        id=str(record.id),
        job_url=record.job_url,
        company_name=record.company_name,
        job_title=record.job_title,
        platform=record.platform,
        resume_id=str(record.resume_id) if record.resume_id else None,
        cover_letter_id=str(record.cover_letter_id) if record.cover_letter_id else None,
        status=record.status,
        submitted_at=record.submitted_at,
        error_message=record.error_message,
        metadata=record.metadata,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.get(
    "/profile",
    response_model=ApplicationProfile,
    summary="Build autofill payload for a resume",
)
async def get_application_profile(
    current_user: Annotated[
        AuthenticatedUser,
        Depends(
            require_scopes(
                "applications:read",
                "resumes:read",
                "profiles:read",
            )
        ),
    ],
    request: Request,
    resume_id: Annotated[str, Query(description="Resume ID")],
    cover_letter_id: Annotated[str | None, Query()] = None,
    job_url: Annotated[str | None, Query()] = None,
    profile_service: ApplicationProfileService = Depends(
        get_application_profile_service
    ),
) -> ApplicationProfile:
    try:
        return await profile_service.build(
            user_id=require_object_id(current_user.id),
            resume_id=PydanticObjectId(resume_id),
            cover_letter_id=PydanticObjectId(cover_letter_id)
            if cover_letter_id
            else None,
            job_url=job_url,
            scopes=_scopes_from_request(request),
        )
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc


@router.post(
    "/prepare",
    response_model=ApplicationPrepareResponse,
    status_code=status.HTTP_201_CREATED,
)
async def prepare_application(
    body: ApplicationPrepareRequest,
    request: Request,
    current_user: Annotated[
        AuthenticatedUser,
        Depends(
            require_scopes(
                "applications:write",
                "resumes:write",
                "jobs:extract",
            )
        ),
    ],
    application_service: JobApplicationService = Depends(get_job_application_service),
) -> ApplicationPrepareResponse:
    if not body.job_url and not body.job_description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_url or job_description is required",
        )
    try:
        application, app_profile, resume = await application_service.prepare(
            user_id=require_object_id(current_user.id),
            job_url=body.job_url,
            job_description=body.job_description,
            compile_pdf=body.compile_pdf,
            generate_cover_letter=body.generate_cover_letter,
            scopes=_scopes_from_request(request),
        )
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return ApplicationPrepareResponse(
        application_id=str(application.id),
        resume_id=str(resume.id),
        application_profile=app_profile,
    )


@router.post(
    "", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED
)
async def create_application(
    body: JobApplicationCreate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_scopes("applications:write"))
    ],
    application_service: JobApplicationService = Depends(get_job_application_service),
) -> JobApplicationResponse:
    try:
        record = await application_service.create(
            user_id=require_object_id(current_user.id),
            job_url=body.job_url,
            company_name=body.company_name,
            job_title=body.job_title,
            resume_id=PydanticObjectId(body.resume_id) if body.resume_id else None,
            cover_letter_id=PydanticObjectId(body.cover_letter_id)
            if body.cover_letter_id
            else None,
            status=body.status,
            metadata=body.metadata,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _to_response(record)


@router.get("", response_model=PaginatedJobApplicationResponse)
async def list_applications(
    current_user: Annotated[
        AuthenticatedUser, Depends(require_scopes("applications:read"))
    ],
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    application_service: JobApplicationService = Depends(get_job_application_service),
) -> PaginatedJobApplicationResponse:
    items, total = await application_service.list(
        require_object_id(current_user.id),
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return PaginatedJobApplicationResponse(
        items=[_to_response(item) for item in items],
        total=total,
    )


@router.get("/{application_id}", response_model=JobApplicationResponse)
async def get_application(
    application_id: str,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_scopes("applications:read"))
    ],
    application_service: JobApplicationService = Depends(get_job_application_service),
) -> JobApplicationResponse:
    try:
        record = await application_service.get(
            PydanticObjectId(application_id), require_object_id(current_user.id)
        )
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    return _to_response(record)


@router.patch("/{application_id}", response_model=JobApplicationResponse)
async def update_application(
    application_id: str,
    body: JobApplicationUpdate,
    current_user: Annotated[
        AuthenticatedUser, Depends(require_scopes("applications:write"))
    ],
    application_service: JobApplicationService = Depends(get_job_application_service),
) -> JobApplicationResponse:
    try:
        record = await application_service.update_status(
            PydanticObjectId(application_id),
            require_object_id(current_user.id),
            status=body.status,
            error_message=body.error_message,
            metadata=body.metadata,
        )
    except NotFoundException as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return _to_response(record)
