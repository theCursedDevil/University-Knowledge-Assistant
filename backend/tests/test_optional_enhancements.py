"""Verification tests for Prompt 28 optional enhancements and Kubernetes HPA configuration."""

import json
from pathlib import Path
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def test_hpa_manifest_structure():
    """Verifies that the Kubernetes HPA manifest exists and matches NFR-SCAL-003 / DEP-K8S-010."""
    hpa_file = REPO_ROOT / "kubernetes" / "base" / "hpa.yaml"
    assert hpa_file.exists(), "kubernetes/base/hpa.yaml must exist"

    with open(hpa_file, "r") as f:
        docs = list(yaml.safe_load_all(f))

    assert len(docs) >= 1
    hpa = docs[0]
    assert hpa["apiVersion"] == "autoscaling/v2"
    assert hpa["kind"] == "HorizontalPodAutoscaler"
    assert hpa["spec"]["scaleTargetRef"]["name"] == "backend"
    assert hpa["spec"]["minReplicas"] == 1
    assert hpa["spec"]["maxReplicas"] >= 2

    # Check that CPU utilization threshold is configured (default 70%)
    metrics = hpa["spec"]["metrics"]
    cpu_metric = next((m for m in metrics if m.get("resource", {}).get("name") == "cpu"), None)
    assert cpu_metric is not None
    assert cpu_metric["resource"]["target"]["averageUtilization"] == 70


def test_kustomization_includes_hpa():
    """Verifies that kustomization.yaml resources include the HPA manifest."""
    kustomization_file = REPO_ROOT / "kubernetes" / "kustomization.yaml"
    assert kustomization_file.exists()

    with open(kustomization_file, "r") as f:
        data = yaml.safe_load(f)

    assert "base/hpa.yaml" in data.get("resources", [])


def test_keycloak_google_identity_provider_configured():
    """Verifies that Keycloak university-realm.json includes the Google Identity Provider."""
    realm_file = REPO_ROOT / "docker" / "keycloak" / "university-realm.json"
    assert realm_file.exists(), "docker/keycloak/university-realm.json must exist"

    with open(realm_file, "r") as f:
        realm_data = json.load(f)

    idps = realm_data.get("identityProviders", [])
    google_idp = next((idp for idp in idps if idp.get("alias") == "google"), None)

    assert google_idp is not None, "Google Identity Provider must be configured in Keycloak realm"
    assert google_idp["providerId"] == "google"
    assert google_idp["enabled"] is True
    assert "GOOGLE_CLIENT_ID" in google_idp["config"]["clientId"]
    assert "GOOGLE_CLIENT_SECRET" in google_idp["config"]["clientSecret"]


def test_optional_enhancements_documentation():
    """Verifies that required documentation files exist and have traceability content."""
    doc_enhancements = REPO_ROOT / "docs" / "optional-enhancements.md"
    doc_google = REPO_ROOT / "docs" / "google-federation.md"

    assert doc_enhancements.exists()
    assert doc_google.exists()

    content = doc_enhancements.read_text()
    assert "FR-RAG-008" in content
    assert "FR-RAG-003" in content
    assert "FR-CHAT-006" in content
    assert "NFR-SCAL-003" in content
