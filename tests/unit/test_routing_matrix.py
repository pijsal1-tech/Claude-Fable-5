# -*- coding: utf-8 -*-
"""AIA-6 (CEV-G8.5): مصفوفة التوجيه — corpus النوايا الدائم.

قلب «كل طلب يصل للبرومبت الصحيح»: `chain/router.py` حتمي (Python خالص)
فقرارات التوجيه قابلة للاختبار في CI **بلا أي نموذج حقيقي** (P-11 كامل).

النوايا الست الإلزامية (مواصفة AIA-6):
  1. لهجة مصرية صريحة
  2. عربي/إنجليزي مختلط في جملة واحدة
  3. غير-ويب (CLI / معالجة بيانات / توثيق)
  4. أمني (مراجعة ثغرة / حقن)
  5. غامض متعدد النوايا (قرار مبرر لا تخمين — RoutingRecord يفسره)
  6. نية واحدة ×3 صياغات (فصحى/مصري/إنجليزي) → نفس الوجهة (R12 جزء CI)

نمط T-034 (stub دائم): كل حالة تُثبِّت **السلوك الفعلي الصادق** كما قيس
حيًّا (S108) — بما فيه الفجوات الموثَّقة كـFindings:
  - CEV-F-015: «أعد هيكلة» (بلا مصدر) و«ريفاكتور» (معرَّبة صوتيًا) لا
    تلتقطهما أنماط _COMPLEX_REQUEST_PATTERNS بينما «إعادة هيكلة» و
    «refactor» تُلتقطان → نفس النية تصل طبقة أدنى. الاختباران الموسومان
    أدناه يثبتان الفجوة **كما هي** (توثيق لا موافقة) — يخضرّان معكوسَين
    عند تنفيذ TSK-CEV-104.

R9/R10: انظر جدول المصفوفة في docs/engineering/AIA_ROUTING_MATRIX.md —
هذا الملف هو الإثبات التنفيذي لصفه «قابل للـCI».
"""
from __future__ import annotations

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from chain.orchestrator import SmartOrchestrator      # noqa: E402
from chain.router import RequestRouter                # noqa: E402
from providers.budget import BudgetSnapshot           # noqa: E402


# ═══════════════ مدخلات حتمية (نمط harness T-034) ═══════════════

def _lines(n: int) -> str:
    return "\n".join(f"line {i}: pass" for i in range(n))


class _FixedBudget:
    def __init__(self, per_provider: dict[str, int]):
        total = sum(per_provider.values())
        best = max(per_provider, key=lambda k: per_provider[k]) \
            if per_provider else ""
        self._snap = BudgetSnapshot(
            total_available=total, per_provider=dict(per_provider),
            best_provider=best, cheapest_provider=best)

    def check(self) -> BudgetSnapshot:
        return self._snap


PLENTY = {"use_ai": 10, "genspark": 6}


@pytest.fixture(scope="module")
def router() -> RequestRouter:
    return RequestRouter(SmartOrchestrator(), _FixedBudget(PLENTY))


@pytest.fixture(scope="module")
def orch() -> SmartOrchestrator:
    return SmartOrchestrator()


# ═══════════════ 1) لهجة مصرية صريحة ═══════════════

class TestIntentEgyptianDialect:
    REQ = "عايزك تظبطلي الفورم دي، الزرار مش شغال لما بادوس عليه"

    def test_small_fix_routes_direct(self, router):
        """إصلاح صغير بالعامية بلا ملف → direct (score=0 — لا أنماط)."""
        d = router.route(self.REQ, mode="build")
        assert d.strategy == "direct"
        assert d.complexity_score == 0.0
        assert d.record is not None and d.record.matched_signals == {}

    def test_with_medium_file_still_direct(self, router):
        """ملف 600 سطر (size=2.0 = حد direct_max بالضبط) → direct."""
        d = router.route(self.REQ, mode="build", file_content=_lines(600))
        assert d.strategy == "direct"
        assert d.complexity_score == 2.0

    def test_dialect_neutrality_score_equals_msa(self, router):
        """حياد اللهجة في الدرجة: نفس الطلب فصحى = نفس score/وجهة."""
        msa = "أريد إصلاح هذا النموذج، الزر لا يعمل عند الضغط عليه"
        d_egy = router.route(self.REQ, mode="build", file_content=_lines(600))
        d_msa = router.route(msa, mode="build", file_content=_lines(600))
        assert d_egy.strategy == d_msa.strategy
        assert d_egy.complexity_score == d_msa.complexity_score


# ═══════════════ 2) عربي/إنجليزي مختلط ═══════════════

