# Webhook Dispatcher

A production-grade, Dockerized webhook dispatcher built with Python, FastAPI, Celery, Redis, and PostgreSQL. Delivers webhook events with at-least-once guarantees, exponential backoff retries, end-to-end idempotency, and full Prometheus observability.

## Architecture

```
Client → FastAPI API → PostgreSQL (state) + Redis (queue) → Celery Worker → Target URL
                                                                    ↓
                                                              Prometheus ← /metrics
```

## Quick Start

### Prerequisites

- Docker and Docker Compose

### Launch

```bash
# Clone and start all services
git clone <repo-url> && cd webhook-dispatcher
docker compose up -d

# Run database migrations
docker compose run --rm migrate

# Verify
curl http://localhost:8000/health
```

All services will be available:

| Service | URL |
|---|---|
| API | http://localhost:8000 |
| Prometheus | http://localhost:9090 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

## API Usage

### 1. Register a Webhook

```bash
curl -X POST http://localhost:8000/v1/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/post",
    "secret": "my-signing-secret",
    "description": "Order notifications"
  }'
```

Response:

```json
{
  "id": "a1b2c3d4-...",
  "url": "https://httpbin.org/post",
  "description": "Order notifications",
  "is_active": true,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

### 2. Send an Event

```bash
curl -X POST http://localhost:8000/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_id": "a1b2c3d4-...",
    "event_type": "order.created",
    "payload": {"order_id": 12345, "amount": 99.99},
    "idempotency_key": "order-12345-created"
  }'
```

Response:

```json
{
  "id": "e5f6g7h8-...",
  "webhook_id": "a1b2c3d4-...",
  "event_type": "order.created",
  "payload": {"order_id": 12345, "amount": 99.99},
  "idempotency_key": "order-12345-created",
  "state": "PENDING",
  "attempt_count": 0,
  "max_attempts": 5,
  "next_retry_at": null,
  "delivered_at": null,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

Sending the same request again (same `webhook_id` + `idempotency_key`) returns the existing event with `200 OK`.

### 3. Check Event Status

```bash
curl http://localhost:8000/v1/events/e5f6g7h8-...
```

Response includes delivery attempt history:

```json
{
  "id": "e5f6g7h8-...",
  "state": "DELIVERED",
  "attempt_count": 1,
  "delivered_at": "2025-01-01T00:00:01Z",
  "delivery_attempts": [
    {
      "attempt_number": 1,
      "status_code": 200,
      "error": null,
      "latency_ms": 234.5,
      "created_at": "2025-01-01T00:00:01Z"
    }
  ]
}
```

### 4. Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

## Outbound Request Headers

Every webhook delivery includes:

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `X-Signature` | `sha256=<HMAC-SHA256 hex digest>` |
| `X-Event-Id` | UUID of the event |
| `X-Event-Type` | e.g., `order.created` |
| `Idempotency-Key` | The client-provided idempotency key |
| `User-Agent` | `WebhookDispatcher/1.0` |

## Prometheus Query Examples

**Success rate (last 5 minutes):**

```promql
rate(webhook_deliveries_total{status="success"}[5m])
/
rate(webhook_deliveries_total[5m])
```

**p95 delivery latency:**

```promql
histogram_quantile(0.95, rate(webhook_delivery_latency_seconds_bucket[5m]))
```

**Failure ratio by event type:**

```promql
rate(webhook_deliveries_total{status="failed"}[5m])
/
rate(webhook_deliveries_total[5m])
```

**Queue depth:**

```promql
webhook_queue_depth
```

## Running Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_retry_logic.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=term-missing
```

Note: Unit tests for idempotency, retry logic, state transitions, HMAC, and URL validation run without any infrastructure dependencies. They test pure business logic.

## Configuration

All configuration via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async Postgres connection |
| `DATABASE_URL_SYNC` | `postgresql+psycopg2://...` | Sync Postgres (for workers) |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery result backend |
| `MAX_DELIVERY_ATTEMPTS` | `5` | Max retries before failure |
| `DELIVERY_TIMEOUT_SECONDS` | `10` | HTTP timeout per attempt |
| `RETRY_BASE_DELAY_SECONDS` | `1.0` | Backoff base delay |
| `RETRY_MAX_DELAY_SECONDS` | `3600.0` | Backoff ceiling |
| `ALLOW_PRIVATE_IPS` | `false` | Allow localhost targets (dev) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `ENVIRONMENT` | `production` | `development` or `production` |

## Project Structure

```
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_schema.py
├── app/
│   ├── main.py              # FastAPI app + middleware
│   ├── config.py             # Pydantic settings
│   ├── database.py           # SQLAlchemy engines
│   ├── logging.py            # Structured JSON logging
│   ├── metrics.py            # Prometheus metric definitions
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── api/                  # FastAPI route handlers
│   ├── services/             # Business logic layer
│   ├── security/             # HMAC signing, URL validation
│   └── worker/               # Celery app + tasks
└── tests/                    # pytest test suite
```

## License

MIT
