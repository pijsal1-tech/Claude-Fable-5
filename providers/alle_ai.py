# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  AlleAIProvider — Adapter لـ Alle-AI
  يدعم: Gemini 3.1 Pro + Nova Pro (Dual Response)
  Smart account rotation + fresh login + buffer thread
═══════════════════════════════════════════════════════
"""
import sys
import os
import json
import time
import pathlib
import threading
import requests
from typing import Generator

from .base import BaseProvider, ProviderConfig, Message, ProviderCapabilities

_DIR = pathlib.Path(__file__).resolve().parent.parent
_NEW_PROVIDERS = _DIR / "new_providers"
_ACCOUNTS_FILE = str(_NEW_PROVIDERS / "ALLe-ai" / "alle_ai_accounts.json")

BASE_URL = "https://api.alle-ai.com"
BASE_HEADERS = {
    "accept": "application/json",
    "accept-encoding": "gzip",
    "content-type": "application/json",
    "host": "api.alle-ai.com",
    "user-agent": "Dart/3.10 (dart:io)",
}

ALLE_MODELS = {
    "gemini-3-1-pro": "gemini-3-1-pro",
    "nova-pro": "nova-pro",
}

RESP_TIMEOUT = 65


class AlleAIConfig(ProviderConfig):
    """إعدادات Alle-AI"""
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "gemini-3-1-pro"),
            timeout=kwargs.get("timeout", 65),
            max_retries=kwargs.get("max_retries", 5),
        )
        self.accounts_file = kwargs.get("accounts_file", _ACCOUNTS_FILE)
        self.second_model = kwargs.get("second_model", "nova-pro")


def _fresh_login(email: str, password: str) -> str | None:
    """تسجيل دخول جديد"""
    try:
        r = requests.post(
            f"{BASE_URL}/api/v1/login",
            headers=BASE_HEADERS,
            json={"email": email, "password": password},
            timeout=10
        )
        if r.status_code == 200:
            return r.json().get("data", {}).get("token", "")
    except Exception:
        pass
    return None


def _hdr(token: str) -> dict:
    h = BASE_HEADERS.copy()
    h["authorization"] = f"Bearer {token}"
    return h


class AlleAIProvider(BaseProvider):
    """
    Alle-AI — Gemini + Nova Pro (Dual response)
    Smart account rotation مع fresh login تلقائي
    """
    name = "alle_ai"
    description = "Alle-AI — Gemini 3.1 Pro + Nova Pro (مجاني)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,               # buffer thread + SSE
            structured_output=False,
            parallel_requests=True,       # account rotation
            max_parallel_requests=2,
            max_context_tokens=128_000,   # Gemini-level
        )

    def __init__(self, config: AlleAIConfig | None = None):
        self.config: AlleAIConfig = config or AlleAIConfig()
        self._initialized = False
        self._accounts: list[dict] = []

    def initialize(self) -> bool:
        self._accounts = self._load_accounts()
        self._initialized = True
        return len(self._accounts) > 0

    def is_available(self) -> bool:
        return self._initialized and len(self._accounts) > 0

    def _load_accounts(self) -> list:
        """تحميل حسابات Alle-AI"""
        acc_file = self.config.accounts_file
        if not os.path.exists(acc_file):
            print(f"  ⚠️ Alle-AI: ملف الحسابات مش موجود: {acc_file}")
            return []
        try:
            accounts = json.loads(open(acc_file, encoding="utf-8").read())
            active = [a for a in accounts
                      if a.get("status") in ("active", "registered", "verified")
                      and a.get("email") and a.get("password")]
            return active
        except Exception as e:
            print(f"  ❌ Alle-AI: خطأ في تحميل الحسابات: {e}")
            return []

    def _try_account(self, account: dict) -> tuple[str | None, bool]:
        """محاولة استخدام حساب — Token القديم أولاً ثم login"""
        # Token قديم
        old_token = account.get("token", "")
        if old_token:
            try:
                r = requests.get(
                    f"{BASE_URL}/api/v1/user/profile",
                    headers=_hdr(old_token),
                    timeout=5
                )
                if r.status_code == 200:
                    return old_token, True
            except Exception:
                pass

        # Login جديد
        new_token = _fresh_login(account.get("email", ""), account.get("password", ""))
        if new_token:
            account["token"] = new_token
            return new_token, True

        return None, False

    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        if not self._initialized:
            self.initialize()

        # Alle-AI API مش بيدعم history — فبندمجه في البرومبت
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        if history:
            # T-030 (R-302): القصّة الحرفية [-6:] → سياسة نافذة مسماة
            from sessions.memory import (
                POLICY_PROVIDER_HISTORY_FOLD, select_history)
            full_prompt += "[سياق المحادثة السابقة]:\n"
            for msg in select_history(history, POLICY_PROVIDER_HISTORY_FOLD):
                role_label = "المستخدم" if msg.role == "user" else "المساعد"
                full_prompt += f"--- {role_label} ---\n{msg.content[:500]}\n\n"
            full_prompt += "[الطلب الحالي]:\n"
        full_prompt += prompt

        model1 = self.config.model
        model2 = self.config.second_model

        # Smart account rotation — max 5 محاولات
        max_attempts = min(len(self._accounts), 5)
        for attempt in range(max_attempts):
            account = self._accounts[attempt]
            email = account.get("email", "?")
            print(f"  🔄 Alle-AI محاولة #{attempt+1}/{max_attempts} بحساب: {email[:25]}...")

            token, ok_flag = self._try_account(account)
            if not ok_flag or not token:
                print(f"  ❌ حساب ميت (login فشل): {email[:25]}")
                continue

            try:
                # إنشاء محادثة
                r = requests.post(
                    f"{BASE_URL}/api/v1/create/conversation",
                    headers=_hdr(token),
                    json={"models": [model1, model2], "type": "chat"},
                    timeout=10
                )
                if r.status_code != 200:
                    if "limit" in r.text.lower():
                        print(f"  💰 ليميت يومي: {email[:25]}")
                        continue
                    print(f"  ⚠️ فشل إنشاء المحادثة: {r.status_code}")
                    continue

                session_id = r.json().get("session", "")
                if not session_id:
                    print(f"  ⚠️ مفيش session_id في الرد")
                    continue

                # إرسال البرومبت
                r = requests.post(
                    f"{BASE_URL}/api/v1/create/prompt",
                    headers=_hdr(token),
                    json={
                        "conversation": session_id,
                        "prompt": full_prompt,
                        "position": [0, 1]
                    },
                    timeout=10
                )
                if r.status_code != 200:
                    print(f"  ⚠️ فشل إرسال البرومبت: {r.status_code} — {r.text[:100]}")
                    continue

                prompt_id = r.json().get("id")
                if not prompt_id:
                    print(f"  ⚠️ مفيش prompt_id في الرد")
                    continue

                # استقبال الرد (من الموديل الأول)
                r = requests.post(
                    f"{BASE_URL}/api/v1/ai-response",
                    headers=_hdr(token),
                    json={
                        "conversation": session_id,
                        "model": model1,
                        "prompt": prompt_id,
                        "is_new": False,
                        "prev": []
                    },
                    timeout=RESP_TIMEOUT
                )

                if r.status_code == 200:
                    resp = r.json().get("data", {})
                    text = resp.get("response", "")
                    if text and text != "LIMIT_HIT":
                        return text

                    if "limit" in str(r.text).lower():
                        print(f"  💰 ليميت: {email[:25]}")
                        continue

                elif r.status_code in (429,):
                    print(f"  💰 Rate limited: {email[:25]}")
                    continue

            except Exception as e:
                print(f"  ❌ Alle-AI error: {e}")

        return "❌ فشل الاتصال بـ Alle-AI بعد كل المحاولات"

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        """Alle-AI مش بيدعم streaming — بنقطّع الرد"""
        full_response = self.send(prompt, history, system_prompt)
        chunk_size = 50
        for i in range(0, len(full_response), chunk_size):
            yield full_response[i:i + chunk_size]

    def get_info(self) -> dict:
        info = super().get_info()
        info["models"] = list(ALLE_MODELS.keys())
        return info

    def get_remaining_calls(self) -> int:
        """عدد الحسابات النشطة في Alle-AI"""
        return len(self._accounts) if self._initialized else 0

