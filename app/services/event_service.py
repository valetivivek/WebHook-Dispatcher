import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.event import Event
from app.models.webhook import Webhook
from app.schemas.event import EventCreateRequest
from app.metrics import events_received_total
from app.logging import get_logger

logger = get_logger(__name__)


async def create_event(db: AsyncSession, request: EventCreateRequest) -> tuple[Event, bool]:
    """Create an event and enqueue for delivery.

    Returns (event, created) where created=False means an idempotent duplicate was found.
    """
    # Verify webhook exists and is active
    result = await db.execute(
        select(Webhook).where(Webhook.id == request.webhook_id, Webhook.is_active.is_(True))
    )
    webhook = result.scalar_one_or_none()
    if webhook is None:
        raise LookupError(f"Active webhook not found: {request.webhook_id}")

    # Check for existing event with same idempotency key (idempotent insert)
    existing = await db.execute(
        select(Event).where(
            Event.webhook_id == request.webhook_id,
            Event.idempotency_key == request.idempotency_key,
        )
    )
    existing_event = existing.scalar_one_or_none()
    if existing_event is not None:
        return existing_event, False

    # Create new event
    event = Event(
        webhook_id=request.webhook_id,
        event_type=request.event_type,
        payload=request.payload,
        idempotency_key=request.idempotency_key,
        max_attempts=settings.MAX_DELIVERY_ATTEMPTS,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Record metric
    events_received_total.labels(event_type=event.event_type).inc()

    # Enqueue Celery task
    from app.worker.tasks import deliver_event

    deliver_event.delay(str(event.id))

    return event, True


async def get_event_by_id(db: AsyncSession, event_id: uuid.UUID) -> Event | None:
    result = await db.execute(
        select(Event)
        .where(Event.id == event_id)
        .options(selectinload(Event.delivery_attempts))
    )
    return result.scalar_one_or_none()
