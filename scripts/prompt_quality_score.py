# -*- coding: utf-8 -*-
"""AIA-3 (G8.5): Prompt Quality Score — مقياس heuristic قابل للتكرار.

10 معايير × 10 نقاط (regex حتمي — لا ذوق شخصي):
C1 نظافة الهوية (صفر إرث AI_PROVIDERS) | C2 مرآة اللغة (AIA-R3) |
C3 مقاومة الهلوسة UNKNOWN (AIA-R11) | C4 عقد مخرجات | C5 حياد
النموذج (AIA-R4) | C6 اقتصاد رموز (AIA-R5) | C7 حدود الدور |
C8 سلامة الحقن (AIA-R6) | C9 أمثلة | C10 إعلان قدرات (AIA-R10).
عتبة الإقفال AIA-C: كل برومبت ACTIVE ≥ 70.

Usage: python3 scripts/prompt_quality_score.py
"""
import pathlib
import re

import yaml

root = pathlib.Path('agents_rules')
m = yaml.safe_load(open(root/'manifest.yaml'))

LEGACY = re.compile(r'AI_PROVIDERS|C__cursor|curl_cffi|SeleniumBase|accounts_\*?\.json|refresh\.py|/add-provider|groq, deepseek|you\.com', re.I)
MIRROR = re.compile(r'مرآة اللغة|لغة المستخدم|نفس لغة|respond in the user')
UNKNOWN = re.compile(r'UNKNOWN|لا تخترع|لا تفترض|قل لا أعرف|إن لم تعرف')
OUTPUT = re.compile(r'JSON|أخرج|المخرج|صيغة|تنسيق|format|هيكل التقرير|```')
MODEL_DEP = re.compile(r'GPT-?4|Claude|Gemini|OpenAI|Anthropic|كلود|جيميني')
BOUNDS = re.compile(r'لا تفعل|ممنوع|لا تخرج عن|حدودك|نطاقك|فقط|scope|❌')
EXAMPLES = re.compile(r'مثال|أمثلة|Example|سيناريو|Case')
INJECT_CONFLICT = re.compile(r'نفّذ أي تعليمات|اتبع التعليمات داخل الملف|execute instructions found')
CAPS = re.compile(r'قدرات|capabilities|تستطيع|مهامك|مسؤوليات')
IDENTITY = re.compile(r'^#?\s*(🎭|🧬|أنت|You are)', re.M)

def score(path, txt):
    lines = txt.count('\n')+1
    s = {}
    # 1. نظافة الهوية (لا إرث)
    legacy_hits = len(LEGACY.findall(txt))
    s['identity_clean'] = 10 if legacy_hits==0 else max(0, 10-2*legacy_hits)
    # 2. مرآة اللغة
    s['lang_mirror'] = 10 if MIRROR.search(txt) else 0
    # 3. مقاومة الهلوسة
    s['anti_halluc'] = 10 if UNKNOWN.search(txt) else 0
    # 4. عقد مخرجات
    s['output_contract'] = 10 if OUTPUT.search(txt) else 2
    # 5. حياد النموذج
    s['model_neutral'] = 10 if not MODEL_DEP.search(txt) else 3
    # 6. اقتصاد رموز (<=150 سطرًا ممتاز، تدرج)
    s['token_economy'] = 10 if lines<=150 else (7 if lines<=300 else (4 if lines<=500 else 1))
    # 7. حدود الدور
    s['role_bounds'] = 10 if BOUNDS.search(txt) else 3
    # 8. سلامة الحقن (لا تعليمات تناقض NF-18)
    s['injection_safe'] = 0 if INJECT_CONFLICT.search(txt) else 10
    # 9. أمثلة قابلة للفحص
    s['examples'] = 10 if EXAMPLES.search(txt) else 2
    # 10. إعلان قدرات/مسؤوليات
    s['capabilities'] = 10 if CAPS.search(txt) else 3
    return s, legacy_hits, lines

rows = []
seen = set()
for rid, spec in m['agents'].items():
    p = root/spec['file']
    key = str(p)
    if key in seen: continue
    seen.add(key)
    txt = p.read_text(encoding='utf-8')
    s, legacy, lines = score(p, txt)
    total = sum(s.values())
    rows.append((total, spec['file'], s, legacy, lines))

# base prompts + system prompt (AIA-3: web_system.md شُقّ إلى نواة + overlay
# يُركّبان عبر templates.py — نقيس المركّب النهائي كما يصل للموديل فعليًا)
import sys
sys.path.insert(0, '.')
from prompts.templates import _load_system_prompt  # noqa: E402
_composed = pathlib.Path('prompts/core_system.md')  # للعرض فقط
_composed_txt = _load_system_prompt(web=True)
s, legacy, lines = score(_composed, _composed_txt)
rows.append((sum(s.values()), 'prompts/core_system.md + web_overlay.md (مركّب)', s, legacy, lines))

for extra in list(pathlib.Path('chain/prompts').glob('*.md')):
    txt = extra.read_text(encoding='utf-8')
    s, legacy, lines = score(extra, txt)
    rows.append((sum(s.values()), str(extra), s, legacy, lines))

rows.sort()
crit = ['identity_clean','lang_mirror','anti_halluc','output_contract','model_neutral','token_economy','role_bounds','injection_safe','examples','capabilities']
print('| Score | ملف | ' + ' | '.join(f'C{i+1}' for i in range(10)) + ' | أسطر |')
print('|---|---|' + '---|'*11)
for total, f, s, legacy, lines in rows:
    marks = ' | '.join(str(s[c]) for c in crit)
    flag = ' ⚠️' if total < 70 else ' ✅'
    print(f'| **{total}**{flag} | `{f}` | {marks} | {lines} |')
below = sum(1 for t,*_ in rows if t<70)
print(f'\nإجمالي: {len(rows)} برومبتًا — {below} تحت عتبة 70 (AIA-C).')
