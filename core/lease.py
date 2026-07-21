# -*- coding: utf-8 -*-
"""حجز المشروع لكل worker (T-110, R-804): ProjectLease.

لماذا: قاعدة «مشروع واحد = worker واحد» يجب أن تكون عابرة للعمليات —
سجل التنفيذ داخل عملية الخادم لا يكفي عندما يتوزع التنفيذ على عمال
منفصلين. الـ TTL يعطينا failover تلقائيًا: موت العامل يعني انقضاء
الحجز وتحرر المشروع لعامل آخر دون تدخل.

الأساس (docs/phase8_plan.md §3):
    SET lease:<project_id> <worker_id> NX PX <ttl_ms>

- الاستحواذ ذري عبر NX (لا حجز فوق حجز قائم).
- التجديد مشروط بالملكية (سكربت Lua — لا تجديد لحجز غيرك).
- التحرير مشروط بالملكية (لا تحرير لحجز غيرك).
- الانقضاء = تحرير تلقائي (failover).

العميل يُحقن — الموديول لا يستورد redis إطلاقًا.
"""
from __future__ import annotations

from typing import Any

_RENEW_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] "
    "then return redis.call('pexpire', KEYS[1], ARGV[2]) "
    "else return 0 end"
)
_RELEASE_LUA = (
    "if redis.call('get', KEYS[1]) == ARGV[1] "
    "then return redis.call('del', KEYS[1]) "
    "else return 0 end"
)


class ProjectLease:
    """حجز حصري لمشروع واحد باسم worker واحد مع TTL."""

    def __init__(
        self,
        client: Any,
        project_id: str,
        worker_id: str,
        ttl_ms: int = 30_000,
        *,
        key_prefix: str = "lease:",
    ) -> None:
        if ttl_ms <= 0:
            raise ValueError("ttl_ms يجب أن يكون موجبًا")
        self._client = client
        self._key = f"{key_prefix}{project_id}"
        self._worker_id = worker_id
        self._ttl_ms = ttl_ms

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def acquire(self) -> bool:
        """محاولة استحواذ ذرية: تنجح فقط إذا لم يوجد حجز قائم."""
        return bool(
            self._client.set(self._key, self._worker_id, nx=True, px=self._ttl_ms)
        )

    def renew(self) -> bool:
        """تجديد مشروط بالملكية: يفشل إن لم نكن نحن الحائز."""
        return bool(
            self._client.eval(_RENEW_LUA, 1, self._key, self._worker_id, self._ttl_ms)
        )

    def release(self) -> bool:
        """تحرير مشروط بالملكية: يفشل إن لم نكن نحن الحائز."""
        return bool(self._client.eval(_RELEASE_LUA, 1, self._key, self._worker_id))

    def holder(self) -> str | None:
        """الحائز الحالي للحجز (أو None إن لم يوجد حجز)."""
        return self._client.get(self._key)
