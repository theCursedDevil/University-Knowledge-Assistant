#!/usr/bin/env bash
# ==============================================================================
# scripts/deploy/rollback-k8s.sh
# Execute and verify Kubernetes deployment rollback (Prompt 24 / Req 6)
# ==============================================================================
set -euo pipefail

DEPLOYMENT="${1:-backend}"
TARGET_DEPLOYMENT="deployment/${DEPLOYMENT}"

echo "=================================================="
echo "Kubernetes Deployment Rollback"
echo "Target: ${TARGET_DEPLOYMENT}"
echo "=================================================="

if ! command -v kubectl &> /dev/null; then
    echo "ERROR: 'kubectl' not found. Please install kubectl." >&2
    exit 1
fi

if ! kubectl cluster-info --request-timeout=5s &> /dev/null; then
    echo "ERROR: Cannot reach Kubernetes cluster." >&2
    exit 1
fi

echo "Rolling back ${TARGET_DEPLOYMENT} to previous revision..."
kubectl rollout undo "${TARGET_DEPLOYMENT}"

echo "Waiting for rollback rollout to complete..."
kubectl rollout status "${TARGET_DEPLOYMENT}" --timeout=120s

echo -e "\nRollout history for ${TARGET_DEPLOYMENT}:"
kubectl rollout history "${TARGET_DEPLOYMENT}"

echo "✓ Rollback completed and verified successfully for ${TARGET_DEPLOYMENT}."
