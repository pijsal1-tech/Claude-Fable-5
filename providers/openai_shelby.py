# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  OpenAIShelbyProvider — OpenAI Android Backend API Adapter
  ChatGPT Mobile Gateway API (Shelby)
  يدعم gpt-5-3-high, gpt-5-3-mini, gpt-5-3-pro
═══════════════════════════════════════════════════════
"""
import json
import uuid
import random
import requests
from typing import Generator, Any

from .base import (
    BaseProvider,
    ProviderConfig,
    Message,
    ProviderCapabilities,
    ProviderMessage,
    history_to_messages
)

PLAY_INTEGRITY_TOKEN = "CpUCARCnMGsloytCYaRi_NzzzQh6pFSungjl0mXOMFJLMR75msmC_ZXXq_xSFnrNRJBwJRjTUXhTrlE_oKQcb4RrKr2Lq8-CgntfCom2kjFCR2cXLmNJwqQmKpubs-NVi5cWCoLxnQdafmLlt9Ce_LlxfigeMI_Wk0GrFcE9T0-NNFBv1OOYIXZZkONlgizBdXd7J6caUF2cNu_Honj5QQDqR6sJoxnomWeKEubbg0TguxVYOhZcZEzeZFYn001x-1lomH_PjN8s1UiMq89YmmoONXl3QQJnZUObpqidVq9D1EeNAzxkCAK05eMJxUYOenyYGyS2td9FzUu8oVXzdFR3IlYHiB2Ecfk2ksVM9iKbAN3MSIazphp-Ac0qh90b0gxMQ16LYiB7bkwvXZaunToc9zR8u7EXDsVsj8FJvmUb5zdXfPqQ9KK4b1oPaRSs-fD8Tb4gWUmIRrI-ebsThafgdtOHuL0Lm8J24SAhUqplh39y4_Ngk_JcuxIJfW7AC-nTd66M_Lv5C22mGnwCe9FSLJiwJx5i"

COOKIES = "__cf_bm=HiO2Au9tmajUEWqTEaXBGvzJd5fB9BF0O.94XnX_V7E-1777431607.2717292-1.0.1.1-zG7ytOnlEVHlz4b0jnlaUGe.96rrGNIPO5UJe6uz7mulwDtvrFHzda7Z5ETGsJTBSSWkTjmQ_wn.6lnUOjs3RTIVUZNNvCyStRcM.OoO8Z9kc2PSBT6dD9WG_HCFtNa9; __cflb=0H28vqQWtcC5yespLhipsiFh3EHzDzwT74NNSQeuPVV; _cfuvid=Kb1_7GKvy6rs28.OiH2RS33aSfzaK1QoRzxvTSl20wY-1777431607.2717292-1.0.1.1-HTF9Col70yz_bI9NwSXf_7xynpTIh90bXb1IuRkgopY; oai-sc=0gAAAAABp8XUJbWxCBKV3b6cdCSbmKH3JYYqRoaXYqi1rrF6rFJOrEgcuL_-kA3-DNVXMaJTDcOgmk_vdut-zr7XVzJ-Ar_H3tAvAwgodKd7-JVrohxqas7-5xslHJ5BwlPstQUk6ffRTav0LwvM75phBpAf74d4O_eRUUQtFcUwiUVW7TFFvvMQNsNw5mrdTM79he8B2A1PKmmG1xodB-MlWU5QXO_XdUpPjcHs0YH4283RfSFoGh-M"

USER_AGENT = "ChatGPT/1.2027.000 (Android 12; SM-M315F; build 2700000)"


class OpenAIShelbyConfig(ProviderConfig):
    """إعدادات OpenAI Shelby Provider"""
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "gpt-5-3-high"),
            timeout=kwargs.get("timeout", 120),
            max_retries=kwargs.get("max_retries", 3),
        )


class OpenAIShelbyProvider(BaseProvider):
    """
    OpenAI ChatGPT Android API Provider (Shelby)
    """
    name = "openai_shelby"
    description = "ChatGPT Android API — (gpt-5-3-high / gpt-5-3-mini)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,
            structured_output=False,
            parallel_requests=True,
            max_parallel_requests=5,
            max_context_tokens=128_000,
        )

    def __init__(self, config: OpenAIShelbyConfig | None = None):
        self.config: OpenAIShelbyConfig = config or OpenAIShelbyConfig()
        self._initialized = True

    def is_available(self) -> bool:
        return self._initialized

    def _get_chat_requirements(self, device_id: str) -> str | None:
        url = "https://android.chat.openai.com/backend-api/sentinel/chat-requirements"
        headers = {
            'User-Agent': USER_AGENT,
            'Accept': "application/json",
            'Content-Type': "application/json",
            'oai-package-name': "com.Modderme",
            'oai-client-type': "android",
            'oai-device-id': device_id,
            'chatgpt-account-id': device_id,
            'Cookie': COOKIES
        }
        try:
            resp = requests.post(url, json={}, headers=headers, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("token")
        except Exception:
            pass
        return None

    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        chunks = list(self.stream(prompt, history, system_prompt))
        return "".join(chunks)

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        device_id = str(random.randint(10000000000000000000, 99999999999999999999))
        session_id = str(uuid.uuid4())

        req_token = self._get_chat_requirements(device_id)
        if not req_token:
            yield "❌ فشل في الحصول على Chat Requirements Token. برجاء تحديث الكوكيز."
            return

        # بناء الرسائل مع السياق
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"[System Instructions]: {system_prompt}\n\n{full_prompt}"
        if history:
            history_text = "\n".join([f"{m.role}: {m.content[:400]}" for m in history[-6:]])
            full_prompt = f"[History]:\n{history_text}\n\n[Current User Message]: {full_prompt}"

        message_id = str(uuid.uuid4())
        url = "https://android.chat.openai.com/backend-api/f/conversation"

        sentinel_payload = {
            "bot_token": {
                "play_integrity_token": PLAY_INTEGRITY_TOKEN,
                "chat_requirement_token": req_token
            }
        }

        payload = {
            "action": "next",
            "messages": [{
                "id": message_id,
                "author": {"role": "user"},
                "content": {"parts": [full_prompt], "content_type": "text"},
                "status": "finished_successfully",
                "recipient": "all",
                "metadata": {
                    "is_visually_hidden_from_conversation": False,
                    "exclude_after_next_user_message": False
                }
            }],
            "model": self.config.model or "gpt-5-3-high",
            "supported_encodings": ["v1"],
            "supports_buffering": True,
            "timezone": "Africa/Cairo",
            "timezone_offset_min": -180,
            "stream": True
        }

        headers = {
            'User-Agent': USER_AGENT,
            'Accept': "text/event-stream,application/json",
            'Content-Type': "application/json",
            'x-sentinel-payload': json.dumps(sentinel_payload),
            'x-oai-convo-session-id': session_id,
            'oai-device-id': device_id,
            'chatgpt-account-id': device_id,
            'Cookie': COOKIES
        }

        try:
            response = requests.post(url, json=payload, headers=headers, stream=True, timeout=self.config.timeout)
            
            full_accumulated = ""
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: ") and "[DONE]" not in decoded:
                        try:
                            data = json.loads(decoded[6:])
                            if not isinstance(data, dict):
                                continue

                            # 1) فحص الرسالة والتأكد إنها بتاعة المساعد (Assistant)
                            msg = data.get("message")
                            if not msg and isinstance(data.get("v"), dict):
                                msg = data.get("v").get("message")

                            if msg and isinstance(msg, dict):
                                role = msg.get("author", {}).get("role", "")
                                if role == "assistant":
                                    parts = msg.get("content", {}).get("parts", [])
                                    if parts and isinstance(parts[0], str) and parts[0]:
                                        diff = parts[0][len(full_accumulated):]
                                        if diff:
                                            full_accumulated = parts[0]
                                            yield diff
                                continue

                            chunk_text = ""
                            # 2) تجميع التحديثات الجديدة (Append / Patch)
                            if data.get("o") == "append" and data.get("p") == "/message/content/parts/0":
                                v = data.get("v", "")
                                if isinstance(v, str):
                                    chunk_text = v
                            elif data.get("o") == "patch" and isinstance(data.get("v"), list):
                                for op in data["v"]:
                                    if isinstance(op, dict):
                                        if op.get("o") == "append" and op.get("p") == "/message/content/parts/0":
                                            v = op.get("v", "")
                                            if isinstance(v, str):
                                                chunk_text += v
                                        elif op.get("o") == "replace" and op.get("p") == "/message/content/parts/0":
                                            v = op.get("v", "")
                                            if isinstance(v, str):
                                                diff = v[len(full_accumulated):]
                                                if diff:
                                                    chunk_text = diff
                                                    full_accumulated = v
                            elif isinstance(data.get("v"), str) and "o" not in data and "message" not in data:
                                chunk_text = data["v"]

                            if chunk_text:
                                full_accumulated += chunk_text
                                yield chunk_text

                        except Exception:
                            continue
        except Exception as e:
            yield f"\n❌ حدث خطأ أثناء الاتصال بـ OpenAI Shelby: {e}"
