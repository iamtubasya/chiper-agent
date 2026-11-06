"""Working requests-based session helper for Formdesk (login + 2FA + data() API).

Usage:
    from fd_session import FD
    f = FD()
    a = f.login()                       # full login incl. email 2FA (reads code from mail.tm)
    r = f.data('settings', 920499, 'get')   # GET data API
    r = f.data('settings', 920499, 'save', method='POST', body={'__rvtoken': f.rvt, ...})

Notes:
- mail.tm credentials are hardcoded (fdauditx9k2m7p4@fldubai.com) — swap EMAIL/PW to your own
  disposable-inbox account if this account no longer exists.
- Page navigation (f.s.get of !... routes) LOSES the session because sidn rotates; only the
  data/<obj>/<id>/?task= API driven through f.data() is reliable.
"""
import requests, re, json, pickle, os, time, html as H, random

EMAIL = "fdauditx9k2m7p4@fldubai.com"
PW = "Str0ngPw123!"
MAILTM = "https://api.mail.tm"
CK = os.path.expanduser("~/cookies.pkl")   # adjust to your workdir
ST = os.path.expanduser("~/state.json")

class FD:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"})
        self.tenant = "sectestco1"
        self.sidn = None
        self.rvt = None
        self.host = "https://www.formdesk.com"

    def appinfo(self, text):
        m = re.search(r'application-info"\s+content="([^"]+)"', text)
        return json.loads(H.unescape(m.group(1))) if m else {}

    def extract_auth(self, text, url=""):
        j = self.appinfo(text)
        a = j.get("auth", {})
        self.sidn = a.get("sidn") or (re.search(r'sidn=([a-f0-9]{32})', url) or [None]*2)[0]
        m = re.search(r'__rvtoken[^>]*value="([^"]+)"', text)
        self.rvt = a.get("rvtoken") or (m.group(1) if m else None)
        d = j.get("domain")
        if d: self.tenant = d
        return a

    def load_state(self):
        if os.path.exists(ST):
            st = json.load(open(ST)); self.tenant = st.get("tenant", self.tenant); self.sidn = st.get("sidn"); self.rvt = st.get("rvt")
        if os.path.exists(CK):
            try:
                with open(CK,"rb") as f: self.s.cookies = pickle.load(f)
            except Exception: pass

    def save_state(self):
        with open(CK,"wb") as f: pickle.dump(self.s.cookies, f)
        json.dump({"tenant": self.tenant, "sidn": self.sidn, "rvt": self.rvt}, open(ST,"w"))

    def mt_token(self):
        return requests.post(MAILTM+"/token", json={"address": EMAIL, "password": PW}, timeout=20).json().get("token","")

    def mt_code(self, clear=True):
        h = {"Authorization": "Bearer " + self.mt_token()}
        if clear:
            try:
                for m in requests.get(MAILTM+"/messages", headers=h, timeout=20).json().get("hydra:member", []):
                    requests.delete(MAILTM+"/messages/"+m["id"], headers=h, timeout=20)
            except Exception: pass
        for _ in range(20):
            try:
                for m in requests.get(MAILTM+"/messages", headers=h, timeout=20).json().get("hydra:member", []):
                    full = requests.get(MAILTM+"/messages/"+m["id"], headers=h, timeout=20).json()
                    blob = " ".join([str(full.get("intro","")), str(full.get("text","")), str(full.get("subject",""))])
                    for c in re.findall(r"\b\d{6}\b", blob): return c
            except Exception: pass
            time.sleep(3)
        return None

    def login(self):
        r = self.s.get(self.host+"/login", allow_redirects=True, timeout=30)
        self.extract_auth(r.text, r.url)
        r2 = self.s.post(f"{self.host}/!login/try/?lang=en&sidn={self.sidn}",
                         data={"txtUsername": EMAIL, "txtPassword": PW, "ts": int(time.time()*1000), "__rvtoken": self.rvt},
                         allow_redirects=True, timeout=30)
        self.extract_auth(r2.text, r2.url)
        r3 = r2
        if "twofactor" in r2.text or "twofactor" in r2.url:
            self.s.get(f"{self.host}/{self.tenant}/data/twofactor/0/?task=check&single=false&silent=false&lang=2&type=backend&value=email&random=tst123&sidn={self.sidn}", timeout=30)
            code = self.mt_code(clear=False)
            r3 = self.s.post(f"{self.host}/{self.tenant}/!login/twofactor/?lang=en&sidn={self.sidn}",
                             data={"code": code, "__rvtoken": self.rvt}, allow_redirects=True, timeout=30)
            self.extract_auth(r3.text, r3.url)
        self.save_state()
        return self.appinfo(r3.text).get("auth",{})

    def data(self, obj, idv=0, task="get", params=None, method="GET", body=None):
        url = (f"{self.host}/{self.tenant}/data/{obj}/{idv}/?task={task}&single=false&silent=false&lang=2"
               f"&random={''.join(random.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(6))}&sidn={self.sidn}")
        if params:
            url += "&" + "&".join(f"{k}={v}" for k,v in params.items())
        if method == "GET":
            return self.s.get(url, timeout=30)
        return self.s.post(url, data=body, timeout=30)

if __name__ == "__main__":
    f = FD()
    a = f.login()
    print("auth type:", a.get("type"), "id:", (a.get("id") or "")[:20])