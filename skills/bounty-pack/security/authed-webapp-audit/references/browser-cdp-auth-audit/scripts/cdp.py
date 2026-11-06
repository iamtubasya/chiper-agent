#!/usr/bin/env python3
"""Minimal CDP driver for authenticated-webapp audits (real Chrome on a debug port).

Why: long SPA flows (signup -> OTP -> password -> onboarding, or login -> feature) cost
dozens of tool round-trips when every step is a separate call. This drives the flow from
bash/python in one pass and is re-runnable after rate-limit locks or session resets.

Prereq: Chrome started with
  chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* \
    --user-data-dir="C:/temp/<app>-chrome-profile" --no-first-run --no-default-browser-check <url>
  (`--remote-allow-origins=*` is REQUIRED for external websocket clients.)

Usage (from bash):
  python cdp.py targets               # list tabs (id | title | url) -> pick one for CDP_TARGET_ID
  CDP_TARGET_ID=<id> python cdp.py text
  python cdp.py eval '<js expr>'      # evaluate + print JSON
  python cdp.py text [n]              # visible body text
  python cdp.py form                  # inputs / buttons / links / errors of current page
  python cdp.py click '<css>' [real]  # JS click, or real mouse click with 'real' (auto scrolls)
  python cdp.py clicktext 'Continue'  # click first <button> whose text contains the string
  python cdp.py type '<css>' 'value'  # focus + Input.insertText (React-friendly)
  python cdp.py setval '<css>' 'valu' # native-setter fallback (use when type() no-ops)
  python cdp.py keyseq 'ID'           # REAL per-char key events (react-select filtering)
  python cdp.py key Enter
  python cdp.py goto '<url>'
  python cdp.py shot out.png
  python cdp.py cookies               # includes HttpOnly
  python cdp.py hook | cap            # install / read the fetch+XHR capture buffer

Env: CDP_PORT (default 9222), CDP_TARGET_ID (default: first page tab)

Reality checks baked in from real sessions:
  * Input.* events only reach the ACTIVE tab -> Cdp() calls Target.activateTarget on attach.
    With two tabs open (target + IdP), an un-activated tab silently swallows insertText.
  * Real-mouse coords are viewport-relative -> click(real=True) scrolls the element into
    view first; otherwise a below-the-fold button "clicks" into empty space.
  * react-select controls need REAL per-char key events -> use keyseq(), not type(); and
    filter by option LABEL (e.g. "ID +62"), not the display name.
  * Some React forms ignore Input.insertText -> setval() (native setter + input/change).
  * window.__cap (fetch/XHR hook) is wiped on reload -> read captured bodies before navigating.
"""
import json
import os
import sys
import time
import base64
import urllib.request

import websocket  # websocket-client

PORT = 9222


def _http(port, path):
    with urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=10) as r:
        return json.load(r)


def list_targets(port=PORT):
    return [t for t in _http(port, "/json/list")
            if t.get("type") == "page" and "webSocketDebuggerUrl" in t]


def page_target(port=PORT, target_id=None):
    pages = list_targets(port)
    if target_id:
        for t in pages:
            if t["id"] == target_id:
                return t
        raise RuntimeError(f"target {target_id} not found — run `cdp.py targets`")
    if pages:
        return pages[0]
    raise RuntimeError("no page target — is Chrome running with --remote-debugging-port?")


