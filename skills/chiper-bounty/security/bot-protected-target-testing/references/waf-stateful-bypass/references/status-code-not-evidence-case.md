# Worked example — "a status code is not evidence" (2026-10, RIR estate)

Engagement: a regional internet registry's bug-bounty VDP (monetary, safe-harbour, 7-day ack SLA).
Operator pushed back three times, escalating, that status codes are not deliverables. This file records
what the refusals actually looked like so a future session can recognise the shapes fast.

## 1. The all-403 apex (edge-keyed)

```
blog.<target>   /wp-json/wp/v2/users     403   121 B
blog.<target>   /wp-json/                403   121 B
blog.<target>   /wp-json/wp/v2/posts     403   121 B
blog.<target>   /xmlrpc.php              403  4569 B   (WAF page)
blog.<target>   /wp-config.php.bak       403  4569 B
www.<target>    /wp-json/wp/v2/users     429  5663 B
api.<target>/                            403     0 B   Server: Envoy
```

Read: 121 B uniform bodies = edge rule, not the app. The `429` = rate limiter. Neither tells you
anything about WordPress, the plugin set, or the API behind it.

**The CMS was identifiable by fingerprint** (`WordPress 7.1.2` on the blog host, `6.9.9` on www, via
`httpx -tech-detect`) — but a version banner is a CVE-lookup prompt, not a finding, and the REST routes
that would confirm anything were all edge-blocked. Correct outcome: journal it, don't report it.

## 2. The challenge path that proves it's IP-keyed

```
GET /cdn-cgi/challenge-platform/h/b/orchestrate/chl_page/v1?ray=...   200   237,555 B
GET /cdn-cgi/challenge-platform/h/b/orchestrate/managed/v1?ray=...     404          0 B
```

A `200` here is Cloudflare's own challenge orchestration page, not target data. Combined with a
stealth-browser tab-open that returned `503` on a freshly-restarted stealth server (killing and
relaunching the browser tree changed nothing), the conclusion is **IP/edge-keyed**: no fingerprint,
TLS, or UA work will pass it. Say that plainly and stop.

## 3. The SPA catch-all that fakes N routes

```
bcap.<sibling>/                     200  606 B  nginx/1.24.0 (Ubuntu)
bcap.<sibling>/api                  404    0 B
bcap.<sibling>/actuator/health      200  606 B
bcap.<sibling>/login                200  606 B
bcap.<sibling>/swagger-ui.html      200  606 B
bcap.<sibling>/v3/api-docs          200  606 B
```

Five paths "exist" with the **identical byte length**. That is one client-side route fallback, not five
endpoints, and none contains data. Real routes are in the JS bundle. Before this was noticed, the `200`s
looked like surface.

## 4. The sibling domain that was actually testable

The whole apex was WAF-gated, but the policy's in-scope list named four more registrable domains. One
of them ran an **un-WAF'd, auth-gated app**:

```
GET  /api/users           401  {"message":"Unauthorized"}     <- route EXISTS, authz works
GET  /api/projects        401  {"message":"Unauthorized"}
GET  /api/audit-logs      401  {"message":"Unauthorized"}
GET  /api/notifications   401  {"message":"Unauthorized"}
GET  /api/edit-requests   401  {"message":"Unauthorized"}
GET  /api/auth/me         401  {"message":"Unauthorized"}
GET  /api/v1, /api/docs   404  {"message":"Cannot GET /api/v1"}
```

The `404` vs `401` split is the map: it separates route families that exist from ones that do not, and
it says the authz layer is real. The testable surface is the one **behind the auth boundary**, reached
with a session — not the one behind the WAF.

Route names came from the 1.65 MB SPA bundle, not from guessing:
`/admin/users`, `/admin/audit-log`, `/admin/edit-requests`, `/superadmin/documents`,
`/superadmin/mel-config`, `/lead/learning` — plus the auth API (`/auth/login`, `/auth/me`,
`/auth/forgot-password`, `/auth/reset-password`, `/auth/invite/<token>`) and data endpoints
(`${base}/uploaded-documents/${id}/download`, `${base}/projects/${id}`, `${base}/reports/${id}`).

Note the paths are **unprefixed** on the front end (`/auth/login` 404s as a GET because it's POST-only;
`/api/auth/login` also 404s) — a scanner that only tries `/api/...` misses the whole auth surface.

## 5. The artifact that LOOKED obtainable — and was disproved by its own control (retracted)

Initial read (single probe, wrong):
```
POST /api/auth/forgot-password {"email":"<random>"}      400 {"message":"Email does not exist"}
```
That looked like a **differential oracle** — "a registered address must produce a different response".
It is NOT one. The follow-up control run (the one this file's own caveat demanded) killed it:

```
15 addresses, 2 obviously fake + 13 plausible-real (csirt@, helpdesk@, info@, admin@,
mel@, test@, demo@ on the apex; grants@, info@, admin@ on the sibling; alumni@ on another sibling)
→ unique bodies: 1   unique statuses: [400]   unique lengths: [34]
→ every single one: {"message":"Email does not exist"}
VERDICT: NO ORACLE — generic anti-enumeration message, working as intended.
```

**The rule this buys you: an enumeration oracle cannot be demonstrated with negative controls only.**
Without a POSITIVE control (an address you have *confirmed* exists — your own freshly-registered
account on that app), you cannot distinguish "app reveals existence" from "app returns one uniform
message to everyone". Here the app was doing exactly the right thing, and 13 addresses that very
plausibly *were* real all produced the identical string. That is the **third** variation of the
false-positive family in this file (uniform 403 = edge, uniform 200 = SPA fallback, uniform 400 =
no oracle).

Honest handling when you catch this late: **retract explicitly** — state the hypothesis, state the
counts that refute it, name it as a retraction in the report/appendix. Do NOT quietly drop it, and do
NOT ship it with "may allow enumeration" hedging. (Retraction entry pattern lives in `triage-validation`
→ RETRACTION DISCIPLINE.)

Two probes that DID stand, as negative results done right:
```
POST /api/auth/login    {"password":"x"}    400 {"message":"password must be longer than or equal to 6 characters"}
POST /api/uploaded-documents/1/download     401 Unauthorized        <- NOT IDOR
POST/GET /api/auth/invite/{1,test,abc123,<zero-uuid>}   400 {"message":"Invalid or expired invite link"}
```
The guessed sequential ID against a real data endpoint was refused → nothing obtained → nothing
reported. The invite route is uniform across valid-shaped and junk tokens, and self-registration is
**not** open, which also means the "register an account and hunt from inside the auth boundary"
step below is genuinely unavailable on this app (its own login contract showed the same on the
sibling environment — staging was behaviourally identical to prod, with no debug/seed/demo endpoints).

## Transferable checklist

1. Uniform tiny `403` across unrelated paths → edge. Don't report, don't call it "hardened".
2. `200` of identical length on unrelated paths → SPA fallback. Don't count it as surface.
3. Find the challenge path; if it `200`s with JS, the block is IP-keyed → change egress or move on.
4. Enumerate **every** in-scope registrable domain, not the apex. The un-WAF'd sibling is the target.
5. On the reachable app, read the JS bundle for route names; probe `404` vs `401` to build the map.
6. Register an account where self-registration exists — the auth boundary is the hunt, not a blocker.
7. Report only what you can name as obtained. Everything else is a journal entry.
