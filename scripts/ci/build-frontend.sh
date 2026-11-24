#!/usr/bin/env bash
# ==============================================================================
# scripts/ci/build-frontend.sh
# Validate frontend production build and type-checking (portable CI & local script)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}/frontend"

echo "=================================================="
echo "Running Frontend Production Build (next build)"
echo "=================================================="

# Set dummy/build-time environment variables for static optimization
export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000/api/v1}"
export NEXT_PUBLIC_KEYCLOAK_URL="${NEXT_PUBLIC_KEYCLOAK_URL:-http://localhost:8080}"
export NEXT_TELEMETRY_DISABLED=1

npm run build
echo "✓ Frontend production build passed cleanly."
