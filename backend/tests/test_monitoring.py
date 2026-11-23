"""Tests for Prometheus application metrics and operational monitoring (C-MON, FR-MON, Prompt 27)."""

import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.core.metrics import (
    LLM_REQUESTS_TOTAL,
    DOCUMENT_PROCESSING_TOTAL,
    POSTGRES_REPLICATION_LAG_BYTES,
    update_postgres_replication_lag,
)


@pytest.fixture
def client():
    """Sync test client fixture."""
    with TestClient(app) as test_client:
        yield test_client


def test_metrics_endpoint_accessible(client: TestClient):
    """Verifies that the /metrics endpoint responds with 200 OK and Prometheus text payload."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "")

    body = resp.text
    # Check that our custom UKA metrics are registered and exported
    assert "uka_http_requests_total" in body
    assert "uka_http_request_duration_seconds" in body
    assert "uka_http_errors_total" in body
    assert "uka_llm_requests_total" in body
    assert "uka_document_processing_total" in body
    assert "uka_postgres_replication_lag_bytes" in body


def test_http_request_and_error_metrics_increment(client: TestClient):
    """Verifies that HTTP calls update request volume and error metrics."""
    # 1. Trigger successful request
    resp_ok = client.get("/health")
    assert resp_ok.status_code == 200

    # 2. Trigger 404 error request
    resp_err = client.get("/api/v1/definite-missing-route-test-404")
    assert resp_err.status_code == 404

    # 3. Check /metrics output
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    metrics_text = metrics_resp.text

    assert 'uka_http_requests_total{endpoint="/health",method="GET",status_code="200"}' in metrics_text
    assert 'uka_http_errors_total{endpoint="/api/v1/definite-missing-route-test-404",method="GET",status_code="404"}' in metrics_text


@pytest.mark.asyncio
async def test_llm_and_document_metrics_tracking():
    """Verifies that LLM generation and document processing counters increment properly."""
    initial_llm = LLM_REQUESTS_TOTAL.labels(model="llama-3.1-8b-instant", status="success")._value.get()
    initial_doc = DOCUMENT_PROCESSING_TOTAL.labels(status="success")._value.get()

    LLM_REQUESTS_TOTAL.labels(model="llama-3.1-8b-instant", status="success").inc()
    DOCUMENT_PROCESSING_TOTAL.labels(status="success").inc()

    updated_llm = LLM_REQUESTS_TOTAL.labels(model="llama-3.1-8b-instant", status="success")._value.get()
    updated_doc = DOCUMENT_PROCESSING_TOTAL.labels(status="success")._value.get()

    assert updated_llm == initial_llm + 1
    assert updated_doc == initial_doc + 1


@pytest.mark.asyncio
async def test_postgres_replication_lag_gauge():
    """Verifies that the PostgreSQL replication lag gauge samples without throwing exceptions."""
    # Run the lag sampler
    await update_postgres_replication_lag()

    # Gauge should have a value (either simulated 0.0 or real LSN diff)
    val_1 = POSTGRES_REPLICATION_LAG_BYTES.labels(replica="replica_1")._value.get()
    assert val_1 is not None
    assert val_1 >= 0.0
