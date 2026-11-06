# DeFi Web Static-Surface Sweep — Hardened-Target Playbook & Negative-Verdict Discipline

Source: CapyFi hunt (Sept 2026). Cloudflare-fronted Next.js/RSC app + SIWE auth +
fiat-ramp proxy (Ripio) + legacy promo API. Result: surface hardened, zero reportable
findings. This file captures HOW to sweep a Web3 frontend to a defensible "nothing"
verdict, and the false-positive traps that nearly produced bogus reports.

## The 7-step sweep (all static, no browser)

1. **Subdomain inventory + takeover check.** Enumerate all subs, resolve each, and
   inspect CNAMEs. A dangling CNAME → claimable resource = real finding.
   Watch out: an S3-style name with NO DNS record (e.g. `awsorg.…`) is NOT claimable —
   takeover needs a live CNAME pointing at an unprovisioned resource. Dead subs with
   responses (403 from CF, empty stub pages) are noise.
2. **Landing/CTA link-graph to find the REAL dapp.** Marketing stub pages often have no
   app. `grep -oE 'href="[^"]+"' page.html | grep -vE 'css|font|ico|\.js|socials'` —
   if the "open vault" button links to mirror.xyz/x.com, the vault is vaporware; the
   actual app lives on `app.*`. Don't waste time attacking a stub.
3. **SIWE/auth flow verification (before claiming auth bugs).** Check: nonce cookie is
   HttpOnly+Secure with short TTL (~10m); verify endpoint binds nonce→session; JWT is
   HS256 with strong secret (test top-100 secret list); `alg:none` rejected. If all pass
   → auth is solid, stop pushing.
4. **IDOR candidates: prove parameter influence BEFORE claiming.** The classic trap:
   `/api/user/email?address=<victim>` returning 200 looks like IDOR. It is NOT unless
   the response CHANGES with the injected value. Correct test: request with own session +
   foreign address param; if server ignores the param and returns session-owner's email
   → parameter is cosmetic, no vuln. Same for ramp `address` params (prefill-only).
5. **Write-path location via method probing.** POST/PUT on a read API returning **405**
   means the web API is read-only and mutation is on-chain (contract `createCampaign`
   etc.). That is architecture, not a broken-access-control finding. Then audit the CHAIN
   instead (see onchain-cast-recon.md) — don't file "missing authorization" on a proxy
   that has no writes.
6. **Session-bound proxy tokens (fiat ramps).** Third-party ramp integrations (Ripio etc.)
   behind the app: verify the upstream token is bound to a server-side session hash, not
   client-controllable, and endpoints 401 unauthenticated. If yes → clean, move on.
7. **Hygiene greps.** Source maps published? (usually cleaned). `.env`/admin/config paths
   (expect CF 403 — noise, not findings). NextAuth endpoints when app uses SIWE (absent).
   Open redirect on callback/returnTo params. Legacy/decommissioned promo endpoints may
   still answer 200 — if the business logic they trigger is expired/no-op, format
   validation only = INFO.

## By-design / INFO floor (do NOT report these)

- 7-day session JWT + free self-registration → cheap account farming. No financial
  impact = not reportable.
- Public Sentry DSN. By design.
- Expired promo endpoints that validate input format. By design-ish, INFO.
- Cloudflare blanket 403s on guessed paths. Noise.

## Negative-verdict discipline (the actual deliverable)

When the sweep is clean, the report is a **structured honest summary to the operator**,
not a PDF:
- List every class tested with ✅/⚠️ and one-line evidence per class
  (SIWE, IDOR, takeover, auth, ramp-proxy, redirects, leaks, campaign API).
- Name the residual surface that static methods can't reach (XSS in RSC hydration,
  TON mini-app initData flow, stored injection via binding forms) and ask before
  escalating to interactive browser work — probability vs cost decision, operator's call.
- NEVER write "no findings without trying everything" as failure — persistence rule
  says pivot to infra (S3, pre-prod, JS bundles, third-party APIs), and this sweep IS
  that infra pass. Once infra is exhausted + chain audit done, a clean "0 reportable"
  is a legitimate, complete outcome. Severity inflation is OMONG KOSONG; a fabricated
  LOW burns researcher reputation on platforms where dedup/triage is human.

## Quick commands

```bash
# CTA/link-graph extraction from saved HTML
grep -oE 'href="[^"]+"' page.html | grep -viE 'css|font|ico|\.js|twitter|github|discord|telegram' | sort -u

# Dangling-CNAME triage: for each sub, dig CNAME then check target exists
dig +short CNAME sub.<target>; curl -so /dev/null -w '%{http_code}' http://<cname-target>

# IDOR param-influence test (own session, foreign param)
curl -s -H "Authorization: Bearer $MY_JWT" "$BASE/api/user/email?address=0xVICTIM"
# → if identical to no-param request: server ignores param, NOT IDOR.
```
