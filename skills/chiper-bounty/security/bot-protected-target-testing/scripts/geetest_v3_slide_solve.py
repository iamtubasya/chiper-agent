#!/usr/bin/env python3
"""Geetest v3 (slide3) solver + operator-handoff driver.

Two modes:

  solve   open a page that renders the Geetest widget, compute the notch from the
          bg/fullbg canvases, drag the slider in a closed loop, and report the
          verdict Geetest itself gave (window.__gt).

  handoff same, but stop at the widget and wait for a human to drag it. Use this
          the moment `solve` returns FAIL twice -- a human drag is 1 second.

Usage
-----
  # generic: you already have a URL that shows the widget
  python geetest_v3_slide_solve.py solve   --url "https://consent.target.tld/register?login_challenge=..."
  python geetest_v3_slide_solve.py handoff --url "..." --handoff-file ./code.txt

  # drive a Galoy-style phone form for you, then solve
  python geetest_v3_slide_solve.py solve \
      --url "https://consent.target.tld/register?login_challenge=..." \
      --phone "+62812..." --channel WHATSAPP

Requires: playwright (channel="chrome"), opencv-python, numpy.  Use a REAL installed
Chrome (headless=False, channel="chrome"); headless gets refused here as elsewhere.

Knobs that matter (all verified in the field, see
references/geetest-v3-slider-solving.md):
  * notch threshold  -> 0.40 * col.max() over the piece's row band (NOT a fixed 60)
  * alignment        -> piece CENTRE to notch CENTRE (the notch is threshold-eroded)
  * slider:piece     -> 1:1; calibrate once rather than deriving it
  * track density    -> 50-90 moves, smoothstep, ~1 s total
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import random
import re
import sys
import time

import cv2
import numpy as np

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    sys.exit("pip install playwright  (then: playwright install chromium)")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Intercept initGeetest (assigned dynamically) so we can read the widget's own verdict.
HOOK_INITGEETEST = r"""
(() => { let _v;
  Object.defineProperty(window,'initGeetest',{configurable:true,
    get(){return _v;},
    set(v){ _v=v; const w=function(o,cb){ return v(o,function(obj){ window.__gt=[];
        try{obj.onSuccess(()=>window.__gt.push('SUCCESS'));}catch(e){}
        try{obj.onError(e=>window.__gt.push('ERR:'+String(e).slice(0,60)));}catch(e){}
        try{obj.onFail&&obj.onFail(()=>window.__gt.push('FAIL'));}catch(e){}
        window.__gtObj=obj; return cb(obj); });};
      Object.defineProperty(window,'initGeetest',{value:w,writable:true,configurable:true}); }
  });
})();
"""

JS_CANVASES = """() => {
  const g = s => document.querySelector(s);
  const bg = g('canvas.geetest_canvas_bg'), fb = g('canvas.geetest_canvas_fullbg'),
        sl = g('canvas.geetest_canvas_slice'), btn = g('.geetest_slider_button');
  if (!bg || !sl) return null;
  const r = btn ? btn.getBoundingClientRect() : null;
  return { bg: bg.toDataURL('image/png'), fb: fb ? fb.toDataURL('image/png') : null,
           sl: sl.toDataURL('image/png'),
           w: bg.width, cssw: bg.getBoundingClientRect().width,
           btn: r ? [r.x, r.y, r.width] : null };
}"""

JS_SLICE = ("() => { try { return document.querySelector('canvas.geetest_canvas_slice')"
            ".toDataURL('image/png'); } catch(e) { return null; } }")


def decode(data_url: str):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data_url.split(",", 1)[1]), np.uint8),
                        cv2.IMREAD_UNCHANGED)


def piece_bbox(slice_img):
    """Leftmost/topmost opaque column/row of the puzzle piece."""
    if slice_img is None or slice_img.ndim < 3 or slice_img.shape[2] < 4:
        return None
    a = slice_img[:, :, 3]
    cols = np.where(a.max(axis=0) > 10)[0]
    rows = np.where(a.max(axis=1) > 10)[0]
    if not len(cols) or not len(rows):
        return None
    return int(cols[0]), int(cols[-1]), int(rows[0]), int(rows[-1])


def find_notch(bg_img, fb_img, piece_rows):
    """Left/right edge of the notch. Returns (left, right, centre)."""
    bg = bg_img[:, :, :3].astype(np.int16)
    fb = fb_img[:, :, :3].astype(np.int16)
    diff = np.abs(bg - fb).sum(axis=2).astype(np.float64)
    r0, r1 = piece_rows
    band = diff[max(0, r0 - 2): r1 + 3, :]
    col = band.sum(axis=0)
    idx = np.where(col > max(0.40 * col.max(), 1.0))[0]
    if not len(idx):
        idx = np.array([int(np.argmax(col))])
    return int(idx[0]), int(idx[-1]), (int(idx[0]) + int(idx[-1])) / 2.0


def track(total: float, n: int):
    """Smoothstep accelerate/cruise/decelerate positions; the widget checks the track."""
    us = [(k + 1) / n for k in range(n)]
    return [total * (3 * u * u - 2 * u * u * u) for u in us]


async def wait_for_widget(pg, timeout_s=40):
    for _ in range(timeout_s):
        if await pg.evaluate("!!document.querySelector('.geetest_slider_button') "
                             "&& !!document.querySelector('canvas.geetest_canvas_fullbg')"):
            return True
        await pg.wait_for_timeout(1000)
    return False


async def fill_phone_form(pg, phone, channel):
    """Galoy-style consent form. Typing the +CC form is what fixes the country."""
    inp = pg.locator("input#phone")
    await inp.click()
    await inp.fill("")
    await inp.type(phone, delay=60)
    await pg.wait_for_timeout(800)
    got = await inp.input_value()
    print(f"  phone input reads: {got!r}")
    if channel:
        opts = await pg.evaluate(
            "() => { const s=document.querySelector('select[name=channel]');"
            " return s ? [...s.options].map(o=>o.value) : null; }")
        print(f"  channel options: {opts}")
        if opts and channel in opts:
            await pg.select_option("select[name=channel]", channel)
    await pg.click("button[type=submit]")


async def solve_widget(pg, max_rounds=2):
    """Returns dict with verdict / geometry. Keeps the button held through one drag."""
    for rnd in range(1, max_rounds + 1):
        d = await pg.evaluate(JS_CANVASES)
        if not d or not d["fb"]:
            print("  ! canvases missing")
            return {"verdict": "NO_CANVAS"}
        bg, fb, sl = decode(d["bg"]), decode(d["fb"]), decode(d["sl"])
        pb = piece_bbox(sl)
        if pb is None:
            return {"verdict": "NO_PIECE"}
        p_left, p_right, p_top, p_bot = pb
        p_w = p_right - p_left + 1
        n_left, n_right, n_mid = find_notch(bg, fb, (p_top, p_bot))
        target_left = n_mid - p_w / 2.0            # CENTRE-align: notch is eroded
        scale = (d["cssw"] / d["w"]) if d["w"] else 1.0
        need_css = (target_left - p_left) * scale
        print(f"  round {rnd}: piece L{p_left} R{p_right} W{p_w} | notch L{n_left} R{n_right} "
              f"C{n_mid:.1f} | need_css={need_css:.1f}")
        if not d["btn"]:
            return {"verdict": "NO_BUTTON"}
        bx, by, bw = d["btn"]
        sx, sy = bx + bw / 2, by + bw / 2
        await pg.mouse.move(sx - 40, sy)
        await pg.wait_for_timeout(120)
        await pg.mouse.move(sx, sy)
        await pg.wait_for_timeout(250)
        await pg.mouse.down()
        await pg.wait_for_timeout(220)
        n = max(48, int(abs(need_css) / 1.5))
        for k, x in enumerate(track(need_css, n)):
            await pg.mouse.move(sx + x, sy + random.uniform(-1.2, 1.2))
            dly = random.randint(9, 20)
            if k == n // 3:
                dly += random.randint(30, 90)
            await pg.wait_for_timeout(dly)
        await pg.mouse.move(sx + need_css - 0.3, sy + random.uniform(-0.4, 0.4))
        await pg.wait_for_timeout(140)
        await pg.mouse.move(sx + need_css, sy)
        await pg.wait_for_timeout(random.randint(150, 250))
        await pg.mouse.up()
        await pg.wait_for_timeout(4000)
        verdict = await pg.evaluate("window.__gt || []")
        print(f"  round {rnd}: verdict={verdict}  events={n}")
        if "SUCCESS" in verdict:
            return {"verdict": "SUCCESS", "round": rnd}
        # regenerate a fresh challenge before the next round
        try:
            await pg.reload(wait_until="domcontentloaded")
            if not await wait_for_widget(pg, 30):
                return {"verdict": "NO_WIDGET_ON_RETRY"}
        except Exception as e:  # noqa: BLE001
            return {"verdict": "RELOAD_FAILED", "error": str(e)[:120]}
    return {"verdict": "FAIL"}


async def run(args):
    async with async_playwright() as p:
        br = await p.chromium.launch(channel="chrome", headless=False,
                                     args=["--disable-blink-features=AutomationControlled",
                                           "--start-maximized", "--window-position=0,0"])
        ctx = await br.new_context(viewport={"width": 1280, "height": 950}, locale="en-US",
                                   user_agent=UA)
        pg = await ctx.new_page()
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
        await ctx.add_init_script(HOOK_INITGEETEST)
        print(f"-> {args.url[:110]}")
        await pg.goto(args.url, wait_until="domcontentloaded")
        await pg.wait_for_timeout(2500)
        if args.phone:
            await fill_phone_form(pg, args.phone, args.channel)
        if not await wait_for_widget(pg, args.widget_timeout):
            print("! widget never appeared")
            await ctx.storage_state(path=args.state or "geetest_state.json")
            await br.close()
            return 2

        if args.mode == "handoff":
            print("=" * 64)
            print(">>> CAPTCHA READY - drag the slider in the Chrome window <<<")
            print("=" * 64)
            for _ in range(int(args.handoff_wait)):
                await pg.wait_for_timeout(1000)
                u = pg.url
                if "verification" in u or "code=" in u:
                    print(f"  left the captcha route: {u[:120]}")
                    break
                st = await pg.evaluate(
                    "() => { const s=document.querySelector('.geetest_panel_success');"
                    " return s ? getComputedStyle(s).display!=='none' : false; }")
                if st:
                    break
            if args.handoff_file:
                print(f"  waiting for OTP in {args.handoff_file} ...")
                for _ in range(600):
                    await pg.wait_for_timeout(2000)
                    try:
                        with open(args.handoff_file) as fh:
                            code = fh.read().strip()
                    except OSError:
                        code = ""
                    if code:
                        print(f"  got code {code[:2]}**** - typing it")
                        el = pg.locator("input[name=code], input#code, "
                                        "input[inputmode=numeric], input[type=tel]").first
                        await el.click()
                        await el.fill("")
                        await el.type(code, delay=90)
                        await pg.click("button[type=submit]")
                        await pg.wait_for_timeout(6000)
                        break
        else:
            res = await solve_widget(pg, max_rounds=args.rounds)
            print(f"RESULT {json.dumps(res)}")
            if res["verdict"] != "SUCCESS":
                print("-> verdict is not SUCCESS. Re-run in `handoff` mode; a human drag "
                      "takes 1 second and beats trajectory tuning.")

        await pg.wait_for_timeout(4000)
        print(f"  url now: {pg.url[:140]}")
        print(f"  gt verdict: {await pg.evaluate('window.__gt || []')}")
        if args.state:
            await ctx.storage_state(path=args.state)
            print(f"  storage_state -> {args.state}")
        await pg.wait_for_timeout(3000)
        await br.close()
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["solve", "handoff"])
    ap.add_argument("--url", required=True, help="page URL that renders the widget")
    ap.add_argument("--phone", help="drive a Galoy-style phone form first (use the +CC form)")
    ap.add_argument("--channel", help="e.g. WHATSAPP / TELEGRAM (read the options first)")
    ap.add_argument("--rounds", type=int, default=2, help="solve attempts before giving up")
    ap.add_argument("--widget-timeout", type=int, default=40)
    ap.add_argument("--handoff-wait", type=int, default=900, help="seconds to wait for the drag")
    ap.add_argument("--handoff-file", help="file the operator writes the OTP into")
    ap.add_argument("--state", default="geetest_state.json", help="storage_state output path")
    args = ap.parse_args()
    sys.exit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
