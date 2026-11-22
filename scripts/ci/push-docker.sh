#!/usr/bin/env bash
# ==============================================================================
# scripts/ci/push-docker.sh
# Push tagged Docker images to container registry (e.g., GHCR)
# ==============================================================================
set -euo pipefail

SERVICE="${1:-}"
if [[ -z "${SERVICE}" || ( "${SERVICE}" != "backend" && "${SERVICE}" != "frontend" ) ]]; then
    echo "Usage: $0 <backend|frontend> [IMAGE_TAG] [REGISTRY_PREFIX]" >&2
    echo "Example: $0 backend \$(git rev-parse HEAD) ghcr.io/myorg/uka" >&2
    exit 1
fi

GIT_COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo "latest")"
IMAGE_TAG="${2:-${GIT_COMMIT_SHA}}"
REGISTRY_PREFIX="${3:-}"

if [[ -z "${REGISTRY_PREFIX}" ]]; then
    echo "ERROR: REGISTRY_PREFIX is required to push images (e.g. ghcr.io/owner/repo)." >&2
    exit 1
fi

BASE_NAME="university-knowledge-assistant-${SERVICE}"
TARGET_IMAGE="${REGISTRY_PREFIX}/${BASE_NAME}"

echo "=================================================="
echo "Pushing Docker Image to Registry"
echo "Target Image SHA Tag:    ${TARGET_IMAGE}:${IMAGE_TAG}"
echo "Target Image Latest Tag: ${TARGET_IMAGE}:latest"
echo "=================================================="

docker push "${TARGET_IMAGE}:${IMAGE_TAG}"
docker push "${TARGET_IMAGE}:latest"

echo "✓ Docker image '${TARGET_IMAGE}' pushed successfully."
