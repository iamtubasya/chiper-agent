#!/usr/bin/env python3
"""Cap-race harness: fire N concurrent resource-create submits through the REAL UI.

Why the UI and not a replay: bound Next.js server actions (no `$ACTION_ID_*` input,
body `{"0":"[{},\\"$K1\\"]", ...}`) often cannot be replayed out-of-band — the replay
returns HTTP 500 + an opaque `E{"digest":<n>}`, which is INDISTINGUISHABLE from a
refused action. Driving the rendered form gives valid per-render bindings and real
parallel HTTP requests.

Preconditions (both matter, both were learned the hard way):
  1. The identity must have ZERO resources. On an account already at the cap the create
     control is not rendered at all, so the "race" silently tests nothing
     (symptom: every page reports `namefield=0`, 0 submits fired).
  2. Assert a logged-in marker first — a stale session cookie makes the recount return
     "0 resources", which reads as a finding.

Usage:
  python ui_cap_race.py <state.json> [--base URL] [--n 6] [--url PATH]
                        [--open "Add income source"] [--sub "Rental property"]
                        [--field "#name"] [--count 'a[href*="/app/sources/"]']
  On Windows/git-bash pass URL-ish args with `env MSYS_NO_PATHCONV=1 ...`
  (per-command). Do NOT export MSYS2_ARG_CONV_EXCL globally — it corrupts later $PWD.

Expected clean result: exactly 1 resource created. That is the NEGATIVE (control holds)
and is worth recording verbatim. >1 = check-then-act race, a real finding.
"""
import argparse
import json
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("state", help="browser storage_state JSON (authed identity, 0 resources)")
    ap.add_argument("--base", default="https://example.com")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--url", default="/app", help="page whose UI opens the create form")
    ap.add_argument("--open", default="Add income source", help="text of the button that opens it")
    ap.add_argument("--sub", default="Rental property", help="second-step choice, '' to skip")
    ap.add_argument("--field", default="#name", help="selector of the name/text input")
    ap.add_argument("--count", default='a[href*="/app/sources/"]',
                    help="selector used to count created resources afterwards")
    ap.add_argument("--logged-in-marker", default="Log out")
    a = ap.parse_args()

    state = json.loads(pathlib.Path(a.state).read_text())
    pw = sync_playwright().start()
    br = pw.chromium.launch(headless=True,
                            args=["--disable-blink-features=AutomationControlled"])
    # ONE browser + ONE context. Two sync_playwright() instances in one process collide
    # ("Playwright Sync API inside the asyncio loop") — don't try it for a 2nd identity.
    ctx = br.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"),
        locale="en-GB")
    for c in state.get("cookies", []):
        try:
            ctx.add_cookies([{**c, "sameSite": "Lax"}])
        except Exception:
            pass

    count_js = "(sel) => [...new Set([...document.querySelectorAll(sel)]" \
               ".map(e => e.getAttribute('href') || e.getAttribute('src') || e.textContent))]"
    pages = []
    try:
        # ---- login assert (never trust a stale jar) ------------------------------
        probe = ctx.new_page()
        probe.goto(a.base + a.url, wait_until="domcontentloaded", timeout=55000)
        probe.wait_for_timeout(2500)
        body = probe.inner_text("body")
        if a.logged_in_marker not in body:
            print("!! NOT LOGGED IN (marker %r absent). Re-login and re-export the jar."
                  % a.logged_in_marker)
            print("   url:", probe.url)
            sys.exit(2)

        base_props = probe.evaluate(count_js, a.count)
        print("baseline resources: %d" % len(base_props))

        # ---- prepare N pages with the create form OPEN and FILLED ----------------
        for i in range(a.n):
            pg = ctx.new_page()
            pg.goto(a.base + a.url, wait_until="domcontentloaded", timeout=55000)
            pg.wait_for_timeout(2500)
            opened = pg.evaluate("""(t) => {
                const b=[...document.querySelectorAll('button,a')]
                          .find(x => x.innerText.includes(t));
                if (!b) return 'nobtn'; b.click(); return 'modal';
            }""", a.open)
            pg.wait_for_timeout(1500)
            if a.sub:
                pg.evaluate("""(t) => {
                    const b=[...document.querySelectorAll('button')]
                              .find(x => x.innerText.includes(t));
                    if (b) b.click();
                }""", a.sub)
                pg.wait_for_timeout(1500)
            fields = pg.locator(a.field).count()
            if fields:
                pg.fill(a.field, "RACEUI-%d-%d" % (i, int(time.time())))
            pages.append((pg, fields))
            print("  page %d ready (open=%s, fields=%d)" % (i, opened, fields))

        if not any(f for _, f in pages):
            print("!! no create form rendered on any page — account is probably already at the "
                  "cap. Use a fresh identity with 0 resources.")
            sys.exit(3)

        # ---- fire all submits as tight as the runtime allows --------------------
        t0 = time.time()
        for pg, fields in pages:
            if fields:
                pg.evaluate("""(sel) => {
                    const el=document.querySelector(sel);
                    el.closest('form').querySelector('button[type=submit]').click();
                }""", a.field)
        print("all %d submits fired in %.3fs" % (a.n, time.time() - t0))

        # ---- recount ------------------------------------------------------------
        pages[0][0].wait_for_timeout(9000)
        after = pages[0][0].goto(a.base + a.url, wait_until="domcontentloaded", timeout=45000)
        pages[0][0].wait_for_timeout(3500)
        props = sorted(set(pages[0][0].evaluate(count_js, a.count)))
        delta = len(props) - len(base_props)
        print("RESOURCES AFTER RACE: %d (delta %+d)" % (len(props), delta))
        for p in props:
            print("   ", p)
        print("VERDICT:", "CAP HELD (negative)" if delta <= 1
              else "RACE WON — %d extra created (FINDING)" % delta)
        ctx.storage_state(path=a.state)
    finally:
        br.close()
        pw.stop()


if __name__ == "__main__":
    main()
