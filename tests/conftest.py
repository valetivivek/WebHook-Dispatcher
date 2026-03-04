import os
import uuid
from datetime import datetime, timezone

import pytest

# Override settings before any app imports
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/webhooks_test"
os.environ["DATABASE_URL_SYNC"] = "postgresql+psycopg2://postgres:postgres@localhost:5432/webhooks_test"
os.environ["CELERY_BROKER_URL"] = "redis://localhost:6379/15"
os.environ["CELERY_RESULT_BACKEND"] = "redis://localhost:6379/15"
os.environ["ALLOW_PRIVATE_IPS"] = "true"
os.environ["ENVIRONMENT"] = "development"


from app.models.event import Event, EventState
from app.models.webhook import Webhook


@pytest.fixture
def sample_webhook() -> Webhook:
    return Webhook(
        id=uuid.uuid4(),
        url="https://example.com/hook",
        secret="test-secret-key",
        description="Test webhook",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_event(sample_webhook: Webhook) -> Event:
    return Event(
        id=uuid.uuid4(),
        webhook_id=sample_webhook.id,
        event_type="order.created",
        payload={"order_id": 123, "amount": 99.99},
        idempotency_key="idem-key-001",
        state=EventState.PENDING,
        attempt_count=0,
        max_attempts=5,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
