from prometheus_client import Counter, Histogram, Gauge

# --- Counters ---

events_received_total = Counter(
    "webhook_events_received_total",
    "Total events ingested via API",
    ["event_type"],
)

deliveries_total = Counter(
    "webhook_deliveries_total",
    "Total delivery outcomes",
    ["event_type", "status"],
)

delivery_attempts_total = Counter(
    "webhook_delivery_attempts_total",
    "Total per-attempt HTTP outcomes",
    ["event_type", "status_code"],
)

# --- Histograms ---

delivery_latency_seconds = Histogram(
    "webhook_delivery_latency_seconds",
    "HTTP round-trip latency per delivery attempt",
    ["event_type"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

end_to_end_latency_seconds = Histogram(
    "webhook_end_to_end_latency_seconds",
    "Time from event creation to successful delivery",
    ["event_type"],
    buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0),
)

# --- Gauges ---

queue_depth = Gauge(
    "webhook_queue_depth",
    "Number of events in PENDING or RETRYING state",
)

active_deliveries = Gauge(
    "webhook_active_deliveries",
    "Number of events currently in DELIVERING state",
)
