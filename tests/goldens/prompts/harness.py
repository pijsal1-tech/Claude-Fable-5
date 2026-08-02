# -*- coding: utf-8 -*-
"""AIA-R8 (G8.5/S108): harness الـ corpus الذهبي للبرومبتات المجمَّعة.

يثبّت — قبل أول إعادة كتابة في AIA-3 — ما يصل للنموذج فعليًا في
مسار السلاسل، بلا نموذج حقيقي (P-11):

1. قرار التوجيه: ``SmartOrchestrator.select_strategy`` → اسم
   الاستراتيجية + بنية الخطوات (stage/agent_role/depends_on/
   context_policy/critical).
2. الـ system prompt النهائي لكل خطوة: ما يحمّله ``AgentLoader``
   من manifest (نفس ما يمرره executor.py:441 لـ ProviderRequest).
3. الـ user prompt النهائي لكل خطوة: ``ChainStep.build_prompt``
   بنتائج تبعيات حتمية ثابتة.

أي فرق لاحق في هذه اللقطات = diff يُصنَّف يدويًا:
تحسين مقصود / محايد / انحدار (AIA-R8) — كسر متعمد يسبقه ADR.

حتمية القياس: sha256 للنصوص الكبيرة (system prompts) + النص الكامل
لقوالب الخطوات (قصيرة) — نفس مبدأ parity بايت-بايت في T-020.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.agent_loader import AgentLoader  # noqa: E402
from chain.orchestrator import SmartOrchestrator  # noqa: E402

GOLDEN_PATH = pathlib.Path(__file__).parent / "prompt_corpus.golden.json"

# سيناريوهات تغطي مفردات التوجيه (نفس روح T-034) + المسار المفوَّض.
# النصوص ثابتة حرفيًا — تعديلها = تعديل corpus (يستلزم إعادة التقاط
# مقصودة + تصنيف الفرق).
SCENARIOS: dict[str, dict] = {
    "direct_simple": {
        "request": "اشرح الفرق بين list و tuple في بايثون",
    },
    "analyze_file": {
        "request": "حلل جودة هذا الملف واقترح تحسينات",
        "file_content": "def add(a, b):\n    return a + b\n",
        "file_path": "utils/math_helpers.py",
    },
    "multi_file_task": {
        "request": "أضف معالجة أخطاء موحدة لكل الدوال في هذه الملفات",
        "files": {
            "app/io_ops.py": "def read_cfg(p):\n    return open(p).read()\n",
            "app/net_ops.py": "def fetch(u):\n    import urllib.request\n    return urllib.request.urlopen(u).read()\n",
        },
    },
    "debug_deep": {
        "request": "التطبيق بينهار عند الإغلاق برسالة RuntimeError: Event loop is closed — حقق في السبب الجذري وأصلحه",
        "file_content": "import asyncio\n\nasync def shutdown(loop):\n    loop.stop()\n",
        "file_path": "core/lifecycle.py",
    },
    "big_refactor_pipeline": {
        "request": "أعد هيكلة طبقة التخزين كاملة من JSON ملفات إلى SQLite مع الحفاظ على الواجهة العامة كما هي وكتابة اختبارات",
        "file_content": "class Store:\n    def save(self, key, value):\n        ...\n" * 40,
        "file_path": "storage/store.py",
    },
    # ملف ضخم أحادي → chunk_chain (فوق TOKEN_BUDGET=8000 توكن مقدَّر)
    "huge_single_file": {
        "request": "راجع هذا الملف الضخم بالكامل وحدد كل الدوال المكررة",
        "file_content": ("def handler_%d(payload):\n"
                         "    value = payload.get('k')\n"
                         "    return value\n\n") * 1200 % tuple(range(1200)),
        "file_path": "legacy/mega_handlers.py",
    },
    # 5 ملفات مترابطة → map_reduce
    "many_files_map_reduce": {
        "request": "وحّد أسلوب التسجيل logging عبر كل هذه الوحدات وارصد أي تعارض في مستويات الخطورة",
        "files": {
            f"pkg/mod_{i}.py": ("import logging\n"
                                f"log = logging.getLogger('mod_{i}')\n"
                                "def work():\n"
                                f"    log.info('mod {i} working')\n")
            for i in range(5)
        },
    },
    # مخاطر عالية (auth/DB/migrate) + 3+ أنماط تعقيد + ملف كبير
    # ⇒ score=10.0 > 7.0 ⇒ pipeline (يُثبت الأدوار الأربعة:
    # deep_debugger/architect/executor/code_reviewer) — مقيس حيًا S108.
    "risky_auth_pipeline": {
        "request": ("Refactor the entire auth module and migrate "
                    "password hashing from MD5 to bcrypt, redesign "
                    "the database schema with a safe migration, "
                    "integrate secure session tokens, and add tests "
                    "plus a full security review"),
        "file_content": ("def authenticate(user, password):\n"
                         "    query = \"SELECT * FROM users WHERE name=\" + user\n"
                         "    return db.execute(query)\n\n") * 300,
        "file_path": "auth/security.py",
    },
    # التجاوز اليدوي الصريح → delegate (المسار المفوَّض بلا history)
    "forced_delegate": {
        "request": "نفّذ إضافة أمر تصدير التقارير PDF كما هو موصوف في الـ brief",
        "force_strategy": "delegate",
    },
}

_FIXED_DEP_RESULT = "[نتيجة حتمية ثابتة للتبعية — corpus R8]"


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def run_scenario(name: str) -> dict:
    """سيناريو واحد → لقطة قابلة للتسلسل JSON (حتمية بالكامل)."""
    spec = SCENARIOS[name]
    orch = SmartOrchestrator()
    loader = AgentLoader()

    result = orch.select_strategy(
        spec["request"],
        files=spec.get("files"),
        file_content=spec.get("file_content"),
        file_path=spec.get("file_path", ""),
        force_strategy=spec.get("force_strategy"),
    )

    steps_snapshot = []
    for step in result.steps:
        agent_prompt = loader.load(step.agent_role)
        dep_results = {d: _FIXED_DEP_RESULT for d in step.depends_on}
        dep_meta = {d: {"name": f"step-{d}", "status": "success"}
                    for d in step.depends_on}
        user_prompt = step.build_prompt(dep_results,
                                        dependency_meta=dep_meta)
        steps_snapshot.append({
            "id": step.id,
            "stage": step.stage,
            "agent_role": step.agent_role,
            "agent_prompt_source": agent_prompt.source,
            "system_prompt_sha256": _sha(agent_prompt.content),
            "system_prompt_len": len(agent_prompt.content),
            "depends_on": list(step.depends_on),
            "context_policy": step.context_policy,
            "critical": step.critical,
            "user_prompt": user_prompt,
        })

    return {
        "scenario": name,
        "strategy": result.strategy_name,
        "steps": steps_snapshot,
    }
