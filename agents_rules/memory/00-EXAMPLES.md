# 00-EXAMPLES — Reference Implementations

## 📸 Vision Payload Multi-block Formatting

عند إرسال مدخلات تحتوي على صور ونصوص (Multimodal/Vision) لـ Genspark، يجب استخدام الهيكل التالي للـ payload مع الالتزام بترتيب الكتل (كتلة الصورة أولاً، ثم كتلة النص ثانياً)، وتعيين `"pending": True` في الرسالة:

```python
if image_data:
    content_blocks = [
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{image_data['mime']};base64,{image_data['base64']}"
            }
        },
        {"type": "text", "text": question}
    ]
    new_msg = {"role": "user", "id": user_msg_id, "content": content_blocks, "pending": True}
else:
    new_msg = {"role": "user", "id": user_msg_id, "content": question, **_NULL_MSG_FIELDS}

## 🧹 Council Refusal Cleaner (Python)

لتطهير ملفات تقارير ردود النماذج الجماعية من الردود التي تحتوي على رفض بسبب سياسات الأمان أو التوجيهات الأخلاقية (دون التأثير ببرومبت السؤال نفسه):

```python
import re

# تقسيم الملف حسب اسم الموديل
sections = content.split("## 🤖 ")
header = sections[0]
model_sections = sections[1:]

refusal_keywords = [
    "cannot assist", "decline", "refuse", "can't help", "cannot help", "can’t help",
    "unable to help", "unable to assist", "not able to help", "not able to assist",
    "not going to help", "not going to assist", "cannot and will not", "sorry",
    "falls outside", "cannot provide", "approach this carefully", "not be able to"
]
rejection_regex = re.compile("|".join([re.escape(k) for k in refusal_keywords]), re.IGNORECASE)

kept_sections = []
for sec in model_sections:
    # عزل السؤال/البرومبت لتفادي الـ False Positives
    response_text = sec
    if "📝 السؤال :" in sec:
        parts = sec.split("📝 السؤال :")
        after_prompt = parts[1]
        if "════════" in after_prompt:
            response_text = after_prompt.split("════════", 1)[1]
            
    if not rejection_regex.search(response_text):
        kept_sections.append(sec)

new_content = header + "## 🤖 " + "## 🤖 ".join(kept_sections)
```

## 🔄 Supabase LocalStorage Token Retrieval Wait Loop

نمط احترافي ديناميكي لانتظار وسحب توكنات Supabase Auth من الـ LocalStorage داخل متصفح SeleniumBase لمنع حدوث Race Conditions (حيث يكتمل تحميل الصفحة قبل حفظ التوكنات برمجياً):

```python
import time

def extract_supabase_tokens(sb, timeout=20.0):
    """
    يقوم بفحص الـ LocalStorage بشكل متناوب ديناميكي حتى ظهور توكنات Supabase.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        tokens = sb.execute_script("""
            (function() {
                let keys = Object.keys(localStorage);
                let key = keys.find(k => k.includes('-auth-token') || k.includes('supabase.auth.token'));
                if (!key) return null;
                try {
                    let data = JSON.parse(localStorage.getItem(key));
                    let access = data.access_token || data.currentSession?.access_token;
                    let refresh = data.refresh_token || data.currentSession?.refresh_token;
                    if (access) return { access_token: access, refresh_token: refresh };
                } catch(e) {}
                return null;
            })();
        """)
        if tokens:
            return tokens
        time.sleep(0.5)
    return None
```

## 📧 BjeduMailClient - Reusable temporary email service client (em.bjedu.tech)

نمط متكامل ومستقل للتحكم في حسابات وعلب بريد موقع `em.bjedu.tech` بدون متصفح وبتخطي كامل لـ Cloudflare، يدعم التسجيل، الدخول، قراءة الرسائل، تحديد الرسائل كمقروءة، وسحب كل الحسابات النشطة:

```python
import cloudscraper
import random
import string
import re
import time

class BjeduMailClient:
    class Config:
        BASE_URL = "https://em.bjedu.tech"
        DEFAULT_DOMAIN = "@bjedu.tech"
        TIMEOUT = 30
        RETRIES = 5
        BACKOFF = 2
        POLL_DELAY = 5
        AUTO_SAVE = False
        SAVE_FILE = "bjedu_session.json"

    def __init__(self, email=None, password=None, token=None, account_id=None, config=None):
        self.config = config if config else self.Config()
        self.scraper = cloudscraper.create_scraper()
        self.email = email
        self.password = password
        self.token = token
        self.account_id = account_id

    def bypass_cloudflare(self) -> bool:
        # Hitting home page to populate cf_clearance session cookies
        r = self.scraper.get(self.config.BASE_URL, timeout=self.config.TIMEOUT)
        return r.status_code == 200

    def create_inbox(self) -> bool:
        # Generates and registers a clean alphanumeric account
        self.email = "ng" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8)) + self.config.DEFAULT_DOMAIN
        self.password = "".join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # 1. Register
        r = self.scraper.post(f"{self.config.BASE_URL}/api/register", json={
            "email": self.email, "password": self.password, "token": "", "code": None
        })
        if r.json().get('code') != 200:
            return False
            
        # 2. Login
        r_login = self.scraper.post(f"{self.config.BASE_URL}/api/login", json={
            "email": self.email, "password": self.password
        })
        self.token = r_login.json().get('data', {}).get('token')
        
        # 3. Get UserInfo
        r_info = self.scraper.get(f"{self.config.BASE_URL}/api/my/loginUserInfo", headers={"Authorization": self.token})
        self.account_id = r_info.json().get('data', {}).get('account', {}).get('accountId')
        return True

    def get_emails(self) -> list:
        # Fetches all incoming messages in the mailbox
        r = self.scraper.get(
            f"{self.config.BASE_URL}/api/email/list?accountId={self.account_id}&allReceive=0&emailId=0&timeSort=0&size=50&type=0",
            headers={"Authorization": self.token}
        )
        return r.json().get('data', {}).get('list', [])

    def mark_as_read(self, email_ids) -> bool:
        # Marks email(s) as read (email_ids: int or list)
        if isinstance(email_ids, int):
            email_ids = [email_ids]
        r = self.scraper.put(
            f"{self.config.BASE_URL}/api/email/read",
            json={"emailIds": email_ids},
            headers={"Authorization": self.token}
        )
        return r.json().get('code') == 200

    def load_session(self, file_path) -> bool:
        # Load from JSON and then bypass Cloudflare to avoid 403
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.email = data["email"]
        self.password = data["password"]
        self.token = data["token"]
        self.account_id = data["account_id"]
        self.bypass_cloudflare()
        return True
```


