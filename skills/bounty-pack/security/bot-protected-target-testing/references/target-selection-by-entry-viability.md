# Target selection by ENTRY VIABILITY — screen before you spend the engagement

Written 2026-10-13 after three consecutive engagements (apnic.net, coderabbit.ai, lecturio.com)
burned a full session each on surfaces that could never produce a reportable finding: WAF-thick
estates, SPA catch-alls, and apps whose only entrance was an invite. Total findings: 0. The cost
was not the testing — it was choosing targets whose *door* was shut before any test began.

This is a **pre-0A screen**, not a substitute for recon. It answers one question in ~2 minutes per
candidate: *if I find something here, can I actually reach it without an invitation?*

## Why it is needed

The operator's bar (verbatim): status codes are **not** findings. A report needs hard impact —
data actually retrieved (PII / user list / token / record), a proven IDOR/BOLA (another party's
object), RCE, or a demonstrated negative business-logic outcome. Therefore a target where every
path returns 403/401/challenge **cannot yield a report**, no matter how long you test it. Screen
that out at selection time.

## The screen (per candidate domain)

```python
SIGNUP = ["/register", "/signup", "/sign-up", "/users/sign_up", "/auth/register", "/auth/signup",
          "/account/register", "/create-account", "/join", "/get-started", "/trial", "/api/register"]

# for each of SIGNUP: GET it, then classify the SAME page by SIZE against the shell
```

Three signals, all cheap:

1. **Shell size as the baseline.** GET `/` and record `size_download`. Then any path whose response
   size is within a few bytes of it is **the SPA shell**, not a page. Verified repeatedly:
   `bcap` 606 B for every path including `/api`, `/swagger-ui.html`, `/actuator/health`;
   `mel.qawolf` 14 654 B for `/api/subscriptions`, `/version`, `/healthz`; `app.lecturio.com/api/*`
   9 331 B for every unknown API path. **Identical size across many paths = catch-all, discard it.**
2. **A real form.** `type="password"` present (or `<form>` containing email+password) on a
   *registration* path. A 200 with the shell does not count.
3. **Edge posture + method policy.** Record `Server`, presence of `CF-Ray`/`cf-mitigated`/
   `X-Amz-Cf-Id`, and — critically — whether **POST is allowed at all** (see the method-keyed wall
   in SKILL.md §2g). A host that 403s every POST is not an entrance.

## The three outcomes, and what each means

| Outcome | Reading | Action |
|---|---|---|
| Real registration form, POST accepted, no CF on that host | **entrance exists** — self-provision a test account and test from inside | worth the engagement |
| Real form but POST 403 (CDN method policy) | entrance exists **on a sibling host** — go find the non-CDN member of the estate | worth it *if* the sibling accepts POST (verified: `app.<target>` did while `www.` did not) |
| Every path = shell size, or every POST = 403, or registration invite-only | **no entrance** | skip; do not run 0A–0F |

## Verified false positive — a login page counts as a "form"

The password-field heuristic fires on **login** pages too. One candidate (`myshippilot.com`) was
recorded as having an open signup because `/signup` returned a page with a password field — it was
the login form. Before calling a registration path open, confirm the page actually offers account
creation (look for a confirm-password / terms-acceptance field, or a "create account" heading), not
just a credential field.

## Verified dead ends — do not re-argue these

- **Invite-only apps have no self-service entrance.** `mel.apnic.foundation` was a real API with
  real auth (401 not 403) and `/api/users`, `/api/projects`, `/api/audit-logs` all present — but
  every invite token answered `400 "Invalid or expired invite link"` and no registration route
  existed. An API you cannot obtain a session for is a coverage gap, not a target.
- **A leaked Keycloak `master` realm is usually not a finding.** `bcap.apnic.foundation` exposed
  `/auth/realms/master/.well-known/openid-configuration` plus the admin console login page, with no
  WAF. Every admin REST path then answered `401`, and anonymous client registration was refused by
  policy (`403 insufficient_scope … Policy 'Trusted Hosts' rejected`). Every Keycloak deployment
  answers OIDC discovery for `master`; that is by design, not a finding. Test the *admin REST* and
  the *registration policy*, not the discovery document.
- **`Welcome to nginx!` / default pages are unconfigured infra**, not a host with an app.
- **A "Build incomplete" 404** on a deploy host (Cloudflare) is a broken deploy, not an entrance.
- **`403 Just a moment…` with CF headers** = challenge; only a real Chrome over CDP resolves it
  (§2g), and if a full restart does not clear the stealth browser, go straight to Chrome+CDP.

## Honest limits of this screen

Passing the screen is **necessary, not sufficient**. Lecturio passed (real signup form on a
non-CDN host, reachable login page) and still produced 0 findings inside the time budget — the open
door led into a Clerk-gated SPA whose API paths were computed at runtime. An open door buys you the
*chance* at IDOR/BOLA/business-logic; it does not promise one. Say that to the operator rather than
implying the screen predicts success.

## Operating notes

- Screen **many candidates in parallel** (a thread pool over the pool's `pick` output), then run
  0A–0F on the one that passes. Screening 120 domains took ~10 minutes wall-clock and prevented
  three more blind engagements.
- Prefer candidates whose program terms are worth the finding. A program capped at €50/report
  (lecturio.com's published cap) changes the cost/benefit of a hard finding — surface that number to
  the operator **before** committing, not after.
- A candidate with `Server: cloudflare` on *every* host and no non-CDN sibling is a poor bet; the
  ones worth taking usually have a legacy/nginx host that answers differently from the CDN apex.
