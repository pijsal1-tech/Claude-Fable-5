# -*- coding: utf-8 -*-
"""
PerplexityProvider — مزود Perplexity AI لـ editor_v5
يستخدم السكربت الميداني new_providers/perplexity_chat.py ديناميكياً عبر _NEW_PROVIDERS
"""
import pathlib
import importlib.util
import sys
import threading
from .base import BaseProvider, ProviderConfig, ProviderCapabilities

_DIR = pathlib.Path(__file__).resolve().parent.parent
_NEW_PROVIDERS = _DIR / "../new_providers"

_pplx_module = None
_pplx_lock = threading.Lock()


def _load_pplx_module():
    global _pplx_module
    if _pplx_module is not None:
        return _pplx_module
    with _pplx_lock:
        if _pplx_module is not None:
            return _pplx_module
        script_path = _NEW_PROVIDERS / "perplexity_chat.py"
        if not script_path.exists():
            raise FileNotFoundError(f"سكريبت Perplexity مش موجود: {script_path}")
        spec = importlib.util.spec_from_file_location("perplexity_chat_mod", str(script_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _pplx_module = mod
        return _pplx_module


class PerplexityConfig(ProviderConfig):
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "pplx_asi_gpt_56_sol"),
            timeout=kwargs.get("timeout", 120),
            max_retries=kwargs.get("max_retries", 2),
        )


class PerplexityProvider(BaseProvider):
    name = "perplexity"
    description = "Perplexity AI — 44 Models Supported"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=False,
            parallel_requests=True,
            max_context_tokens=128_000,
        )

    def __init__(self, config: PerplexityConfig | None = None):
        self.config = config or PerplexityConfig()
        self._initialized = False

    def is_available(self) -> bool:
        return True

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def send(self, prompt: str, history=None, system_prompt: str = "") -> str:
        try:
            mod = _load_pplx_module()
            model_id = self.config.model
            # 🚀 بانر ملون لـ Perplexity مع flush=True
            print(f"\n\033[96m\033[1m🔮 [Perplexity AI Runner]\033[0m \033[93mالموديل المستهدف: \033[92m{model_id}\033[0m", flush=True)
            
            full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            res = mod.ask(full_prompt, model=model_id)
            reply = str(res)
            
            # 💬 طباعة المعاينة بالـ Terminal
            preview = reply[:120].replace('\n', ' ') if reply else ""
            print(f"\033[95m💬 [رد Perplexity AI]:\033[0m \033[97m{preview}...\033[0m\n", flush=True)
            return reply
        except Exception as e:
            print(f"\033[91m❌ [Perplexity AI Exception]: {e}\033[0m", flush=True)
            return f"⚠️ [PerplexityProvider Exception]: {e}"

    def stream(self, prompt: str, history=None, system_prompt: str = ""):
        reply = self.send(prompt, history, system_prompt)
        yield reply
