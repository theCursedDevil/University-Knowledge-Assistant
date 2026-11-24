#!/usr/bin/env bash
# ==============================================================================
# scripts/deploy/deploy-k8s.sh
# Automated or manual Kubernetes deployment with cluster accessibility gating
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

GIT_COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo "latest")"
IMAGE_TAG="${1:-${GIT_COMMIT_SHA}}"
REGISTRY_PREFIX="${2:-}"

BACKEND_IMAGE="university-knowledge-assistant-backend:${IMAGE_TAG}"
FRONTEND_IMAGE="university-knowledge-assistant-frontend:${IMAGE_TAG}"

if [[ -n "${REGISTRY_PREFIX}" ]]; then
    BACKEND_IMAGE="${REGISTRY_PREFIX}/university-knowledge-assistant-backend:${IMAGE_TAG}"
    FRONTEND_IMAGE="${REGISTRY_PREFIX}/university-knowledge-assistant-frontend:${IMAGE_TAG}"
fi

echo "=================================================="
echo "Kubernetes Deployment Verification & Rollout"
echo "Backend Target Image:  ${BACKEND_IMAGE}"
echo "Frontend Target Image: ${FRONTEND_IMAGE}"
echo "=================================================="

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: 'kubectl' command not found; deployment cannot proceed." >&2
    exit 1
fi

# Verify cluster connectivity
echo "Checking Kubernetes cluster connectivity..."
if ! kubectl cluster-info --request-timeout=5s &> /dev/null; then
    echo "ERROR: Kubernetes cluster is unreachable; refusing to report a successful deployment." >&2
    exit 1
fi

echo "Cluster is reachable. Proceeding with rolling update..."

# Update deployment container images
kubectl set image deployment/backend backend="${BACKEND_IMAGE}"
kubectl set image deployment/frontend frontend="${FRONTEND_IMAGE}"

# Verify rolling update status
echo "Verifying backend rollout status..."
kubectl rollout status deployment/backend --timeout=120s

echo "Verifying frontend rollout status..."
kubectl rollout status deployment/frontend --timeout=120s

echo "✓ Kubernetes rolling update successfully verified."
