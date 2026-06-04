"""Inbound email webhooks."""

import json

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from config.logging_config import get_logger
from config.settings import settings
from core.schemas.resend_schemas import ResendWebhookEvent
from core.services.email_resume_service import build_email_resume_service
from core.utils.svix_verify import WebhookVerificationError, verify_svix_webhook

router = APIRouter()
logger = get_logger(__name__)


async def _run_inbound_email_job(email_id: str) -> None:
    service = build_email_resume_service()
    await service.process_inbound_email(email_id)


@router.post("/resend", status_code=status.HTTP_200_OK)
async def resend_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    """Handle Resend ``email.received`` webhook events."""
    if not settings.features.enable_email_to_resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email-to-resume is not enabled",
        )

    raw_body = await request.body()
    webhook_secret = settings.resend.webhook_secret.get_secret_value()

    if webhook_secret:
        try:
            payload = verify_svix_webhook(
                raw_body,
                dict(request.headers),
                webhook_secret,
            )
        except WebhookVerificationError as exc:
            logger.warning("Resend webhook verification failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            ) from exc
    else:
        logger.warning(
            "RESEND_WEBHOOK_SECRET not set; accepting webhook without verification"
        )
        payload = json.loads(raw_body.decode("utf-8"))

    event_type = payload.get("type")
    if event_type != "email.received":
        return {"status": "ignored"}

    event = ResendWebhookEvent.model_validate(payload)
    email_id = event.data.email_id
    background_tasks.add_task(_run_inbound_email_job, email_id)
    logger.info("Accepted inbound email job for Resend email_id=%s", email_id)
    return {"status": "accepted"}
