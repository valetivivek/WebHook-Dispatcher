from datetime import datetime, timezone, timedelta

from sqlalchemy import select, text as sa_text

from app.worker.celery_app import celery_app
from app.database import SyncSessionLocal
from app.models.event import Event, EventState
from app.models.delivery_attempt import DeliveryAttempt
from app.services.delivery_service import deliver_http, is_retryable_status, compute_backoff
from app.config import settings
from app.logging import get_logger
from app import metrics as m

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.worker.tasks.deliver_event",
    max_retries=None,  # We manage retries ourselves
    acks_late=True,
)
def deliver_event(self, event_id: str) -> dict:
    """Deliver a webhook event to its target URL.

    Uses SELECT ... FOR UPDATE SKIP LOCKED to prevent concurrent delivery
    of the same event by multiple workers.
    """
    with SyncSessionLocal() as session:
        # Acquire row lock — SKIP LOCKED means if another worker holds
        # this row, we get zero rows back and abort gracefully.
        result = session.execute(
            select(Event)
            .where(Event.id == event_id)
            .with_for_update(skip_locked=True)
        )
        event = result.scalar_one_or_none()

        if event is None:
            logger.info(
                "Event locked by another worker or not found, skipping",
                extra={"event_id": event_id},
            )
            return {"status": "skipped", "reason": "locked_or_missing"}

        # Only process events in deliverable states
        if event.state not in (EventState.PENDING, EventState.RETRYING):
            logger.info(
                "Event not in deliverable state, skipping",
                extra={"event_id": event_id, "state": event.state},
            )
            session.rollback()
            return {"status": "skipped", "reason": f"state={event.state}"}

        # Transition to DELIVERING
        event.state = EventState.DELIVERING
        event.updated_at = datetime.now(timezone.utc)
        session.commit()

    # --- HTTP delivery happens OUTSIDE the transaction / lock ---
    m.active_deliveries.inc()
    try:
        with SyncSessionLocal() as session:
            # Re-fetch event (no lock needed for read)
            event = session.execute(
                select(Event).where(Event.id == event_id)
            ).scalar_one()

            # Fetch the webhook to get URL and secret
            from app.models.webhook import Webhook

            webhook = session.execute(
                select(Webhook).where(Webhook.id == event.webhook_id)
            ).scalar_one()

            status_code, response_body, error, latency_ms = deliver_http(
                url=webhook.url,
                payload=event.payload,
                secret=webhook.secret,
                event_id=str(event.id),
                event_type=event.event_type,
                idempotency_key=event.idempotency_key,
            )

            # Record delivery attempt
            attempt = DeliveryAttempt(
                event_id=event.id,
                attempt_number=event.attempt_count + 1,
                status_code=status_code,
                response_body=response_body,
                error=error,
                latency_ms=latency_ms,
            )
            session.add(attempt)

            # Record latency metric
            m.delivery_latency_seconds.labels(event_type=event.event_type).observe(
                latency_ms / 1000.0
            )

            # Determine outcome
            now = datetime.now(timezone.utc)
            network_error = status_code is None
            success = not network_error and 200 <= status_code < 400
            retryable = network_error or is_retryable_status(status_code)

            event.attempt_count += 1
            event.updated_at = now

            if success:
                event.state = EventState.DELIVERED
                event.delivered_at = now
                session.commit()

                # Record metrics
                m.deliveries_total.labels(
                    event_type=event.event_type, status="success"
                ).inc()
                if status_code:
                    m.delivery_attempts_total.labels(
                        event_type=event.event_type, status_code=str(status_code)
                    ).inc()

                # End-to-end latency
                e2e = (now - event.created_at).total_seconds()
                m.end_to_end_latency_seconds.labels(event_type=event.event_type).observe(e2e)

                logger.info(
                    "Event delivered successfully",
                    extra={
                        "event_id": event_id,
                        "status_code": status_code,
                        "attempt": event.attempt_count,
                        "latency_ms": round(latency_ms, 2),
                    },
                )
                return {"status": "delivered", "status_code": status_code}

            elif retryable and event.attempt_count < event.max_attempts:
                backoff = compute_backoff(
                    attempt_number=event.attempt_count - 1,
                    base_delay=settings.RETRY_BASE_DELAY_SECONDS,
                    max_delay=settings.RETRY_MAX_DELAY_SECONDS,
                )
                event.state = EventState.RETRYING
                event.next_retry_at = now + timedelta(seconds=backoff)
                session.commit()

                m.deliveries_total.labels(
                    event_type=event.event_type, status="retrying"
                ).inc()
                if status_code:
                    m.delivery_attempts_total.labels(
                        event_type=event.event_type, status_code=str(status_code)
                    ).inc()
                else:
                    m.delivery_attempts_total.labels(
                        event_type=event.event_type, status_code="network_error"
                    ).inc()

                logger.info(
                    "Event scheduled for retry",
                    extra={
                        "event_id": event_id,
                        "attempt": event.attempt_count,
                        "backoff_seconds": round(backoff, 2),
                        "next_retry_at": event.next_retry_at.isoformat(),
                    },
                )

                # Schedule the Celery retry with the computed backoff
                raise self.retry(countdown=backoff)

            else:
                event.state = EventState.FAILED
                session.commit()

                m.deliveries_total.labels(
                    event_type=event.event_type, status="failed"
                ).inc()
                if status_code:
                    m.delivery_attempts_total.labels(
                        event_type=event.event_type, status_code=str(status_code)
                    ).inc()
                else:
                    m.delivery_attempts_total.labels(
                        event_type=event.event_type, status_code="network_error"
                    ).inc()

                logger.warning(
                    "Event delivery failed permanently",
                    extra={
                        "event_id": event_id,
                        "attempt": event.attempt_count,
                        "status_code": status_code,
                        "error": error,
                    },
                )
                return {"status": "failed", "status_code": status_code, "error": error}

    finally:
        m.active_deliveries.dec()


@celery_app.task(name="app.worker.tasks.update_queue_depth")
def update_queue_depth():
    """Periodic task to update the queue depth gauge metric."""
    with SyncSessionLocal() as session:
        result = session.execute(
            sa_text(
                "SELECT count(*) FROM events WHERE state IN ('PENDING', 'RETRYING')"
            )
        )
        depth = result.scalar()
        m.queue_depth.set(depth or 0)


# Beat schedule for periodic queue depth updates
celery_app.conf.beat_schedule = {
    "update-queue-depth-every-15s": {
        "task": "app.worker.tasks.update_queue_depth",
        "schedule": 15.0,
    },
}
