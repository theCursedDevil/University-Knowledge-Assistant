#!/usr/bin/env bash
# ==============================================================================
# scripts/ci/test-backend.sh
# Execute backend automated test suite using pytest (portable CI & local script)
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "${REPO_ROOT}"

echo "=================================================="
echo "Running Backend Test Suite (pytest)"
echo "=================================================="

# Check if pytest is available in PATH or .venv
if command -v pytest &> /dev/null; then
    PYTEST_BIN="pytest"
elif [[ -x "${REPO_ROOT}/.venv/bin/pytest" ]]; then
    PYTEST_BIN="${REPO_ROOT}/.venv/bin/pytest"
else
    echo "ERROR: 'pytest' not found in PATH or .venv. Please install pytest." >&2
    exit 1
fi

export PYTHONPATH="${REPO_ROOT}"

# If specific arguments are provided, pass them to pytest; otherwise run test suite
if [[ $# -gt 0 ]]; then
    "${PYTEST_BIN}" "$@"
else
    "${PYTEST_BIN}" backend/tests/test_health.py \
                    backend/tests/test_auth_admin.py \
                    backend/tests/test_citations.py \
                    backend/tests/test_security_requirements.py \
                    backend/tests/test_conversations.py \
                    backend/tests/test_admin_console.py \
                    backend/tests/test_role_restricted_documents.py \
                    -v --tb=short
fi

echo "✓ Backend automated tests passed successfully."
