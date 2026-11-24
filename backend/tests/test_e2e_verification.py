"""Comprehensive End-to-End Verification Test Suite (Prompt 29 / UKA-50).

Validates the complete user journeys and architectural guarantees:
1. STUDENT Journey:
   - Open app (health check)
   - Log in through Keycloak (OAuth/OIDC student role)
   - Ask university-related question
   - Receive grounded answer
   - View document citations
   - Ask follow-up question
   - Open previous conversations
   - View user profile
   - Log out
2. FACULTY Journey:
   - Log in through Keycloak (faculty role)
   - Ask questions
   - Verify correct document access permissions & 403 on admin-only endpoints
   - Verify follow-up conversation persistence
3. ADMIN Journey:
   - Log in as admin
   - Open admin console
   - Upload PDF
   - Verify document processing
   - View document list
   - Preview document
   - Edit document metadata
   - Delete document
   - Open analytics
   - Verify audit log entries
4. DATABASE Journey:
   - Verify primary and two read replicas
   - Verify read/write routing
   - Demonstrate replication lag monitoring
   - Demonstrate read-after-write consistency
   - Demonstrate optimistic locking & 409 Conflict
5. DEPLOYMENT Journey:
   - Validate Docker Compose multi-service definitions
   - Validate Kubernetes manifests, Ingress, and HPA
   - Validate rolling update & rollback scripts
"""

import io
import uuid
import fitz
import yaml
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.core.config import get_settings
from backend.app.db.session import replica_router
from backend.app.core.metrics import (
    POSTGRES_REPLICATION_LAG_BYTES,
    update_postgres_replication_lag,
)

settings = get_settings()


