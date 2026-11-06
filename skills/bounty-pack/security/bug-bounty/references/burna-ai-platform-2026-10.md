# Health-AI platform with a published VDP — authorization, surface expansion, split-plane API

Worked case: a clinical-research AI platform (2026-10). Reusable shape for any target that
publishes a VDP with a safe-harbour clause.

## 1. Authorization preflight (do this before any probe)
- `/.well-known/security.txt` -> `Contact: mailto:security@…`, `Expires`, `Policy: /responsible-disclosure`.
- Read the policy: **scope** (named hosts + "the APIs behind these services"), **out-of-scope** list
  (scanner output without PoC, best-practice-only, social engineering, DoS, spam, physical), and the
  **safe-harbour** sentence ("we will not pursue legal action against researchers acting in good faith").
- A *different owner* for a sibling domain (e.g. a foundation) = OUT, even when the brand matches.
- Policy that says "create accounts where needed" is the authorization to self-register; use your OWN
  inbox for OTP.

## 2. Surface expansion via Certificate Transparency
`certspotter` (`?domain=<d>&include_subdomains=true&expand=dns_names`) reveals the real map:
`staging.*`, `app-v2.*`/`agents-v2.*`, `logs*`, `evidence.*`, `comp.*`, `synthea.*` (synthetic-patient
generator), `uploads.*`, `public-*-media.*`. Then classify each (DoH A/CNAME + Cloudflare vs origin IP).
Highlights worth reporting as *hardening* (not standalone vulns under a "no best-practice" clause):
- staging hosts answering **200 with the full app** and the **same auth stack as prod** — exposure.
- `evidence.*` behind **Cloudflare Access** (Zero Trust) = good control; say so.
- Dead Railway hostnames ("Application not found") after a DNS record lingers — record, don't chase.

## 3. Split-plane architecture (the key discovery)
The UI is Next.js App Router. Recording XHR while the authed UI loads reveals THREE hosts:

```
app.<t>    UI + Server Actions          (mutations; POST to page + `next-action` header)
api.<t>    control plane REST           auth = better-auth session cookie (__Secure-better-auth.session_token, .<t>)
agent.<t>  data plane REST              auth = short-lived Bearer JWT
```

- The JWT is minted by a Server Action literally named **`getAuthToken`**; capture the header off any
  data-plane request. Decode it: `iss=api.<t>`, `aud=control-plane`, `iat/exp` ~ **5-minute TTL**,
  claims `sub`,`email`,`activeOrganizationId`,`activeMemberRole`,`hasPassword`. Pinned org + short TTL
  = hardening, not a bug.
- **Reads are GET; writes 404** on the REST API (`POST /api/trials` -> 404 while GET is 200). Creation
  lives in Server Actions — create via the UI, list via REST.
- IDOR probe that fits: swap the tenant id in a control-plane read
  (`/api/auth/organization/list-members?organizationId=<other>`) -> explicit
  `403 {"code":"YOU_ARE_NOT_A_MEMBER_OF_THIS_ORGANIZATION"}` vs own org `200`. The boundary held.

## 4. Enrollment-token design (their stated #1 priority) — result: hardened
Feature: "PRO enrollment" issues a token a patient uses in a check-in portal, no account needed.
Issued one in an own workspace and inspected it:
- Format `pro_` + 32 hex = **128-bit** random -> not guessable/enumerable.
- Server stores only the **sha256 hash**; API returns `hashedToken` + `tokenSuffix`, never the raw.
  Raw shown once in the UI, masked afterwards (`•••• •••• C086`); 30-day expiry; revoke/re-issue; audited.
- Observations worth a LOW/INFO mention, not a finding: `maxUses = 0` (meaning unclear), token issued
  with `studySiteId=null` / `visitWindow=null` (not site/window-bound).
=> "guess or forge the enrollment link" was NOT feasible. Report the negative as a positive control.

## 5. Entity-setup automation pitfalls (cost real cycles)
- **Python slicing is not JS.** In `page.evaluate`, `e.textContent.trim()[:28]` -> `SyntaxError:
  Unexpected token ':'`. Use `.slice(0,28)`.
- **A required base-ui combobox blocks submit CLIENT-SIDE, with NO POST.** The create dialog showed an
  inline "Say which CTCAE publication this trial grades to" and zero network requests. The native value
  setter does not drive `[role=combobox]`. Drive it like a user: click the trigger, click the option in
  the **portal** (`[role=option]`), re-query the combobox list after each pick (indices shift), press
  `Escape` if a listbox lingers (a stale overlay makes the next `.click()` time out "not visible").
  Verify the trigger text changed, then wait for the first POST as proof.
- **Registrations/sign-in are self-serve** on both the platform and the CTCAE sub-app; read the OTP from
  your OWN inbox via the `google-workspace` skill's `gmail search "from:<domain> newer_than:5m"`.
- Headless Playwright + `storage_state` persisted a full session across many script runs — the cheapest
  way to keep an authed engagement moving.

## 6. AI-feature negative (record it, don't overclaim)
The assistant had many tools (CTCAE grading, drug label, guideline, PubMed, trials). Direct prompt
injection, SSRF-via-tool (metadata + localhost), cross-org record listing, and tool enumeration were
ALL refused, and a conversation-ID IDOR returned the app shell with no leaked content. Under the
`hunt-llm-ai` false-positive gate this is "guardrails hold" — a credible negative, not a finding.
