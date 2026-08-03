---
description: تفعيل agent معين — يقرأ الملف ويشتغل بالشخصية والأسلوب المحدد
---

# /activate — تفعيل Agent

## الاستخدام
```
/activate [اسم الـ agent]
```

## الخطوات

### 1. حدد الـ Agent المطلوب
الـ agents المتاحة (19 agent):

**🔍 تحليل:**
- `محلل API Flow` — تحليل Requestly requests
- `محلل طلبات` — HAR/Burp → Python
- `خبير Burp` — Burp Suite analysis
- `خبير المحرك` — ai_engine.py (10 providers)

**🛡️ أمان وحماية:**
- `خبير حماية` — anti-bot bypass (هجوم)
- `مهندس أمان` — security audit (دفاع)

**📝 مراجعة:**
- `مراجع أخطاء` — bug finder
- `مراجع توافق` — coherence check
- `محلل جودة` — DRY + SOLID
- `مراجع Vibe` — 5-axis deep review

**📋 تخطيط وتوثيق:**
- `مخطط` — implementation planner
- `كاتب برومبت` — prompt engineer
- `كاتب تقني` — documentation
- `مهندس معماري` — architecture design

**🔧 عمليات:**
- `مدير فريق` — ai_team.py CLI
- `خبير v2` — v2/ Flow Tool
- `منسق المشاريع` — project map
- `مراقب` — monitor.py

**🎭 إدارة:**
- `مدير الأوركسترا` — يوزع على كل الـ agents

### 2. اقرأ ملف الـ Agent
// turbo
```
افتح `.agents/سيستم/أنت [الاسم].md`
```

### 3. تبنّى الشخصية
- اتبع الـ YAML frontmatter (name, emoji, vibe)
- اشتغل بالـ mission والـ workflow المحددين
- التزم بالـ قواعد في الملف

### 4. ابدأ بالـ START message
```
ابدأ ردك بالـ START message الموجود في آخر ملف الـ agent
```

## أمثلة
```
/activate مراجع Vibe
→ يقرأ أنت مراجع Vibe.md
→ يشتغل بأسلوب الـ 5 محاور

/activate مدير الأوركسترا
→ يقرأ أنت مدير الأوركسترا.md
→ يوزع المهمة على agents تانية
```
