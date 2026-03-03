from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import Webhook
from app.schemas.webhook import WebhookRegisterRequest
from app.security.url_validator import validate_webhook_url


async def register_webhook(db: AsyncSession, request: WebhookRegisterRequest) -> Webhook:
    url = str(request.url)
    validate_webhook_url(url)

    webhook = Webhook(
        url=url,
        secret=request.secret,
        description=request.description,
    )
    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)
    return webhook
