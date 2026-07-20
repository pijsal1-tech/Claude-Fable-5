#!/usr/bin/env bash
# T-050 (R-703): تنقية ملفات الجلسات من تاريخ git — git filter-repo.
#
# ⚠️ هذا السكريبت يعيد كتابة التاريخ. **ينفذه مالك الريبو يدويًا** بعد
# تنسيق مع كل من لديه clone (سيحتاجون re-clone — راجع "بعد التنفيذ").
#
# لماذا: 43 ملف جلسة (محادثات مستخدم حقيقية) عاشت متتبَّعة في git.
# T-028 أخرجها من الـ index (git rm --cached) لكنها باقية في **التاريخ**
# — أي clone قديم أو `git log -p` يكشفها. هذا عيب خصوصية (R-703).
#
# ماذا يفعل:
#   1. وسم مرجع ما-قبل-التنقية (pre-purge-tag) — شبكة أمان للتراجع.
#   2. git filter-repo يحذف sessions/*.json (+jsonl/meta) من كل التاريخ
#      **مع إبقاء كود sessions/ الإنتاجي** (__init__.py, store.py, ...).
#   3. تحقق: `git log --all -- 'sessions/*.json'` يجب أن يكون فارغًا.
#   4. تعليمات الدفع القسري المنسّق + إشعار الفريق.
#
# الاستخدام (على clone نظيف حديث):
#   pip install git-filter-repo
#   ./scripts/purge_sessions_history.sh          # تشغيل فعلي
#   DRY_RUN=1 ./scripts/purge_sessions_history.sh  # عرض الخطة فقط
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== T-050: sessions history purge =="

# ── 0. فحوصات أمان ──
if ! command -v git-filter-repo >/dev/null 2>&1 \
   && ! git filter-repo --version >/dev/null 2>&1; then
  echo "ERROR: git-filter-repo غير مثبت — pip install git-filter-repo" >&2
  exit 1
fi
if [ -n "$(git status --porcelain)" ]; then
  echo "ERROR: شجرة العمل غير نظيفة — commit أو stash أولًا." >&2
  exit 1
fi

# ── 1. وسم ما-قبل-التنقية (شبكة الأمان الموصى بها في R-703) ──
TAG="pre-purge-$(date +%Y-%m-%d)"
if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "[dry-run] git tag $TAG"
else
  git tag -f "$TAG"
  echo "safety tag: $TAG (احذفه بعد التأكد: git tag -d $TAG)"
fi

# ── 2. التنقية — بيانات الجلسات فقط، كود sessions/ يبقى ──
#     glob:sessions/*.json يلتقط ملفات الجلسات المسربة (8 هيكس .json)
#     لكنه يلتقط أيضًا أي *.json مباشر — كود الحزمة py فقط فلا تضارب.
PATH_ARGS=(--path-glob 'sessions/*.json'
           --path-glob 'sessions/*.jsonl'
           --path-glob 'sessions/*.meta.json'
           --invert-paths)
if [ "${DRY_RUN:-0}" = "1" ]; then
  echo "[dry-run] git filter-repo ${PATH_ARGS[*]} --force"
  exit 0
fi
git filter-repo "${PATH_ARGS[@]}" --force

# ── 3. التحقق (معيار قبول T-050) ──
LEFT=$(git log --all --oneline -- 'sessions/*.json' 'sessions/*.jsonl' \
       'sessions/*.meta.json' | wc -l)
if [ "$LEFT" -ne 0 ]; then
  echo "ERROR: بقيت $LEFT إشارة لملفات جلسات في التاريخ!" >&2
  exit 1
fi
CODE_FILES=$(git ls-files sessions/ | wc -l)
echo "verification: sessions data history EMPTY ✓ — sessions/ code files kept: $CODE_FILES"

# ── 4. الدفع المنسّق (يدوي — عمدًا ليس في السكريبت) ──
cat <<'EOF'

✅ التنقية تمت محليًا. الخطوات المتبقية (يدوية، منسّقة):

  1. أعد ربط الريموت (filter-repo يفصله عمدًا):
       git remote add origin https://github.com/pijsal1-tech/Claude-Fable-5.git
  2. أعلن للفريق: "force-push قادم — أوقفوا الدفع حتى إشعار".
  3. ادفع قسريًا:  git push origin --force --all && git push origin --force --tags
  4. أبلغ الفريق: كل clone قديم يجب استبداله بـ re-clone نظيف
     (لا pull/rebase فوق التاريخ القديم — سيعيد حقن الملفات المنقّاة).
  5. تحقق على clone جديد:  git log --all -- 'sessions/*.json'  ← فارغ.
  6. احذف وسم الأمان بعد أسبوع هادئ:  git tag -d pre-purge-<date>
EOF
