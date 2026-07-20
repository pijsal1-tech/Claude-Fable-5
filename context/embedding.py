# -*- coding: utf-8 -*-
"""بروتوكول الـ Embedder + تنفيذ provider-backed (R-802 / T-104).

**اختيار الخلفية موثّق في** ``docs/phase8_plan.md`` **§2** — الخلاصة:
embeddings عبر endpoint متوافق مع OpenAI (``/embeddings``) بطبقة HTTP
الموجودة (requests — نفس اعتماد ``providers/``)، **صفر اعتماديات ثقيلة
جديدة** (لا torch/faiss/chromadb): الذاكرة لكل مشروع مئات-إلى-آلاف
قليلة من القطع، وcosine بايثون-صرف فوق ≤5k متجه تحت ميزانية زمن
الطبقة ``opportunistic`` بمراحل. الغياب حالة مصمَّمة: مزوّد غير مهيأ/
غير قابل للوصول ⇒ الطبقة الدلالية تتدهور بنظافة (T-105 fallback-to-skip).

**حارس الواجهة** (phase8_plan §2): الاختيار مخفي خلف بروتوكول
``Embedder`` — ``embed(texts) -> list[list[float]]`` — فتُبدَّل خلفية
محلية لاحقًا بلا لمس الفهرس أو مصدر ContextEngine.

**عقد الفشل:** التنفيذ الحقيقي يرفع ``EmbedderUnavailable`` لأي عائق
(غير مهيأ، شبكة، HTTP غير 200، شكل رد غير متوقع) — استثناء واحد مكتوب
يمسكه الفهرس (semantic_index) ويحوّله إلى "غير متاح" النظيفة؛ لا
تسريب لاستثناءات requests الخام عبر الحدود.
"""
from __future__ import annotations

from typing import Any, Protocol, Sequence

__all__ = [
    "Embedder",
    "EmbedderUnavailable",
    "ProviderEmbedder",
]


class EmbedderUnavailable(Exception):
    """الـ embedder لا يستطيع الخدمة — غير مهيأ أو المزوّد غير قابل للوصول.

    الاستثناء الوحيد الذي يعبر حدود هذه الوحدة: الفهرس يمسكه ويبلّغ
    «غير متاح» — لا انهيار ولا تسريب استثناءات نقل خام.
    """


class Embedder(Protocol):
    """عقد الـ embedding — الطريقة الوحيدة التي يعرفها الفهرس.

    ``embed(texts)`` تعيد متجهًا لكل نص **بنفس الترتيب**؛ الفشل =
    ``EmbedderUnavailable`` (لا None ولا قوائم ناقصة).
    """

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class ProviderEmbedder:
    """Embedder عبر endpoint متوافق مع OpenAI: ``POST {base_url}/embeddings``.

    الإعداد صريح بالمُنشئ (``base_url``/``api_key``/``model``) — القراءة
    من config مسؤولية المستدعي (T-105 wiring). ``base_url`` فارغ =
    غير مهيأ ⇒ ``EmbedderUnavailable`` فورًا بلا محاولة شبكة.

    الطلب/الرد بصيغة OpenAI القياسية:
      ``{"model": ..., "input": [texts...]}`` ⇒
      ``{"data": [{"index": i, "embedding": [floats...]}, ...]}``
    الرد يُرتَّب بـ ``index`` (المواصفة لا تضمن ترتيب data) ويُتحقق من
    اكتماله — أي نقص/تشوه = ``EmbedderUnavailable``.
    """

    def __init__(self, base_url: str = "", api_key: str = "",
                 model: str = "text-embedding-3-small",
                 timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        if not self._base_url:
            raise EmbedderUnavailable("embedding provider غير مهيأ "
                                      "(base_url فارغ)")
        # استيراد كسول: الوحدة تُستورد بلا requests مثبتة (بوابة
        # لا-اعتماد-صلب في check.sh/الاختبارات)
        try:
            import requests
        except ImportError as exc:   # pragma: no cover — بيئة بلا requests
            raise EmbedderUnavailable(f"requests غير متاحة: {exc}") from exc

        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            resp = requests.post(
                f"{self._base_url}/embeddings",
                json={"model": self._model, "input": list(texts)},
                headers=headers, timeout=self._timeout,
            )
        except Exception as exc:   # noqa: BLE001 — كل أعطال النقل = غير متاح
            raise EmbedderUnavailable(f"فشل نداء المزوّد: {exc}") from exc
        if resp.status_code != 200:
            raise EmbedderUnavailable(
                f"رد المزوّد {resp.status_code}: {resp.text[:200]}")
        try:
            payload: Any = resp.json()
            data = payload["data"]
            by_index: dict[int, list[float]] = {
                int(item["index"]): [float(x) for x in item["embedding"]]
                for item in data
            }
            vectors = [by_index[i] for i in range(len(texts))]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise EmbedderUnavailable(
                f"شكل رد /embeddings غير متوقع: {exc}") from exc
        if any(not v for v in vectors):
            raise EmbedderUnavailable("متجه فارغ في رد المزوّد")
        return vectors
