# """LinkedIn integration router."""

# from datetime import datetime
# from typing import Any, Dict, List, Optional

# from beanie import PydanticObjectId
# from fastapi import APIRouter, Depends, HTTPException, status
# from pydantic import BaseModel, EmailStr, Field

# from api.dependencies.auth import get_current_active_user
# from config.logging_config import get_logger
# from core.exceptions.base import NotFoundException, OperationFailedException
# from core.models.user import User
# from core.services.linkedin_service import LinkedInService

# router = APIRouter()
# logger = get_logger(__name__)


# class LinkedInCredentialsRequest(BaseModel):
#     """Request model for LinkedIn credentials."""

#     email: EmailStr = Field(..., description="LinkedIn email address")
#     password: str = Field(..., description="LinkedIn password")


# class LinkedInStatusResponse(BaseModel):
#     """Response model for LinkedIn integration status."""

#     enabled: bool = Field(..., description="Whether LinkedIn integration is enabled")
#     email: Optional[EmailStr] = Field(None, description="LinkedIn email if available")
#     last_login: Optional[datetime] = Field(None, description="Last LinkedIn login time")


# class LinkedInJobSearchRequest(BaseModel):
#     """Request model for LinkedIn job search."""

#     keywords: str = Field(..., description="Job search keywords")
#     location: str = Field(..., description="Job search location")
#     num_jobs: int = Field(10, description="Number of jobs to search for")


# class LinkedInJobApplicationRequest(BaseModel):
#     """Request model for LinkedIn job application."""

#     job_urls: List[str] = Field(..., description="LinkedIn job URLs to apply for")
#     resume_id: str = Field(..., description="Resume ID to use for applications")


# class LinkedInSingleJobApplicationRequest(BaseModel):
#     """Request model for single LinkedIn job application."""

#     job_url: str = Field(..., description="LinkedIn job URL to apply for")
#     resume_id: str = Field(..., description="Resume ID to use for application")


# @router.post("/credentials", status_code=status.HTTP_200_OK)
# async def save_linkedin_credentials(
#     request: LinkedInCredentialsRequest,
#     current_user: CurrentActiveUser,
# ) -> Dict[str, str]:
#     """Save LinkedIn credentials for the current user.

#     Args:
#         request: LinkedIn credentials request
#         current_user: Current authenticated user

#     Returns:
#         dict: Success message
#     """
#     linkedin_service = LinkedInService()
#     success = await linkedin_service.save_credentials(
#         current_user, request.email, request.password
#     )

#     if not success:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Failed to save LinkedIn credentials",
#         )

#     return {"message": "LinkedIn credentials saved successfully"}


# @router.get("/status", response_model=LinkedInStatusResponse)
# async def get_linkedin_status(
#     current_user: CurrentActiveUser,
# ) -> LinkedInStatusResponse:
#     """Get LinkedIn integration status for the current user.

#     Args:
#         current_user: Current authenticated user

#     Returns:
#         LinkedInStatusResponse: LinkedIn integration status
#     """
#     return LinkedInStatusResponse(
#         enabled=current_user.linkedin_integration_enabled,
#         email=current_user.linkedin_email,
#         last_login=current_user.linkedin_last_login,
#     )


# @router.post("/search", status_code=status.HTTP_200_OK)
# async def search_linkedin_jobs(
#     request: LinkedInJobSearchRequest,
#     current_user: CurrentActiveUser,
# ) -> List[Dict[str, Any]]:
#     """Search for jobs on LinkedIn using the current user's credentials.

#     Args:
#         request: LinkedIn job search request
#         current_user: Current authenticated user

#     Returns:
#         List of job descriptions
#     """
#     if not current_user.linkedin_integration_enabled:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="LinkedIn integration not enabled for this user",
#         )

#     linkedin_service = LinkedInService()

#     try:
#         jobs = await linkedin_service.search_jobs(
#             current_user, request.keywords, request.location, request.num_jobs
#         )
#         return jobs
#     except OperationFailedException as e:
#         logger.error(f"Error searching for LinkedIn jobs: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to search for LinkedIn jobs: {str(e)}",
#         )
#     finally:
#         linkedin_service.close()


# @router.post("/apply", status_code=status.HTTP_200_OK)
# async def apply_for_linkedin_jobs(
#     request: LinkedInJobApplicationRequest,
#     current_user: CurrentActiveUser,
# ) -> Dict[str, Any]:
#     """Apply for jobs on LinkedIn using the current user's credentials.

#     Args:
#         request: LinkedIn job application request
#         current_user: Current authenticated user

#     Returns:
#         dict: Application results
#     """
#     if not current_user.linkedin_integration_enabled:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="LinkedIn integration not enabled for this user",
#         )

#     # Validate resume_id is a valid ObjectId
#     try:
#         resume_id = PydanticObjectId(request.resume_id)
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resume ID format"
#         )

#     linkedin_service = LinkedInService()

#     try:
#         results = await linkedin_service.apply_for_jobs(
#             current_user, request.job_urls, resume_id
#         )
#         return results
#     except NotFoundException as e:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e),
#         )
#     except OperationFailedException as e:
#         logger.error(f"Error applying for LinkedIn jobs: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to apply for LinkedIn jobs: {str(e)}",
#         )
#     finally:
#         linkedin_service.close()


# @router.post("/apply/single", status_code=status.HTTP_200_OK)
# async def apply_for_single_linkedin_job(
#     request: LinkedInSingleJobApplicationRequest,
#     current_user: CurrentActiveUser,
# ) -> Dict[str, Any]:
#     """Apply for a single job on LinkedIn using the current user's credentials.

#     Args:
#         request: LinkedIn single job application request
#         current_user: Current authenticated user

#     Returns:
#         dict: Application result
#     """
#     if not current_user.linkedin_integration_enabled:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="LinkedIn integration not enabled for this user",
#         )

#     # Validate resume_id is a valid ObjectId
#     try:
#         resume_id = PydanticObjectId(request.resume_id)
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid resume ID format"
#         )

#     linkedin_service = LinkedInService()

#     try:
#         result = await linkedin_service.apply_for_job(
#             current_user, request.job_url, resume_id
#         )
#         return result
#     except NotFoundException as e:
#         raise HTTPException(
#             status_code=status.HTTP_404_NOT_FOUND,
#             detail=str(e),
#         )
#     except OperationFailedException as e:
#         logger.error(f"Error applying for LinkedIn job: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Failed to apply for LinkedIn job: {str(e)}",
#         )
#     finally:
#         linkedin_service.close()
