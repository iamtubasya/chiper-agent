#!/usr/bin/env python3
"""Solve a DataDome audio CAPTCHA and graft the resulting ticket onto the target domain.

Why this exists: on a DataDome-gated signup, `POST /.../register` answers
  403 {"url":"https://geo.captcha-delivery.com/captcha/?...&t=fe&..."}
from curl, from Playwright's request context, and from the app's own in-page fetch.
The challenge page offers an AUDIO alternative, which is the reliable way through when you
must create your own test account.

Chain (verified end-to-end 2026-10-01 against www.vinted.com):
  1. trigger the challenge (or reuse a fresh captcha URL someone else produced)
  2. pull the .wav out of the challenge HTML
  3. transcribe 6 spoken digits with faster-whisper
  4. click audio toggle -> play -> type digits one per field -> submit
  5. the ticket comes back on GET geo.captcha-delivery.com/captcha/check?cid=...
     as {"cookie":"datadome=<v>; Domain=.<target>; ..."} -- the BROWSER WILL NOT APPLY IT
     (different origin), so parse it and ctx.add_cookies() it yourself
  6. retry the original app request -> 200

Usage:
  python datadome_audio_captcha_solve.py <captcha_url> <target_domain> [--profile DIR] [--headed]

Then re-issue the request that was challenged (route-rewrite an app request, see the SKILL body).

NOTE: three faster-whisper models voting is more robust than one; the audio starts with the
sentence "Please type the numbers you hear." followed by the six digits.
"""
import argparse
import asyncio
import re
import sys
from pathlib import Path

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


def transcribe_digits(wav: Path) -> tuple[str, str]:
    from faster_whisper import WhisperModel
    votes, notes = {}, []
    for size in ("base", "small", "tiny"):
        try:
            m = WhisperModel(size, device="cpu", compute_type="int8")
            segs, _ = m.transcribe(str(wav), language="en", beam_size=5,
                                   condition_on_previous_text=False)
            txt = " ".join(s.text for s in segs)
            d = "".join(re.findall(r"\d", txt))
            notes.append(f"{size}:{d}")
            if len(d) == 6:
                votes[d] = votes.get(d, 0) + 1
        except Exception as exc:                      # model download / OOM -> try the next size
            notes.append(f"{size}:ERR({type(exc).__name__})")
    best = max(votes, key=votes.get) if votes else ""
    return best, " | ".join(notes)


async def solve(captcha_url: str, target_domain: str, profile: str, headed: bool) -> bool:
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=profile, headless=not headed,
            viewport={"width": 1366, "height": 900}, user_agent=UA, locale="en-US",
            args=["--disable-blink-features=AutomationControlled"])
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await pg.goto(captcha_url, wait_until="domcontentloaded", timeout=60000)
        await pg.wait_for_timeout(2500)

        html = await pg.content()
        m = re.search(r"(https://dd\.prod\.captcha-delivery\.com/audio/[^\"']+\.wav)", html)
        if not m:
            print(f"[!] no audio URL on the page (title={await pg.title()!r}) -- "
                  f"either the challenge expired or this is the visual variant")
            await ctx.close()
            return False

        wav = Path(profile).parent / "captcha_audio.wav"
        wav.parent.mkdir(parents=True, exist_ok=True)
        wav.write_bytes(await (await ctx.request.get(m.group(1))).body())
        digits, notes = transcribe_digits(wav)
        print(f"[*] {notes} -> using {digits or '<none>'}")
        if len(digits) != 6:
            print("[!] did not get 6 digits; re-run for a fresh challenge")
            await ctx.close()
            return False

        await pg.click("#captcha__audio__button", timeout=8000)
        await pg.wait_for_timeout(800)
        try:
            await pg.click(".audio-captcha-play-button", timeout=4000)
        except Exception:
            pass                                        # play is not always required
        await pg.wait_for_timeout(2200)

        fields = await pg.query_selector_all(".audio-captcha-inputs")
        for i, ch in enumerate(digits):
            await fields[i].click()
            await pg.keyboard.type(ch, delay=60)
        typed = await pg.eval_on_selector_all(".audio-captcha-inputs", "e=>e.map(x=>x.value)")
        print(f"[*] typed {typed}")                     # .fill() alone does not always satisfy the widget
        await pg.click(".audio-captcha-submit-button", timeout=8000)
        await pg.wait_for_timeout(9000)

        # --- the ticket ---------------------------------------------------------
        ticket = None
        for c in await ctx.cookies():
            if c["name"] == "datadome" and target_domain.strip(".") in c.get("domain", ""):
                ticket = c["value"]
        if not ticket:
            print("[!] no datadome cookie landed on the target domain.")
            print("    The /captcha/check response carries it with Domain=.<target>, but it arrives "
                  "from a captcha-delivery.com origin and browsers refuse it. Capture the response "
                  "body (Network listener on '/captcha/check'), regex datadome=([^;\"\\\\]+), then:")
            print(f'    ctx.add_cookies([{{"name":"datadome","value":v,"domain":".{target_domain}",'
                  f'"path":"/","secure":True}}])')
            await ctx.close()
            return False

        print(f"[+] ticket on .{target_domain}: {ticket[:24]}...")
        print("[+] now RETRY the original request (route-rewrite the app's own XHR) -> expect 200")
        await ctx.close()
        return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("captcha_url")
    ap.add_argument("target_domain", help="e.g. vinted.com (leading dot optional)")
    ap.add_argument("--profile", default="./pw-profile")
    ap.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    ok = asyncio.run(solve(a.captcha_url, a.target_domain.lstrip("."), a.profile, a.headed))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
