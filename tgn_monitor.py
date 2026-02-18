import httpx, json
from pathlib import Path
from bs4 import BeautifulSoup as BS

BASE = "https://tgnmob.ir"
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
H = {"User-Agent": UA, "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8"}

def make_client():
    try:
        return httpx.Client(http2=True, headers=H, timeout=45.0, follow_redirects=False)
    except ImportError:
        return httpx.Client(http2=False, headers=H, timeout=45.0, follow_redirects=False)

def _parse_form(html, default_action):
    soup = BS(html, "html.parser")
    form = soup.find("form")
    if not form:
        return default_action, {}
    action = form.get("action") or default_action
    if not action.startswith("http"):
        action = f"{BASE}/{action.strip('/')}"
    inputs = {}
    for i in form.find_all("input"):
        name = i.get("name") or i.get("id")
        if not name:
            continue
        inputs[name] = i.get("value") or ""
    return action, inputs

def save_cookies(client, path="tgn_cookies.json"):
    jar = []
    for c in client.cookies.jar:
        jar.append({"name": c.name, "value": c.value, "domain": c.domain, "path": c.path, "expires": getattr(c, "expires", None)})
    Path(path).write_text(json.dumps(jar, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 cookies → {path}")

def login(phone: str):
    with make_client() as s:
        r1 = s.get(f"{BASE}/Cell.aspx")
        r1.raise_for_status()
        Path("cell_first.html").write_text(r1.text, encoding="utf-8")
        action_cell, inputs_cell = _parse_form(r1.text, f"{BASE}/Cell.aspx")

        data = dict(inputs_cell)
        data["CellphoneNum"] = phone
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
        r2 = s.post(action_cell, data=data, headers=headers)
        if r2.status_code in (301,302,303,307,308):
            loc = r2.headers.get("Location", "")
            if loc and not loc.startswith("http"):
                loc = f"{BASE}/{loc.lstrip('/')}"
            # دنبال کردن ریدایرکت به صفحه OTP
            r2f = s.get(loc, headers={**H, "Referer": action_cell})
            r2f.raise_for_status()
            Path("after_phone.html").write_text(r2f.text, encoding="utf-8")
            otp_page_html = r2f.text
        else:
            r2.raise_for_status()
            Path("after_phone.html").write_text(r2.text, encoding="utf-8")
            otp_page_html = r2.text

        print("📨 شماره ارسال شد؛ کد پیامک را وارد کنید…")
        otp = input("کد پیامک: ").strip()
        action_otp, inputs_otp = _parse_form(otp_page_html, f"{BASE}/Token.aspx")
        data_otp = dict(inputs_otp)
        data_otp["Token"] = otp
        if "cell2" not in data_otp:
            data_otp["cell2"] = phone

        r3 = s.post(action_otp, data=data_otp, headers={
            **H,
            "Origin": BASE,
            "Referer": f"{BASE}/Token.aspx?cell={phone}",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        if r3.status_code in (301,302,303,307,308):
            loc = r3.headers.get("Location", "")
            if loc and not loc.startswith("http"):
                loc = f"{BASE}/{loc.lstrip('/')}"
            r3f = s.get(loc, headers={**H, "Referer": action_otp})
            Path("after_otp.html").write_text(r3f.text, encoding="utf-8")
        else:
            Path("after_otp.html").write_text(r3.text, encoding="utf-8")
            r3.raise_for_status()

        test = s.get(f"{BASE}/PriceNew.aspx", headers=H)
        Path("price_page.html").write_text(test.text, encoding="utf-8")
        if test.status_code == 200 and ("کد پیامک شده را وارد" not in test.text and "شماره موبایل" not in test.text):
            print("✅ لاگین موفق و صفحه قیمت‌ها در دسترس است.")
            save_cookies(s)
        else:
            print("⚠️ هنوز داخل نیستیم؛ خروجی after_otp.html/price_page.html را ببین.")

if __name__ == "__main__":
    phone = input("📱 شماره موبایل: ").strip()
    login(phone)
