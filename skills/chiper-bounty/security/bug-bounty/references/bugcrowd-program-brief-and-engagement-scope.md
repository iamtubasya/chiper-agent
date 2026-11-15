# Bugcrowd program brief & engagement scope — unauthenticated extraction + test-account setup

Load this when a task names a Bugcrowd engagement URL (e.g. `bugcrowd.com/engagements/<slug>`)
and you need the real scope/rules/reward table before testing. Owner rule still holds: get scope
FIRST, then hunt. Do NOT default to "allow-all".

## 1. The engagement page is a SPA — the brief JSON is NOT in the HTML
`curl https://bugcrowd.com/engagements/<slug>` returns a ~114KB React shell. Stripping tags yields
~77 chars. The brief is fetched client-side from the changelog endpoint.

## 2. Recipe (works unauthenticated)
1. Pull the brief/changelog UUID out of the page's embedded API map:
   ```
   curl -s "https://bugcrowd.com/engagements/<slug>" \
     | grep -oE 'changelog/[0-9a-f-]{36}'
   ```
   (The SPA HTML contains `"engagementBriefApi":{"getBriefVersionDocument":"/engagements/<slug>/changelog/<uuid>"}`.)
2. Fetch the brief — **the `.json` suffix is mandatory**. Without it the endpoint 404s
   (`{"errors":[{"detail":"Not found"}]}`); with it you get the full brief:
   ```
   curl -s "https://bugcrowd.com/engagements/<slug>/changelog/<uuid>.json" \
     -H "Accept: application/json" > brief.json
   ```
3. Parse it:
   - `data.brief.description`  → the whole "General Program Rules" text (UA/account rules, forbidden actions)
   - `data.brief.targetsOverview` → the Out-of-Scope list (host patterns AND excluded vuln classes)
   - `data.brief.safeHarborStatus` → safe harbour text
   - `data.scope` → array of target GROUPS: `name`, `inScope`, `rewardRange{p1MaxCents..p4MaxCents}`,
     `rewardRangeData` (dollars `{1:{min,max},...}`), `targets[]{uri, category, tags[]}`
4. Free public extras (GET, no auth): `/engagements/<slug>/statistics`
   (`rewardedVulnerabilities`, `averagePayout`, `validationWithin`) and `/engagements/<slug>/scope_ranks`.

## 3. Gotchas
- `web_extract` cannot handle Bugcrowd (the `ddgs` backend is search-only) → use curl or the browser.
- Reward numbers are in CENTS (`p1MaxCents: 500000` = $5000); use `rewardRangeData` for dollars.
- Some `targets[].uri` are empty → fall back to `targets[].name` (free text, e.g.
  "Localized versions of www…", or OOS rows like `*.bokun.eu`).
- The scope is VENDOR-DEFINED. Read BOTH the host list AND the excluded vuln CLASSES. Programs
  commonly exclude: missing security headers, DoS, social engineering / open redirect, mass account
  creation / spam, attacks on AI systems, physical access, and specific product areas (marked
  "temporarily out of scope"). Reporting those wastes a submission.
- Rules that gate EVERYTHING (live in `brief.description`): a required identifier in the User-Agent
  (e.g. the string `bugcrowd`), account/display names must contain a program token, test-properties
  only, never touch live customers/properties, no DoS.

## 4. Test-account setup under program rules (worked example: Tripadvisor)
Programs that need authenticated testing require an account whose identifiers satisfy the rule.
For Tripadvisor: email + display name must contain `bugcrowd` (e.g. `RESEARCHER_BC_EMAIL`,
name "Bugcrowd Test"). The Bugcrowd ninja alias `RESEARCHER_BC_EMAIL` forwards to the
researcher's real inbox.

Drive sign-up with a REAL headful browser over CDP — WAFs (DataDome etc.) block curl/headless-ish
clients. Two things that matter:
- **Chrome-on-the-configured-port**: Hermes browser tools may point at Camofox even when
  `browser.cdp_url` is set. Check `config.yaml` for `browser.cdp_url` (e.g. `ws://localhost:9222`),
  launch Chrome yourself on THAT port + a dedicated `--user-data-dir`, and drive it with
  `browser_cdp` (`Page.navigate`, `Runtime.evaluate`, `Input.*`) as long as `browser_navigate`
  insists on Camofox.
- **Legacy form-fill caveat (MooTools, e.g. Tripadvisor)**: a JS value-setter + synthetic
  `input`/`change` events is REJECTED (throws inside the site's own JS). Also the DOM often has
  DUPLICATE element ids — a container `<div id="regSignUp.password">` and the inner
  `<input id="regSignUp.password">` share the id, so `getElementById` returns the DIV (its `.value`
  is just an expando you set on a div). Fixes:
    - target the real control: `document.querySelector('input[id="regSignUp.password"]')`
    - focus it, then type with `Input.insertText` (real input events the app's handlers accept)
    - click with `Input.dispatchMouseEvent` (mouseMoved → mousePressed → mouseReleased)
    - re-read the real inputs after each step; never trust a setter's return value.
- A VISIBLE reCAPTCHA Enterprise checkbox is not necessarily enforced at submit (Tripadvisor
  sign-up succeeded without solving it). Try the submit before assuming it blocks — but do NOT
  claim "CAPTCHA bypass" as a finding; mass account creation is usually OOS and score-based
  Enterprise frequently passes a genuine headful browser.
- After creating a test account, log the state change (email/name/profile URL/password) in the
  engagement log and disclose it. Keep the account "bugcrowd"-labelled so the vendor can clean up.

## 5. Deliverable staging (owner workflow)
Bugcrowd takes submissions through the WEB FORM (`/engagements/<slug>/submissions/new`), not email.
Owner's staging workflow: put the FINISHED deliverable in a **Gmail draft**
(IMAP `[Gmail]/Draf`, `APPEND` with `(\Draft)`). Requirements he enforces (he rejected a draft that
had the report text but no PoC PDF — *"draft gmail tidak ada pdf poc-nya, harusnya kamu lengkapi
semua baru lanjut"*):
- **Complete it in one pass.** Do not close a deliverable half-built — the report text AND the PoC
  PDF must be attached in the SAME action before moving on to further hunting.
- **Attach the PDF PoC**, not just inline text. Generate it (reportlab) with: a meta table
  (asset / category / priority / CVSS 3.1 / auth required), summary, numbered repro, raw
  request + response, a screenshot of the live endpoint, representative body excerpts, impact,
  remediation, and an evidence/hygiene list.
- **Replace, don't duplicate.** Search `SUBJECT "..."` → `store \Deleted` → `expunge` the prior
  same-topic draft so there is exactly ONE, then re-verify the new draft over IMAP with an
  `RFC822` fetch (check filename + content-type + byte size of the attachment actually landed).
- **Say plainly that the mail draft does not submit the report** — it is a staging container.
- For a request/response PoC (e.g. an open metrics endpoint) a headless screenshot works:
  `chrome --headless=new --screenshot=out.png --window-size=1280,1000 <url>`. Verify it before
  embedding: non-uniform pixels (`PIL` unique-gray check) and `--dump-dom` showing the real body.

## 6. Reporting note
Bugcrowd submissions go through the platform web form, never email. If the user asks to stage the
report in a mail draft, that draft is a STAGING container only — state this explicitly.
