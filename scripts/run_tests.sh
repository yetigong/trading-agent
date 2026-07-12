#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-}:$ROOT"

PYTHON="${ROOT}/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Missing venv at $PYTHON. Run: python3 -m venv .venv && pip install -r requirements.txt" >&2
  exit 1
fi

# Unit / mock tests only (top-level tests/). Live API checks live under
# tests/integration/ and are opt-in so pre-commit is not blocked by optional
# provider credit/model issues.
UNIT_TESTS=(tests/test_*.py)
"$PYTHON" -m unittest "${UNIT_TESTS[@]}" -v

if [ "${RUN_INTEGRATION:-0}" = "1" ]; then
  echo "Running live integration tests..."
  "$PYTHON" -m unittest discover -s tests/integration -p 'test_*.py' -v
fi
