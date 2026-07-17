# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  UseAIProvider — مزود Use.ai
  منقول ومُنظف من use_ai__claude-sonnet-5.py
  يدعم: إدارة الحسابات، WebSocket streaming، Share Links
═══════════════════════════════════════════════════════
"""
import os
import sys
import time
import uuid
import json
import re
import subprocess
import threading
import pathlib
import requests
from datetime import datetime
from typing import Generator

from .base import BaseProvider, ProviderConfig, Message, ProviderCapabilities

# ── websocket-client ─────────────────────────────────
try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

# ── الإعدادات ──
_DIR = pathlib.Path(__file__).resolve().parent.parent
_SAVE_LOCK = threading.Lock()

_HEADERS = {
    "accept": "*/*",
    "content-type": "application/json",
    "origin": "https://use.ai",
    "referer": "https://use.ai/",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
}


class UseAIConfig(ProviderConfig):
    """إعدادات خاصة بـ Use.ai"""
    def __init__(self, **kwargs):
        # فقط نمرر الحقول اللي ProviderConfig يقبلها
        super().__init__(
            model=kwargs.get("model", "gateway-claude-sonnet-5"),
            timeout=kwargs.get("timeout", 90),
            max_retries=kwargs.get("max_retries", 2),
        )
        self.ws_timeout = kwargs.get("ws_timeout", 90)
        self.request_timeout = kwargs.get("request_timeout", 12)
        self.auto_register = kwargs.get("auto_register", True)
        self.auto_register_max = kwargs.get("auto_register_max", 5)
        self.accounts_dir = kwargs.get("accounts_dir", str(_DIR))
        self.accounts_file = kwargs.get("accounts_file", "accounts_use_ai.json")
        self.create_share = kwargs.get("create_share", True)


class UseAIProvider(BaseProvider):
    """
    مزود Use.ai — يستخدم WebSocket للتواصل مع Claude عبر use.ai
    """
    name = "use_ai"
    description = "Use.ai — Claude Sonnet 5 عبر WebSocket (مجاني)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True,               # WebSocket streaming حقيقي
            structured_output=False,
            parallel_requests=False,      # حساب واحد لكل طلب
            max_parallel_requests=1,
            max_context_tokens=200_000,   # Claude-level
        )

    def __init__(self, config: UseAIConfig | None = None):
        self.config: UseAIConfig = config or UseAIConfig()
        self._initialized = False
        self._accounts_path = pathlib.Path(self.config.accounts_dir) / self.config.accounts_file
        self._print_fn = print  # يمكن استبدالها بدالة طباعة مخصصة

    def set_printer(self, fn):
        """تعيين دالة طباعة مخصصة (للـ CLI)"""
        self._print_fn = fn

    # ════════════════════════════════════════════
    # التحقق من الجاهزية
    # ════════════════════════════════════════════
    def is_available(self) -> bool:
        if not HAS_WEBSOCKET:
            return False
        accounts = self._load_accounts()
        ready = self._find_ready_account(accounts)
        return ready is not None

    def initialize(self) -> bool:
        if not HAS_WEBSOCKET:
            self._print_fn("❌ مكتبة websocket-client مش مثبتة! شغّل: pip install websocket-client")
            return False
        self._initialized = True
        return True

    # ════════════════════════════════════════════
    # الإرسال (رد كامل)
    # ════════════════════════════════════════════
    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        """إرسال رسالة وانتظار الرد الكامل"""
        full_prompt = self._build_full_prompt(prompt, system_prompt)
        account = self._get_ready_account()
        if not account:
            raise RuntimeError("مفيش حسابات متاحة!")

        # تحويل History لصيغة Use.ai
        ws_messages = self._convert_history(history) if history else []

        if ws_messages:
            # إرسال مع history
            chat_id = str(uuid.uuid4())
            ws_messages.append(self._make_user_msg(full_prompt))
            result = self._ws_send(account, chat_id, ws_messages, stream_print=False)
        else:
            # شات جديد
            result = self._ws_send_fresh(account, full_prompt, stream_print=False)

        if not result:
            self._expire_account(account["email"])
            raise RuntimeError("فشل استقبال الرد من الموديل!")

        self._mark_account_used(account["email"], result.get("share_url"))
        return result["reply"]

    # ════════════════════════════════════════════
    # الإرسال (stream)
    # ════════════════════════════════════════════
    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        """إرسال واستقبال الرد كـ stream — مع retry تلقائي عند rate limit"""

        # بناء الرسائل: System + History + الرسالة الجديدة
        all_messages = []

        # 1) System prompt كأول رسالة
        if system_prompt:
            all_messages.append(self._make_user_msg(
                f"[SYSTEM INSTRUCTIONS — follow strictly]\n{system_prompt}"
            ))
            all_messages.append({
                "id": "msg_sys_ack",
                "role": "assistant",
                "parts": [{"type": "text", "text": "فهمت التعليمات. جاهز للمساعدة في تطوير الويب."}],
            })

        # 2) History السابقة
        if history:
            for msg in history:
                if msg.role == "system":
                    continue
                all_messages.append({
                    "id": f"msg_{uuid.uuid4().hex[:8]}",
                    "role": msg.role,
                    "parts": [{"type": "text", "text": msg.content}],
                })

        # 3) الرسالة الجديدة
        all_messages.append(self._make_user_msg(prompt))

        # ═══ Retry loop بلا حدود — يمسح الحساب وينشئ جديد لحد ما ينجح ═══
        attempt = 0
        while True:
            attempt += 1
            account = self._get_ready_account()
            if not account:
                self._print_fn(f"  ⏳ مفيش حسابات جاهزة... بنحاول ننشئ جداد (محاولة {attempt})")
                time.sleep(3)
                continue

            self._print_fn(f"  🔄 محاولة #{attempt} بحساب: {account['email'][:20]}...")

            # جلب التوكنات المطلوبة للـ WebSocket
            ws_token, app_token = self._get_ws_tokens(account['session_token'], account['user_id'])

            chat_id = str(uuid.uuid4())
            ws_url = (
                f"wss://agents.use.ai/agents/budget-agent/{chat_id}"
                f"?token={ws_token}&app_token={app_token}"
                f"&userId={account['user_id']}&userType=regular&userEmail={account['email']}"
                f"&planType=free&isTestUser=false"
            )
            ws_headers = [
                "Origin: https://use.ai",
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                f"Cookie: __Secure-better-auth.session_token={account['session_token']}"
            ]

            # اتصال WebSocket
            try:
                ws = websocket.create_connection(ws_url, header=ws_headers, timeout=30)
                ws.send(json.dumps({"type": "prewarm", "chatId": chat_id}))
            except Exception as e:
                self._print_fn(f"  ❌ فشل الاتصال: {e} — بنمسح الحساب ونجرب غيره...")
                self._expire_account(account["email"])
                time.sleep(2)
                continue

            # إرسال الرسالة
            payload = self._build_payload(account, chat_id, all_messages)
            got_response = False
            rate_limited = False
            connection_error = False

            try:
                ws.send(json.dumps(payload))
                deadline = time.time() + self.config.ws_timeout

                while time.time() < deadline:
                    try:
                        raw = ws.recv()
                        if not raw:
                            break
                        data = json.loads(raw)
                        msg_type = data.get("type", "")

                        if msg_type == "rate-limit-error":
                            self._expire_account(account["email"])
                            rate_limited = True
                            break
                        elif msg_type == "error":
                            err_txt = data.get("error", data.get("message", "خطأ غير معروف"))
                            self._print_fn(f"  ❌ خطأ من السيرفر: {err_txt} — بنمسح الحساب ونجرب غيره...")
                            self._expire_account(account["email"])
                            connection_error = True
                            break
                        elif msg_type in ("stream-complete", "done"):
                            break

                        chunk = data.get("chunk", {})
                        if chunk.get("type") == "text-delta":
                            delta = chunk.get("delta", "")
                            if delta:
                                got_response = True
                                yield delta
                        elif chunk.get("type") == "finish":
                            break
                    except websocket.WebSocketConnectionClosedException:
                        self._print_fn(f"  ❌ انقطع الاتصال — بنمسح الحساب ونجرب غيره...")
                        self._expire_account(account["email"])
                        connection_error = True
                        break
                    except Exception as e:
                        self._print_fn(f"  ❌ خطأ: {e} — بنمسح الحساب ونجرب غيره...")
                        self._expire_account(account["email"])
                        connection_error = True
                        break

                # لو الوقت خلص ومجاش رد
                if not got_response and not rate_limited and not connection_error:
                    self._print_fn(f"  ⏰ انتهت المهلة بدون رد — بنمسح الحساب ونجرب غيره...")
                    self._expire_account(account["email"])
                    connection_error = True

            finally:
                try:
                    ws.close()
                except Exception:
                    pass

            if rate_limited or connection_error:
                if not got_response:
                    time.sleep(2)
                    continue

            # نجح — حذف الحساب وتجديد الـ pool
            self._mark_account_used(account["email"], None)
            return

    # ════════════════════════════════════════════
    # أدوات داخلية
    # ════════════════════════════════════════════
    def _build_full_prompt(self, prompt: str, system_prompt: str) -> str:
        if system_prompt:
            return f"[System Instructions]\n{system_prompt}\n\n[User Request]\n{prompt}"
        return prompt

    def _convert_history(self, history: list[Message]) -> list[dict]:
        """تحويل History من Message objects لصيغة Use.ai"""
        result = []
        for msg in history:
            if msg.role == "system":
                continue  # system يُدمج في البرومبت
            result.append({
                "id": f"msg_{uuid.uuid4().hex[:8]}",
                "role": msg.role,
                "parts": [{"type": "text", "text": msg.content}],
            })
        return result

    def _make_user_msg(self, text: str) -> dict:
        return {
            "id": f"msg_{uuid.uuid4().hex[:8]}",
            "role": "user",
            "parts": [{"type": "text", "text": text}],
            "metadata": {
                "isDeepResearchMode": False, "isWebSearchMode": False,
                "isAgenticMode": False, "isImageGenerationMode": False,
                "needsBlurPreview": False, "deepResearchProcessor": "pro-fast"
            }
        }

    def _get_ws_tokens(self, session_token: str, user_id: str) -> tuple:
        """جلب توكن الـ WS وتوكن الـ App Attestation المطلوبة للاتصال"""
        headers = {
            "accept": "*/*",
            "content-type": "application/json",
            "origin": "https://use.ai",
            "referer": "https://use.ai/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Cookie": f"__Secure-better-auth.session_token={session_token}"
        }
        ws_token = ""
        app_token = ""
        try:
            r1 = requests.get("https://api.use.ai/v1/auth/token", headers=headers, timeout=10)
            if r1.status_code == 200:
                ws_token = r1.json().get("token", "")
        except Exception as e:
            self._print_fn(f"  ⚠️ فشل جلب ws_token: {e}")

        try:
            r2 = requests.post("https://api.use.ai/v1/auth/app-attestation",
                              json={"userId": user_id}, headers=headers, timeout=10)
            if r2.status_code == 200:
                app_token = r2.json().get("token", "")
        except Exception as e:
            self._print_fn(f"  ⚠️ فشل جلب app_token: {e}")

        return ws_token, app_token

    def _build_payload(self, account: dict, chat_id: str, messages: list) -> dict:
        return {
            "chatId": chat_id,
            "userId": account["user_id"],
            "email": account["email"],
            "userType": "regular",
            "userEmail": account["email"],
            "planType": "free",
            "subscriptionStatus": "inactive",
            "isFreemium": False,
            "isTestUser": False,
            "cfModelsVariant": "OFF",
            "mixpanelUserId": account["mixpanel_id"],
            "deviceId": account["device_id"],
            "isWebSearchMode": False,
            "isDeepResearchMode": False,
            "isImageGenerationMode": False,
            "agenticMode": False,
            "connectorsEnabled": False,
            "isStandaloneImageMode": False,
            "needsBlurPreview": False,
            "deepResearchProcessor": "pro-fast",
            "selectedModel": self.config.model,
            "locale": "en",
            "userTimezone": "Africa/Cairo",
            "userCountry": "Egypt (EG)",
            "messages": messages,
            "trigger": "submit-message",
            "source": "chat_page"
        }

    # ── WebSocket Fresh Send (بدون stream_print) ──
    def _ws_send_fresh(self, account: dict, question: str,
                       stream_print: bool = True) -> dict | None:
        chat_id = str(uuid.uuid4())
        messages = [self._make_user_msg(question)]
        return self._ws_send(account, chat_id, messages, stream_print)

    def _ws_send(self, account: dict, chat_id: str, messages: list,
                 stream_print: bool = True) -> dict | None:
        user_id = account["user_id"]
        email = account["email"]
        session_token = account["session_token"]

        # جلب التوكنات المطلوبة
        ws_token, app_token = self._get_ws_tokens(session_token, user_id)

        ws_url = (
            f"wss://agents.use.ai/agents/budget-agent/{chat_id}"
            f"?token={ws_token}&app_token={app_token}"
            f"&userId={user_id}&userType=regular&userEmail={email}"
            f"&planType=free&isTestUser=false"
        )
        ws_headers = [
            "Origin: https://use.ai",
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            f"Cookie: __Secure-better-auth.session_token={session_token}"
        ]

        try:
            ws = websocket.create_connection(ws_url, header=ws_headers, timeout=15)
            ws.send(json.dumps({"type": "prewarm", "chatId": chat_id}))
        except Exception:
            return None

        payload = self._build_payload(account, chat_id, messages)
        full_response = ""

        try:
            ws.send(json.dumps(payload))
            deadline = time.time() + self.config.ws_timeout

            while time.time() < deadline:
                try:
                    raw = ws.recv()
                    if not raw:
                        break
                    data = json.loads(raw)
                    msg_type = data.get("type", "")

                    if msg_type == "rate-limit-error":
                        break
                    elif msg_type in ("stream-complete", "done"):
                        break

                    chunk = data.get("chunk", {})
                    if chunk.get("type") == "text-delta":
                        delta = chunk.get("delta", "")
                        if delta:
                            if stream_print:
                                self._print_fn(delta, end="", flush=True)
                            full_response += delta
                    elif chunk.get("type") == "finish":
                        break
                except websocket.WebSocketConnectionClosedException:
                    break
                except Exception:
                    break
        finally:
            ws.close()

        if not full_response:
            return None

        return {"chatId": chat_id, "messages": messages, "reply": full_response}

    # ════════════════════════════════════════════
    # إدارة الحسابات
    # ════════════════════════════════════════════
    def _load_accounts(self) -> list:
        if not self._accounts_path.exists():
            return []
        try:
            return json.loads(self._accounts_path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_accounts(self, accounts: list):
        with _SAVE_LOCK:
            tmp = self._accounts_path.with_suffix(".json.tmp")
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(accounts, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp, self._accounts_path)
            except Exception:
                pass

    def _find_ready_account(self, accounts: list) -> dict | None:
        now = datetime.now()
        for acc in accounts:
            if acc.get("status") == "active" and not acc.get("messages_sent", 0):
                last_up = acc.get("last_updated")
                if last_up:
                    try:
                        dt = datetime.fromisoformat(last_up)
                        if (now - dt).total_seconds() > 24 * 3600:
                            acc["status"] = "expired"
                            continue
                    except Exception:
                        pass
                if acc.get("cookies", {}).get("__Secure-better-auth.session_token"):
                    return acc
        return None

    def _get_ready_account(self) -> dict | None:
        for _ in range(3):
            accounts = self._load_accounts()
            ready = self._find_ready_account(accounts)
            if ready:
                email = ready["email"]
                for acc in accounts:
                    if acc.get("email") == email:
                        acc["status"] = "claiming"
                        acc["last_updated"] = datetime.now().isoformat()
                        break
                self._save_accounts(accounts)

                account_info = self._login_pool_account(ready)
                if account_info:
                    # نحطه "in_use" مش "used" — يتحول "used" بعد إرسال رسالة ناجحة
                    accounts = self._load_accounts()
                    for acc in accounts:
                        if acc.get("email") == email:
                            acc["status"] = "in_use"
                            acc["last_updated"] = datetime.now().isoformat()
                            break
                    self._save_accounts(accounts)
                    return account_info
                continue

        # إنشاء حسابات جديدة
        return self._register_and_save(count=self.config.auto_register_max)

    def _return_account_to_pool(self, email: str):
        """إعادة حساب للـ pool بعد فشل الاتصال"""
        accounts = self._load_accounts()
        for acc in accounts:
            if acc.get("email") == email:
                if acc["status"] == "in_use":
                    acc["status"] = "active"
                    acc["last_updated"] = datetime.now().isoformat()
                break
        self._save_accounts(accounts)

    def _login_pool_account(self, acc: dict) -> dict | None:
        session_token = acc.get("cookies", {}).get("__Secure-better-auth.session_token", "")
        if not session_token:
            return None
        cookies = {"__Secure-better-auth.session_token": session_token}
        try:
            r = requests.get(
                "https://api.use.ai/v1/auth/get-session",
                headers=_HEADERS, cookies=cookies,
                timeout=self.config.request_timeout
            )
            if r.status_code == 200:
                user_id = r.json().get("user", {}).get("id")
                if user_id:
                    return {
                        "email": acc["email"], "user_id": user_id,
                        "cookies": cookies, "session_token": session_token,
                        "mixpanel_id": str(uuid.uuid4()),
                        "device_id": f"guest:{uuid.uuid4()}"
                    }
                else:
                    self._expire_account(acc["email"])
        except Exception:
            pass
        return None

    def _register_fresh_account(self) -> dict | None:
        email = f"user_{uuid.uuid4().hex[:8]}@mail.tm"
        mixpanel_id = str(uuid.uuid4())
        guest_id = f"guest:{uuid.uuid4()}"

        try:
            r1 = requests.post(
                "https://api.use.ai/v1/auth/email-login",
                json={"email": email}, headers=_HEADERS,
                timeout=self.config.request_timeout
            )
            if r1.status_code != 200:
                return None
        except Exception:
            return None

        try:
            r2 = requests.post(
                "https://api.use.ai/v1/auth/sign-in/credentials",
                json={
                    "email": email, "mixpanelUserId": mixpanel_id,
                    "guestId": guest_id, "mid": mixpanel_id
                },
                headers=_HEADERS, timeout=self.config.request_timeout
            )
            if r2.status_code != 200:
                return None
        except Exception:
            return None

        auth_token = r2.headers.get("set-auth-token")
        if not auth_token:
            return None

        cookies = {"__Secure-better-auth.session_token": auth_token}
        try:
            r3 = requests.get(
                "https://api.use.ai/v1/auth/get-session",
                headers=_HEADERS, cookies=cookies,
                timeout=self.config.request_timeout
            )
            if r3.status_code == 200:
                user_id = r3.json().get("user", {}).get("id")
                if user_id:
                    return {
                        "email": email, "user_id": user_id,
                        "cookies": cookies, "session_token": auth_token,
                        "mixpanel_id": mixpanel_id, "device_id": guest_id
                    }
        except Exception:
            pass
        return None

    def _register_and_save(self, count: int = 5) -> dict | None:
        first = None
        accounts = self._load_accounts()
        for i in range(count):
            acc_info = self._register_fresh_account()
            if not acc_info:
                continue
            accounts.append({
                "email": acc_info["email"], "password": "",
                "cookies": acc_info["cookies"], "provider": "generated",
                "status": "active", "messages_sent": 0, "share_url": None,
                "last_updated": datetime.now().isoformat(), "expires_in": 48
            })
            self._save_accounts(accounts)
            if first is None:
                first = acc_info
        return first

    def _mark_account_used(self, email: str, share_url: str | None):
        """حذف الحساب المستخدم + تجديد الـ pool"""
        accounts = self._load_accounts()
        accounts = [a for a in accounts if a.get("email") != email]
        self._save_accounts(accounts)
        self._print_fn(f"  🗑️ حذف حساب: {email[:20]}...")
        # تجديد الـ pool في الخلفية
        self._maintain_pool()

    def _expire_account(self, email: str):
        """حذف حساب منتهي + تجديد الـ pool"""
        accounts = self._load_accounts()
        accounts = [a for a in accounts if a.get("email") != email]
        self._save_accounts(accounts)
        self._maintain_pool()

    def _maintain_pool(self, min_ready: int = 5):
        """التأكد من وجود 5 حسابات جاهزة — يعمل في الخلفية"""
        import threading

        def _refill():
            accounts = self._load_accounts()
            active_count = sum(1 for a in accounts if a.get("status") == "active")
            needed = min_ready - active_count

            if needed <= 0:
                return

            self._print_fn(f"  🔄 تجديد الـ pool: {active_count} جاهز، محتاج {needed} جديد...")
            for i in range(needed):
                acc_info = self._register_fresh_account()
                if acc_info:
                    accounts = self._load_accounts()
                    accounts.append({
                        "email": acc_info["email"], "password": "",
                        "cookies": acc_info["cookies"], "provider": "generated",
                        "status": "active", "messages_sent": 0, "share_url": None,
                        "last_updated": datetime.now().isoformat(), "expires_in": 48
                    })
                    self._save_accounts(accounts)
            final = self._load_accounts()
            active_now = sum(1 for a in final if a.get("status") == "active")
            self._print_fn(f"  ✅ الـ pool جاهز: {active_now} حساب")

        t = threading.Thread(target=_refill, daemon=True)
        t.start()

    def get_remaining_calls(self) -> int:
        """عدد الحسابات الجاهزة في pool — كل حساب = رسالة واحدة"""
        try:
            accounts = self._load_accounts()
            return sum(
                1 for a in accounts
                if a.get("status") == "active" and not a.get("messages_sent", 0)
            )
        except Exception:
            return 0


