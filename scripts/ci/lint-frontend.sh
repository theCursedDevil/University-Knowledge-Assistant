#!/usr/bin/env bash
# ==============================================================================
# scripts/ci/lint-frontend.sh
# Lint frontend Next.js codebase using ESLint (portable CI & local script)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}/frontend"

echo "=================================================="
echo "Running Frontend Linting (next lint)"
echo "=================================================="

npm run lint
echo "✓ Frontend linting passed cleanly with 0 errors."
