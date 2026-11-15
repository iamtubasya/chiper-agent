#!/usr/bin/env python3
"""Reusable CDP (Chrome DevTools Protocol) driver for bug-bounty account bootstrap.

Proven in the Neon/neon_bbp audit. Encapsulates the durable pitfalls:
  - launch Chrome in background (foreground launch + short timeout KILLS Chrome)
  - Chrome >=117 uses PUT /json/new (GET -> 405)
  - CSS selectors passed as JSON strings in JS (Python %s/f-string escaping breaks them)
  - React-controlled inputs set via the HTMLInputElement value setter + input/change events
  - Cloudflare challenges auto-resolve: poll location.href until it flips to the app
  - real mouse clicks (Input.dispatchMouseEvent) for forms that reject synthetic clicks
  - ONE shared incrementing CDP id counter (two counters make responses collide)
  - SSO logout = realm logout URL + Network.clearBrowserCookies (SSO cookie outlives app logout)

Requires: pip install websocket-client
Usage:
  python cdp_driver.py launch            # start background CDP Chrome on :9222
  python cdp_driver.py goto <url>        # navigate + auto-wait CF challenge
  python cdp_driver.py fill <selector> <value>
  python cdp_driver.py click <selector>  # real mouse click
  python cdp_driver.py eval "<js expr>"  # returnByValue evaluate
  python cdp_driver.py cookies <path>    # write Netscape cookie jar
  python cdp_driver.py logout            # SSO realm logout + clear cookies
"""
import json, os, sys, time, urllib.request, urllib.parse

BASE = "http://localhost:9222"
WS_TIMEOUT = 30

def http_get(path, method="GET"):
    req = urllib.request.Request(BASE + path, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode())

def pick_page():
    tabs = http_get("/json/list")
    pages = [t for t in tabs if t.get("type") == "page"]
    if not pages:
        path = "/json/new?" + urllib.parse.quote("about:blank", safe="")
        pages = [http_get(path, method="PUT")]
    return pages[0]

def connect():
    import websocket
    tab = pick_page()
    ws = websocket.create_connection(tab["webSocketDebuggerUrl"], timeout=WS_TIMEOUT)
    state = {"id": 0}

    def send(method, **params):
        state["id"] += 1
        mid = state["id"]
        ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        end = time.time() + WS_TIMEOUT
        while time.time() < end:
            try:
                ws.settimeout(max(0.1, end - time.time()))
                m = json.loads(ws.recv())
            except Exception:
                continue
            if m.get("id") == mid:
                return m
        return None

    def ev(expr):
        r = send("Runtime.evaluate", expression=expr, returnByValue=True)
        if not r:
            return "TIMEOUT"
        res = r.get("result", {})
        inner = res.get("result", {})
        if "value" in inner:
            return inner["value"]
        exc = res.get("exceptionDetails")
        return "EXC:" + (json.dumps(exc.get("exception", {}))[:300] if exc else json.dumps(res)[:200])

    return ws, send, ev, pick_page()

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "launch":
        import subprocess
        chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome):
            chrome = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        user_dir = os.path.join(os.environ.get("TEMP", "."), "chrome_cdp_audit")
        p = subprocess.Popen([chrome, "--remote-debugging-port=9222",
                              "--remote-allow-origins=*", "--user-data-dir=" + user_dir,
                              "--no-first-run", "--no-default-browser-check", "about:blank"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(5)
        try:
            print(http_get("/json/version").get("Browser"))
        except Exception as e:
            print("CDP not ready:", e)
        print("pid", p.pid)
        return

    if cmd == "goto":
        url = sys.argv[2]
        ws, send, ev, _ = connect()
        send("Page.navigate", url=url)
        # auto-wait for Cloudflare challenge to resolve
        for _ in range(12):
            time.sleep(4)
            href = ev("location.href")
            if isinstance(href, str) and "Just a moment" not in href and "challenge" not in href.lower():
                break
        print(href)
        ws.close()
        return

    if cmd == "fill":
        sel, val = sys.argv[2], sys.argv[3]
        ws, send, ev, _ = connect()
        js = ("(function(){var el=document.querySelector(%s);"
              "if(!el)return 'NO_EL';"
              "var proto=el.tagName==='INPUT'?window.HTMLInputElement.prototype:window.HTMLTextAreaElement.prototype;"
              "var s=Object.getOwnPropertyDescriptor(proto,'value').set;s.call(el,%s);"
              "el.dispatchEvent(new Event('input',{bubbles:true}));"
              "el.dispatchEvent(new Event('change',{bubbles:true}));return 'OK:'+el.value.length;})()") \
            % (json.dumps(sel), json.dumps(val))
        print(ev(js))
        ws.close()
        return

    if cmd == "click":
        sel = sys.argv[2]
        ws, send, ev, _ = connect()
        # locate leaf text, climb to <button>, real mouse click
        loc = ev("""(function(){
          var all=document.querySelectorAll(%s);
          var t=Array.from(all).filter(function(b){return b.textContent.trim();}).pop()||all[all.length-1];
          if(!t)return 'NO_EL';
          var b=t; while(b&&b.tagName!=='BUTTON')b=b.parentElement;
          var el=b||t; var r=el.getBoundingClientRect();
          return JSON.stringify({x:r.x+r.width/2,y:r.y+r.height/2,dis:el.disabled,txt:el.textContent.trim().slice(0,30)});
        })()""" % json.dumps(sel))
        d = json.loads(loc) if loc.startswith("{") else {}
        print("locate:", loc)
        if "x" in d:
            send("Input.dispatchMouseEvent", type="mousePressed", x=d["x"], y=d["y"], button="left", clickCount=1)
            time.sleep(0.15)
            send("Input.dispatchMouseEvent", type="mouseReleased", x=d["x"], y=d["y"], button="left", clickCount=1)
            print("clicked")
        ws.close()
        return

    if cmd == "eval":
        ws, send, ev, _ = connect()
        print(ev(sys.argv[2]))
        ws.close()
        return

    if cmd == "cookies":
        path = sys.argv[2]
        ws, send, ev, _ = connect()
        send("Network.enable")
        time.sleep(1)
        cookies = []
        r = send("Storage.getCookies")
        end = time.time() + 10
        while time.time() < end:
            try:
                ws.settimeout(1)
                m = json.loads(ws.recv())
            except Exception:
                continue
            if m.get("id") and r and m.get("id") == r.get("id"):
                cookies = m.get("result", {}).get("cookies", [])
                break
        lines = ["# Netscape HTTP Cookie File"]
        for c in cookies:
            domflag = "TRUE" if c.get("domain", "").startswith(".") else "FALSE"
            sec = "TRUE" if c.get("secure") else "FALSE"
            exp = str(int(c.get("expires", 0))) if c.get("expires") else "0"
            lines.append("\t".join([c.get("domain",""), domflag, c.get("path","/"), sec, exp,
                                    c.get("name",""), c.get("value","")]))
        open(path, "w").write("\n".join(lines))
        print("wrote", len(cookies), "cookies ->", path)
        ws.close()
        return

    if cmd == "logout":
        ws, send, ev, _ = connect()
        send("Network.enable")
        time.sleep(1)
        send("Network.clearBrowserCookies")
        # find the keycloak realm logout from the current page (if any)
        send("Page.navigate", url="https://console.neon.tech/realms/prod-realm/protocol/openid-connect/logout?redirect_uri=https://console.neon.tech/login")
        time.sleep(8)
        print("logged out:", ev("location.href"))
        ws.close()
        return

    print(__doc__)

if __name__ == "__main__":
    main()
