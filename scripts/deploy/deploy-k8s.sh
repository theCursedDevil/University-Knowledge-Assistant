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
    echo "WARNING: 'kubectl' command not found. Skipping Kubernetes deployment."
    exit 0
fi

# Verify cluster connectivity
echo "Checking Kubernetes cluster connectivity..."
if ! kubectl cluster-info --request-timeout=5s &> /dev/null; then
    echo "========================================================================"
    echo "NOTICE: Kubernetes cluster is not accessible from the current environment."
    echo ""
    echo "Reason: If running on a GitHub-hosted runner, GitHub cloud runners"
    echo "cannot directly access local Minikube running on your Mac."
    echo ""
    echo "To deploy published GHCR images to your local Minikube cluster:"
    echo "1. On your Mac, ensure Minikube is running:"
    echo "   minikube status"
    echo ""
    echo "2. Update deployment images to the published build tag (${IMAGE_TAG}):"
    echo "   kubectl set image deployment/backend backend=${BACKEND_IMAGE}"
    echo "   kubectl set image deployment/frontend frontend=${FRONTEND_IMAGE}"
    echo ""
    echo "3. Verify the rollout:"
    echo "   kubectl rollout status deployment/backend --timeout=120s"
    echo "   kubectl rollout status deployment/frontend --timeout=120s"
    echo "========================================================================"
    exit 0
fi

echo "Cluster is reachable. Proceeding with rolling update..."

# Update deployment container images
kubectl set image deployment/backend backend="${BACKEND_IMAGE}" --record=true || true
kubectl set image deployment/frontend frontend="${FRONTEND_IMAGE}" --record=true || true

# Verify rolling update status
echo "Verifying backend rollout status..."
kubectl rollout status deployment/backend --timeout=120s

echo "Verifying frontend rollout status..."
kubectl rollout status deployment/frontend --timeout=120s

echo "✓ Kubernetes rolling update successfully verified."
