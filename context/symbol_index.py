# -*- coding: utf-8 -*-
"""SymbolIndex (R-205 / T-055): جداول رموز لكل ملف عبر tree-sitter.

═══════════════════ Symbol Index Design Note ═══════════════════

**المشكلة:** ``ProjectIndex`` (T-049) يفهرس *أسماء الملفات* فقط —
لا يعرف أن ``UserService`` معرَّف في ``services/user.py`` أو أن
``app.js`` يستورد ``./utils``. مطابقة الذكر (mention) على مستوى
الرموز تتطلب فهم بنية الكود، لا أسماء الملفات.

**الحل:** ``SymbolIndex`` — جدول رموز لكل ملف (تعريفات/مراجع/
استيرادات) مبني بمحلّلات ``tree-sitter`` للغات المهيمنة:

| اللغة       | الامتدادات                    | التعريفات المستخرجة              |
|-------------|-------------------------------|----------------------------------|
| Python      | .py                           | function / class / method        |
| JavaScript  | .js .mjs .cjs .jsx            | function / class / method / arrow|
| TypeScript  | .ts / .tsx                    | + interface / type alias        |
| HTML        | .html .htm                    | id / class attributes            |
| CSS         | .css                          | class / id selectors             |

**المراجع (references):** أسماء الاستدعاءات (``call`` /
``call_expression``) — تكفي لسؤال "من يستعمل ``foo``؟" بدقة نحوية
(ليست دلالية — الحسم الدلالي مجال T-057).

**الاستيرادات (imports):** نص الوحدة المستوردة (``import x`` /
``from x import`` / ``import ... from 'm'`` / ``require('m')``).

**التدهور الرشيق (بالتصميم — لا يرفع استثناء أبدًا):**
1. حزم tree-sitter غائبة ⇒ الفهرس يعمل وكل ملف "بلا رموز"
   (``available() == False``) — تبعية اختيارية لا شرط تشغيل.
2. امتداد غير مدعوم ⇒ جدول فارغ، ``language == ""``.
3. فشل قراءة/ملف سري (SafeReader redaction) ⇒ جدول فارغ مع
   ``error`` مرصود.
4. فشل تحليل (ملف معطوب) ⇒ ما استُخرج جزئيًا أو جدول فارغ —
   tree-sitter متسامح مع الأخطاء أصلًا (error nodes).

**الطزاجة:** ``attach(fm)`` يسجّل ``notify_write`` في
``FileManager.add_write_hook`` (نفس نمط ProjectIndex/T-049) —
كل كتابة تُبطل مدخل الكاش فيُعاد التحليل كسولًا عند أول طلب.

**حدود صارمة:**
- كل قراءة محتوى تمر عبر ``SafeReader`` (بوابة R-204 في check.sh) —
  الملفات السرية تصل كـ stub محجوب فتُفهرَس "بلا رموز" لا كنص خام.
- لا ``rglob`` (بوابة check.sh) — الفهرسة الجماعية تأخذ قائمة مسارات
  جاهزة (من ProjectIndex عادةً)، لا مشية شجرية خاصة.
- التحليل كسول + مُكاش (mtime ليس جزءًا من المفتاح — الإبطال عبر
  الخطاف؛ التعديلات الخارجية يلتقطها sweep ProjectIndex في T-056).

**سقف الأداء المتفق عليه (T-055):** بناء فهرس 2000 ملف ≤ 10 ثوانٍ
(القياس الفعلي محليًا ~1-2s؛ الهامش لعتاد CI البارد).
═══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from context.safe_reader import SafeReader

# ═══════════════════ تحميل المحلّلات (مُحصَّن) ═══════════════════
#
# tree-sitter تبعية *اختيارية*: الاستيراد مُحصَّن بالكامل — أي غياب
# أو خطأ تحميل يجعل اللغة (أو الحزمة كلها) غير متاحة بلا استثناء.
# ملاحظة API: حزمة tree_sitter_typescript لا تصدّر ``language()``
# بل ``language_typescript()`` و``language_tsx()`` (خصوصية موثّقة).

_LANGUAGE_FACTORIES: dict[str, Callable[[], Any]] = {}
_TS_AVAILABLE = False

try:  # pragma: no cover - يعتمد على بيئة التثبيت
    from tree_sitter import Language as _TSLanguage
    from tree_sitter import Parser as _TSParser
    _TS_AVAILABLE = True
except Exception:  # pragma: no cover
    _TSLanguage = None  # type: ignore[assignment, misc]
    _TSParser = None    # type: ignore[assignment, misc]

if _TS_AVAILABLE:
    def _try_register(lang_key: str, loader: Callable[[], Any]) -> None:
        try:
            factory = loader()
        except Exception:
            return
        _LANGUAGE_FACTORIES[lang_key] = factory

    _try_register("python", lambda: __import__("tree_sitter_python").language)
    _try_register("javascript",
                  lambda: __import__("tree_sitter_javascript").language)
    _try_register(
        "typescript",
        lambda: __import__("tree_sitter_typescript").language_typescript)
    _try_register(
        "tsx", lambda: __import__("tree_sitter_typescript").language_tsx)
    _try_register("html", lambda: __import__("tree_sitter_html").language)
    _try_register("css", lambda: __import__("tree_sitter_css").language)


#: امتداد الملف → مفتاح اللغة (مصفوفة اللغات المدعومة — وثيقة T-055)
EXTENSION_LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
}


# ═══════════════════ بنى البيانات ═══════════════════

@dataclass(frozen=True)
class Symbol:
    """رمز واحد مستخرج من ملف — اسم + نوع + سطر (1-based)."""
    name: str
    kind: str          # function/class/method/interface/type/id/css_class/...
    line: int


@dataclass(frozen=True)
class FileSymbols:
    """جدول رموز ملف واحد — العقد: موجود دائمًا، فارغ عند التعذر.

    - ``language == ""`` ⇒ امتداد غير مدعوم (أو المكتبة غائبة).
    - ``error`` مرصود عند فشل قراءة/حجب سري — الجداول تبقى فارغة.
    """
    path: str
    language: str = ""
    definitions: tuple[Symbol, ...] = ()
    references: tuple[Symbol, ...] = ()
    imports: tuple[str, ...] = ()
    error: Optional[str] = None

    @property
    def empty(self) -> bool:
        return not (self.definitions or self.references or self.imports)


# ═══════════════════ الاستخراج لكل لغة ═══════════════════
#
# مشيات AST تكرارية (stack) — لا عودية: أشجار الملفات الحقيقية قد
# تكون عميقة (HTML متداخل، سلاسل استدعاء) وحد بايثون العودي ليس عقدًا.

def _node_text(node: Any) -> str:
    raw = node.text
    if raw is None:
        return ""
    return raw.decode("utf-8", errors="replace")


def _name_of(node: Any, *, field_name: str = "name") -> Optional[Symbol]:
    """اسم التعريف من حقل ``name`` (fallback: أول ابن identifier)."""
    name_node = node.child_by_field_name(field_name)
    if name_node is None:
        for child in node.children:
            if child.type in ("identifier", "type_identifier",
                              "property_identifier"):
                name_node = child
                break
    if name_node is None:
        return None
    return Symbol(name=_node_text(name_node), kind="",
                  line=name_node.start_point[0] + 1)


def _walk(root: Any) -> Iterable[Any]:
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        # عكس الترتيب ليخرج المسح بترتيب المستند (stack = LIFO)
        for child in reversed(node.children):
            stack.append(child)


def _extract_python(root: Any) -> tuple[list[Symbol], list[Symbol],
                                        list[str]]:
    defs: list[Symbol] = []
    refs: list[Symbol] = []
    imports: list[str] = []
    for node in _walk(root):
        t = node.type
        if t in ("function_definition", "class_definition"):
            sym = _name_of(node)
            if sym is not None:
                kind = "class" if t == "class_definition" else "function"
                defs.append(Symbol(sym.name, kind, sym.line))
        elif t == "import_statement":
            for child in node.children:
                if child.type in ("dotted_name", "aliased_import"):
                    target = (child.child_by_field_name("name")
                              if child.type == "aliased_import" else child)
                    if target is not None:
                        imports.append(_node_text(target))
        elif t == "import_from_statement":
            module = node.child_by_field_name("module_name")
            if module is not None:
                imports.append(_node_text(module))
        elif t == "call":
            fn = node.child_by_field_name("function")
            if fn is not None:
                if fn.type == "identifier":
                    refs.append(Symbol(_node_text(fn), "call",
                                       fn.start_point[0] + 1))
                elif fn.type == "attribute":
                    attr = fn.child_by_field_name("attribute")
                    if attr is not None:
                        refs.append(Symbol(_node_text(attr), "call",
                                           attr.start_point[0] + 1))
    return defs, refs, imports


_JS_DEF_KINDS = {
    "function_declaration": "function",
    "class_declaration": "class",
    "method_definition": "method",
    "interface_declaration": "interface",   # TS فقط — غائبة في JS بلا ضرر
    "type_alias_declaration": "type",
}


def _extract_javascript(root: Any) -> tuple[list[Symbol], list[Symbol],
                                            list[str]]:
    """JS/TS/TSX — قواعد JS + عقد TS الإضافية (interface/type)."""
    defs: list[Symbol] = []
    refs: list[Symbol] = []
    imports: list[str] = []
    for node in _walk(root):
        t = node.type
        if t in _JS_DEF_KINDS:
            sym = _name_of(node)
            if sym is not None:
                defs.append(Symbol(sym.name, _JS_DEF_KINDS[t], sym.line))
        elif t == "variable_declarator":
            value = node.child_by_field_name("value")
            if value is not None and value.type in ("arrow_function",
                                                    "function_expression",
                                                    "function"):
                sym = _name_of(node)
                if sym is not None:
                    defs.append(Symbol(sym.name, "function", sym.line))
        elif t == "import_statement":
            src = node.child_by_field_name("source")
            if src is not None:
                for frag in src.children:
                    if frag.type == "string_fragment":
                        imports.append(_node_text(frag))
        elif t == "call_expression":
            fn = node.child_by_field_name("function")
            if fn is None:
                continue
            if fn.type == "identifier":
                name = _node_text(fn)
                if name == "require":
                    args = node.child_by_field_name("arguments")
                    if args is not None:
                        for arg in args.children:
                            if arg.type == "string":
                                for frag in arg.children:
                                    if frag.type == "string_fragment":
                                        imports.append(_node_text(frag))
                else:
                    refs.append(Symbol(name, "call", fn.start_point[0] + 1))
            elif fn.type == "member_expression":
                prop = fn.child_by_field_name("property")
                if prop is not None:
                    refs.append(Symbol(_node_text(prop), "call",
                                       prop.start_point[0] + 1))
    return defs, refs, imports


def _extract_html(root: Any) -> tuple[list[Symbol], list[Symbol],
                                      list[str]]:
    """HTML: قيم ``id`` و``class`` كتعريفات — أهداف الذكر المعتادة."""
    defs: list[Symbol] = []
    for node in _walk(root):
        if node.type != "attribute":
            continue
        attr_name = ""
        attr_value = None
        for child in node.children:
            if child.type == "attribute_name":
                attr_name = _node_text(child).lower()
            elif child.type == "quoted_attribute_value":
                for inner in child.children:
                    if inner.type == "attribute_value":
                        attr_value = inner
            elif child.type == "attribute_value":
                attr_value = child
        if attr_value is None or attr_name not in ("id", "class"):
            continue
        line = attr_value.start_point[0] + 1
        text = _node_text(attr_value)
        if attr_name == "id":
            defs.append(Symbol(text, "id", line))
        else:
            for token in text.split():
                defs.append(Symbol(token, "css_class", line))
    return defs, [], []


def _extract_css(root: Any) -> tuple[list[Symbol], list[Symbol],
                                     list[str]]:
    """CSS: محدِّدات ``.class`` و``#id`` كتعريفات؛ ``@import`` كاستيراد."""
    defs: list[Symbol] = []
    imports: list[str] = []
    for node in _walk(root):
        t = node.type
        if t == "class_name":
            defs.append(Symbol(_node_text(node), "css_class",
                               node.start_point[0] + 1))
        elif t == "id_name":
            defs.append(Symbol(_node_text(node), "id",
                               node.start_point[0] + 1))
        elif t == "import_statement":
            for child in node.children:
                if child.type in ("string_value", "call_expression"):
                    imports.append(_node_text(child).strip("'\""))
    return defs, [], imports


