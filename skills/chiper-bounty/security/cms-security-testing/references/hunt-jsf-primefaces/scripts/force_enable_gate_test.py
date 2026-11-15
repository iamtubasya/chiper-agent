#!/usr/bin/env python3
"""Differential gate test for JSF/PrimeFaces consoles (hunt-jsf-primefaces §8).

Answers ONE question, with evidence: when a control is disabled/readonly, does the
SERVER enforce the restriction, or is the gate cosmetic?

Method
  1. load page, read the field's current server value
  2. count disabled vs total fields (gate surface area)
  3. force-enable the field and set the new value
  4. submit -- real click first, JS .click() as fallback (bypasses overlays/modals)
  5. RELOAD from the server and re-read the value
  6. verdict = KEPT (server accepted) | REVERTED (server enforced) | UNCLEAR

Verdict semantics
  REVERTED  -> server-side enforcement -> NOT a bug. Keep the output as negative proof.
  KEPT      -> gated feature reachable   -> real finding. Reproduce 3x, then escalate.
  UNCLEAR   -> field missing after reload, page changed, or session lost. Do NOT report.

Usage
  python force_enable_gate_test.py \
      --url "https://host/mc2/faces/setup/configMgmt.xhtml" \
      --state nac_admin_state.json \
      --field "#form1\\:NCTIME_IPCHANGE" \
      --value 5 \
      --submit "#form1\\:actionBtn" \
      --repeat 2

Notes
  * --state is a Playwright storage_state JSON (cookies + localStorage). Produce it once by
    logging in with a helper, then reuse it; otherwise you will re-do the OTP flow every run.
  * --field/--submit use CSS selectors. JSF clientIds contain ':' -- escape as \\:
    (in a shell, quote the whole arg; in Python, use a raw string).
  * --revert sets the field back to its original value and submits, so testing on a
    self-provisioned instance leaves it clean.
  * Always run --repeat 2 or 3 before writing anything up.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    sys.exit("playwright not installed: pip install playwright && playwright install chromium")


async def read_value(page, selector: str) -> str | None:
    try:
        return await page.input_value(selector)
    except Exception:
        return None


async def gate_stats(page, selector: str) -> dict:
    """Count disabled vs total inputs inside the field's enclosing form."""
    try:
        return await page.evaluate(
            """(sel) => {
                const el = document.querySelector(sel);
                if (!el) return {found: false};
                const form = el.closest('form') || document;
                const inputs = Array.from(form.querySelectorAll('input,select,textarea'));
                return {
                    found: true,
                    total: inputs.length,
                    disabled: inputs.filter(e => e.disabled).length,
                    field_disabled: !!el.disabled,
                    field_readonly: !!el.readOnly,
                };
            }""",
            selector,
        )
    except Exception:
        return {"found": False}


async def set_value(page, selector: str, value: str) -> bool:
    """Force-enable then set. Returns True if the DOM accepted the value."""
    try:
        await page.evaluate(
            """([sel, v]) => {
                const e = document.querySelector(sel);
                if (!e) return false;
                e.removeAttribute('disabled');
                e.disabled = false;
                e.readOnly = false;
                e.value = v;
                e.dispatchEvent(new Event('input', {bubbles: true}));
                e.dispatchEvent(new Event('change', {bubbles: true}));
                return e.value === v;
            }""",
            [selector, value],
        )
        return (await read_value(page, selector)) == value
    except Exception:
        return False


async def submit(page, selector: str) -> str:
    """Real click first; fall back to JS click when an overlay intercepts."""
    try:
        await page.click(selector, timeout=8000)
        return "real-click"
    except Exception:
        try:
            await page.evaluate(
                """(sel) => {
                    const b = document.querySelector(sel);
                    if (!b) return false;
                    b.disabled = false;
                    b.removeAttribute('disabled');
                    b.click();
                    return true;
                }""",
                selector,
            )
            return "js-click"
        except Exception:
            return "failed"


