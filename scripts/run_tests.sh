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

# Unit / mock tests by package. Live API checks live under tests/integration/
# and are opt-in so pre-commit is not blocked by optional provider credit/model issues.
echo "strategy_learning unit tests..."
"$PYTHON" -m unittest discover -s strategy_learning/tests -p 'test_*.py' -v

echo "trading_agent unit tests..."
"$PYTHON" -m unittest discover -s trading_agent/tests -p 'test_*.py' -v

echo "cross-package / shared unit tests..."
# Top-level only — do not recurse into tests/integration/
shopt -s nullglob
CROSS_TESTS=(tests/test_*.py)
if [ ${#CROSS_TESTS[@]} -gt 0 ]; then
  "$PYTHON" -m unittest "${CROSS_TESTS[@]}" -v
fi

if [ "${RUN_INTEGRATION:-0}" = "1" ]; then
  echo "Running live integration tests..."
  "$PYTHON" -m unittest discover -s tests/integration -p 'test_*.py' -v
fi
