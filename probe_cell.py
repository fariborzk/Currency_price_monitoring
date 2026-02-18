# probe_cell.py
import httpx, json, time
from bs4 import BeautifulSoup as BS
from pathlib import Path

BASE = "https://tgnmob.ir"
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
H = {
    "User-Agent": UA,
    "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

def dump(name, resp):
    Path(f"{name}.html").write_text(resp.text or "", encoding="utf-8", errors="ignore")
    meta = {
        "status": resp.status_code,
        "url": str(resp.url),
        "headers": dict(resp.headers),
        "request_headers": dict(resp.request.headers),
        "cookies": {c.name: c.value for c in resp.cookies.jar},
    }
    Path(f"{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 {name}.html / {name}.json")

def parse_form(html):
    soup = BS(html, "html.parser")
    form = soup.find("form")
    if not form:
        return None, {}
    action = form.get("action") or "/Cell.aspx"
    if not action.startswith("http"):
        action = f"{BASE}/{action.strip('/')}"
    inputs = {}
    for i in form.find_all("input"):
        name = i.get("name") or i.get("id")
        if not name:
            continue
        inputs[name] = i.get("value") or ""
    return action, inputs

def main(phone="09134351050"):
    with httpx.Client(http2=False, headers=H, timeout=45.0, follow_redirects=False) as s:
        r = s.get(f"{BASE}/Cell.aspx")
        dump("step1_get_cell", r)
        if r.is_redirect:
            print("🔁 redirect on GET cell:", r.headers.get("Location"))

        action, inputs = parse_form(r.text)
        if not action:
            print("❌ فرم Cell.aspx پیدا نشد."); return
        inputs["CellphoneNum"] = phone
        headers = {
            **H,
            "Origin": BASE,
            "Referer": f"{BASE}/Cell.aspx",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Sec-CH-UA": '"Chromium";v="124", "Not.A/Brand";v="24"',
            "Sec-CH-UA-Mobile": "?1",
            "Sec-CH-UA-Platform": '"Android"',
            "Upgrade-Insecure-Requests": "1",
        }
        r2 = s.post(action, data=inputs, headers=headers)
        dump("step2_post_phone", r2)
        print("POST phone status:", r2.status_code, "| redirect?", r2.is_redirect, "| to:", r2.headers.get("Location"))
        if r2.is_redirect:
            loc = r2.headers.get("Location")
            if loc and not loc.startswith("http"):
                loc = f"{BASE}/{loc.lstrip('/')}"
            r3 = s.get(loc, headers={**H, "Referer": action})
            dump("step2_follow", r3)
        r4 = s.get(f"{BASE}/Token.aspx", params={"cell": phone}, headers=H)
        dump("step3_token_page", r4)

        print("✅ پروب تمام شد. فایل‌های step*.html/json را بفرست تا بررسی کنم.")

if __name__ == "__main__":
    main()