_EXTRACTORS: dict[str, Callable[[Any], tuple[list[Symbol], list[Symbol],
                                             list[str]]]] = {
    "python": _extract_python,
    "javascript": _extract_javascript,
    "typescript": _extract_javascript,
    "tsx": _extract_javascript,
    "html": _extract_html,
    "css": _extract_css,
}


# ═══════════════════ SymbolIndex ═══════════════════

class SymbolIndex:
    """فهرس رموز المشروع — كسول، مُكاش، متدهور رشيقًا.

    الاستخدام:
        idx = SymbolIndex(project_root)
        idx.attach(fm)                       # طزاجة write-through
        table = idx.symbols_for("src/app.py")
        hits = idx.lookup_definition("UserService")
    """

    def __init__(self, root: str | pathlib.Path,
                 reader: Optional[SafeReader] = None) -> None:
        self.root = pathlib.Path(root).resolve()
        self._reader = reader if reader is not None else SafeReader(self.root)
        self._cache: dict[str, FileSymbols] = {}
        self._parsers: dict[str, Any] = {}

    # ── التوفر والدعم ──

    @staticmethod
    def available() -> bool:
        """هل مكتبة tree-sitter + محلّل واحد على الأقل متاحان؟"""
        return _TS_AVAILABLE and bool(_LANGUAGE_FACTORIES)

    @staticmethod
    def language_for(rel_path: str) -> str:
        """مفتاح اللغة لامتداد المسار — "" إن لم يكن مدعومًا."""
        suffix = pathlib.PurePosixPath(rel_path.replace("\\", "/")).suffix
        return EXTENSION_LANGUAGES.get(suffix.lower(), "")

    def _parser_for(self, lang: str) -> Optional[Any]:
        """Parser مُكاش لكل لغة — None إذا اللغة/المكتبة غير متاحة."""
        if not _TS_AVAILABLE:
            return None
        if lang in self._parsers:
            return self._parsers[lang]
        factory = _LANGUAGE_FACTORIES.get(lang)
        if factory is None:
            return None
        try:
            parser = _TSParser(_TSLanguage(factory()))
        except Exception:
            return None
        self._parsers[lang] = parser
        return parser

    # ── الفهرسة ──

    def symbols_for(self, rel_path: str) -> FileSymbols:
        """جدول رموز الملف — كسول + مُكاش؛ لا يرفع استثناء أبدًا."""
        key = rel_path.replace("\\", "/")
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        table = self._build(key)
        self._cache[key] = table
        return table

    def _build(self, rel_path: str) -> FileSymbols:
        lang = self.language_for(rel_path)
        if not lang:
            return FileSymbols(path=rel_path)          # غير مدعوم — فارغ
        parser = self._parser_for(lang)
        if parser is None:
            return FileSymbols(path=rel_path)          # المكتبة غائبة
        result = self._reader.read_text(rel_path)
        if not result.ok or result.content is None:
            return FileSymbols(path=rel_path, language=lang,
                               error=result.reason or "read_failed")
        if result.redacted:
            return FileSymbols(path=rel_path, language=lang,
                               error="redacted")
        try:
            tree = parser.parse(result.content.encode("utf-8"))
            defs, refs, imports = _EXTRACTORS[lang](tree.root_node)
        except Exception as exc:                       # حزام أمان أخير
            return FileSymbols(path=rel_path, language=lang,
                               error=f"parse_error: {exc}")
        return FileSymbols(
            path=rel_path, language=lang,
            definitions=tuple(defs), references=tuple(refs),
            imports=tuple(imports),
        )

    def index_files(self, rel_paths: Iterable[str]) -> int:
        """فهرسة جماعية (قائمة جاهزة — لا مشية شجرية هنا بالتصميم)."""
        count = 0
        for rel_path in rel_paths:
            self.symbols_for(rel_path)
            count += 1
        return count

    # ── الاستعلام ──

    def lookup_definition(self, name: str) -> list[tuple[str, Symbol]]:
        """كل التعريفات المفهرسة بالاسم — أزواج (rel_path, Symbol)."""
        hits: list[tuple[str, Symbol]] = []
        for rel_path in sorted(self._cache):
            table = self._cache[rel_path]
            for sym in table.definitions:
                if sym.name == name:
                    hits.append((rel_path, sym))
        return hits

    def lookup_references(self, name: str) -> list[tuple[str, Symbol]]:
        """كل المراجع (استدعاءات) المفهرسة بالاسم."""
        hits: list[tuple[str, Symbol]] = []
        for rel_path in sorted(self._cache):
            table = self._cache[rel_path]
            for sym in table.references:
                if sym.name == name:
                    hits.append((rel_path, sym))
        return hits

    @property
    def indexed_count(self) -> int:
        return len(self._cache)

    # ── الطزاجة (نمط T-049) ──

    def notify_write(self, rel_path: str) -> None:
        """خطاف write-through — إبطال الكاش فيُعاد التحليل كسولًا."""
        self._cache.pop(rel_path.replace("\\", "/"), None)

    def attach(self, fm: Any) -> None:
        """تسجيل الخطاف في FileManager (تسامحيًا مع fm بلا خطافات)."""
        add_hook = getattr(fm, "add_write_hook", None)
        if callable(add_hook):
            add_hook(self.notify_write)
