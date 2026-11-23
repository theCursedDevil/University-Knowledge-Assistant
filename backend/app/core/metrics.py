"""Prometheus metrics registry and definitions (C-MON, FR-MON, Prompt 27).

Exposes core operational metrics:
- API request volume, error rates, and latency.
- LLM generation activity and latency.
- Document processing lifecycle counts.
- PostgreSQL replication lag in bytes.
"""

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from sqlalchemy import text

# ---------------------------------------------------------------------------
# 1. API Request & Latency Metrics
# ---------------------------------------------------------------------------

HTTP_REQUESTS_TOTAL = Counter(
    "uka_http_requests_total",
    "Total HTTP requests received by the application layer.",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "uka_http_request_duration_seconds",
    "HTTP request latency distribution in seconds.",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

HTTP_ERRORS_TOTAL = Counter(
    "uka_http_errors_total",
    "Total HTTP 4xx and 5xx error responses produced.",
    ["method", "endpoint", "status_code"],
)

# ---------------------------------------------------------------------------
# 2. LLM Activity & Latency Metrics
# ---------------------------------------------------------------------------

LLM_REQUESTS_TOTAL = Counter(
    "uka_llm_requests_total",
    "Total LLM generation invocations across the RAG pipeline.",
    ["model", "status"],
)

LLM_REQUEST_DURATION_SECONDS = Histogram(
    "uka_llm_request_duration_seconds",
    "LLM API roundtrip generation latency distribution in seconds.",
    ["model"],
    buckets=(0.25, 0.5, 1.0, 2.0, 3.5, 5.0, 8.0, 12.0),
)

# ---------------------------------------------------------------------------
# 3. Document Processing Metrics
# ---------------------------------------------------------------------------

DOCUMENT_PROCESSING_TOTAL = Counter(
    "uka_document_processing_total",
    "Total document ingestion and chunking processing events.",
    ["status"],  # "success", "failed"
)

# ---------------------------------------------------------------------------
# 4. PostgreSQL Replication Lag Metrics
# ---------------------------------------------------------------------------

POSTGRES_REPLICATION_LAG_BYTES = Gauge(
    "uka_postgres_replication_lag_bytes",
    "Replication lag in bytes between PostgreSQL primary and standbys.",
    ["replica"],  # "replica_1", "replica_2"
)


async def update_postgres_replication_lag() -> None:
    """Samples PostgreSQL replication lag from primary and updates the Prometheus gauge."""
    try:
        from backend.app.db.router import replica_router

        if not replica_router.primary_engine:
            return

        async with replica_router.primary_engine.connect() as conn:
            # Query WAL replay lag in bytes per connected standby application
            query = text(
                """
                SELECT application_name,
                       COALESCE(pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn), 0) AS lag_bytes
                FROM pg_stat_replication
                """
            )
            rows = await conn.execute(query)
            records = rows.fetchall()

            if records:
                for row in records:
                    app_name = row.application_name or "unknown_replica"
                    lag = float(row.lag_bytes)
                    POSTGRES_REPLICATION_LAG_BYTES.labels(replica=app_name).set(lag)
            else:
                # Fallback zero when in single-node/CI test mode
                POSTGRES_REPLICATION_LAG_BYTES.labels(replica="replica_1").set(0.0)
                POSTGRES_REPLICATION_LAG_BYTES.labels(replica="replica_2").set(0.0)
    except Exception:
        # Avoid breaking metrics scrape if database is momentarily unreachable
        pass


def get_metrics_payload() -> tuple[bytes, str]:
    """Serializes the default Prometheus metrics registry for the /metrics endpoint."""
    return generate_latest(), CONTENT_TYPE_LATEST
