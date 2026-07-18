# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════
  GensparkProvider — Adapter لـ Genspark
  يلف سكريبت genspark_chat الأصلي في BaseProvider
  يدعم: account rotation, auto-register, SSE streaming
═══════════════════════════════════════════════════════
"""
import sys
import pathlib
import importlib.util
import threading
from typing import Any, Generator

from .base import BaseProvider, ProviderConfig, Message, ProviderCapabilities

_DIR = pathlib.Path(__file__).resolve().parent.parent
_NEW_PROVIDERS = _DIR / "new_providers"

# ── تحميل الموديول الأصلي ديناميكياً ──
_gs_module = None
_gs_lock = threading.Lock()

# خريطة الموديلات → ملف السكريبت
GENSPARK_MODELS = {
    "claude-sonnet-5":       "Genspark_sonnet-5.py",
    "claude-opus-4-8":       "Genspark_opus-4-8.py",
    "claude-opus-4-7":       "Genspark_opus-4-7.py",
    "claude-opus-4-6":       "Genspark_opus-4-6.py",
    "claude-sonnet-4-6":     "Genspark_sonnet-4-6.py",
    "o3-pro":                "Genspark_o3-pro.py",
    "grok-4.20-reasoning":   "Genspark_grok-4.20-0309-reasoning.py",
    "kimi-k2p6":             "Genspark_kimi-k2p6.py",
    "glm-5p2":               "Genspark_glm-5p2.py",
    "deep-seek-v4-pro":      "Genspark_deep-seek-v4-pro.py",
    "minimax-3":             "Genspark_minimax-3.py",
    "minimax-m2p7":          "Genspark_minimax-m2p7.py",
    "trinity-large-thinking":"Genspark_trinity-large-thinking.py",
    "genspark-v5.5":         "Genspark_V5.5.py",
    "kimi-k2p7-code":        "Genspark_kimi-k2p7-code.py",
    "claude-fable-5":        "Genspark_claude-fable-5.py",
    "gpt-5.6-sol":           "Genspark_gpt-5.6-sol.py",
    "gpt-5.6-terra":         "Genspark_gpt-5.6-terra.py",
    "grok-4.5":              "Genspark_grok-4.5.py",
}


def _load_genspark_module(script_name: str):
    """تحميل سكريبت Genspark كموديول Python"""
    script_path = _NEW_PROVIDERS / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"سكريبت Genspark مش موجود: {script_path}")

    spec = importlib.util.spec_from_file_location(
        f"genspark_{script_name.replace('.py', '').replace('-', '_')}",
        str(script_path)
    )
    if spec is None or spec.loader is None:  # T-010: mypy narrow
        raise ImportError(f"تعذر تحميل spec لسكريبت Genspark: {script_path}")
    mod = importlib.util.module_from_spec(spec)
    # Suppress prints during import
    spec.loader.exec_module(mod)
    return mod


class GensparkConfig(ProviderConfig):
    """إعدادات Genspark"""
    def __init__(self, **kwargs):
        super().__init__(
            model=kwargs.get("model", "claude-sonnet-5"),
            timeout=kwargs.get("timeout", 600),
            max_retries=kwargs.get("max_retries", 10),
        )
        self.script_name = GENSPARK_MODELS.get(
            self.model,
            kwargs.get("script_name", "Genspark_sonnet-5.py")
        )


class GensparkProvider(BaseProvider):
    """
    Genspark — يدعم 13+ موديل عبر SSE streaming
    يستخدم curl_cffi + account rotation + auto-register
    """
    name = "genspark"
    description = "Genspark — Claude, GPT, Grok, DeepSeek, وأكتر (مجاني)"

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=False,              # SSE لكن مش streaming حقيقي في الواجهة
            structured_output=False,
            parallel_requests=True,       # account rotation بيسمح بالتوازي
            max_parallel_requests=3,
            max_context_tokens=200_000,   # Claude-level context
        )

    def __init__(self, config: GensparkConfig | None = None):
        self.config: GensparkConfig = config or GensparkConfig()
        self._initialized = False
        # T-010: dynamically-loaded script module — typed Any so mypy
        # accepts attribute access on it after initialize().
        self._module: Any = None
        self._cfg: Any = None

    def initialize(self) -> bool:
        try:
            self._module = _load_genspark_module(self.config.script_name)
            self._cfg = self._module.Config()
            self._cfg.model = self.config.model
            self._cfg.always_new_chat = True
            self._cfg.save_to_json = False
            self._cfg.auto_share = False
            self._cfg.persistent = False
            self._cfg.max_retries = self.config.max_retries
            self._initialized = True
            return True
        except Exception as e:
            print(f"❌ Genspark init error: {e}")
            return False

    def is_available(self) -> bool:
        if not self._initialized:
            return False
        try:
            accounts = self._module.load_accounts(self._cfg)
            return len(accounts) > 0
        except Exception:
            return False

    def send(self, prompt: str, history: list[Message] | None = None,
             system_prompt: str = "") -> str:
        """
        إرسال رسالة — مع:
        ✅ اختيار عشوائي بين الحسابات (مش بالترتيب)
        ✅ يكمل يجرب لغاية ما يلاقي حساب شغال
        ✅ إنشاء حساب جديد تلقائياً لو كلهم خلصوا
        """
        import random

        if not self._initialized:
            self.initialize()

        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        # تحويل الـ history لسياق في البرومبت (API مش بيقبل history format خارجي)
        if history and len(history) > 0:
            full_prompt += "[سياق المحادثة السابقة]:\n"
            for msg in history[-6:]:  # آخر 6 رسائل
                role_label = "المستخدم" if msg.role == "user" else "المساعد"
                # نقطّع المحتوى الطويل عشان ما نستهلكش رصيد كتير
                content = msg.content[:800] if len(msg.content) > 800 else msg.content
                full_prompt += f"--- {role_label} ---\n{content}\n\n"
            full_prompt += "[الطلب الحالي]:\n"
        full_prompt += prompt

        # تدوير عشوائي — يجرب كل الحسابات
        skip_emails: set[str] = set()
        max_rounds = 2  # جولتين: الأولى كل الحسابات، الثانية بعد auto-register

        for round_num in range(max_rounds):
            # حساب عدد المحاولات = كل الحسابات المتاحة
            try:
                all_accounts = self._module.load_accounts(self._cfg)
                total_accounts = len(all_accounts)
            except Exception:
                total_accounts = self._cfg.max_retries

            max_attempts = max(total_accounts, self._cfg.max_retries)

            for attempt in range(max_attempts):
                # تفعيل الاختيار العشوائي
                old_tie_break = getattr(self._cfg, 'tie_break', 'highest')
                self._cfg.tie_break = "random"

                result = self._module.lock_pick_and_reserve(self._cfg, skip_emails=skip_emails)

                # إرجاع الإعداد الأصلي
                self._cfg.tie_break = old_tie_break

                if not result:
                    # مفيش حسابات متاحة خالص — نخرج من الحلقة الداخلية
                    print(f"  ❌ Genspark: مفيش حسابات متاحة (جولة {round_num+1}، محاولة {attempt+1})")
                    break

                acc, cookies = result
                email = acc.get("email", "?")
                print(f"  🎲 Genspark محاولة #{attempt+1} (عشوائي) بحساب: {email[:20]}...")

                try:
                    answer, project_id, msg_id = self._module.send_chat(
                        cookies=cookies,
                        question=full_prompt,
                        email=email,
                        project_id=None,
                        history=[],
                        cfg=self._cfg,
                    )

                    # حساب خلص الرصيد
                    if answer == "__CREDIT_EXHAUSTED__":
                        print(f"  💰 رصيد خلص: {email[:20]}")
                        self._module.release_account(email, self._cfg, status_zero=True)
                        skip_emails.add(email)
                        continue

                    # session انتهت → نجرب نجددها بـ login
                    if answer == "__SESSION_EXPIRED__":
                        password = acc.get("password", "")
                        if password:
                            print(f"  🔄 Session منتهية — بيجدد login: {email[:20]}...")
                            new_cookies = self._module.do_login(email, password)
                            if new_cookies:
                                # Login نجح! → نحدّث الحساب ونعيد المحاولة
                                print(f"  ✅ Login نجح — بيعيد الطلب: {email[:20]}")
                                # حفظ الـ cookies الجديدة في الملف
                                self._update_account_cookies(email, new_cookies)
                                # إعادة المحاولة بنفس الحساب
                                try:
                                    answer2, _, _ = self._module.send_chat(
                                        cookies=new_cookies,
                                        question=full_prompt,
                                        email=email,
                                        project_id=None,
                                        history=[],
                                        cfg=self._cfg,
                                    )
                                    if answer2 and answer2 not in ("__CREDIT_EXHAUSTED__", "__SESSION_EXPIRED__"):
                                        self._module.release_account(email, self._cfg)
                                        return answer2
                                    elif answer2 == "__CREDIT_EXHAUSTED__":
                                        print(f"  💰 رصيد خلص بعد التجديد: {email[:20]}")
                                        self._module.release_account(email, self._cfg, status_zero=True)
                                    else:
                                        self._module.release_account(email, self._cfg, status_failed=True)
                                except Exception:
                                    self._module.release_account(email, self._cfg, status_failed=True)
                            else:
                                print(f"  ❌ Login فشل: {email[:20]}")
                                self._module.release_account(email, self._cfg, status_failed=True)
                        else:
                            print(f"  🔒 Session منتهية (مفيش password): {email[:20]}")
                            self._module.release_account(email, self._cfg, status_failed=True)
                        skip_emails.add(email)
                        continue

                    if answer:
                        self._module.release_account(email, self._cfg)
                        return answer

                    # رد فاضي — نجرب حساب تاني
                    self._module.release_account(email, self._cfg)
                    skip_emails.add(email)

                except Exception as e:
                    print(f"  ❌ Genspark error: {e}")
                    try:
                        self._module.release_account(email, self._cfg)
                    except Exception:
                        pass
                    skip_emails.add(email)

            # ═══ لو وصلنا هنا = كل الحسابات خلصت ═══
            if round_num == 0:
                # الجولة الأولى خلصت — نجرب ننشئ حساب جديد
                print("  🔄 كل الحسابات خلصت — بيتم إنشاء حساب جديد...")
                reg_proc = self._auto_register_and_wait()
                if reg_proc:
                    # حساب جديد اتسجل — نجرب تاني (جولة 2) بـ skip_emails فاضي
                    skip_emails.clear()
                    continue
                else:
                    print("  ❌ فشل إنشاء حساب جديد")
                    break

        return "❌ فشل الاتصال بـ Genspark بعد كل المحاولات + إنشاء حساب جديد"

    def _update_account_cookies(self, email: str, new_cookies: dict):
        """حفظ cookies جديدة في ملف الحسابات بعد login ناجح"""
        try:
            accounts = self._module.load_accounts(self._cfg)
            for i, acc in enumerate(accounts):
                if acc.get("email") == email:
                    accounts[i]["cookies"] = new_cookies
                    accounts[i]["session_refreshed"] = True
                    break
            self._module.save_accounts(accounts, self._cfg)
            print(f"  💾 Cookies محدثة في الملف: {email[:20]}")
        except Exception as e:
            print(f"  ⚠️ فشل حفظ cookies: {e}")

    def _auto_register_and_wait(self, timeout: int = 120) -> bool:
        """
        يشغل auto-register وينتظر حتى يتم إنشاء حساب جديد.
        يرجع True لو نجح.
        """
        import time

        try:
            # تفعيل auto-register
            old_auto = getattr(self._cfg, 'auto_register', True)
            old_max = getattr(self._cfg, 'auto_register_max', 1)
            self._cfg.auto_register = True
            self._cfg.auto_register_max = 1

            proc = self._module._start_auto_register(self._cfg)

            self._cfg.auto_register = old_auto
            self._cfg.auto_register_max = old_max

            if not proc:
                return False

            # ننتظر حتى يخلص أو timeout
            start = time.time()
            while time.time() - start < timeout:
                ret = proc.poll()
                if ret is not None:
                    # خلص — نتحقق هل أضاف حساب جديد
                    try:
                        new_accounts = self._module.load_accounts(self._cfg)
                        if len(new_accounts) > 0:
                            print(f"  ✅ حساب جديد اتسجل! ({len(new_accounts)} حساب متاح)")
                            return True
                    except Exception:
                        pass
                    return ret == 0

                time.sleep(5)
                print(f"  ⏳ بينتظر تسجيل حساب جديد... ({int(time.time() - start)}s)")

            # Timeout — نوقف العملية
            try:
                proc.kill()
            except Exception:
                pass
            print(f"  ⏰ Timeout — التسجيل أخذ أكتر من {timeout}s")
            return False

        except Exception as e:
            print(f"  ❌ Auto-register error: {e}")
            return False

    def stream(self, prompt: str, history: list[Message] | None = None,
               system_prompt: str = "") -> Generator[str, None, None]:
        """Genspark مش بيدعم streaming حقيقي للـ WebSocket — فبنستخدم send وبنقطّع"""
        full_response = self.send(prompt, history, system_prompt)
        # نبعت الرد كقطع كبيرة عشان يبان streaming
        chunk_size = 50
        for i in range(0, len(full_response), chunk_size):
            yield full_response[i:i + chunk_size]

    def switch_model(self, model: str) -> bool:
        """تغيير الموديل — يحمل الموديول المناسب"""
        if model not in GENSPARK_MODELS:
            return False
        self.config.model = model
        self.config.script_name = GENSPARK_MODELS[model]
        self._initialized = False
        return self.initialize()

    def get_info(self) -> dict:
        info = super().get_info()
        info["models"] = list(GENSPARK_MODELS.keys())
        return info

    def get_remaining_calls(self) -> int:
        """عدد الحسابات المتاحة في Genspark"""
        if not self._initialized:
            return 0
        try:
            accounts = self._module.load_accounts(self._cfg)
            return len(accounts)
        except Exception:
            return 0

