# MFA controls, calculation-engine oracles, and a real tool sweep

Condensed from a Pro-plan follow-up engagement (same target as
`quarterwise-vdp-case-2026-09.md`), covering the areas the vendor asked to be tested:
public API (rate limit + idempotency), receipt capture, document storage, AI categorisation,
foreign tax credit, accruals vs cash basis, section 24 finance costs, ownership shares, and
capital gains on disposal.

---

## 1. MFA / 2FA — what was tested and what held

Enrolled TOTP on the test account (secret read from the enrollment page, codes generated with
pyotp, a small helper `totp_helper.py` printing `current_code()` + `seconds_left()`).

| # | Test | Result |
|---|---|---|
| 1 | Half-auth session (password ok, code pending) → `/app`, `/app/account` | 307 → `/login` |
| 2 | Empty code submit | rejected client-side, no message leakage |
| 3 | Wrong code | "That code is not correct. Try the current code from your authenticator app." |
| 4 | "Turn off authenticator" with wrong code | refused, 2FA stayed on; copy: "Enter a current code from your authenticator app to turn 2FA off." |
| 5 | Tax-ID (NINO) save with wrong code | stored value unchanged |
| 6 | 5 wrong codes | lockout: "Too many attempts. Please wait about 15 minutes and try again." |
| 7 | Account-level? | YES — fresh login + CORRECT code still refused during the window |
| 8 | Does it expire? | YES — normal login succeeded ~15 min later |
| 9 | **Replay: one code on two logins in the same 30s window** | login #1 accepted, login #2 with the same code refused → replay prevented |
| 10 | Recovery (`/login/mfa/recover`) | "this takes 24 hours, and we'll email you first so you can stop it if it wasn't you" — left unpressed to avoid starting the timer |

Method note worth repeating: the first replay attempt reused a code for a *data-entry* action and
looked like it was blocked — but the real rejection was the identifier checksum (NINO suffix must
be A–D; `AB123456E` is invalid). The raw RSC segment gave it away:
`1:{"error":"Enter a valid National Insurance number, e.g. QQ123456C."}`. The clean replay test is
two full logins with one code.

Expectation gap reported to the vendor: while the login was locked out, `/api/v1/me` and
`/api/v1/sources` still returned 200 with the API key — MFA protects interactive login, not the
API. Also: enabling 2FA did **not** invalidate pre-existing API keys.

