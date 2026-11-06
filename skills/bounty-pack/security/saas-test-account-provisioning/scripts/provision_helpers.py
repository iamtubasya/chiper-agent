# Safer-text helpers for SaaS account provisioning
# Import these into a session script; they encode the pitfalls found on ably.com (2026-10).

import re, json, time, requests

# ── mail.tm ───────────────────────────────────────────────────────────────────
def mailtm_domain():
    d = requests.get("https://api.mail.tm/domains", timeout=25).json()
    items = d if isinstance(d, list) else d.get("hydra:member", [])
    return items[0]["domain"]

def mailtm_create(dom):
    import secrets, string
    local = "".join(secrets.choice(string.ascii_lowercase) for _ in range(10))
    pw = "".join(secrets.choice(string.ascii_letters + string.digits + "!@#$") for _ in range(14))
    r = requests.post("https://api.mail.tm/accounts", json={"address": f"{local}@{dom}", "password": pw}, timeout=25).json()
    addr = r["address"]                      # <-- returned address (dots stripped)
    tok = requests.post("https://api.mail.tm/token", json={"address": addr, "password": pw}, timeout=25).json()["token"]
    return addr, pw, tok

def mailtm_messages(tok):
    d = requests.get("https://api.mail.tm/messages", headers={"Authorization": f"Bearer {tok}"}, timeout=25).json()
    return d.get("hydra:member", []) if isinstance(d, dict) else d

def _s(v):
    return " ".join(str(x) for x in v) if isinstance(v, list) else str(v or "")

def mailtm_body(tok, mid):
    md = requests.get(f"https://api.mail.tm/messages/{mid}", headers={"Authorization": f"Bearer {tok}"}, timeout=25).json()
    return _s(md.get("text")), _s(md.get("html"))

def extract_code(html, text):
    """Extract a verification code by CONTEXT, never by any-6-digits (CSS colours like #292831 fool you)."""
    for blob in (text, html):
        for m in re.finditer(r"(?:code|verify|pin|otp)[^0-9]{0,40}(\d{4,8})", blob, re.I):
            return m.group(1)
    # fallback: 6-digit not preceded by '#'
    for m in re.finditer(r"(?<!#)\b(\d{6})\b", text or html):
        c = m.group(1)
        if not c.startswith("20"):
            return c
    return None

# ── generic ───────────────────────────────────────────────────────────────────
def fetch_json(page, url, accept="application/json", method="GET", body=None):
    """fetch inside the browser session; retries with text/html on 406."""
    js = """async ({u,a,m,b})=>{try{const o={method:m,credentials:'same-origin',headers:{'Accept':a}};
        if(b){o.headers['Content-Type']='application/json';o.body=JSON.stringify(b);}
        const r=await fetch(u,o); let t='';try{t=await r.text()}catch(e){}
        return {s:r.status,t};}catch(e){return {s:'ERR',t:e.message}}}"""
    r = page.evaluate(js, {"u": url, "a": accept, "m": method, "b": body})
    if r.get("s") == 406 and accept == "application/json":
        r = page.evaluate(js, {"u": url, "a": "text/html", "m": method, "b": body})
    return r

APIKEY_RE = re.compile(r"\b([A-Za-z0-9]{4,8}\.[A-Za-z0-9_\-]{4,10}:[A-Za-z0-9_\-]{10,})\b")
def extract_api_keys(html, app_id=None):
    keys = set(APIKEY_RE.findall(html))
    if app_id:                               # keep only keys for the real app, drop CSS tokens
        keys = {k for k in keys if k.startswith(app_id + ".")}
    # drop obvious CSS class fragments
    return {k for k in keys if "ot-" not in k and "layout" not in k}
