#!/usr/bin/env bash
# ==============================================================================
# scripts/ci/build-docker.sh
# Multi-stage Docker image builder for backend and frontend services
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SERVICE="${1:-}"
if [[ -z "${SERVICE}" || ( "${SERVICE}" != "backend" && "${SERVICE}" != "frontend" ) ]]; then
    echo "Usage: $0 <backend|frontend> [IMAGE_TAG] [REGISTRY_PREFIX]" >&2
    echo "Example: $0 backend \$(git rev-parse HEAD) ghcr.io/myorg/uka" >&2
    exit 1
fi

GIT_COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null || echo "latest")"
IMAGE_TAG="${2:-${GIT_COMMIT_SHA}}"
REGISTRY_PREFIX="${3:-}"

cd "${REPO_ROOT}"

DOCKERFILE="docker/${SERVICE}.Dockerfile"
if [[ ! -f "${DOCKERFILE}" ]]; then
    echo "ERROR: Dockerfile not found at ${DOCKERFILE}" >&2
    exit 1
fi

BASE_NAME="university-knowledge-assistant-${SERVICE}"
if [[ -n "${REGISTRY_PREFIX}" ]]; then
    TARGET_IMAGE="${REGISTRY_PREFIX}/${BASE_NAME}"
else
    TARGET_IMAGE="${BASE_NAME}"
fi

echo "=================================================="
echo "Building Docker Image: ${SERVICE}"
echo "Target Image: ${TARGET_IMAGE}:${IMAGE_TAG}"
echo "Dockerfile:   ${DOCKERFILE}"
echo "Context:      ${REPO_ROOT}"
echo "=================================================="

docker build \
    -f "${DOCKERFILE}" \
    -t "${TARGET_IMAGE}:${IMAGE_TAG}" \
    -t "${TARGET_IMAGE}:latest" \
    "${REPO_ROOT}"

echo "✓ Docker image '${TARGET_IMAGE}:${IMAGE_TAG}' built successfully."
