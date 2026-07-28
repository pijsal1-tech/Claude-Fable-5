# -*- coding: utf-8 -*-
"""QA-T05 — بوابة M1: المحلل mode-aware (TSK-101 BUG-01 + TSK-102 NF-13).

ردود AI مزيّفة بالكامل (صفر استدعاءات خارجية — حدود QA_MASTER_PLAN):
- شرح كود عادي في chat يجب ألا يُنتج أي ملفات/أوامر.
- بلوك bash يحوي rm -rf في chat يجب ألا يتحول لأوامر أبدًا.
- fallback بلوكات bash يتطلب وسم CMD: صريحًا لكل سطر (كل الأوضاع).
"""
from actions.response_parser import ResponseParser


FAKE_CHAT_EXPLAIN_CODE = """دي طريقة كتابة دالة جمع في بايثون:

```python
def add(a, b):
    return a + b

print(add(2, 3))
```

الدالة بتاخد رقمين وترجّع مجموعهما.
"""

FAKE_CHAT_RM_RF = """لتنظيف مجلدات البناء تقدر تستخدم:

```bash
rm -rf build/
rm -rf dist/
```

بس خلي بالك دي أوامر خطيرة.
"""

FAKE_CHAT_MIXED = """شرح مع مثالين:

```python
x = 1
y = x * 2
```

وأمر فحص:

```bash
ls -la
```
"""


class TestChatModeNoActions:
    """BUG-01: وضع chat لا يُنتج إجراءات من fallback إطلاقًا."""

    def setup_method(self):
        self.parser = ResponseParser()

    def test_explain_code_no_files(self):
        parsed = self.parser.parse(FAKE_CHAT_EXPLAIN_CODE, mode="chat")
        assert parsed.files == []
        assert parsed.edits == []
        assert parsed.commands == []

    def test_rm_rf_never_becomes_command(self):
        parsed = self.parser.parse(FAKE_CHAT_RM_RF, mode="chat")
        assert parsed.commands == []
        assert parsed.files == []

    def test_mixed_reply_no_actions(self):
        parsed = self.parser.parse(FAKE_CHAT_MIXED, mode="chat")
        assert parsed.files == []
        assert parsed.commands == []

    def test_explicit_file_tag_still_works_in_chat(self):
        """الوسوم الصريحة (FILE:) تعمل حتى في chat — فقط fallback معطّل."""
        reply = "```FILE: hello.py\nprint('hi')\n```"
        parsed = self.parser.parse(reply, mode="chat")
        assert len(parsed.files) == 1
        assert parsed.files[0].path == "hello.py"


class TestOtherModesUnchanged:
    """السلوك التاريخي محفوظ خارج chat."""

    def setup_method(self):
        self.parser = ResponseParser()

    def test_build_mode_fallback_still_suggests_files(self):
        parsed = self.parser.parse(FAKE_CHAT_EXPLAIN_CODE, mode="build")
        assert len(parsed.files) == 1

    def test_mode_none_keeps_historical_behavior(self):
        parsed = self.parser.parse(FAKE_CHAT_EXPLAIN_CODE)
        assert len(parsed.files) == 1

    def test_explicit_file_tag_all_modes(self):
        reply = "```FILE: a.py\nprint(1)\n```"
        for mode in ("chat", "plan", "build", "edit", None):
            parsed = self.parser.parse(reply, mode=mode)
            assert len(parsed.files) == 1, f"mode={mode}"


class TestBashFallbackTamed:
    """NF-13: بلوكات bash في fallback تتطلب وسم CMD: صريحًا لكل سطر."""

    def setup_method(self):
        self.parser = ResponseParser()

    def test_untagged_bash_lines_ignored(self):
        reply = "شرح:\n\n```bash\nrm -rf build/\necho hello\n```\n"
        parsed = self.parser.parse(reply, mode="build")
        assert parsed.commands == []

    def test_dollar_prefixed_lines_ignored(self):
        reply = "مثال:\n\n```bash\n$ npm install\n$ npm run dev\n```\n"
        parsed = self.parser.parse(reply, mode="build")
        assert parsed.commands == []

    def test_cmd_tagged_lines_extracted(self):
        reply = "نفّذ:\n\n```bash\nCMD: echo safe\nrm -rf /\nCMD: ls -la\n```\n"
        parsed = self.parser.parse(reply, mode="build")
        assert [c.command for c in parsed.commands] == ["echo safe", "ls -la"]

    def test_explicit_cmd_block_unchanged(self):
        reply = "نفّذ:\n\n```CMD\npytest -q\n```\n"
        parsed = self.parser.parse(reply, mode="build")
        assert [c.command for c in parsed.commands] == ["pytest -q"]
