# 📌 Decisions Log — قرارات تقنية مهمة

> الـ AI يراجع الملف ده قبل ما يقترح حاجة جديدة — مش يعيد اختراع العجلة

## 🏗️ Architecture Decisions

| القرار | السبب | البديل المرفوض |
|--------|-------|---------------|
| curl_cffi بدل requests | TLS fingerprint bypass — Cloudflare بيشوف requests | requests العادية |
| CDP Runtime.evaluate + userGesture بدل execute_script | React بيشتغل في main world — execute_script isolated | execute_script, ActionChains |
| Playwright للـ Baidu فقط | server بيربط tokens بـ browser session | curl_cffi مع Baidu |
| JSON atomic (.tmp → replace) | مفيش data corruption لو فيه crash | write مباشر |
| LOOP_MODE = True كـ default | الـ loop هو الـ production mode — --no-loop للاختبار بس | loop=False default |
| shared/ library مش تكرار | DRY — step(), ok(), fail() مكتوبين مرة واحدة | copy-paste |

## 📧 Email Provider Decisions

| الموقع | الـ Provider المختار | السبب |
|--------|---------------------|-------|
| Gmail needed | emailnator | aliases (dot/plus) — مستقر |
| Cloudflare + Gmail | tempnet | Gmail + bypass |
| Custom domain needed | mailtm | domains متغيرة |
| Mix strategy | rotation بين كل الـ providers | تنويع لتجنب بان |

## 🔑 Security Decisions

- API keys دايماً في `.env` — مش في الكود أبداً
- accounts_*.json مش على git (في .gitignore)
- مفيش `input()` في production — بيبلوك السكريبت

## 📁 Project Structure Decisions

```
.agents/
  workflows/     → slash commands للـ AI
  memory/        → سياق دائم عن المستخدم
  سيستم/         → system prompts

TikTok_SMS/[Subproject]/Root/ (AI Project Operating System - APMS)
  ├── 00_CONSTITUTION.md  ← القواعد والضوابط الدستورية الصارمة للـ AI
  ├── 01_DESIGN_SYSTEM.md ← خريطة سلكتورات الـ DOM وهيكل الـ Layout
  ├── 02_ARCHITECTURE.md  ← معمارية السكريبت والـ Environment Variables
  ├── 03_PROJECT_PLAN.md  ← الخطة التفصيلية مقسمة لـ Phases (P1-P5)
  ├── 04_WORK_PROGRESS.md ← سجل التحديثات اليومي والـ Changelog
  ├── 05_ISSUES_RESOLVED.md ← سجل المشكلات التفصيلي (Symptom-Cause-Fix)
  ├── 06_HANDOFF.md       ← كوبري تسليم الجلسات والـ Handoff Rules
  └── ai_state.json       ← ملف التحكم التفاعلي بالـ AI State لحظة بلحظة
```

---
*[AI: ضيف هنا أي قرار تقني جديد اتخد في المشروع]*
