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

# T-047 (R-604): النقل معزول — ممنوع أي ws.send خارج المحوّل الوحيد
# (_WSAdapter._send في server.py). المنفّذون ينشرون أحداثًا على الـ
# EventBus فقط. (providers/use_ai.py مستثنى: عميل WS خارجي لمزوّد AI —
# ليس نقل واجهة المستخدم.)
echo "== ws.send boundary grep (transport isolated to _WSAdapter) =="
ws_violations=$(grep -rn 'ws\.send(' --include='*.py' \
  server.py chain/ core/ runners/ actions/ context/ sessions/ \
  | grep -v 'self\._ws\.send(' || true)
if [ -n "$ws_violations" ]; then
  echo "ws.send boundary violation — raw send outside _WSAdapter:"
  echo "$ws_violations"
  exit 1
fi
echo "transport boundary clean"

# T-048 (R-701): الحالة لكل اتصال — ممنوع global أو قراءة حالة وحدوية
# متغيّرة داخل دوال الـ handlers (ws_handler/_handle_ws_message/...).
# القاعدة كاملة في core/session_context.py؛ الفاحص AST-based.
echo "== handler state lint (no module-level mutable state in handlers) =="
python3 scripts/lint_handler_state.py server.py

# T-049 (R-702): مسار كل-رسالة يستعلم ProjectIndex — ممنوع أي نداء
# rglob في كود حزمة context/ (البناء عبر os.walk في engine/index فقط،
# والمصادر تستعلم lookup_* — صفر مشيات شجرية وقت الرسالة).
echo "== rglob ban grep (no rglob calls in context/ per-message paths) =="
rglob_violations=$(grep -rn '\.rglob(' --include='*.py' context/ || true)
if [ -n "$rglob_violations" ]; then
  echo "rglob violation — tree walk in context/ per-message path:"
  echo "$rglob_violations"
  exit 1
fi
echo "rglob clean"

# T-060 (R-905): طبقة توكنز التصميم — ممنوع أي لون خام (hex/rgb/hsl)
# خارج static/themes/. كل استهلاك عبر var(--token) أو color-mix.
echo "== color token lint (no raw colors outside static/themes/) =="
color_violations=$(grep -rnE '#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(' \
  --include='*.css' --include='*.html' --include='*.js' \
  static/ public/ \
  | grep -v '^static/themes/' || true)
if [ -n "$color_violations" ]; then
  echo "raw color outside static/themes/ — use var(--token) / color-mix:"
  echo "$color_violations"
  exit 1
fi
echo "colors clean"

echo "== pytest =="
python3 -m pytest

echo "== check.sh: ALL GREEN =="
