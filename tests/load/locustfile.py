"""Locust Load Test Suite for University Knowledge Assistant (Prompt 25 — Area 10).

Simulates concurrent university traffic:
- Authenticates through Keycloak OIDC (university-realm)
- Queries university academic regulations and campus policies via RAG
- Browses cached circulars and document listings across PostgreSQL read replicas
- Probes system health endpoints

Usage:
  UKA_LOADTEST_TOKEN=<short-lived-token> locust -f tests/load/locustfile.py --headless -u 15 -r 3 --run-time 25s --host http://localhost:8000
"""

import logging
import os
import random
from locust import HttpUser, task, between


SAMPLE_QUESTIONS = [
    "What is the minimum physical attendance required for B.Tech students?",
    "What is the minimum CGPA required for degree award?",
    "What is the curfew time for undergraduate hostel residents?",
    "What is the procedure for semester exam re-evaluation?",
    "What are the library borrowing rules and overdue book fines?",
]

def get_test_token():
    """Read a short-lived token provisioned for the load-test run.

    The Keycloak realm intentionally disables the password grant. Never embed a
    username/password pair or request an end-user password token from this script.
    """
    return os.getenv("UKA_LOADTEST_TOKEN")


class UniversityUser(HttpUser):
    """Simulates a university user interacting with the platform."""

    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Initializes user session with authenticated Bearer token."""
        token = get_test_token()
        self.authenticated = bool(token)
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        if not token:
            logging.warning("UKA_LOADTEST_TOKEN is unset; authenticated tasks will be skipped.")

    @task(5)
    def test_health_check(self):
        """Tests system health and liveness endpoint."""
        self.client.get("/api/v1/health", name="GET /health")

    @task(3)
    def test_list_documents(self):
        """Tests document catalog listing with caching and replica distribution."""
        if self.authenticated:
            self.client.get("/api/v1/documents", headers=self.headers, name="GET /api/v1/documents")

    @task(2)
    def test_rag_query(self):
        """Tests core RAG search and question-answering workflow."""
        if not self.authenticated:
            return
        question = random.choice(SAMPLE_QUESTIONS)
        payload = {
            "question": question,
            "top_k": 3,
            "confidence_threshold": 0.20,
            "category": "Academic",
        }
        self.client.post("/api/v1/rag/query", json=payload, headers=self.headers, name="POST /api/v1/rag/query")
