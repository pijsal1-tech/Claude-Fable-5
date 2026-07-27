# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  ProviderRegistry — سجل النماذج
  تسجيل/جلب/عرض مزودي AI ديناميكياً
═══════════════════════════════════════════════════════
"""
from .base import BaseProvider
from .openai_shelby import OpenAIShelbyProvider


class ProviderRegistry:
    """سجل مركزي لمزودي النماذج"""

    def __init__(self):
        self._providers: dict[str, type[BaseProvider]] = {}
        self._instances: dict[str, BaseProvider] = {}
        # تسجيل المزود الافتراضي
        self.register("openai_shelby", OpenAIShelbyProvider)

    def register(self, name: str, provider_class: type[BaseProvider]):
        """تسجيل مزود جديد"""
        self._providers[name] = provider_class

    def get(self, name: str, config=None) -> BaseProvider:
        """جلب instance من المزود — يعمل cache"""
        if name not in self._providers:
            available = ", ".join(self._providers.keys()) or "لا يوجد"
            raise KeyError(f"المزود '{name}' غير مسجل. المتاحون: {available}")

        if name not in self._instances:
            self._instances[name] = self._providers[name](config)

        return self._instances[name]

    def list_available(self) -> list[dict]:
        """عرض كل المزودين المسجلين"""
        result = []
        for name, cls in self._providers.items():
            info = {"name": name, "description": getattr(cls, "description", "")}
            if name in self._instances:
                info["available"] = self._instances[name].is_available()
            result.append(info)
        return result

    def has(self, name: str) -> bool:
        return name in self._providers


# ── Instance عام ──
_registry = ProviderRegistry()


def register_provider(name: str, provider_class: type[BaseProvider]):
    _registry.register(name, provider_class)


def get_provider(name: str, config=None) -> BaseProvider:
    return _registry.get(name, config)


def list_providers() -> list[dict]:
    return _registry.list_available()
