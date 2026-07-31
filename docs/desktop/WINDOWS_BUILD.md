# بناء نسخة سطح المكتب على Windows — دليل المالك (TSK-727c)

> المرجع المعماري: ADR-006 (pywebview + PyInstaller).
> وضع المتصفح (`python server.py`) يبقى المسار الأول — هذا الدليل
> يضيف توزيعة سطح مكتب ولا يغيّر شيئًا في المسار القائم.

## المتطلبات المسبقة (مرة واحدة)

1. **Python 3.11+** من python.org — أثناء التثبيت فعِّل
   ☑ *Add python.exe to PATH*.
2. **Microsoft Edge WebView2 Runtime** — مثبَّت مسبقًا على معظم
   أنظمة Windows 10/11؛ إن لم يكن:
   <https://developer.microsoft.com/microsoft-edge/webview2/>

## خطوات البناء (أمرًا-بأمر، من PowerShell داخل مجلد المشروع)

```powershell
# 1) بيئة معزولة (يُنصح بها)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) تبعيات التشغيل + وضع سطح المكتب + أداة التغليف
pip install -r requirements.txt
pip install pywebview pyinstaller

# 3) تجربة سريعة قبل التغليف (نافذة مباشرة بلا exe)
python desktop.py
#   يجب أن تفتح نافذة «WebDev AI Editor» — أغلقها ثم تابع.

# 4) التغليف
pyinstaller desktop.spec

# 5) الناتج
# dist\WebDevAIEditor\WebDevAIEditor.exe  ← شغّله بنقرة مزدوجة
```

## ملاحظات

- **مجلد المشروع الافتراضي** هو مجلد تشغيل الـ exe. لفتح مشروع
  محدد: `WebDevAIEditor.exe --project C:\path\to\project`.
- **مفاتيح المزودات**: `config.yaml` يُضمَّن داخل التوزيعة كنسخة
  وقت البناء — عدِّله قبل البناء، أو ضع نسخة بجوار الـ exe
  (`dist\WebDevAIEditor\config.yaml`) فهي التي تُقرأ.
- **لا يفتح شيء؟** أعد البناء بعد تغيير `console=False` إلى
  `console=True` في `desktop.spec` — ستظهر نافذة كونسول برسائل
  الإقلاع تشخّص المشكلة.
- **جدار الحماية**: الخادم يستمع على 127.0.0.1 حصريًا (منفذ حر
  عشوائي) — لا حاجة لأي استثناء في جدار الحماية ولا تعريض شبكي.

## بعد البناء

نفّذ قائمة الفحص: `docs/desktop/OWNER_CHECKLIST.md` — إقفال P2
النهائي معلَّق على تأشيرك عليها (D-8-ب).
