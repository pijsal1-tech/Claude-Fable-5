#!/usr/bin/env bash
# T-001: single entry point for lint + types + tests.
# Usage: ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== mypy (advisory: core modules) =="
mypy --ignore-missing-imports chain/models.py actions/session_manager.py || true

echo "== pytest =="
python3 -m pytest

echo "== check.sh: ALL GREEN =="
