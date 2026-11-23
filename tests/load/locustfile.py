"""Locust Load Test Suite for University Knowledge Assistant (Prompt 25 — Area 10).

Simulates concurrent university traffic:
- Authenticates through Keycloak OIDC (university-realm)
- Queries university academic regulations and campus policies via RAG
- Browses cached circulars and document listings across PostgreSQL read replicas
- Probes system health endpoints

Usage:
  locust -f tests/load/locustfile.py --headless -u 15 -r 3 --run-time 25s --host http://localhost:8000
"""

import random
import requests
from locust import HttpUser, task, between


SAMPLE_QUESTIONS = [
    "What is the minimum physical attendance required for B.Tech students?",
    "What is the minimum CGPA required for degree award?",
    "What is the curfew time for undergraduate hostel residents?",
    "What is the procedure for semester exam re-evaluation?",
    "What are the library borrowing rules and overdue book fines?",
]

# Keycloak Token Cache for load testing efficiency
_CACHED_TOKEN = None


def get_keycloak_token():
    """Fetches and caches an OIDC Bearer token from Keycloak for load testing."""
    global _CACHED_TOKEN
    if _CACHED_TOKEN:
        return _CACHED_TOKEN
    try:
        resp = requests.post(
            "http://localhost:8080/realms/university-realm/protocol/openid-connect/token",
            data={
                "client_id": "university-assistant-client",
                "grant_type": "password",
                "username": "admin",
                "password": "AdminPassword123!",
            },
            timeout=5.0,
        )
        if resp.status_code == 200:
            _CACHED_TOKEN = resp.json().get("access_token")
            return _CACHED_TOKEN
    except Exception:
        pass
    return None


class UniversityUser(HttpUser):
    """Simulates a university user interacting with the platform."""

    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Initializes user session with authenticated Bearer token."""
        token = get_keycloak_token()
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    @task(5)
    def test_health_check(self):
        """Tests system health and liveness endpoint."""
        self.client.get("/health", name="GET /health")

    @task(3)
    def test_list_documents(self):
        """Tests document catalog listing with caching and replica distribution."""
        self.client.get("/api/v1/documents", headers=self.headers, name="GET /api/v1/documents")

    @task(2)
    def test_rag_query(self):
        """Tests core RAG search and question-answering workflow."""
        question = random.choice(SAMPLE_QUESTIONS)
        payload = {
            "question": question,
            "top_k": 3,
            "confidence_threshold": 0.20,
            "category": "Academic",
        }
        self.client.post("/api/v1/rag/query", json=payload, headers=self.headers, name="POST /api/v1/rag/query")
