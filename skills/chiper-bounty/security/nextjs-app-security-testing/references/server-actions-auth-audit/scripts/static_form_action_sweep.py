#!/usr/bin/env python3
"""Static (browserless) Server-Action FORM sweep for Next.js App Router targets.

What it does
------------
1. Loads each configured app page with an authenticated session cookie.
2. Slices every <form> block and extracts its action fields ($ACTION_ID_* / $ACTION_REF_N +
   $ACTION_N:0/1 + $ACTION_KEY) and business fields, PER FORM (never page-wide).
3. Fires each form UNPATCHED as a baseline, then again with every object-id field replaced by a
   FOREIGN value and by a RANDOM value, using the BARE (unprefixed) field names the server accepts.
4. Prints a per-form table: baseline result, and for each substitution the server's own reaction
   (RSC error string / redirect / no-op) so the authz answer is quotable.

Safety defaults
---------------
* Skips any form carrying a sensitive field (file/email/password/mfa/code/sms/phone).
* Skips HMRC-submission / dangerous pages listed in BLOCK_PAGE.
* FOREIGN targets must be objects you own in a second tenant; RANDOM ids are always safe
  (nothing can match). Never point a destructive form at a third party's real object.

Usage
-----
    python static_form_action_sweep.py --cookie-file browser_state_pro.json \
        --pages /app /app/account/api /app/clients/<client-uuid> /app/sources/<own-uuid> \
        --foreign propertyId=<other-tenant-source-uuid> txnId=<other-tenant-txn-uuid>

Exit code is always 0; read the printed table + the JSON it writes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

BLOCK_PAGE = ("/app/hmrc", "/app/file", "/app/year-end", "/app/account/security",
              "/app/account/advisers", "/app/imports")
BLOCK_FIELD = ("file", "email", "password", "mfa", "code", "sms", "phone", "current", "new")
ID_FIELD_RE = re.compile(
    r"^(propertyId|txnId|transactionId|id|sourceId|batchId|shareId|accessId|keyId|adviserId|"
    r"noteId|documentId|reminderId|invoiceId|attachmentId|listing-\d+|clientId|targetId)$", re.I)
RANDOM_ID = "deadbeef-1234-5679-89ab-cdef01234567"


def cookie_value(path: pathlib.Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "cookies" in data:
        return next(c["value"] for c in data["cookies"] if c["name"] == "qw_session")
    return path.read_text(encoding="utf-8").strip()


def unesc(v: str) -> str:
    return (v.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&#x27;", "'"))


def parse_forms(html: str):
    """Yield one dict per <form>: {'action': {...}, 'fields': {...}, 'buttons': [...]}"""
    out = []
    for block in re.findall(r"<form\b.*?</form>", html, re.S | re.I):
        action = {}
        for m in re.finditer(r'name="(\$ACTION[^"]*)"(?:\s+value="([^"]*)")?', block):
            action[m.group(1)] = unesc(m.group(2) or "")
        fields = {}
        for m in re.finditer(r'<input\b[^>]*name="([^"$][^"]*)"[^>]*?(?:value="([^"]*)")?[^>]*>', block):
            fields[m.group(1)] = unesc(m.group(2) or "")
        for m in re.finditer(r'<select\b[^>]*name="([^"$][^"]*)"[^>]*>(.*?)</select>', block, re.S):
            opts = re.findall(r'<option[^>]*value="([^"]*)"', m.group(2))
            fields[m.group(1)] = unesc(opts[0]) if opts else ""
        buttons = [re.sub(r"<[^>]+>", " ", b).strip()[:28]
                   for b in re.findall(r"<button[^>]*>(.*?)</button>", block, re.S)][:2]
        out.append({"action": action, "fields": fields, "buttons": buttons})
    return out


def fire(session, base, page, form, overrides=None, timeout=60):
    """POST the form with BARE field names. Returns (status, len, location, errors, body)."""
    data = dict(form["action"])
    for k, v in form["fields"].items():
        data[k] = (overrides or {}).get(k, v)
    data["0"] = '[{},"$K1"]'
    try:
        r = session.post(base + page,
                         files={k: (None, str(v)) for k, v in data.items()},
                         headers={"Origin": base, "Referer": base + page,
                                  "Accept": "text/x-component"},
                         timeout=timeout, allow_redirects=False)
    except Exception as exc:                      # network / transient
        return "ERR", 0, "", [str(exc)[:90]], ""
    errs = re.findall(r'"error":"([^"]{3,200})"', r.text)
    return r.status_code, len(r.text), r.headers.get("location", ""), errs[:2], r.text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://quarterwise.co.uk")
    ap.add_argument("--cookie-file", required=True, type=pathlib.Path)
    ap.add_argument("--pages", nargs="+", required=True)
    ap.add_argument("--foreign", nargs="*", default=[],
                    help="field=<uuid> pairs pointing at objects you own in a SECOND tenant")
    ap.add_argument("--out", default="evidence/form-action-sweep.json")
    args = ap.parse_args()

    foreign = {}
    for kv in args.foreign:
        k, _, v = kv.partition("=")
        foreign[k] = v

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Cookie": "qw_session=" + cookie_value(args.cookie_file)})

    rows = []
    for page in args.pages:
        if any(b in page for b in BLOCK_PAGE):
            print(f"\n=== {page} :: SKIPPED (blocked page)")
            continue
        r = s.get(args.base + page, timeout=45, allow_redirects=False)
        if r.status_code != 200:
            print(f"\n=== {page} :: HTTP {r.status_code} (session valid? in scope?)")
            continue
        forms = parse_forms(r.text)
        print(f"\n=== {page} :: {len(forms)} form(s)")
        for i, form in enumerate(forms):
            names = [k for k in form["fields"] if not k.startswith("$")]
            if any(any(b in n.lower() for b in BLOCK_FIELD) for n in names):
                print(f"  form[{i}] {form['buttons']} :: SKIPPED (sensitive field)")
                continue
            ids = [n for n in names if ID_FIELD_RE.match(n)]
            print(f"  form[{i}] {form['buttons']} fields={names[:8]} idfields={ids}")
            st, ln, loc, errs, _ = fire(s, args.base, page, form)
            rows.append({"page": page, "form": i, "mode": "baseline", "fields": names,
                         "status": st, "len": ln, "location": loc, "errors": errs})
            print(f"    baseline -> {st} len={ln} loc={loc[:34]} errs={errs}")
            for field in ids:
                for label, value in (("foreign", foreign.get(field)), ("random", RANDOM_ID)):
                    if not value:
                        continue
                    st2, ln2, loc2, errs2, _ = fire(s, args.base, page, form, {field: value})
                    rows.append({"page": page, "form": i, "mode": f"{field}={label}",
                                 "status": st2, "len": ln2, "location": loc2, "errors": errs2})
                    verdict = ("REJECT" if errs2 else
                               "REJECT? (verify oracle + positive control)" if st2 in (200, 303)
                               else "UNTESTED")
                    print(f"      {field}={label:<8} -> {st2} len={ln2} loc={loc2[:26]} "
                          f"errs={errs2} :: {verdict}")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\n{len(rows)} probes -> {out}")
    print("Reminder: pair every REJECT with (a) a positive control on an owned id and (b) an "
          "independent oracle (ledger/account export). A no-op is only a rejection if the same "
          "action provably works on an owned object.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
