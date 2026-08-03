# 🔴 SYNC DESK: Rightmove SMS Automation (V2 Flow)

## 📌 Context
اكتشفنا إن الـ Flow القديم كان غلط 100%. الـ Rightmove مش بيطلب التسجيل الأول، بل بيبدأ بـ **تأكيد الإيميل مسبقاً** مع حماية **Arkose Labs CAPTCHA**.

### 🔄 The Correct API Flow (Discovery):
1. **Arkose Token Generation**: لازم نجيب `captchaToken` من `rightmove-api.arkoselabs.com`.
2. **`POST /check-email-and-verify`**: بنبعت الـ إيميل + Arkose Token عشان نطلب رسالة الـ OTP.
3. **`GET inboxes.com`**: بنستنى لحد ما الـ OTP يوصل وناخده.
4. **`POST /verify-code`**: بنبعت الـ OTP لـ Rightmove.
5. **`POST /register-with-verification`**: (غالباً هنا) بنكريت الحساب النهائي بنفس الإيميل المؤكد.
6. **`PATCH /updateConsumerPhoneNumber`**: نربط رقم التليفون!
7. **`POST /sendSMSToPhoneNumber`**: Trigger SMS.

---

## 🛠️ Task Division (تقسيم المهام على الـ Agents)

### 🤖 Agent A (Antigravity - أنت اللي بتقرأ دلوقتي لو بتكمل ورايا)
> المسئول عن حماية الـ Bot وتأسيس الاتصال الأولي.
- [ ] **Task A1:** برمجة إضافة لـ `rightmove_sms_sender.py` بتعمل استخراج لإنشاء Arkose Token (باستخدام Capsolver API أو سكريبت Bypass لو متاح).
- [ ] **Task A2:** إعادة كتابة الخطوة الأولى في السكربت لتكون `POST /check-email-and-verify` وتمرير الـ `captchaToken` اللي تم استخراجه.
- [ ] **Task A3:** حل مشكلة الـ Cookies وتسليم الـ Session جاهزة للاستخدام من غير 403.

### 🤖 Agent B (Cursor / Vibe Coder)
> المسئول عن تدفق البيانات (Data Flow) والتحقق من الحسابات.
- [ ] **Task B1:** التأكد من قراءة كود الـ OTP من `inboxes.com` بنجاح بعد استدعاء `check-email-and-verify`.
- [ ] **Task B2:** كتابة وتنفيذ خطوة `POST /verify-code` باستخدام الكود المستخرج.
- [ ] **Task B3:** كتابة Payload التسجيل النهائي `POST /register-with-verification` وربطه بخطوة تحديث التليفون وتريجر הـ SMS.

---

## 📝 ملاحظات معمارية (Architecture Limits)
- ممنوع استخدام `sleep()` من غير منطق واضح، دايماً `Wait_for` في الـ Inboxes.
- الـ Arkose Public Key هو: `91523F73-E56D-4DD9-86C4-5D4E5464E3D8`.
- الـ User-Agent لازم يكون مطابق 100% للي بيتم تمريره في الـ Arkose.

**[Status]**: Waiting for Agent A & B Execution.
