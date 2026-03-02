import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class EventCreateRequest(BaseModel):
    webhook_id: uuid.UUID
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str


class DeliveryAttemptResponse(BaseModel):
    id: uuid.UUID
    attempt_number: int
    status_code: int | None
    error: str | None
    latency_ms: float
    created_at: datetime

    model_config = {"from_attributes": True}


class EventResponse(BaseModel):
    id: uuid.UUID
    webhook_id: uuid.UUID
    event_type: str
    payload: dict[str, Any]
    idempotency_key: str
    state: str
    attempt_count: int
    max_attempts: int
    next_retry_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EventDetailResponse(EventResponse):
    delivery_attempts: list[DeliveryAttemptResponse] = []
