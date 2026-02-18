# dump_pages.py
import json, httpx

BASE = "https://tgnmob.ir"
UA = "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"

def load_cookies(client, path="tgn_cookies.json"):
    data = json.load(open(path, "r", encoding="utf-8"))
    for c in data:
        client.cookies.set(name=c["name"], value=c["value"], domain=c.get("domain") or "tgnmob.ir", path=c.get("path") or "/")

def save(url, name):
    with httpx.Client(http2=True, headers={"User-Agent": UA, "Accept-Language":"fa-IR,fa;q=0.9,en-US;q=0.8"}, follow_redirects=True, timeout=45) as s:
        load_cookies(s)
        r = s.get(url)
        r.raise_for_status()
        open(name, "w", encoding="utf-8").write(r.text)
        print("saved:", name, "←", str(r.url))

if __name__ == "__main__":

    save(f"{BASE}/PriceNew.aspx", "page_main.html")
