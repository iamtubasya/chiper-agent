#!/usr/bin/env python3
"""File-driven browser daemon — keeps one CloakBrowser session alive across many steps.

Drop into the session work dir, edit WORK/PROFILE paths, then:
    python bd.py > bd.log 2>&1 &          # start (terminal background=true)
    python bctl.py '{"cmd":"goto","url":"https://target/login"}'   # drive it

Commands: goto, fill, click, type, key, wait, eval, dump, body, shot, cookies, pages, exit
Results land in res.json. Re-send identical cmd is deduped — change a "_n" field to force re-run.
"""
import json, os, time
from cloakbrowser import launch_persistent_context

WORK = os.environ.get("BD_WORK", os.getcwd())
CMD = os.path.join(WORK, "cmd.json")
RES = os.path.join(WORK, "res.json")
PROFILE = os.path.join(WORK, "profile")
TTL = int(os.environ.get("BD_TTL", "1200"))  # seconds the daemon self-exits after

os.remove(CMD) if os.path.exists(CMD) else None
os.remove(RES) if os.path.exists(RES) else None

ctx = launch_persistent_context(PROFILE, headless=False, humanize=True,
                                viewport={"width": 1366, "height": 900})
print("browser up, pages:", len(ctx.pages), flush=True)

deadline = time.time() + TTL
last = None
while time.time() < deadline:
    try:
        cmd = json.load(open(CMD))
    except Exception:
        time.sleep(0.4); continue
    key = json.dumps(cmd, sort_keys=True)
    if key == last:
        time.sleep(0.4); continue
    last = key
    c = cmd.get("cmd")
    out = {"ok": False}
    try:
        pages = ctx.pages
        if c == "pages":
            out = {"ok": True, "pages": [{"i": i, "url": p.url, "title": p.title()}
                                         for i, p in enumerate(pages)]}
        elif c == "newpage":
            p = ctx.new_page(); out = {"ok": True, "url": p.url}
        else:
            pi = cmd.get("page", 0)
            pg = pages[pi] if pi < len(pages) else pages[-1]
            if c == "goto":
                pg.goto(cmd["url"], wait_until="domcontentloaded", timeout=90000)
                time.sleep(cmd.get("wait", 4))
                out = {"ok": True, "url": pg.url, "title": pg.title()}
            elif c == "fill":
                el = pg.query_selector(cmd["sel"])
                if el:
                    el.click(); el.fill(cmd["val"])
                    out = {"ok": True, "filled": cmd["sel"]}
                else:
                    out = {"ok": False, "err": "no such selector", "sel": cmd["sel"]}
            elif c == "type":
                pg.keyboard.type(cmd["val"], delay=cmd.get("delay", 40)); out = {"ok": True}
            elif c == "key":
                pg.keyboard.press(cmd["val"]); out = {"ok": True}
            elif c == "click":
                if "sel" in cmd:
                    el = pg.query_selector(cmd["sel"])
                    if el:
                        el.click(); out = {"ok": True, "clicked": cmd["sel"]}
                    else:
                        out = {"ok": False, "err": "no selector", "sel": cmd["sel"]}
                else:
                    pg.mouse.click(cmd["x"], cmd["y"]); out = {"ok": True, "xy": [cmd["x"], cmd["y"]]}
            elif c == "wait":
                time.sleep(cmd.get("sec", 3)); out = {"ok": True, "url": pg.url}
            elif c == "eval":
                out = {"ok": True, "result": pg.evaluate(cmd["js"])}
            elif c == "dump":
                out = {"ok": True, "url": pg.url, "title": pg.title(),
                       "els": pg.evaluate("""() => Array.from(document.querySelectorAll('input,button,a[role=button]')).map(e=>({t:e.tagName,ty:e.type||'',id:e.id||'',nm:e.name||'',ph:e.placeholder||'',tx:(e.innerText||'').slice(0,30).trim(),v:!!(e.offsetWidth||e.offsetHeight)})).filter(o=>o.v)"""),
                       "frames": [f.url[:90] for f in pg.frames]}
            elif c == "shot":
                p = os.path.join(WORK, f"s_{cmd.get('tag','x')}.png")
                pg.screenshot(path=p); out = {"ok": True, "path": p, "url": pg.url}
            elif c == "body":
                out = {"ok": True, "url": pg.url,
                       "text": pg.evaluate("() => document.body.innerText.slice(0,2500)")}
            elif c == "cookies":
                cs = ctx.cookies()
                saved = os.path.join(WORK, "cookies_auth.json")
                json.dump(cs, open(saved, "w"), indent=2)
                out = {"ok": True, "n": len(cs),
                       "names": sorted(set(x["name"] for x in cs)), "saved": saved}
            elif c == "storage":
                out = {"ok": True,
                       "local": pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(localStorage)))"),
                       "session": pg.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(sessionStorage)))")}
            elif c == "exit":
                out = {"ok": True, "bye": True}
                json.dump(out, open(RES, "w")); break
            else:
                out = {"ok": False, "err": "unknown cmd", "c": c}
        time.sleep(cmd.get("after", 1))
    except Exception as e:
        out = {"ok": False, "err": str(e)[:400]}
    json.dump(out, open(RES, "w"), indent=2, default=str)
    print(c, "->", json.dumps(out)[:200], flush=True)

try:
    ctx.close()
except Exception:
    pass
print("daemon exit", flush=True)
