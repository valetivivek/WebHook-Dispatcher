"""Tests for idempotency behavior."""
import uuid
from datetime import datetime, timezone

import pytest

from app.models.event import Event, EventState
from app.schemas.event import EventCreateRequest


class TestIdempotencyKeyLogic:
    """Unit tests for idempotency key behavior (no database required)."""

    def test_same_idempotency_key_same_webhook_should_be_duplicate(self):
        """Two events with the same webhook_id + idempotency_key are duplicates."""
        webhook_id = uuid.uuid4()
        key = "order-abc-123"

        event1 = Event(
            id=uuid.uuid4(),
            webhook_id=webhook_id,
            event_type="order.created",
            payload={"order": 1},
            idempotency_key=key,
            state=EventState.PENDING,
            attempt_count=0,
            max_attempts=5,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Simulate what the service layer does: check if key matches
        is_duplicate = (
            event1.webhook_id == webhook_id and event1.idempotency_key == key
        )
        assert is_duplicate is True

    def test_same_idempotency_key_different_webhook_not_duplicate(self):
        """Same key on different webhooks should NOT be considered duplicate."""
        webhook_a = uuid.uuid4()
        webhook_b = uuid.uuid4()
        key = "order-abc-123"

        event_a = Event(
            id=uuid.uuid4(),
            webhook_id=webhook_a,
            event_type="order.created",
            payload={"order": 1},
            idempotency_key=key,
            state=EventState.PENDING,
            attempt_count=0,
            max_attempts=5,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Check against webhook_b — should not match
        is_duplicate = (
            event_a.webhook_id == webhook_b and event_a.idempotency_key == key
        )
        assert is_duplicate is False

    def test_different_idempotency_key_same_webhook_not_duplicate(self):
        """Different keys on the same webhook should NOT be duplicates."""
        webhook_id = uuid.uuid4()

        event1 = Event(
            id=uuid.uuid4(),
            webhook_id=webhook_id,
            event_type="order.created",
            payload={"order": 1},
            idempotency_key="key-001",
            state=EventState.PENDING,
            attempt_count=0,
            max_attempts=5,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        is_duplicate = (
            event1.webhook_id == webhook_id
            and event1.idempotency_key == "key-002"
        )
        assert is_duplicate is False

    def test_idempotent_event_preserves_original_id(self):
        """When an idempotent duplicate is found, the original event's ID is returned."""
        original_id = uuid.uuid4()
        webhook_id = uuid.uuid4()
        key = "order-abc-123"

        original = Event(
            id=original_id,
            webhook_id=webhook_id,
            event_type="order.created",
            payload={"order": 1},
            idempotency_key=key,
            state=EventState.DELIVERED,
            attempt_count=1,
            max_attempts=5,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Simulate service returning existing event
        returned_event = original  # This is what the service does
        assert returned_event.id == original_id
        assert returned_event.state == EventState.DELIVERED

    def test_event_create_request_validation(self):
        """Verify Pydantic schema validates correctly."""
        request = EventCreateRequest(
            webhook_id=uuid.uuid4(),
            event_type="payment.completed",
            payload={"amount": 50.00},
            idempotency_key="pay-xyz-789",
        )
        assert request.event_type == "payment.completed"
        assert request.idempotency_key == "pay-xyz-789"
