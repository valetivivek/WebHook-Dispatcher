import uuid
from datetime import datetime

from pydantic import BaseModel, HttpUrl


class WebhookRegisterRequest(BaseModel):
    url: HttpUrl
    secret: str
    description: str | None = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    url: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
