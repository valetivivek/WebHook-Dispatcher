import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class EventState:
    PENDING = "PENDING"
    DELIVERING = "DELIVERING"
    DELIVERED = "DELIVERED"
    RETRYING = "RETRYING"
    FAILED = "FAILED"

    VALID_TRANSITIONS = {
        PENDING: {DELIVERING},
        DELIVERING: {DELIVERED, RETRYING, FAILED},
        RETRYING: {DELIVERING},
    }

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        return to_state in cls.VALID_TRANSITIONS.get(from_state, set())


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint("webhook_id", "idempotency_key", name="uq_events_webhook_idempotency"),
        Index("idx_events_state", "state"),
        Index("idx_events_webhook_id", "webhook_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'PENDING'"), default=EventState.PENDING
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), default=0
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("5"), default=5
    )
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        default=lambda: datetime.now(timezone.utc),
    )

    webhook = relationship("Webhook", back_populates="events", lazy="selectin")
    delivery_attempts = relationship(
        "DeliveryAttempt", back_populates="event", lazy="selectin", order_by="DeliveryAttempt.attempt_number"
    )
