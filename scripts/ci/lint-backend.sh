#!/usr/bin/env bash
# ==============================================================================
# scripts/ci/lint-backend.sh
# Lint backend Python codebase using Ruff (portable CI & local script)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

echo "=================================================="
echo "Running Backend Linting (Ruff)"
echo "=================================================="

# Check if ruff binary is available in PATH or .venv
if command -v ruff &> /dev/null; then
    RUFF_BIN="ruff"
elif [[ -x "${REPO_ROOT}/.venv/bin/ruff" ]]; then
    RUFF_BIN="${REPO_ROOT}/.venv/bin/ruff"
else
    echo "ERROR: 'ruff' not found in PATH or .venv. Please install ruff." >&2
    exit 1
fi

echo "Using Ruff: $(${RUFF_BIN} --version)"
"${RUFF_BIN}" check backend/ "$@"
echo "✓ Backend linting passed cleanly with 0 errors."
