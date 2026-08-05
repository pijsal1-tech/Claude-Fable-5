# -*- coding: utf-8 -*-
"""
اختبارات TSK-737a — core/network_guard.py (القرار 9 من تسلسل D-19).

**صفر شبكة/ربط فعلي** (القرار الواعي 7): الوحدة نقية — الاختبارات
بارامترية على قيم نصية فقط.

العقد المُختبَر (القرار الواعي 6 — fail-closed):
- loopback حصري: 127.0.0.0/8 كاملة + ::1 + localhost حرفيًا.
- كل ما عداه مكشوف — بما فيه 0.0.0.0/::/LAN/hostnames/قمامة/غير-نص.
"""
from __future__ import annotations

import pytest

from core.network_guard import (EXPOSE_FLAG, exposure_refusal_message,
                                is_loopback_host)


class TestLoopbackAccepted:
    """القيم الآمنة الوحيدة — تربط على جهاز المالك حصرًا."""

    @pytest.mark.parametrize("host", [
        "127.0.0.1",            # الافتراضي (server.py --host)
        "127.0.0.2",            # النطاق 127/8 كاملًا loopback
        "127.1.2.3",
        "127.255.255.254",
        "::1",                  # IPv6 loopback
        "[::1]",                # صيغة الأقواس تُطبَّع
        "localhost",            # الاسم الحرفي
        "LOCALHOST",            # case-insensitive
        "LocalHost",
        "  127.0.0.1  ",        # فراغات حواف تُشذَّب
        "::ffff:127.0.0.1",     # IPv4-mapped loopback — فعليًا محلي
    ])
    def test_loopback_values(self, host):
        assert is_loopback_host(host) is True


class TestExposedRejected:
    """fail-closed: ما لم يثبت loopback فهو مكشوف."""

    @pytest.mark.parametrize("host", [
        "0.0.0.0",              # كل الواجهات — الخطر الأول
        "::",                   # كل الواجهات IPv6
        "[::]",
        "192.168.1.10",         # LAN
        "10.0.0.5",
        "172.16.0.1",
        "8.8.8.8",              # عام
        "128.0.0.1",            # خارج 127/8 بفارق بت واحد
        "126.255.255.255",
        "example.com",          # hostname — لا استعلام DNS (fail-closed)
        "myhost.local",
        "localhost.evil.com",   # ليس localhost الحرفية
        "127.0.0.1.evil.com",
        "",                     # فارغ
        "   ",
        "not-an-ip",            # قمامة
        "127.0.0",              # IPv4 ناقص
        "127.0.0.256",          # ثماني خارج النطاق
    ])
    def test_exposed_values(self, host):
        assert is_loopback_host(host) is False

    @pytest.mark.parametrize("host", [None, 0, 127, [], {}, b"127.0.0.1"])
    def test_non_string_is_exposed(self, host):
        """غير-نص ⇒ مكشوف (fail-closed — لا رفع أبدًا)."""
        assert is_loopback_host(host) is False


class TestRefusalMessage:
    """رسالة الرفض الموحّدة — تشرح الخطر والمسار السليم والراية."""

    def test_mentions_host_and_flag(self):
        msg = exposure_refusal_message("0.0.0.0")
        assert "0.0.0.0" in msg
        assert EXPOSE_FLAG in msg

    def test_mentions_safe_remote_paths(self):
        """المسار الموصى (نفق SSH) والافتراضي الآمن مذكوران."""
        msg = exposure_refusal_message("192.168.1.5")
        assert "SSH" in msg
        assert "127.0.0.1" in msg

    def test_mentions_hardened_paths_under_flag(self):
        """حتى تحت الراية — المسارات المقسّاة مُعلَنة سلفًا."""
        msg = exposure_refusal_message("0.0.0.0")
        assert "/api/permissions" in msg
        assert "ACP" in msg
        assert "force_command_approval" in msg

    def test_flag_name_declares_danger(self):
        """اسم الراية يصرّح بالخطر (القرار الواعي 2)."""
        assert "unsafe" in EXPOSE_FLAG
