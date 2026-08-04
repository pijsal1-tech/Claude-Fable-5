# -*- coding: utf-8 -*-
"""
BlackboxProvider — مزود Blackbox AI لـ editor_v5
يستخدم السكربت الميداني new_providers/blackbox_chat.py ديناميكياً عبر _NEW_PROVIDERS
"""
import pathlib
import importlib.util
import sys
import threading
from .base import BaseProvider, ProviderConfig, ProviderCapabilities

_DIR = pathlib.Path(__file__).resolve().parent.parent
_NEW_PROVIDERS = _DIR / "../new_providers"

_blackbox_module = None
_blackbox_lock = threading.Lock()


def _load_blackbox_module():
    global _blackbox_module
    if _blackbox_module is not None:
        return _blackbox_module
    with _blackbox_lock:
        if _blackbox_module is not None:
            return _blackbox_module
        script_path = _NEW_PROVIDERS / "blackbox_chat.py"
        if not script_path.exists():
            raise FileNotFoundError(f"سكريبت Blackbox مش موجود: {script_path}")
        spec = importlib.util.spec_from_file_location("blackbox_chat_mod", str(script_path))
        # D-18 (BATCH-CLOSEOUT): حارس None بنمط genspark.py:58-59 — يرفع
        # استبعاد mypy الموروث (TSK-CEV-102) لهذا الملف.
        if spec is None or spec.loader is None:
            raise ImportError(f"تعذر تحميل spec لسكريبت Blackbox: {script_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _blackbox_module = mod
        return _blackbox_module


class BlackboxConfig(ProviderConfig):
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "gpt-5.3-codex"),
            timeout=kwargs.get("timeout", 120),
            max_retries=kwargs.get("max_retries", 2),
        )


class BlackboxProvider(BaseProvider):
    name = "blackbox"
    description = "Blackbox AI — 24 Models Supported"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=False,
            parallel_requests=True,
            max_context_tokens=128_000,
        )

    def __init__(self, config: BlackboxConfig | None = None):
        self.config = config or BlackboxConfig()
        self._initialized = False

    def is_available(self) -> bool:
        return True

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def send(self, prompt: str, history=None, system_prompt: str = "") -> str:
        try:
            mod = _load_blackbox_module()
            model_id = self.config.model
            # 🎨 طباعة بانر نيون ملون فور استلام الطلب بالـ Terminal مع flush=True لإظهاره فوراً بالسيرفر
            print(f"\n\033[96m\033[1m🚀 [Blackbox AI Runner]\033[0m \033[93mالموديل المستهدف: \033[92m{model_id}\033[0m", flush=True)
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            reply = mod.ask_blackbox(full_prompt, model=model_id, show_spinner=False)
            
            # 💬 طباعة المعاينة الفخمة للاستجابة بالـ Terminal
            preview = reply[:120].replace('\n', ' ') if reply else ""
            print(f"\033[95m💬 [رد Blackbox AI]:\033[0m \033[97m{preview}...\033[0m\n", flush=True)
            return reply
        except Exception as e:
            print(f"\033[91m❌ [Blackbox AI Exception]: {e}\033[0m", flush=True)
            return f"⚠️ [BlackboxProvider Exception]: {e}"

    def stream(self, prompt: str, history=None, system_prompt: str = ""):
        reply = self.send(prompt, history, system_prompt)
        yield reply