async def one_round(args) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not args.headful)
        ctx = await browser.new_context(
            ignore_https_errors=True,
            storage_state=args.state,
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            ),
            viewport={"width": 1600, "height": 1000},
        )
        page = await ctx.new_page()
        page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(args.settle)

        baseline = await read_value(page, args.field)
        stats = await gate_stats(page, args.field)
        if baseline is None:
            return {"verdict": "UNCLEAR", "reason": "field not found on load",
                    "url": page.url, "stats": stats}

        accepted = await set_value(page, args.field, str(args.value))
        pre_submit = await read_value(page, args.field)
        how = await submit(page, args.submit)
        await page.wait_for_timeout(args.wait)

        body = ""
        try:
            body = (await page.inner_text("body"))[:600]
        except Exception:
            pass

        # Reload FROM THE SERVER -- this is the only thing that constitutes proof.
        await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(args.settle)
        after = await read_value(page, args.field)

        if after is None:
            verdict, reason = "UNCLEAR", "field missing after reload (page/session changed)"
        elif after == str(args.value):
            verdict, reason = "KEPT", "new value survived reload -> server accepted the write"
        elif after == baseline:
            verdict, reason = "REVERTED", "server restored the original value -> enforced"
        else:
            verdict, reason = "UNCLEAR", f"unexpected value after reload: {after!r}"

        if args.revert and verdict == "KEPT":
            await set_value(page, args.field, baseline)
            await submit(page, args.submit)
            await page.wait_for_timeout(args.wait)
            await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(args.settle)
            reverted_to = await read_value(page, args.field)
        else:
            reverted_to = None

        result = {
            "url": args.url,
            "field": args.field,
            "baseline": baseline,
            "attempted": str(args.value),
            "dom_accepted": accepted,
            "value_at_submit": pre_submit,
            "submit_via": how,
            "after_reload": after,
            "verdict": verdict,
            "reason": reason,
            "gate_stats": stats,
            "body_snippet": body,
        }
        if reverted_to is not None:
            result["reverted_to"] = reverted_to

        await browser.close()
        return result


async def main() -> int:
    ap = argparse.ArgumentParser(description="JSF/PrimeFaces differential gate test")
    ap.add_argument("--url", required=True)
    ap.add_argument("--state", help="Playwright storage_state JSON (cookies/auth)")
    ap.add_argument("--field", required=True, help="CSS selector; escape ':' as \\\\:")
    ap.add_argument("--value", required=True)
    ap.add_argument("--submit", required=True, help="CSS selector of the submit control")
    ap.add_argument("--repeat", type=int, default=1, help="rounds to run (use 3 before reporting)")
    ap.add_argument("--settle", type=int, default=7000, help="ms to wait after each navigation")
    ap.add_argument("--wait", type=int, default=12000, help="ms to wait after submit")
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--revert", action="store_true", help="restore original value if it persisted")
    ap.add_argument("--out", help="write JSON results here")
    args = ap.parse_args()

    results = []
    for i in range(args.repeat):
        r = await one_round(args)
        r["round"] = i + 1
        results.append(r)
        print(f"[round {i+1}] {r['verdict']:<9} {r['reason']}")
        print(f"           baseline={r['baseline']!r} attempted={r['attempted']!r} "
              f"after_reload={r.get('after_reload')!r} submit_via={r['submit_via']}")
        if r["stats"].get("found"):
            print(f"           gate: {r['stats']['disabled']}/{r['stats']['total']} inputs disabled, "
                  f"field_disabled={r['stats']['field_disabled']}")
        if i + 1 < args.repeat:
            await asyncio.sleep(2)

    verdicts = {r["verdict"] for r in results}
    print()
    if verdicts == {"REVERTED"}:
        print("CONCLUSION: REVERTED -> server-side enforcement -> NOT a finding (negative proof).")
    elif verdicts == {"KEPT"}:
        print("CONCLUSION: KEPT -> gated write accepted -> real finding. Escalate and write up.")
    elif "KEPT" in verdicts:
        print("CONCLUSION: INCONSISTENT (some rounds KEPT) -> unstable, reproduce more. Do not report yet.")
    else:
        print("CONCLUSION: UNCLEAR -> do not report. Fix the run (selector/session) first.")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(f"results -> {args.out}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
