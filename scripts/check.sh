#!/usr/bin/env bash
# T-001: single entry point for lint + types + tests.
# Usage: ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# T-010: mypy gate (كان advisory) — يفشل السكريبت لو ظهرت أخطاء types
# في providers/ أو chain/. عند إضافة provider جديد راجع أيضًا
# tests/contracts/provider_contract.py (ProviderContractMixin) وأضف صنفه هناك.
echo "== mypy (gate: providers/ + chain/ + core/ + context/) =="
mypy --ignore-missing-imports --follow-imports=silent providers/ chain/ core/ context/

echo "== pytest =="
python3 -m pytest

echo "== check.sh: ALL GREEN =="