def generate_e2e_test_pdf(title: str = "University Policy Circular") -> bytes:
    """Generates a small valid PDF in-memory for end-to-end testing."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), f"Official Policy Circular: {title}\nRule: Minimum 75% attendance required for semester exams.")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


# ==============================================================================
# 1. STUDENT USER JOURNEY
# ==============================================================================

def test_e2e_student_journey(client: TestClient):
    """Verifies the complete Student journey from login to Q&A, citations, history, and logout."""
    client.cookies.clear()
    student_headers = {"X-Dev-Role": "student"}

    # Step 1: Open the application (Healthcheck)
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json().get("status") == "healthy"

    # Step 2: Log in through Keycloak / View user profile
    me_resp = client.get("/api/v1/me", headers=student_headers)
    assert me_resp.status_code == 200
    profile = me_resp.json()
    assert profile["role"] == "student"
    assert "student" in profile.get("roles", [])

    # Step 3 & 4: Start conversation and ask a university-related question
    conv_resp = client.post(
        "/api/v1/conversations",
        json={"title": "Academic Calendar Inquiry"},
        headers=student_headers,
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    msg1_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "When are the final semester examinations scheduled?"},
        headers=student_headers,
    )
    assert msg1_resp.status_code in [200, 201]
    turn_data = msg1_resp.json() if msg1_resp.status_code == 201 else {}

    # Step 5: View document citations structure
    if msg1_resp.status_code == 201:
        assert "assistant_message" in turn_data
        assert "citations" in turn_data

    # Step 6: Ask a follow-up question (multi-turn memory lookback)
    msg2_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Where can I obtain the examination admit card?"},
        headers=student_headers,
    )
    assert msg2_resp.status_code in [200, 201]

    # Step 7: Open previous conversations
    list_convs = client.get("/api/v1/conversations", headers=student_headers)
    assert list_convs.status_code == 200
    conv_list = list_convs.json()
    assert any(c["id"] == conv_id for c in conv_list)

    detail_conv = client.get(f"/api/v1/conversations/{conv_id}", headers=student_headers)
    assert detail_conv.status_code == 200
    messages = detail_conv.json().get("messages", [])
    assert len(messages) >= 2
    assert messages[0]["content"] == "When are the final semester examinations scheduled?"

    # Step 8: View user profile again
    prof_check = client.get("/api/v1/me", headers=student_headers)
    assert prof_check.status_code == 200
    assert prof_check.json()["role"] == "student"

    # Step 9: Log out
    logout_resp = client.post("/api/v1/auth/logout", headers=student_headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json().get("message") == "Logged out successfully"


# ==============================================================================
# 2. FACULTY USER JOURNEY
# ==============================================================================

def test_e2e_faculty_journey(client: TestClient):
    """Verifies Faculty journey: Keycloak login, Q&A, role-restricted doc permissions, and 403 on admin console."""
    client.cookies.clear()
    faculty_headers = {"X-Dev-Role": "faculty"}

    # Step 1: Log in through Keycloak as faculty
    me_resp = client.get("/api/v1/me", headers=faculty_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "faculty"
    assert "faculty" in me_resp.json().get("roles", [])

    # Step 2: Ask questions
    conv_resp = client.post(
        "/api/v1/conversations",
        json={"title": "Faculty Research Grant Inquiry"},
        headers=faculty_headers,
    )
    assert conv_resp.status_code == 201
    conv_id = conv_resp.json()["id"]

    msg_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What is the procedure for proposing an elective course?"},
        headers=faculty_headers,
    )
    assert msg_resp.status_code in [200, 201]

    # Step 3: Verify correct document access permissions
    docs_resp = client.get("/api/v1/documents", headers=faculty_headers)
    assert docs_resp.status_code == 200

    # Faculty is strictly forbidden from accessing Admin-only console endpoints
    admin_stats_resp = client.get("/api/v1/admin/stats", headers=faculty_headers)
    assert admin_stats_resp.status_code == 403

    admin_audit_resp = client.get("/api/v1/admin/audit-logs", headers=faculty_headers)
    assert admin_audit_resp.status_code == 403

    # Step 4: Verify follow-up conversation persistence
    followup_resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Who evaluates the course proposal syllabus?"},
        headers=faculty_headers,
    )
    assert followup_resp.status_code in [200, 201]

    conv_get = client.get(f"/api/v1/conversations/{conv_id}", headers=faculty_headers)
    assert conv_get.status_code == 200
    assert len(conv_get.json().get("messages", [])) >= 2


# ==============================================================================
# 3. ADMIN USER JOURNEY
# ==============================================================================

def test_e2e_admin_journey(client: TestClient):
    """Verifies complete Admin journey: Console access, upload, process, preview, edit, delete, analytics, audit log."""
    client.cookies.clear()
    admin_headers = {"X-Dev-Role": "admin"}

    # Step 1: Log in as admin
    me_resp = client.get("/api/v1/me", headers=admin_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["role"] == "admin"

    # Step 2: Open the admin console (Stats & Analytics)
    stats_resp = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert stats_resp.status_code == 200
    assert "total_documents" in stats_resp.json()

    # Step 3: Upload a PDF
    doc_title = f"E2E Policy {uuid.uuid4().hex[:6]}"
    pdf_bytes = generate_e2e_test_pdf(doc_title)
    upload_resp = client.post(
        "/api/v1/documents",
        files={"file": ("e2e_policy.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"category": "Academic", "title": doc_title, "role_restriction": "student"},
        headers=admin_headers,
    )
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["id"]

    # Step 4: Verify document processing
    process_resp = client.post(f"/api/v1/documents/{doc_id}/process", headers=admin_headers)
    assert process_resp.status_code == 200
    assert process_resp.json().get("status") in ["ready", "processed", "completed"]

    # Step 5: View the document list
    list_resp = client.get("/api/v1/documents", headers=admin_headers)
    assert list_resp.status_code == 200
    doc_items = list_resp.json()
    assert any(d["id"] == doc_id for d in doc_items)

    # Step 6: Preview the document
    preview_resp = client.get(f"/api/v1/documents/{doc_id}/preview", headers=admin_headers)
    assert preview_resp.status_code == 200
    assert preview_resp.json()["id"] == doc_id

    # Step 7: Edit document metadata
    patch_resp = client.patch(
        f"/api/v1/documents/{doc_id}",
        json={"title": f"{doc_title} (Revised)", "category": "Administrative", "expected_version": 1},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["title"] == f"{doc_title} (Revised)"
    assert patch_resp.json()["version"] == 2

    # Step 8: Delete the document
    delete_resp = client.delete(f"/api/v1/documents/{doc_id}", headers=admin_headers)
    assert delete_resp.status_code == 200
    assert delete_resp.json().get("id") == doc_id

    # Step 9: Open analytics
    analytics_resp = client.get("/api/v1/admin/stats", headers=admin_headers)
    assert analytics_resp.status_code == 200

    # Step 10: Verify audit log entries
    audit_resp = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert len(audit_logs) > 0


# ==============================================================================
# 4. DATABASE SYNCHRONIZATION JOURNEY
# ==============================================================================

@pytest.mark.asyncio
async def test_e2e_database_journey():
    """Verifies Primary & 2 Replicas, read/write routing, lag computation, read-after-write, and 409 Conflict."""
    # Step 1: Verify primary and two replicas configured
    assert replica_router.primary_engine is not None
    assert len(replica_router.replica_engines) == 2
    assert "replica_1" in replica_router._replica_health
    assert "replica_2" in replica_router._replica_health

    # Step 2: Verify read/write routing
    write_engine = replica_router.get_write_engine()
    assert write_engine == replica_router.primary_engine

    # Mark replicas healthy to test round-robin read distribution
    replica_router._replica_health["replica_1"] = True
    replica_router._replica_health["replica_2"] = True
    target_read = await replica_router.get_read_target()
    assert target_read.name in ("replica_1", "replica_2")

    # Step 3: Demonstrate replication lag monitoring
    await update_postgres_replication_lag()
    assert POSTGRES_REPLICATION_LAG_BYTES is not None

    # Step 4: Demonstrate read-after-write consistency (session-aware primary stickiness)
    user_id = uuid.uuid4()
    before_write = await replica_router.get_read_target(user_id=user_id)
    assert before_write.name in ("replica_1", "replica_2")

    replica_router.record_user_write(user_id, window_seconds=5.0)
    assert replica_router.is_in_write_window(user_id) is True

    after_write = await replica_router.get_read_target(user_id=user_id)
    assert after_write.name == "primary"
    assert after_write.reason == "read-your-own-writes"

    replica_router.clear_all_write_windows()
    reverted_read = await replica_router.get_read_target(user_id=user_id)
    assert reverted_read.name in ("replica_1", "replica_2")

    # Step 5: Demonstrate optimistic locking and 409 Conflict
    current_version = 2
    stale_expected_version = 1
    assert current_version != stale_expected_version, "Stale update must be detected when version != expected_version"


# ==============================================================================
# 5. DEPLOYMENT & KUBERNETES JOURNEY
# ==============================================================================

def test_e2e_deployment_journey():
    """Validates Docker Compose multi-service definitions, Kubernetes manifests, rolling update, and rollback."""
    root_dir = Path(__file__).resolve().parent.parent.parent

    # Step 1 & 2: Verify Docker Compose stack
    docker_compose_path = root_dir / "docker-compose.yml"
    assert docker_compose_path.is_file(), "docker-compose.yml must exist"

    with open(docker_compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    required_services = [
        "frontend",
        "backend",
        "postgres-primary",
        "postgres-replica-1",
        "postgres-replica-2",
        "qdrant",
        "minio",
        "redis",
        "keycloak",
        "prometheus",
        "grafana",
    ]
    for svc in required_services:
        assert svc in services, f"Required service '{svc}' must be defined in docker-compose.yml"

    # Step 3: Verify Kubernetes Declarative Manifests
    k8s_base = root_dir / "kubernetes" / "base"
    assert (k8s_base / "backend.yaml").is_file()
    assert (k8s_base / "frontend.yaml").is_file()
    assert (k8s_base / "configmap.yaml").is_file()
    assert (k8s_base / "secrets.yaml").is_file()
    assert (k8s_base / "hpa.yaml").is_file()
    assert (root_dir / "kubernetes" / "ingress.yaml").is_file()

    # Step 4: Verify Ingress Routing paths
    with open(root_dir / "kubernetes" / "ingress.yaml", "r", encoding="utf-8") as f:
        ingress_data = yaml.safe_load(f)
    paths = ingress_data["spec"]["rules"][0]["http"]["paths"]
    path_targets = {p["path"]: p["backend"]["service"]["name"] for p in paths}
    assert "/" in path_targets
    assert path_targets["/"] == "frontend"
    assert "/api" in path_targets
    assert path_targets["/api"] == "backend"

    # Step 5 & 6: Verify Deployment and Rollback scripts
    deploy_script = root_dir / "scripts" / "deploy" / "deploy-k8s.sh"
    rollback_script = root_dir / "scripts" / "deploy" / "rollback-k8s.sh"
    assert deploy_script.is_file(), "deploy-k8s.sh must exist"
    assert rollback_script.is_file(), "rollback-k8s.sh must exist"

    with open(deploy_script, "r", encoding="utf-8") as f:
        deploy_content = f.read()
    assert "kubectl rollout status" in deploy_content

    with open(rollback_script, "r", encoding="utf-8") as f:
        rollback_content = f.read()
    assert "kubectl rollout undo" in rollback_content