class TestIntentMixedArabicEnglish:
    REQ = "اعمل refactor للـ authentication module وخلي الـ tokens في env"

    def test_text_only_direct_with_signal(self, router):
        """نص فقط: نمط refactor يُلتقط (1.5) لكن يبقى ≤ direct_max."""
        d = router.route(self.REQ, mode="build")
        assert d.strategy == "direct"
        assert d.complexity_score == 1.5
        assert "refactor" in d.record.matched_signals["request_complexity"]

    def test_multi_file_project_reaches_delegate(self, router):
        """4 ملفات ×700 سطر → score=9.5 > full_chain_max → delegate."""
        files = {f"src/m{i}.py": _lines(700) for i in range(4)}
        d = router.route(self.REQ, mode="build", files=files)
        assert d.strategy == "delegate"
        assert d.complexity_score == 9.5
        assert d.chain_strategy == "pipeline"
        # القرار مفسَّر: الإشارة الإنجليزية داخل الجملة المختلطة موثقة
        assert "refactor" in d.record.matched_signals["request_complexity"]


# ═══════════════ 3) غير-ويب: CLI / بيانات / توثيق ═══════════════

class TestIntentNonWeb:
    def test_cli_data_processing_direct(self, router):
        """CLI + CSV: لا أنماط تعقيد/مخاطر → direct نظيف."""
        d = router.route(
            "اكتب سكربت CLI بايثون يقرأ CSV ويطلع إحصائيات لكل عمود",
            mode="build")
        assert d.strategy == "direct"
        assert d.record.matched_signals == {}

    def test_docs_request_direct(self, router):
        d = router.route("أضف docstrings لكل الدوال في الملف ده",
                         mode="build")
        assert d.strategy == "direct"

    def test_non_web_scales_by_size_not_domain(self, router):
        """غير-ويب يخضع لنفس سلّم الحجم — الحياد المجالي للراوتر."""
        files = {f"data/etl_{i}.py": _lines(900) for i in range(7)}
        d = router.route(
            "اكتب pipeline معالجة بيانات يقرأ CSV وينظفها ويجمعها",
            mode="build", files=files)
        assert d.strategy in {"full_chain", "delegate"}
        assert d.complexity_score >= 8.0


# ═══════════════ 4) أمني: ثغرة / حقن ═══════════════

class TestIntentSecurity:
    REQ = ("راجع الكود ده — في احتمال SQL injection في دالة login "
           "وعايز تقرير أمان")

    def test_risk_signals_captured(self, router):
        """login + أمان يُلتقطان في matched_signals['risk']."""
        d = router.route(self.REQ, mode="build")
        risk = d.record.matched_signals.get("risk", [])
        assert r"\blogin\b" in risk
        assert "أمان" in risk

    def test_with_vulnerable_file_auto_chain(self, router):
        """ملف فيه دالة login → risk من الطلب والملف → auto_chain=3.5."""
        vuln = ("def login(u,p):\n"
                "    q = 'SELECT * FROM users WHERE name=%s' % u\n"
                + _lines(300))
        d = router.route(self.REQ, mode="build", file_content=vuln)
        assert d.strategy == "auto_chain"
        assert d.complexity_score == 3.5
        assert d.chain_strategy == "context_window"


# ═══════════════ 5) غامض متعدد النوايا ═══════════════

class TestIntentAmbiguousMultiIntent:
    REQ = ("الموقع بطيء وفي bug في تسجيل الدخول وكمان عايز أضيف "
           "صفحة جديدة")

    def test_text_only_direct_low_risk_signal(self, router):
        """الغموض النصي وحده لا يغيّر الاستراتيجية — تبقى direct.

        تاريخيًا كان هذا الاختبار يثبّت أن «تسجيل الدخول» غير مغطاة
        (درجة 0.0)؛ TSK-CEV-104 (F-015، بموجب D-15) أضافتها إلى
        _HIGH_RISK_PATTERNS فصارت إشارة خطر واحدة = 0.5 — دون أي
        تغيير في القرار النهائي (direct)."""
        d = router.route(self.REQ, mode="build")
        assert d.strategy == "direct"
        assert d.complexity_score == 0.5
        assert d.record.matched_signals.get("risk")  # الإشارة موثقة

    def test_project_context_justified_delegate(self, router):
        """مع مشروع 7 ملفات: قرار مبرر لا تخمين — RoutingRecord يوثق
        أن الدرجة بنيوية في أساسها (حجم+عدد = 9.0) مع إشارة خطر
        نصية واحدة (0.5) أضافتها TSK-CEV-104 («تسجيل الدخول»)."""
        files = {f"src/p{i}.py": _lines(900) for i in range(7)}
        d = router.route(self.REQ, mode="build", files=files)
        assert d.strategy == "delegate"
        assert d.complexity_score == 9.5
        r = d.record
        assert r.scores["size_score"] == 5.0
        assert r.scores["file_count_score"] == 4.0
        assert list(r.matched_signals) == ["risk"]  # نمط 104 فقط
        assert r.ideal == "delegate" and r.downgrade_path == []


