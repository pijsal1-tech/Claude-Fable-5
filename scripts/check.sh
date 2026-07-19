#!/usr/bin/env bash
# T-001: single entry point for lint + types + tests.
# Usage: ./scripts/check.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# T-010: mypy gate (كان advisory) — يفشل السكريبت لو ظهرت أخطاء types
# في providers/ أو chain/. عند إضافة provider جديد راجع أيضًا
# tests/contracts/provider_contract.py (ProviderContractMixin) وأضف صنفه هناك.
# T-027 (R-301): sessions/ انضمت للبوابة — وحدة إنتاجية جديدة.
echo "== mypy (gate: providers/ + chain/ + core/ + context/ + sessions/) =="
mypy --ignore-missing-imports --follow-imports=silent providers/ chain/ core/ context/ sessions/

# T-026 (R-204): حدود SafeReader — ممنوع أي قراءة خام لمحتوى ملفات داخل
# context/ خارج safe_reader.py. حدود مُلتفّ عليها في مكان واحد ليست حدودًا.
# (نستثني نداء بوابة SafeReader نفسها: reader.read_text / self._reader.read_text)
echo "== SafeReader boundary grep (context/ has no raw reads) =="
violations=$(grep -rn 'open(\|\.read_text(\|\.read_bytes(' context/ --include='*.py' \
  | grep -v '^context/safe_reader\.py:' \
  | grep -v 'reader\.read_text(' || true)
if [ -n "$violations" ]; then
  echo "SafeReader boundary violation — raw read in context/ outside safe_reader.py:"
  echo "$violations"
  exit 1
fi
echo "boundary clean"

# T-035 (R-401): مفردات التوجيه موحّدة في core/strategy.py — ممنوع أي
# مقارنة نصية حرة لأسماء الاستراتيجيات في كود الإنتاج (المقارنات عبر
# أعضاء RouteLabel/ExecutionStrategy فقط؛ ‎.value مسموح للسلك/الحدود).
echo "== strategy vocabulary grep (no free-string strategy comparisons) =="
strategy_violations=$(grep -rn \
  -e '== "direct"' -e '== "auto_chain"' -e '== "full_chain"' \
  -e '== "delegate"' -e '== "context_window"' -e '== "chunk_chain"' \
  -e '== "map_reduce"' -e '== "pipeline"' \
  -e 'in ("auto_chain"' -e "in ('auto_chain'" \
  --include='*.py' chain/ core/ providers/ context/ sessions/ server.py \
  || true)
if [ -n "$strategy_violations" ]; then
  echo "strategy vocabulary violation — free-string comparison found:"
  echo "$strategy_violations"
  exit 1
fi
echo "vocabulary clean"

# T-036 (R-402): العتبات مصدرها config فقط — ممنوع إعادة إدخال ثوابت
# العتبات المضمّنة في الراوتر (RoutingThresholds هي المصدر الوحيد).
echo "== routing thresholds grep (no inline threshold constants) =="
threshold_violations=$(grep -rn \
  -e 'DIRECT_THRESHOLD' -e 'AUTO_CHAIN_THRESHOLD' \
  -e 'FULL_CHAIN_THRESHOLD' -e 'MIN_ACCOUNTS_' \
  --include='*.py' chain/ core/ providers/ context/ sessions/ server.py \
  || true)
if [ -n "$threshold_violations" ]; then
  echo "inline routing threshold constant found — use config routing: section:"
  echo "$threshold_violations"
  exit 1
fi
echo "thresholds clean"

echo "== pytest =="
python3 -m pytest

echo "== check.sh: ALL GREEN =="
