#!/usr/bin/env python3
"""
Headed-browser captcha handoff template.

Use when a target's signup/login is gated by an interactive captcha (jigsaw, hCaptcha
drag, etc.) that automation cannot solve: drive the flow up to the challenge in a HEADED
persistent browser, let the operator solve it once by hand, then detect completion and
persist the session for all subsequent headless probing.

Verified live 2026-10-20 on Proton signup (ProtonCAPTCHA jigsaw).

Usage:
    python headed_captcha_handoff.py <username> <profile_dir> [wait_seconds]

Args:
    username     account identifier to type into the signup form
    profile_dir  persistent Chromium profile dir (session survives across runs)
    wait_seconds how long to keep the window open for the operator (default 480)

The script prints a JSON state line to <profile_dir>/../headed-state.txt (create the
parent first) with {"user":..., "captcha":bool, "url":...} when the challenge appears and
{"solved":bool,"final_url":...} when the URL changes or the wait expires.
"""
import json, sys, time
from playwright.sync_api import sync_playwright

USER = sys.argv[1] if len(sys.argv) > 1 else "testuser"
PROFILE = sys.argv[2] if len(sys.argv) > 2 else os.path.expanduser("~/captcha-handoff-profile")
WAIT = int(sys.argv[3]) if len(sys.argv) > 3 else 480
PW = "ChangeMe#2026xY"          # set per engagement
STATE = PROFILE.rstrip("/\\") + ".state.json"

# Generic React-safe fill: controlled inputs ignore plain value assignment.
FILL_JS = """([sel,val])=>{
  const els=[...document.querySelectorAll(sel)];
  const el=els.find(e=>e.offsetParent!==null)||els[els.length-1];
  if(!el) return 'no element';
  el.scrollIntoView({block:'center',inline:'center'});
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'value').set.call(el,val);
  ['input','change','keyup','blur'].forEach(t=>el.dispatchEvent(new Event(t,{bubbles:true})));
  return 'ok';
}"""

def click_text(pg, pattern):
    """Real mouse click on a visible button matching /pattern/i (bypasses actionability checks)."""
    box = pg.evaluate("""(pat)=>{
      const re=new RegExp(pat,'i');
      const bs=[...document.querySelectorAll('button')];
      const t=bs.find(b=>re.test((b.textContent||'').trim()) && b.offsetParent!==null);
      if(!t) return null;
      t.scrollIntoView({block:'center'});
      const r=t.getBoundingClientRect();
      return {x:r.x+r.width/2, y:r.y+r.height/2};
    }""", pattern)
    if box:
        pg.mouse.click(int(box["x"]), int(box["y"]))
        return True
    return False

def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(PROFILE, headless=False,
            args=["--disable-blink-features=AutomationControlled"],
            viewport={"width": 1400, "height": 950}, locale="en-US")
        pg = ctx.new_page()
        pg.bring_to_front()
        # ---- engagement-specific flow: adapt selectors/steps per target ----
        pg.goto("https://TARGET.example/signup", wait_until="commit", timeout=90000)
        pg.wait_for_timeout(6000)
        pg.evaluate(FILL_JS, ["#username", USER])
        pg.wait_for_timeout(800)
        pg.evaluate(FILL_JS, ["#password", PW])
        pg.wait_for_timeout(1200)
        click_text(pg, "Start using|Create account|Sign up")
        pg.wait_for_timeout(5000)
        if pg.evaluate("()=>!!document.getElementById('password-confirm')"):
            pg.evaluate(FILL_JS, ["#password-confirm", PW])
            pg.wait_for_timeout(1000)
            click_text(pg, "Start using|Create account|Sign up")
        pg.wait_for_timeout(10000)
        # -------------------------------------------------------------------
        cap = any("captcha" in (f.url or "").lower() for f in pg.frames)
        print("USER:", USER, "| captcha:", cap, "| url:", pg.url, flush=True)
        import os
        os.makedirs(os.path.dirname(STATE) or ".", exist_ok=True)
        open(STATE + ".txt", "w").write(json.dumps({"user": USER, "captcha": cap, "url": pg.url}))
        # poll for completion (operator solving the challenge)
        start_url = pg.url
        solved = False
        for _ in range(WAIT // 3):
            pg.wait_for_timeout(3000)
            if pg.url != start_url:
                solved = True
                print("URL CHANGED ->", pg.url, flush=True)
                break
        st = {"user": USER, "solved": solved, "final_url": pg.url, "ts": time.time()}
        print("FINAL:", json.dumps(st), flush=True)
        open(STATE + ".txt", "w").write(json.dumps(st))
        ctx.storage_state(path=STATE)   # persist session for headless runs
        pg.wait_for_timeout(60000)      # grace period in case operator still working
        ctx.close()

if __name__ == "__main__":
    main()