class Cdp:
    def __init__(self, port=PORT, target_id=None, activate=True):
        global PORT
        PORT = port
        t = page_target(port, target_id or os.environ.get("CDP_TARGET_ID"))
        self.target_id = t["id"]
        self.ws = websocket.create_connection(t["webSocketDebuggerUrl"], timeout=30,
                                             suppress_origin=True)
        self.i = 0
        # Input.* events are delivered to the ACTIVE tab only. Without this, typing into a
        # background tab returns {} and the field silently stays empty.
        if activate:
            try:
                self.send("Target.activateTarget", {"targetId": self.target_id})
            except Exception:
                pass

    def send(self, method, params=None, timeout=30):
        self.i += 1
        mid = self.i
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(method)

    def ev(self, expr, await_promise=False):
        r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True,
                                           "awaitPromise": await_promise})
        if r.get("exceptionDetails"):
            return {"__error__": r["exceptionDetails"].get("exception", {}).get("description", "js error")}
        return r.get("result", {}).get("value")

    def js(self, body):
        """Run a statement body wrapped in an IIFE: c.js("return 1+1")"""
        return self.ev(f"(() => {{ {body} }})()")

    # ---- interaction -------------------------------------------------------
    def click(self, selector, real=False):
        if not real:
            return self.ev(f"(() => {{ const e=document.querySelector({json.dumps(selector)});"
                           f" if(!e) return 'NOT_FOUND'; e.click(); return 'clicked'; }})()")
        # viewport-relative coords -> scroll into view first, then re-measure
        box = self.ev(f"(() => {{ const e=document.querySelector({json.dumps(selector)});"
                      f" if(!e) return null; e.scrollIntoView({{block:'center'}});"
                      f" const r=e.getBoundingClientRect();"
                      f" return {{x:Math.round(r.x+r.width/2), y:Math.round(r.y+r.height/2)}}; }})()")
        if not box or not isinstance(box, dict):
            return "NOT_FOUND"
        for t in ("mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", {"type": t, "x": box["x"], "y": box["y"],
                                                   "button": "left", "clickCount": 1})
        return "clicked-real"

    def click_text(self, text, tag="button"):
        return self.ev(
            f"(() => {{ const els=[...document.querySelectorAll({json.dumps(tag)})];"
            f" const e=els.find(x=>x.innerText.trim().toLowerCase()"
            f".includes({json.dumps(text.lower())}));"
            f" if(!e) return 'NOT_FOUND'; e.click(); return 'clicked:'+e.innerText.trim().slice(0,30); }})()")

    def type(self, selector, value, clear=True):
        """Plain inputs only. For react-select / comboboxes use keyseq()."""
        r = self.ev(f"(() => {{ const e=document.querySelector({json.dumps(selector)});"
                    f" if(!e) return 'NOT_FOUND'; e.focus();"
                    f" {'e.select();' if clear else ''} return 'focused'; }})()")
        if r != "focused":
            return r
        self.send("Input.insertText", {"text": value})
        return self.ev(f"(() => {{ const e=document.querySelector({json.dumps(selector)}); return e.value; }})()")

    def setval(self, selector, value):
        """Native-setter fallback: some React forms ignore Input.insertText."""
        return self.ev(
            f"(() => {{ const e=document.querySelector({json.dumps(selector)}); if(!e) return 'NOT_FOUND';"
            f" const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            f" s.call(e,{json.dumps(value)});"
            f" e.dispatchEvent(new Event('input',{{bubbles:true}}));"
            f" e.dispatchEvent(new Event('change',{{bubbles:true}}));"
            f" return e.value; }})()")

    def keyseq(self, text, delay=0.15):
        """REAL per-character key events. Required for react-select filtering."""
        for ch in text:
            vk = ord(ch.upper())
            p = {"type": "keyDown", "key": ch, "code": "Key" + ch, "text": ch,
                 "unmodifiedText": ch, "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
            self.send("Input.dispatchKeyEvent", p)
            self.send("Input.dispatchKeyEvent", {**p, "type": "keyUp"})
            time.sleep(delay)

    def key(self, key, code=None):
        vk = 13 if key == "Enter" else 0
        p = {"type": "keyDown", "key": key, "code": code or key,
             "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
        self.send("Input.dispatchKeyEvent", p)
        self.send("Input.dispatchKeyEvent", {**p, "type": "keyUp"})

    # ---- page state --------------------------------------------------------
    def goto(self, url, wait=2.5):
        self.send("Page.navigate", {"url": url})
        time.sleep(wait)
        return self.ev("location.href")

    def text(self, n=1500):
        return self.ev(f"document.body.innerText.slice(0,{n})")

    def form(self):
        return self.ev("""JSON.stringify({
          url: location.href, title: document.title,
          inputs: [...document.querySelectorAll('input,select,textarea')].map(i=>({n:i.name,t:i.type,v:(i.value||'').slice(0,60),ph:i.placeholder})),
          buttons: [...document.querySelectorAll('button')].map(b=>({t:b.innerText.trim().slice(0,40),d:b.disabled})).filter(b=>b.t),
          links: [...document.querySelectorAll('a')].map(a=>a.innerText.trim().slice(0,30)).filter(Boolean).slice(0,10),
          errors: [...document.querySelectorAll('[class*=error],[class*=Error],[role=alert]')].map(e=>e.innerText.trim()).filter(Boolean).slice(0,5)
        })""")

    def captcha_state(self):
        """Turnstile/CAPTCHA triage: undefined turnstile + disabled button => switch browser backend."""
        return self.ev("""JSON.stringify({
          turnstile: typeof window.turnstile,
          token_len: ((document.querySelector('input[name=cf-turnstile-response]')||{}).value||'').length,
          iframes: [...document.querySelectorAll('iframe')].map(f=>(f.src||'').slice(0,60)),
          disabled_buttons: [...document.querySelectorAll('button')].filter(b=>b.disabled).map(b=>b.innerText.trim().slice(0,30))
        })""")

    def cookies(self):
        return self.send("Network.getAllCookies").get("cookies", [])

    def shot(self, path):
        r = self.send("Page.captureScreenshot", {"format": "png"})
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        return path


# ---- fetch/XHR capture hook (install BEFORE the request; wiped on reload) ----
CAPTURE_HOOK = r"""
(() => { if (window.__capInstalled) return 'already';
  window.__cap = [];
  const of = window.fetch;
  window.fetch = async (...a) => { const r = await of.apply(this, a);
    try { const u = (typeof a[0]==='string') ? a[0] : (a[0]&&a[0].url)||'';
          const t = await r.clone().text();
          window.__cap.push({t:'fetch', u, s:r.status, body:t.slice(0,6000)}); } catch(e){}
    return r; };
  const oo = XMLHttpRequest.prototype.open, os = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(m,u,...r){ this.__u = u; return oo.call(this,m,u,...r); };
  XMLHttpRequest.prototype.send = function(...a){
    this.addEventListener('load', ()=>{ try { window.__cap.push({t:'xhr', u:this.__u, s:this.status,
      body:(this.responseText||'').slice(0,6000)}); } catch(e){} });
    return os.apply(this, a); };
  window.__capInstalled = true; return 'installed'; })()
"""


def install_capture(c: Cdp):
    return c.ev(CAPTURE_HOOK)


def read_capture(c: Cdp, pattern=r"mfa|totp|authenticat|sso|saml|secret"):
    import re
    raw = c.ev("JSON.stringify(window.__cap || [])") or "[]"
    out = []
    for e in json.loads(raw):
        if re.search(pattern, (e.get("u") or "") + (e.get("body") or "")[:400], re.I):
            out.append(e)
    return out


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    a = sys.argv[1]
    if a == "targets":
        for t in list_targets():
            print(f"{t['id']} | {t.get('title','')[:40]} | {t.get('url','')[:80]}")
        return
    c = Cdp()
    if a == "eval":
        print(json.dumps(c.ev(sys.argv[2]), ensure_ascii=False, indent=1))
    elif a == "text":
        print(c.text(int(sys.argv[2]) if len(sys.argv) > 2 else 1500))
    elif a == "form":
        print(c.form())
    elif a == "captcha":
        print(c.captcha_state())
    elif a == "click":
        print(c.click(sys.argv[2], real=(len(sys.argv) > 3 and sys.argv[3] == "real")))
    elif a == "clicktext":
        print(c.click_text(sys.argv[2]))
    elif a == "type":
        print(c.type(sys.argv[2], sys.argv[3]))
    elif a == "setval":
        print(c.setval(sys.argv[2], sys.argv[3]))
    elif a == "keyseq":
        c.keyseq(sys.argv[2]); print("keyseq sent")
    elif a == "key":
        print(c.key(sys.argv[2]))
    elif a == "goto":
        print(c.goto(sys.argv[2]))
    elif a == "shot":
        print(c.shot(sys.argv[2]))
    elif a == "cookies":
        print(json.dumps(c.cookies(), indent=1)[:2000])
    elif a == "hook":
        print(install_capture(c))
    elif a == "cap":
        print(json.dumps(read_capture(c), indent=1)[:3000])
    else:
        print("unknown cmd", a)


if __name__ == "__main__":
    main()