# ═══════════════ 6) نية واحدة ×3 صياغات → نفس الوجهة (R12) ═══════════════

TRIPLE_PHRASINGS = {
    "msa": "أعد هيكلة وحدة المصادقة بالكامل ونقل الرموز إلى ملف البيئة",
    "egy": "اعملي إعادة هيكلة لموديول المصادقة كله وانقل التوكنز لملف الـ env",
    "en": ("refactor the whole authentication module and migrate tokens "
           "to the env file"),
}


class TestTriplePhrasingConsistency:
    def test_all_three_reach_same_destination(self, router):
        """فصحى/مصري/إنجليزي بنفس السياق → نفس (strategy, score, chain)."""
        decisions = {
            k: router.route(req, mode="build", file_content=_lines(2500))
            for k, req in TRIPLE_PHRASINGS.items()
        }
        outcomes = {(d.strategy, d.complexity_score, d.chain_strategy)
                    for d in decisions.values()}
        assert outcomes == {("full_chain", 6.0, "chunk_chain")}, decisions

    def test_all_three_same_agent_roles(self, orch):
        """نفس تسلسل الأدوار عبر الصياغات الثلاث (اتساق R12)."""
        role_seqs = set()
        for req in TRIPLE_PHRASINGS.values():
            sel = orch.select_strategy(req, file_content=_lines(2500))
            role_seqs.add(tuple(s.agent_role for s in sel.steps))
        assert role_seqs == {
            ("code_analyzer", "code_analyzer", "planner", "executor")}

    def test_each_phrasing_has_matched_signal(self, router):
        """كل صياغة أشعلت نمط تعقيد واحدًا على الأقل — الاتساق ليس
        صدفة صفرية بل التقاط فعلي بالثلاث لغات."""
        for k, req in TRIPLE_PHRASINGS.items():
            d = router.route(req, mode="build", file_content=_lines(2500))
            assert d.record.matched_signals.get("request_complexity"), k


# ═══════════════ CEV-F-015: فجوة المعجم — مثبتة كما هي ═══════════════

class TestLexiconGapF015:
    """نفس نية إعادة الهيكلة بكل صيغها تصل الطبقة نفسها (F-015 مُغلقة).

    تاريخ الفجوة (S108، قياس حي): «أعد هيكلة» (فعل أمر بلا مصدر) و
    «ريفاكتور» (معرَّبة صوتيًا) لم تكونا تطابقان
    r\"إعادة.*هيكلة\"/r\"refactor\" ففقدت النية 1.5-2.0 نقطة وهبطت
    auto_chain بدل full_chain. الحسم: TSK-CEV-104 وسّع المعجم
    (D-15) — التأكيدات أدناه هي الاختبارات المثبتة نفسها **معكوسة**
    كما نصّت المهمة (104b: هما معيار القبول الجاهز).
    """

    def test_imperative_msa_catches_pattern(self, router):
        d = router.route("أعد هيكلة هذا الكود بالكامل وقسّمه إلى وحدات",
                         mode="build", file_content=_lines(2500))
        # بعد TSK-CEV-104: فعل الأمر يلتقط ⇒ نفس طبقة صيغة المصدر
        assert d.strategy == "full_chain"
        assert d.record.matched_signals.get("request_complexity")

    def test_transliterated_refactor_catches_pattern(self, router):
        d = router.route("اعمل ريفاكتور شامل للكود ده كله",
                         mode="build", file_content=_lines(2500))
        assert d.strategy == "full_chain"
        assert d.record.matched_signals.get("request_complexity")

    def test_masdar_form_catches_pattern_baseline(self, router):
        """الخط المرجعي المقابل: صيغة المصدر «إعادة هيكلة» تُلتقط —
        الفارق بين الاختبارين هو نص الفجوة F-015 حرفيًّا."""
        d = router.route("اعملي إعادة هيكلة للكود ده كله وقسمه لوحدات",
                         mode="build", file_content=_lines(2500))
        assert d.strategy == "full_chain"
        assert d.record.matched_signals.get("request_complexity")


# ═══════════════ R10: القدرات المعلنة ↔ حالات corpus ═══════════════

