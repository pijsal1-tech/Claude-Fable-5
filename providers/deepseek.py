# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  DeepSeekProvider — Adapter لـ DeepSeek R1
  يستخدم NoteGPT API عبر cloudscraper
  مجاني 100% — مش محتاج حسابات
═══════════════════════════════════════════════════════
"""
import json
import uuid
import random
import time
from typing import Generator

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

from .base import BaseProvider, ProviderConfig, Message, ProviderCapabilities


class DeepSeekConfig(ProviderConfig):
    """إعدادات DeepSeek"""
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "deepseek-r1"),
            timeout=kwargs.get("timeout", 120),
            max_retries=kwargs.get("max_retries", 3),
        )


def _generate_fake_ip():
    return f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"


class DeepSeekProvider(BaseProvider):
    """
    DeepSeek R1 عبر NoteGPT — مجاني بدون حسابات
    كل طلب بيستخدم anonymous session جديدة
    """
    name = "deepseek"
    description = "DeepSeek R1 — عبر NoteGPT (مجاني بدون حسابات)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,               # SSE streaming حقيقي
            structured_output=False,
            parallel_requests=True,       # كل طلب anonymous session مستقلة
            max_parallel_requests=3,
            max_context_tokens=64_000,
        )

    def __init__(self, config: DeepSeekConfig | None = None):
        self.config: DeepSeekConfig = config or DeepSeekConfig()
        self._initialized = False
        self._scraper = None
        self._url = "https://notegpt.io/api/v2/chat/stream"

    def initialize(self) -> bool:
        if not HAS_CLOUDSCRAPER:
            print("❌ مكتبة cloudscraper مش مثبتة! شغّل: pip install cloudscraper")
            return False
        self._scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome', 'platform': 'android', 'desktop': False}
        )
        self._initialized = True
        return True

    def is_available(self) -> bool:
        return HAS_CLOUDSCRAPER and self._initialized

    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        if not self._initialized:
            self.initialize()

        # DeepSeek API مش بيدعم history — فبندمجه في البرومبت
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        if history:
            full_prompt += "[سياق المحادثة السابقة]:\n"
            for msg in history[-6:]:  # آخر 6 رسائل
                role_label = "المستخدم" if msg.role == "user" else "المساعد"
                full_prompt += f"--- {role_label} ---\n{msg.content[:500]}\n\n"
            full_prompt += "[الطلب الحالي]:\n"
        full_prompt += prompt

        for attempt in range(self.config.max_retries):
            try:
                anon_user_id = str(uuid.uuid4())
                conv_id = str(uuid.uuid4())
                fake_ip = _generate_fake_ip()

                cookies = {
                    "anonymous_user_id": anon_user_id,
                    "sbox-guid": str(uuid.uuid4())
                }

                headers = {
                    'Accept': "*/*",
                    'Accept-Encoding': "gzip, deflate",
                    'Content-Type': "application/json",
                    'origin': "https://notegpt.io",
                    'referer': "https://notegpt.io/ai-chat?hl=ar-EG",
                    'accept-language': "ar-EG,ar;q=0.9,en-US;q=0.8",
                    'X-Forwarded-For': fake_ip,
                    'X-Real-IP': fake_ip,
                    'Client-IP': fake_ip,
                }

                payload = {
                    "message": full_prompt,
                    "language": "auto",
                    "model": "TA/deepseek-ai/DeepSeek-R1",
                    "tone": "default",
                    "length": "moderate",
                    "conversation_id": conv_id,
                    "image_urls": [],
                    "chat_mode": "deep_think"
                }

                print(f"  🧠 DeepSeek R1 محاولة #{attempt+1}...")
                response = self._scraper.post(
                    self._url, json=payload, headers=headers,
                    cookies=cookies, stream=True, timeout=self.config.timeout
                )

                if response.status_code == 200:
                    full_text = ""
                    for line in response.iter_lines():
                        if line:
                            decoded = line.decode('utf-8')
                            if decoded.startswith("data: "):
                                try:
                                    data = json.loads(decoded[6:])
                                    if data.get("done"):
                                        break
                                    text = data.get("text", "")
                                    if text:
                                        full_text += text
                                except json.JSONDecodeError:
                                    pass
                    if full_text.strip():
                        return full_text.strip()
                else:
                    print(f"  ⚠️ DeepSeek HTTP {response.status_code}")

            except Exception as e:
                print(f"  ❌ DeepSeek error: {e}")

            time.sleep(1)

        return "❌ فشل الاتصال بـ DeepSeek R1"

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        """DeepSeek بيدعم streaming أصلاً"""
        if not self._initialized:
            self.initialize()

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        anon_user_id = str(uuid.uuid4())
        conv_id = str(uuid.uuid4())
        fake_ip = _generate_fake_ip()

        cookies = {
            "anonymous_user_id": anon_user_id,
            "sbox-guid": str(uuid.uuid4())
        }

        headers = {
            'Accept': "*/*",
            'Content-Type': "application/json",
            'origin': "https://notegpt.io",
            'referer': "https://notegpt.io/ai-chat",
            'X-Forwarded-For': fake_ip,
            'X-Real-IP': fake_ip,
        }

        payload = {
            "message": full_prompt,
            "language": "auto",
            "model": "TA/deepseek-ai/DeepSeek-R1",
            "tone": "default",
            "length": "moderate",
            "conversation_id": conv_id,
            "image_urls": [],
            "chat_mode": "deep_think"
        }

        try:
            response = self._scraper.post(
                self._url, json=payload, headers=headers,
                cookies=cookies, stream=True, timeout=self.config.timeout
            )
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        decoded = line.decode('utf-8')
                        if decoded.startswith("data: "):
                            try:
                                data = json.loads(decoded[6:])
                                if data.get("done"):
                                    break
                                text = data.get("text", "")
                                if text:
                                    yield text
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            yield f"❌ خطأ: {e}"

    def get_info(self) -> dict:
        info = super().get_info()
        info["models"] = ["deepseek-r1"]
        return info

    def get_remaining_calls(self) -> int:
        """DeepSeek بيستخدم anonymous sessions — بلا حدود عملياً"""
        return 999 if self._initialized else 0