Account-takeover chain tested separately: changing the account email requires current password +
TOTP + a code sent to the NEW address (double opt-in: "your address only moves once you enter that
code"); changing the password requires current password + TOTP. So a stolen session alone cannot
move or take over the account. By contrast, **deleting a property permanently required no code**
(destructive action, inconsistent with the credential flows) — hardening note.

---

## 2. Calculation-engine oracles (tax figures)

Estimate panel wording that made it a usable oracle:
`Total income / Total expenses / Net profit / Profit / Taxable / Finance costs relief (20%) /
Tax deducted at source / Estimated tax still to pay / Top rate`.

Recipes that produced clean results:

- **Single-variable isolation for a comparison bug.** Property A: rent £30,000, mortgage interest
  £2,000, repairs £50 → panel said *"Your actual expenses (£2,050.00) beat the £1,000 property
  allowance, so we've used those"* and returned taxable £17,380. The £2,050 counted the £2,000 of
  finance costs, which are no longer deductible expenses (they are a 20% tax reducer), so they
  should not displace the £1,000 allowance. Adding £1 of interest vs £0 flipped the treatment:
  a 1-unit delta proving an operator bug. Effect: taxable £1,000 too high (~£200 basic rate,
  ~£450 at 45%), and the app's own copy claims "we've used whichever saves you more".
- **Impact proof via before/after on the figure that matters.** Fabricated "tax withheld" entries
  (created through the paths below) drove the panel from `Estimated tax still to pay £11,227.77` to
  `£0.00`; deleting only those entries restored it. Screenshots of both states are the impact
  evidence.
- **Serve the same ledger through every write path.** The vendor's fix for a category/amount
  coupling held on the add form and on form edit (both refused), but the category was still
  accepted via (a) the import mapping dropdown — reachable on the FREE plan, (b) the public REST
  API (`201 created` on a UK property, while other invalid keys returned `422 invalid_category`),
  (c) the AI review-queue dropdown (offered `Tax withheld from rent`; confirm could not be made to
  apply anything, even a legitimate category, so it stayed "unverified"), and (d) an edit/delete
  path that orphaned the dependent entry (delete the rent entry → the withheld credit survives and
  stays in the totals).
- **Verify the marketed capability is actually reflected.** The FAQ said recording foreign tax
  lets you "claim Foreign Tax Credit Relief"; the ledger recorded it as "not income" but the
  estimate had no credit line at all, and the foreign property's own XLSX export labelled it
  "Tax withheld at source (paid to HMRC for you…)" — wrong authority. Reported as a question with
  the cap rule quoted (relief limited to the lower of foreign tax paid and UK tax on that income).

HMRC rules used as the yardstick (quote these in reports): property allowance is an alternative
to deducting actual expenses; s.24 finance costs are relieved as a 20% basic-rate reducer and are
not deducted; cash basis is the default for property receipts ≤ £150,000 (PIM1092); FTCR is capped
at the lower of foreign tax paid and UK tax on that income (HS263); residential CGT 18%/24% with a
£3,000 annual exempt amount and 60-day reporting.

---

## 3. Tool sweep — commands and outcomes

```bash
# route discovery (authed)
ffuf -u https://TARGET/api/v1/FUZZ -w api_words.txt -H "Authorization: Bearer $KEY" \
     -H "Accept: application/json" -rate 20 -ac -o ffuf_api.json -of json
ffuf -u https://TARGET/app/FUZZ   -w app_words.txt -H "Cookie: $COOKIE" -rate 15 -ac

# hidden params
arjun -u https://TARGET/api/v1/sources/$ID/transactions -m GET \
      --headers "$(cat authhdr.txt)" --headers "Accept: application/json" -t 5

# templates (background, local dirs)
nuclei -u https://TARGET/api/v1/me -H "Authorization: Bearer $KEY" \
       -t ~/nuclei-templates/http/misconfiguration -t .../http/exposures -t .../http/technologies \
       -rl 10 -c 10 -timeout 12

# injection
sqlmap -u "https://TARGET/api/v1/categories?sourceType=uk-property" \
       --headers="$(cat authhdr.txt)" --level=3 --risk=2 --technique=BEUST --batch
dalfox url "https://TARGET/app?view=mine" --cookie "$COOKIE" --no-spinner
trufflehog filesystem app_recon/js2 --no-update
wafw00f https://TARGET ; naabu -host TARGET -top-ports 100 -rate 60 -silent
```

Outcomes on a hardened Next.js + Cloudflare target:
- ffuf: only documented endpoints (`/api/v1/{me,sources,categories,openapi.json}`); `/app` had no
  hidden routes. `openapi.json` itself served without auth (informational).
- arjun: "No parameters were discovered" on both endpoints (103 chunks each).
- nuclei (2,597 templates × API + site, 100% complete): INFO only — missing COEP and
  X-Permitted-Cross-Domain-Policies, CSP `'unsafe-inline'` in script-src, Cloudflare tech-detect.
- sqlmap: `sourceType` not injectable; `User-Agent` was flagged injectable then self-disproved;
  final `[CRITICAL] all tested parameters do not appear to be injectable`, with `403 (Forbidden) -
  3742 times` recorded as the WAF coverage caveat.
- dalfox: ran (5,536 queries); output only `Reflected ... param` lines from RSC flight echoes.
- trufflehog: 68 chunks / 777 KB, 0 verified, 0 unverified secrets.
- wafw00f: Cloudflare; naabu: 80/443 open (8080/8443 answer via the CDN).
- `gau`/`waybackurls`: no historical footprint. `katana -d 3 -jc` surfaced two public endpoints:
  `/api/og/{id}/{base64}.png` (needs a valid id — every probe 404, oversized URI 414) and
  `/api/collect` (unauthenticated POST sink: 204 for small/200 KB/malformed JSON, GET 405 →
  recommend a body cap and rate limit).
- XXE via XLSX import: external entity injected into `sharedStrings.xml` and the worksheet, OOB
  listener attached → no callback, and the DTD-bearing file was rejected before preview (weak
  negative: the doctype root name in the payload was wrong; a clean XLSX imported fine).
- `commix` on this host turned out to be a stub binary, not the real tool — command injection was
  covered by the manual payload set instead (all `422`).

---

## 4. Engagement hygiene on a vendor-granted account

- Rules given by the vendor (repeat them back in the report): no connecting the tax authority, no
  submitting anything to it; test data removed afterwards.
- 2FA enrolment on a borrowed account locks the owner out unless you hand over the secret — ask or
  restore it at the end.
- Do not fill a documented daily write cap (observed cap: 5,000 transactions / 24h) — it locks the
  account's write quota for a day and would block the vendor's own testing.
- Keep a cleanup list (entries, properties, shares, identifiers, API keys) and verify the end state
  through the API, not just the UI. One imported property resisted automated deletion (button
  fired nothing) — report leftovers honestly instead of claiming a clean account.
- Record state changes in a rules file inside the engagement directory so later sessions honour
  them (e.g. `pro/RULES-HMRC-DILARANG.md`).
