# -*- coding: utf-8 -*-
"""QA-T05 (TSK-101 + TSK-102): وضع chat لا يُنتج actions — والـ fallback مهذَّب.

ثلاثة ردود AI مزيفة (منها مثال شرح يحوي ``rm -rf``) — صفر نداءات AI
خارجية (حدود QA_MASTER_PLAN: الحدود stubbed دائمًا).

يغطي:
- TSK-101: parse(response, mode="chat") يعطّل الـ fallback العدواني؛
  أوضاع plan/build/edit وmode=None بلا تغيير سلوكي.
- TSK-102: بلوكات bash داخل الـ fallback لا تتحول لأوامر إلا بوسم CMD: صريح.
- طبقة الخادم: إطار done في chat بلا actions (فحص مسار _dispatch مباشرة
  يتطلب تشغيل provider — يُغطى هنا على مستوى الوحدة بمنطق الإسقاط نفسه).
"""
from actions.response_parser import ResponseParser

parser = ResponseParser()

# ── الردود المزيفة الثلاثة (QA-T05) ──────────────────────

FAKE_CHAT_EXPLAIN_CODE = """شرح مفهوم الدوال في بايثون:

```python
def greet(name):
    return f"Hello {name}"
```

هذا مثال توضيحي فقط."""

FAKE_CHAT_RM_RF = """لتنظيف مخرجات البناء يمكنك نظريًا استخدام:

```bash
rm -rf build/
rm -rf dist/
```

⚠️ لكن انتبه قبل تنفيذ أي أمر حذف."""

FAKE_CHAT_MIXED = """مقارنة بين طريقتين:

```javascript
console.log("approach A");
```

```bash
npm install lodash
$ npm run build
```

اختر ما يناسبك."""


# ── TSK-101: chat = صفر actions من الـ fallback ──────────

class TestChatModeNoActions:
    def test_explain_code_no_file(self):
        r = parser.parse(FAKE_CHAT_EXPLAIN_CODE, mode="chat")
        assert not r.has_actions
        assert r.files == [] and r.edits == [] and r.commands == []

    def test_rm_rf_example_no_commands(self):
        """بند القبول الحرفي: رد chat يحوي rm -rf كمثال → لا CommandBlock."""
        r = parser.parse(FAKE_CHAT_RM_RF, mode="chat")
        assert r.commands == []
        assert not r.has_actions

    def test_mixed_blocks_no_actions(self):
        r = parser.parse(FAKE_CHAT_MIXED, mode="chat")
        assert not r.has_actions

    def test_explicit_blocks_still_extracted_in_chat(self):
        """البلوكات الصريحة FILE:/CMD تُستخرج (إسقاطها من الإطار شأن الخادم)."""
        r = parser.parse("```FILE: x.py\nprint(1)\n```", mode="chat")
        assert [f.path for f in r.files] == ["x.py"]


# ── TSK-101: بقية الأوضاع بلا تغيير سلوكي ────────────────

class TestOtherModesUnchanged:
    def test_build_mode_fallback_still_works(self):
        r = parser.parse(FAKE_CHAT_EXPLAIN_CODE, mode="build")
        assert len(r.files) == 1 and r.files[0].language == "python"

    def test_default_mode_none_fallback_still_works(self):
        """mode=None (مسارات chain/action_applier) = السلوك التاريخي."""
        r = parser.parse(FAKE_CHAT_EXPLAIN_CODE)
        assert len(r.files) == 1

    def test_explicit_file_block_all_modes(self):
        raw = "```FILE: app/main.py\nprint('hi')\n```"
        for m in (None, "chat", "plan", "build", "edit"):
            r = parser.parse(raw, mode=m)
            assert [f.path for f in r.files] == ["app/main.py"], m


# ── TSK-102: fallback bash يتطلب CMD: صريح ───────────────

class TestBashFallbackTamed:
    def test_untagged_bash_lines_ignored(self):
        r = parser.parse(FAKE_CHAT_RM_RF)  # حتى بدون chat mode
        assert r.commands == []

    def test_dollar_prefixed_lines_ignored(self):
        r = parser.parse("```bash\n$ npm run build\n```")
        assert r.commands == []

    def test_cmd_tagged_lines_extracted(self):
        r = parser.parse("```bash\nCMD: echo safe\nrm -rf /tmp/x\nCMD: ls -la\n```")
        assert [c.command for c in r.commands] == ["echo safe", "ls -la"]

    def test_explicit_cmd_block_unchanged(self):
        """المسار الصريح ```CMD يبقى كما هو تاريخيًا."""
        r = parser.parse("```CMD\npytest -q\n```")
        assert [c.command for c in r.commands] == ["pytest -q"]