class TestR10CapabilityCorpusLink:
    """كل tier معلن في manifest للأدوار المسندة فعليًا (F-014 الستة)
    له حالة corpus تصل إليه في هذا الملف أو corpus T-034."""

    def test_all_wire_strategies_covered_here(self, router):
        """المفردات الأربع للراوتر كلها مغطاة بحالات هذا الملف."""
        reached = set()
        probes = [
            ("أضف تعليقًا", "build", {}),                       # direct
            (TestIntentSecurity.REQ, "build",
             dict(file_content="def login(u,p): pass\n" + _lines(300))),
            (TRIPLE_PHRASINGS["en"], "build",
             dict(file_content=_lines(2500))),                  # full_chain
            (TestIntentMixedArabicEnglish.REQ, "build",
             dict(files={f"src/m{i}.py": _lines(700) for i in range(4)})),
        ]
        for req, mode, kw in probes:
            reached.add(router.route(req, mode=mode, **kw).strategy)
        assert reached == {"direct", "auto_chain", "full_chain", "delegate"}

    def test_assigned_roles_reachable_via_strategies(self, orch):
        """الأدوار الستة المسندة (F-014) تظهر كلها في خطوات
        الاستراتيجيات القابلة للوصول من select_strategy/build_delegate."""
        from chain.strategies import build_delegate
        roles: set[str] = set()
        for req, kw in [
            ("hi", {}),
            ("fix", dict(file_content=_lines(2500))),
            ("refactor everything across files carefully",
             dict(files={f"m{i}.py": _lines(900) for i in range(7)})),
        ]:
            sel = orch.select_strategy(req, **kw)
            roles.update(s.agent_role for s in sel.steps)
        roles.update(s.agent_role for s in build_delegate("task").steps)
        assert {"executor", "code_analyzer", "planner", "deep_debugger",
                "architect", "code_reviewer"} <= roles


class TestLibraryRolesF014:
    """حسم CEV-F-014 (بموجب D-16 طابور البند 3): الأدوار الـ15 غير
    الموصولة بالاستراتيجيات مُسندة رسميًا بصفة **أدوار مكتبة**
    (manual-load library) — مسار وصولها المعتمد هو load(role) API
    الحقيقي، لا التوجيه الآلي. هذا الاختبار يثبّت الإسناد تنفيذيًا:
    كل دور مكتبة موجود في الـmanifest ويُحمَّل فعليًا ببرومبت غير فارغ.
    شطبها رُفض (ملفات ذكاء مالك — سابقة D-8-أ) وربطها بالتوجيه رُفض
    (اختراع إسناد دلالي بلا حاجة — عكس منطق AIA-6)."""

    LIBRARY_ROLES = frozenset({
        "bug_analyzer", "api_analyzer", "security_analyzer",
        "perf_analyzer", "request_analyzer", "quality_guard",
        "backend_dev", "frontend_dev", "quality_reviewer",
        "vibe_reviewer", "evidence_reviewer", "compat_reviewer",
        "orchestrator", "review_manager", "team_manager",
    })
    STRATEGY_ROLES = frozenset({
        "executor", "code_analyzer", "planner", "deep_debugger",
        "architect", "code_reviewer",
    })

    @pytest.fixture(scope="class")
    def loader(self):
        from chain.agent_loader import AgentLoader
        return AgentLoader(agents_dir=REPO_ROOT / "agents_rules")

    def test_partition_is_exhaustive_and_disjoint(self, loader):
        """مكتبة (15) + استراتيجيات (6) = كل أدوار الـmanifest (21) بلا تقاطع."""
        available = set(loader.get_available_roles())
        assert self.LIBRARY_ROLES | self.STRATEGY_ROLES == available
        assert not (self.LIBRARY_ROLES & self.STRATEGY_ROLES)

    @pytest.mark.parametrize("role", sorted(LIBRARY_ROLES))
    def test_library_role_loads_via_public_api(self, loader, role):
        """مسار الإسناد الرسمي: load(role) يعيد برومبت حقيقيًا غير فارغ."""
        prompt = loader.load(role)
        assert prompt.role == role
        assert prompt.content and prompt.content.strip()

    def test_library_roles_absent_from_strategies_source(self):
        """الإسناد مكتبةً يعني: صفر ذكر لأي دور مكتبة في strategies.py —
        ظهور أي منها هناك لاحقًا = ترقية إسناد تتطلب تحديث هذا التثبيت."""
        src = (REPO_ROOT / "chain" / "strategies.py").read_text(encoding="utf-8")
        for role in sorted(self.LIBRARY_ROLES):
            assert role not in src, (
                f"{role} ظهر في strategies.py — حدّث تصنيف F-014")
