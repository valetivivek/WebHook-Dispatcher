from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.webhook import WebhookRegisterRequest, WebhookResponse
from app.services.webhook_service import register_webhook
from app.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/register", response_model=WebhookResponse, status_code=201)
async def register_webhook_endpoint(
    request: WebhookRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        webhook = await register_webhook(db, request)
        logger.info("Webhook registered", extra={"webhook_id": str(webhook.id)})
        return webhook
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
