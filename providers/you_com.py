# -*- coding: utf-8 -*-
"""
YouComProvider — مزود You.com AI لـ editor_v5
يستخدم السكربت الميداني new_providers/you__chat.py ديناميكياً عبر _NEW_PROVIDERS
"""
import pathlib
import importlib.util
import sys
import threading
from .base import BaseProvider, ProviderConfig, ProviderCapabilities

_DIR = pathlib.Path(__file__).resolve().parent.parent
_NEW_PROVIDERS = _DIR / "../new_providers"

_you_module = None
_you_lock = threading.Lock()


def _load_you_module():
    global _you_module
    if _you_module is not None:
        return _you_module
    with _you_lock:
        if _you_module is not None:
            return _you_module
        script_path = _NEW_PROVIDERS / "you__chat.py"
        if not script_path.exists():
            raise FileNotFoundError(f"سكريبت You.com مش موجود: {script_path}")
        spec = importlib.util.spec_from_file_location("you__chat_mod", str(script_path))
        # D-18 (BATCH-CLOSEOUT): حارس None بنمط genspark.py:58-59 — يرفع
        # استبعاد mypy الموروث (TSK-CEV-102) لهذا الملف.
        if spec is None or spec.loader is None:
            raise ImportError(f"تعذر تحميل spec لسكريبت You.com: {script_path}")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _you_module = mod
        return _you_module


class YouComConfig(ProviderConfig):
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "claude_4_8_opus_thinking"),
            timeout=kwargs.get("timeout", 120),
            max_retries=kwargs.get("max_retries", 2),
        )


class YouComProvider(BaseProvider):
    name = "you_com"
    description = "You.com AI — 21 Models Supported"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=False,
            parallel_requests=True,
            max_context_tokens=128_000,
        )

    def __init__(self, config: YouComConfig | None = None):
        self.config = config or YouComConfig()
        self._initialized = False

    def is_available(self) -> bool:
        return True

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def send(self, prompt: str, history=None, system_prompt: str = "") -> str:
        try:
            mod = _load_you_module()
            model_id = self.config.model
            # 🚀 بانر ملون لـ You.com مع flush=True
            print(f"\n\033[94m\033[1m🌐 [You.com AI Runner]\033[0m \033[93mالموديل المستهدف: \033[92m{model_id}\033[0m", flush=True)
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            res = mod.ask(full_prompt, model=model_id)
            reply = res.text if hasattr(res, "text") and res.text else (str(res.response) if hasattr(res, "response") and res.response else str(res))
            
            # 💬 طباعة المعاينة بالـ Terminal
            preview = reply[:120].replace('\n', ' ') if reply else ""
            print(f"\033[95m💬 [رد You.com AI]:\033[0m \033[97m{preview}...\033[0m\n", flush=True)
            return reply
        except Exception as e:
            print(f"\033[91m❌ [You.com AI Exception]: {e}\033[0m", flush=True)
            return f"⚠️ [YouComProvider Exception]: {e}"

    def stream(self, prompt: str, history=None, system_prompt: str = ""):
        reply = self.send(prompt, history, system_prompt)
        yield reply
