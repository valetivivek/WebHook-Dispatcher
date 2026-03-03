import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.event import EventCreateRequest, EventDetailResponse, EventResponse
from app.services.event_service import create_event, get_event_by_id
from app.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("", response_model=EventResponse, status_code=201)
async def create_event_endpoint(
    request: EventCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        event, created = await create_event(db, request)
        if created:
            logger.info(
                "Event created and enqueued",
                extra={
                    "event_id": str(event.id),
                    "webhook_id": str(event.webhook_id),
                    "event_type": event.event_type,
                },
            )
            return EventResponse.model_validate(event)
        else:
            logger.info(
                "Idempotent event returned",
                extra={
                    "event_id": str(event.id),
                    "idempotency_key": event.idempotency_key,
                },
            )
            return EventResponse.model_validate(event)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{event_id}", response_model=EventDetailResponse)
async def get_event_endpoint(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    event = await get_event_by_id(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return EventDetailResponse.model_validate(event)
