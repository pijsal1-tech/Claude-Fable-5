# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  AgentLoader — تحميل agent prompts من agents_rules/

  M1b: Agent Registry
  R-502 (T-042): تعريفات الأسطول كبيانات —
  - ROLE_MAP/ROLE_STAGE_MAP حُذفتا؛ المصدر الوحيد
    agents_rules/manifest.yaml (id → file/stage/…)
  - تحقق schema صارم برسائل تحمل أرقام الأسطر؛
    manifest مكسور عند الإقلاع = فشل فوري صاخب
  - hot-reload: تغيّر mtime للـ manifest يعيد بناء السجل
    (تبديل ذرّي — تعديل مكسور أثناء التشغيل يُبقي السجل
    القديم ويسجّل الخطأ في last_reload_error)
  - كاش الـ prompts بمفتاح (path, mtime) — تعديل ملف
    وكيل منتصف الجلسة يسري في التحميل التالي
  - دور غير معروف أو ملف مفقود = خطأ منظّم صاخب؛
    الـ fallback فقط للأدوار المعلنة `fallback: base`
  - حماية من path traversal + encoding + size (كما كانت)
  - versioning عبر content hash (كما كان)
═══════════════════════════════════════════════════════
"""
import hashlib
import pathlib
import threading
from dataclasses import dataclass

import yaml


# ── حدود أمان ──
MAX_PROMPT_SIZE = 50_000    # 50KB حد أقصى لملف prompt
MAX_PROMPT_LINES = 1000     # حد أقصى للأسطر

# ── مفردات الـ manifest ──
MANIFEST_FILENAME = "manifest.yaml"
MANIFEST_VERSION = 1
VALID_STAGES = ("analyze", "plan", "execute", "review", "meta")
VALID_AGENT_KEYS = frozenset(
    {"file", "stage", "name", "description", "capabilities", "tier", "fallback"}
)


class ManifestError(Exception):
    """
    manifest مرفوض — parse أو schema أو ملفات لا تُحلّ.
    كل رسالة تحمل رقم السطر: "manifest.yaml:12: ...".
    """

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__("\n".join(self.errors))


class UnknownAgentRoleError(Exception):
    """طُلب دور غير معرّف في الـ manifest — خطأ صاخب لا fallback صامت."""


@dataclass(frozen=True)
class AgentDefinition:
    """تعريف وكيل واحد كما ورد في الـ manifest (frozen — يُستبدل لا يُعدّل)."""
    role: str
    file: str
    stage: str
    name: str
    description: str
    capabilities: tuple[str, ...]
    tier: str
    fallback: str | None      # None أو "base"
    line: int                 # رقم سطر التعريف في الـ manifest


@dataclass(frozen=True)
class AgentPrompt:
    """
    prompt محمّل ومعرّف — frozen للأمان والـ caching.

    role: الدور (مثل "code_analyzer")
    stage: المرحلة (analyze / plan / execute / review / meta)
    source: المصدر (agents_rules / base / fallback)
    content: محتوى الـ prompt
    content_hash: sha256 للتحقق والـ cache key
    size_bytes: حجم المحتوى
    line_count: عدد الأسطر
    """
    role: str
    stage: str
    source: str              # "agents_rules" | "base" | "fallback"
    content: str
    content_hash: str
    size_bytes: int
    line_count: int


class AgentLoader:
    """
    يحمّل agent prompts وفق agents_rules/manifest.yaml:
    1. agents_rules/<manifest.file> (الدور المتخصص)
    2. chain/prompts/base_{stage}.md — فقط للأدوار المعلنة
       `fallback: base` عند غياب ملفها
    3. _make_fallback — شبكة أمان أخيرة للسلسلة المعلنة فقط

    دور غير معروف ⇒ UnknownAgentRoleError.
    ملف مفقود بلا fallback معلن ⇒ ManifestError (عند الإقلاع
    بالتحقق الشامل، وعند التحميل لو اختفى الملف لاحقًا).

    حماية:
    - path traversal (../../) ممنوع — يُرفض في تحقق الـ manifest
      وعند التحميل
    - ملفات أكبر من MAX_PROMPT_SIZE مرفوضة
    - encoding errors تُتعامل بـ replace
    """

    def __init__(self, agents_dir: str | pathlib.Path | None = None,
                 base_prompts_dir: str | pathlib.Path | None = None,
                 manifest_path: str | pathlib.Path | None = None):
        """
        agents_dir: مسار agents_rules/ (افتراضي: بجوار chain/)
        base_prompts_dir: مسار chain/prompts/ (افتراضي: chain/prompts/)
        manifest_path: مسار الـ manifest (افتراضي: agents_dir/manifest.yaml)

        الإقلاع fail-fast: manifest مفقود/مكسور/بملفات لا تُحلّ
        يرفع ManifestError من هنا مباشرة.
        """
        if agents_dir is None:
            # agents_rules/ بجوار chain/
            self._agents_dir = pathlib.Path(__file__).resolve().parent.parent / "agents_rules"
        else:
            self._agents_dir = pathlib.Path(agents_dir).resolve()

        if base_prompts_dir is None:
            self._base_dir = pathlib.Path(__file__).resolve().parent / "prompts"
        else:
            self._base_dir = pathlib.Path(base_prompts_dir).resolve()

        if manifest_path is None:
            self._manifest_path = self._agents_dir / MANIFEST_FILENAME
        else:
            self._manifest_path = pathlib.Path(manifest_path).resolve()

        self._lock = threading.Lock()
        # cache للـ prompts المحمّلة — role → (path, mtime, prompt)
        self._cache: dict[str, tuple[pathlib.Path, float, AgentPrompt]] = {}
        self._reload_error: str | None = None

        # ── بناء السجل الأولي — fail fast ──
        self._manifest_mtime = self._stat_manifest_mtime(required=True)
        self._registry: dict[str, AgentDefinition] = self._parse_and_validate()

    # ═══════════════════════════════════════════════════
    #   Public API
    # ═══════════════════════════════════════════════════

    def load(self, role: str) -> AgentPrompt:
        """
        يحمّل prompt لدور معرّف في الـ manifest.

        - hot-reload: يفحص mtime الـ manifest أولًا ويعيد بناء
          السجل لو تغيّر (تعديل مكسور ⇒ يُبقي السجل القديم).
        - كاش بمفتاح (path, mtime): تعديل ملف الوكيل يسري
          في التحميل التالي بلا restart.
        - دور غير معروف ⇒ UnknownAgentRoleError.
        - ملف مفقود: fallback المعلن فقط، وإلا ManifestError.
        """
        registry = self._current_registry()

        definition = registry.get(role)
        if definition is None:
            available = ", ".join(sorted(registry))
            raise UnknownAgentRoleError(
                f"دور غير معرّف في الـ manifest: {role!r} — "
                f"الأدوار المتاحة: {available}"
            )

        # ── محاولة الملف المتخصص (cache بمفتاح path+mtime) ──
        full_path = self._resolve_inside_agents_dir(definition.file)
        if full_path is not None:
            mtime = self._safe_mtime(full_path)
            if mtime is not None:
                cached = self._cache.get(role)
                if cached is not None and cached[0] == full_path and cached[1] == mtime:
                    return cached[2]
                prompt = self._load_from_dir(
                    self._agents_dir, definition.file, role,
                    definition.stage, "agents_rules",
                )
                if prompt is not None:
                    self._cache[role] = (full_path, mtime, prompt)
                    return prompt

        # ── الملف غائب/غير صالح — fallback المعلن فقط ──
        if definition.fallback == "base":
            base_file = f"base_{definition.stage}.md"
            prompt = self._load_from_dir(
                self._base_dir, base_file, role, definition.stage, "base",
            )
            if prompt is not None:
                return prompt
            return self._make_fallback(role, definition.stage)

        raise ManifestError([
            f"{self._manifest_path.name}:{definition.line}: الدور {role!r} "
            f"يشير إلى ملف غير قابل للتحميل: {definition.file!r} "
            f"(ولا يعلن fallback: base)"
        ])

    def load_by_stage(self, stage: str) -> AgentPrompt:
        """
        يحمّل base prompt لـ stage معيّن مباشرةً.
        مفيد لما مفيش agent_role محدد.
        """
        base_file = f"base_{stage}.md"
        prompt = self._load_from_dir(self._base_dir, base_file,
                                     f"base_{stage}", stage, "base")
        if prompt is not None:
            return prompt
        return self._make_fallback(f"base_{stage}", stage)

    def get_available_roles(self) -> list[str]:
        """الأدوار المعرّفة في الـ manifest وملفاتها موجودة فعلًا."""
        registry = self._current_registry()
        available = []
        for role, definition in registry.items():
            full_path = self._resolve_inside_agents_dir(definition.file)
            if full_path is not None and full_path.exists() and full_path.is_file():
                available.append(role)
        return sorted(available)

    def get_role_stage(self, role: str) -> str:
        """يرجع الـ stage لدور معين (من الـ manifest)."""
        registry = self._current_registry()
        definition = registry.get(role)
        if definition is None:
            raise UnknownAgentRoleError(
                f"دور غير معرّف في الـ manifest: {role!r}"
            )
        return definition.stage

    def get_definition(self, role: str) -> AgentDefinition:
        """التعريف الكامل لدور (name/description/capabilities/tier)."""
        registry = self._current_registry()
        definition = registry.get(role)
        if definition is None:
            raise UnknownAgentRoleError(
                f"دور غير معرّف في الـ manifest: {role!r}"
            )
        return definition

    @property
    def last_reload_error(self) -> str | None:
        """آخر خطأ hot-reload (None لو آخر إعادة بناء نجحت)."""
        return self._reload_error

    def clear_cache(self) -> None:
        """تنظيف الـ cache"""
        self._cache.clear()

    # ═══════════════════════════════════════════════════
    #   Registry lifecycle (manifest parse + hot-reload)
    # ═══════════════════════════════════════════════════

    def _current_registry(self) -> dict[str, AgentDefinition]:
        """
        السجل الحالي مع فحص hot-reload:
        - mtime لم يتغيّر ⇒ السجل كما هو (مسار ساخن رخيص).
        - تغيّر ⇒ إعادة parse + validate ثم تبديل ذرّي؛
          فشل الـ parse يُبقي السجل القديم ويسجّل الخطأ.
        """
        with self._lock:
            mtime = self._stat_manifest_mtime(required=False)
            if mtime is None:
                # الـ manifest اختفى — نُبقي السجل القديم ونسجّل
                self._reload_error = (
                    f"{self._manifest_path}: الـ manifest غير موجود — "
                    f"السجل القديم ما زال فعّالًا"
                )
                return self._registry
            if mtime != self._manifest_mtime:
                try:
                    new_registry = self._parse_and_validate()
                except ManifestError as exc:
                    self._reload_error = str(exc)
                else:
                    self._registry = new_registry      # تبديل ذرّي
                    self._cache.clear()
                    self._reload_error = None
                # في الحالتين لا نعيد المحاولة حتى يتغيّر mtime مجددًا
                self._manifest_mtime = mtime
            return self._registry

    def _stat_manifest_mtime(self, required: bool) -> float | None:
        try:
            return self._manifest_path.stat().st_mtime
        except OSError:
            if required:
                raise ManifestError([
                    f"{self._manifest_path}: الـ manifest غير موجود أو غير مقروء "
                    f"— R-502: تعريفات الوكلاء بيانات، بدونها لا يُقلع اللودر"
                ]) from None
            return None

    def _parse_and_validate(self) -> dict[str, AgentDefinition]:
        """
        parse + schema validation برسائل تحمل أرقام الأسطر،
        ثم تحقق شامل أن كل ملف مُعلن يُحلّ داخل agents_dir
        (الأدوار المعلنة fallback: base يُسمح بغياب ملفها).
        """
        try:
            text = self._manifest_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ManifestError(
                [f"{self._manifest_path.name}: تعذّرت القراءة: {exc}"]
            ) from None

        name = self._manifest_path.name
        try:
            root = yaml.compose(text, Loader=yaml.SafeLoader)
        except yaml.YAMLError as exc:
            mark = getattr(exc, "problem_mark", None)
            line = (mark.line + 1) if mark is not None else 0
            raise ManifestError(
                [f"{name}:{line}: خطأ YAML: {getattr(exc, 'problem', exc)}"]
            ) from None

        errors: list[str] = []

        def _line(node: yaml.Node) -> int:
            return node.start_mark.line + 1

        if not isinstance(root, yaml.MappingNode):
            raise ManifestError([f"{name}:1: الجذر يجب أن يكون mapping "
                                 f"بمفتاحي version و agents"])

        version_node: yaml.Node | None = None
        agents_node: yaml.Node | None = None
        for key_node, value_node in root.value:
            key = str(getattr(key_node, "value", ""))
            if key == "version":
                version_node = value_node
            elif key == "agents":
                agents_node = value_node
            else:
                errors.append(f"{name}:{_line(key_node)}: مفتاح غير معروف "
                              f"في الجذر: {key!r}")

        # ── version ──
        if version_node is None:
            errors.append(f"{name}:1: المفتاح المطلوب version مفقود")
        else:
            raw = getattr(version_node, "value", None)
            if not isinstance(version_node, yaml.ScalarNode) or \
                    str(raw) != str(MANIFEST_VERSION):
                errors.append(
                    f"{name}:{_line(version_node)}: version يجب أن يكون "
                    f"{MANIFEST_VERSION} — وجدت: {raw!r}"
                )

        # ── agents ──
        registry: dict[str, AgentDefinition] = {}
        if agents_node is None:
            errors.append(f"{name}:1: المفتاح المطلوب agents مفقود")
        elif not isinstance(agents_node, yaml.MappingNode) or not agents_node.value:
            line = _line(agents_node)
            errors.append(f"{name}:{line}: agents يجب أن يكون mapping غير فارغ")
        else:
            for role_node, body_node in agents_node.value:
                role = str(getattr(role_node, "value", ""))
                role_line = _line(role_node)
                if role in registry:
                    errors.append(f"{name}:{role_line}: دور مكرر: {role!r}")
                    continue
                definition = self._parse_agent(
                    name, role, role_line, body_node, errors
                )
                if definition is not None:
                    registry[role] = definition

        if errors:
            raise ManifestError(errors)

        # ── تحقق الحلّ الشامل: كل ملف يُحلّ داخل agents_dir ──
        for role, definition in registry.items():
            full_path = self._resolve_inside_agents_dir(definition.file)
            if full_path is None:
                errors.append(
                    f"{name}:{definition.line}: الدور {role!r} — المسار "
                    f"{definition.file!r} يهرب خارج agents_rules/ "
                    f"(path traversal مرفوض)"
                )
            elif not (full_path.exists() and full_path.is_file()):
                if definition.fallback != "base":
                    errors.append(
                        f"{name}:{definition.line}: الدور {role!r} — الملف "
                        f"غير موجود: {definition.file!r} "
                        f"(أعلن fallback: base أو أصلح المسار)"
                    )

        if errors:
            raise ManifestError(errors)
        return registry

    def _parse_agent(self, name: str, role: str, role_line: int,
                     body_node: yaml.Node,
                     errors: list[str]) -> AgentDefinition | None:
        """يفكك تعريف وكيل واحد — يجمع الأخطاء بدل الرمي المبكر."""
        if not isinstance(body_node, yaml.MappingNode):
            errors.append(f"{name}:{role_line}: تعريف الدور {role!r} "
                          f"يجب أن يكون mapping")
            return None

        fields: dict[str, yaml.Node] = {}
        for key_node, value_node in body_node.value:
            key = str(getattr(key_node, "value", ""))
            key_line = key_node.start_mark.line + 1
            if key not in VALID_AGENT_KEYS:
                errors.append(f"{name}:{key_line}: الدور {role!r} — "
                              f"مفتاح غير معروف: {key!r}")
                continue
            fields[key] = value_node

        ok = True

        def _scalar(key: str, required: bool = False) -> str | None:
            nonlocal ok
            node = fields.get(key)
            if node is None:
                if required:
                    errors.append(f"{name}:{role_line}: الدور {role!r} — "
                                  f"المفتاح المطلوب {key!r} مفقود")
                    ok = False
                return None
            if not isinstance(node, yaml.ScalarNode) or not str(node.value).strip():
                errors.append(f"{name}:{node.start_mark.line + 1}: "
                              f"الدور {role!r} — {key!r} يجب أن يكون نصًا غير فارغ")
                ok = False
                return None
            return str(node.value)

        file_val = _scalar("file", required=True)
        stage_val = _scalar("stage", required=True)
        if stage_val is not None and stage_val not in VALID_STAGES:
            stage_node = fields["stage"]
            errors.append(
                f"{name}:{stage_node.start_mark.line + 1}: الدور {role!r} — "
                f"stage غير صالح: {stage_val!r} — المسموح: "
                f"{', '.join(VALID_STAGES)}"
            )
            ok = False

        name_val = _scalar("name") or role
        desc_val = _scalar("description") or ""
        tier_val = _scalar("tier") or "core"

        fallback_val = _scalar("fallback")
        if fallback_val is not None and fallback_val != "base":
            fb_node = fields["fallback"]
            errors.append(
                f"{name}:{fb_node.start_mark.line + 1}: الدور {role!r} — "
                f"fallback القيمة الوحيدة المسموحة هي \"base\" — "
                f"وجدت: {fallback_val!r}"
            )
            ok = False

        capabilities: tuple[str, ...] = ()
        caps_node = fields.get("capabilities")
        if caps_node is not None:
            if not isinstance(caps_node, yaml.SequenceNode):
                errors.append(
                    f"{name}:{caps_node.start_mark.line + 1}: الدور {role!r} — "
                    f"capabilities يجب أن تكون قائمة نصوص"
                )
                ok = False
            else:
                caps: list[str] = []
                for item in caps_node.value:
                    if not isinstance(item, yaml.ScalarNode):
                        errors.append(
                            f"{name}:{item.start_mark.line + 1}: الدور "
                            f"{role!r} — عنصر capabilities يجب أن يكون نصًا"
                        )
                        ok = False
                    else:
                        caps.append(str(item.value))
                capabilities = tuple(caps)

        if not ok or file_val is None or stage_val is None:
            return None

        return AgentDefinition(
            role=role,
            file=file_val,
            stage=stage_val,
            name=name_val,
            description=desc_val,
            capabilities=capabilities,
            tier=tier_val,
            fallback=fallback_val,
            line=role_line,
        )

    # ═══════════════════════════════════════════════════
    #   Internal
    # ═══════════════════════════════════════════════════

    def _resolve_inside_agents_dir(self, rel_path: str) -> pathlib.Path | None:
        """يحلّ المسار داخل agents_dir — None لو هرب خارجها أو فشل الحلّ."""
        try:
            full_path = (self._agents_dir / rel_path).resolve()
        except (ValueError, OSError):
            return None
        try:
            full_path.relative_to(self._agents_dir.resolve())
        except ValueError:
            return None
        return full_path

    @staticmethod
    def _safe_mtime(path: pathlib.Path) -> float | None:
        try:
            return path.stat().st_mtime
        except OSError:
            return None

    def _load_from_dir(self, base_dir: pathlib.Path, rel_path: str,
                       role: str, stage: str, source: str) -> AgentPrompt | None:
        """
        يحمّل ملف prompt مع حماية:
        - path traversal
        - حجم الملف
        - encoding
        """
        if not base_dir.exists():
            return None

        # ── حماية path traversal ──
        # نتأكد إن المسار النهائي بيقع جوه base_dir
        try:
            full_path = (base_dir / rel_path).resolve()
        except (ValueError, OSError):
            return None

        # Check: المسار لازم يكون جوه base_dir
        try:
            full_path.relative_to(base_dir.resolve())
        except ValueError:
            # Path traversal attempt!
            return None

        if not full_path.exists() or not full_path.is_file():
            return None

        # ── حماية الحجم ──
        try:
            size = full_path.stat().st_size
        except OSError:
            return None

        if size > MAX_PROMPT_SIZE:
            return None

        # ── قراءة المحتوى ──
        try:
            content = full_path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            return None

        if not content.strip():
            return None

        line_count = content.count("\n") + 1
        if line_count > MAX_PROMPT_LINES:
            # اقطع الملف لو طويل جداً (مع تحذير)
            lines = content.split("\n")[:MAX_PROMPT_LINES]
            content = "\n".join(lines)
            content += f"\n\n[... truncated at {MAX_PROMPT_LINES} lines ...]"
            line_count = MAX_PROMPT_LINES

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        return AgentPrompt(
            role=role,
            stage=stage,
            source=source,
            content=content,
            content_hash=content_hash,
            size_bytes=len(content.encode("utf-8")),
            line_count=line_count,
        )

    def _make_fallback(self, role: str, stage: str) -> AgentPrompt:
        """fallback prompt بسيط لما مفيش ملف (للسلاسل المعلنة فقط)"""
        stage_instructions = {
            "analyze": "حلل الكود التالي واستخرج: الرموز (functions, classes)، العلاقات (imports)، المشاكل المحتملة. أرجع النتيجة بصيغة JSON منظمة.",
            "plan":    "بناءً على التحليل، اكتب خطة تعديل واضحة تحدد: أي ملفات تتعدل، أي أسطر تتغير، ما هو التعديل بالضبط. كن محدداً.",
            "execute": "نفّذ المهمة التالية. أرجع الكود فقط بصيغة EDIT blocks. لا شرح طويل. لا أسئلة.",
            "review":  "راجع الكود/التعديلات التالية. اذكر المشاكل بصيغة JSON: severity, evidence, fix. أرجع verdict: APPROVE / REQUIRES_FIXES / BLOCK.",
            "meta":    "نسّق بين المهام التالية واتخذ القرار المناسب.",
        }
        content = stage_instructions.get(stage, stage_instructions["execute"])
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

        return AgentPrompt(
            role=role,
            stage=stage,
            source="fallback",
            content=content,
            content_hash=content_hash,
            size_bytes=len(content.encode("utf-8")),
            line_count=content.count("\n") + 1,
        )
