"""
سكريبت تحليل ملفات HAR للبحث عن ترويسات المصادقة (Authorization/Cookies).
القيم الحساسة تُعرض مقنّعة (redacted) لمنع تسريب secrets في المخرجات.

الاستخدام:
    python scripts/scan_har_auth.py test_har.txt
    python scripts/scan_har_auth.py test_har.txt --full   (يعرض قيم غير حساسة كاملة، الحساسة تبقى مقنّعة دوماً)
"""

import json
import sys
import argparse
from pathlib import Path

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "x-access-token",
    "proxy-authorization",
}


def redact(value: str, keep: int = 4) -> str:
    """يقنّع القيمة الحساسة ويبقي فقط أول/آخر عدد محدد من المحارف."""
    if value is None:
        return ""
    value = str(value)
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}{'*' * (len(value) - keep * 2)}{value[-keep:]} (len={len(value)})"


def is_sensitive(header_name: str) -> bool:
    return header_name.strip().lower() in SENSITIVE_HEADER_NAMES


def scan_headers(headers: list, url: str, direction: str, results: list) -> None:
    for h in headers or []:
        name = h.get("name", "")
        value = h.get("value", "")
        if is_sensitive(name):
            results.append(
                {
                    "url": url,
                    "direction": direction,
                    "header": name,
                    "value": redact(value),
                }
            )


def scan_har_cookies(cookies: list, url: str, direction: str, results: list) -> None:
    """حقل cookies المنفصل داخل request/response في مواصفات HAR."""
    for c in cookies or []:
        name = c.get("name", "")
        value = c.get("value", "")
        results.append(
            {
                "url": url,
                "direction": f"{direction} (cookie jar)",
                "header": name,
                "value": redact(value),
            }
        )


def analyze_har(file_path: str) -> list:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"الملف غير موجود: {file_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"الملف ليس JSON صالحاً (HAR تالف؟): {e}")

    entries = data.get("log", {}).get("entries", [])
    if not entries:
        raise ValueError("لا توجد entries داخل الملف — تأكد أنه HAR صحيح.")

    results = []
    for entry in entries:
        request = entry.get("request", {})
        response = entry.get("response", {})
        url = request.get("url", "unknown-url")

        scan_headers(request.get("headers", []), url, "request", results)
        scan_headers(response.get("headers", []), url, "response", results)
        scan_har_cookies(request.get("cookies", []), url, "request", results)
        scan_har_cookies(response.get("cookies", []), url, "response", results)

    return results


def print_report(results: list) -> None:
    if not results:
        print("✅ لم يتم العثور على أي ترويسات Authorization/Cookie في الملف.")
        return

    print(f"🔎 تم العثور على {len(results)} ترويسة/كوكي حساسة:\n")
    for i, r in enumerate(results, start=1):
        print(f"[{i}] {r['direction'].upper()}")
        print(f"    URL     : {r['url']}")
        print(f"    Header  : {r['header']}")
        print(f"    Value   : {r['value']}")
        print()

    unique_urls = {r["url"] for r in results}
    unique_headers = {r["header"].lower() for r in results}
    print("—" * 40)
    print(f"عدد الروابط المتأثرة: {len(unique_urls)}")
    print(f"أنواع الترويسات المكتشفة: {', '.join(sorted(unique_headers))}")
    print(
        "⚠️  تذكير: القيم أعلاه مقنّعة عمداً. لا تشارك القيم الكاملة "
        "في أي مكان عام أو مستودع Git."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="فحص ملف HAR عن ترويسات مصادقة")
    parser.add_argument("har_file", help="مسار ملف HAR (json)")
    args = parser.parse_args()

    try:
        results = analyze_har(args.har_file)
        print_report(results)
    except (FileNotFoundError, ValueError) as e:
        print(f"❌ خطأ: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()