# Authenticated Vector Battery — the ordered checklist (run AFTER session settle)

Once you hold a session (and prefer a SECOND account), run these tiers in order.
Every item produces an artifact or a written negative. Do not declare "authed
surface clean" until each reachable tier is walked — and never judge a single
endpoint in isolation (chain leads ≥3x before calling them dead).

## Tier 0 — Session settle + identity assert (per account)
1. Pin credentials PER INSTANCE (`self.creds = dict(CREDS)`), never a module global
   — `importlib.reload` silently switches accounts mid-run (see main skill).
2. Assert identity after every session create: `GET /me` must equal the expected id
   BEFORE any probe. A contaminated session fabricates phantom BOLA.
3. Note token TTL (`exp-iat`); bake `401 → re-login once → retry`, account-pinned.
4. Discriminate WAF/edge from app by BODY: JSON `403 {message}` = app; HTML error
   page = edge (tells you nothing about authz).

## Tier 1 — BOLA / IDOR battery (the whole point of a second account)
Seed account B with a MARKER object first (`IDORPROBE_R1`) — else every cross-user
probe reads as a false empty. Then differential:
1. Collection endpoints (`/api/users`, `/api/orders`) — swap token, diff BODY not status.
2. ID substitution per type: sequential ±1, harvested UUID (from share URL/JS/email),
   hashed (decode), composite (`orgId_resourceId` — swap one part).
3. All verbs: GET/PUT/PATCH/DELETE; POST-create with `parent_id`/`owner_id` of victim.
4. Method override (`X-HTTP-Method-Override`, `_method=`) — authz often per-verb.
5. Null-byte/array/duplicate on the id (`id[]=own&id[]=victim`, `id=A&id=B`, `%00`).
6. Export endpoints (`/export?format=pdf|xlsx`, aggregate CSV) — highest-value read, usually missed.
7. The ACK is not the oracle: re-read the victim's object from B's own page; own-object
   positive control is non-negotiable (dead session → both turn login redirect → false signal).

## Tier 2 — Function-level authz (BFLA / privilege escalation)
1. Admin-only endpoints from JS bundle/Swagger, called with a plain account.
2. Multi-step workflow: skip to the terminal step (`/orders/{id}/approve` without review).
3. Tenant overrides: headers (`X-Org-Id`, `X-User-Id`, `X-Tenant-Id`) + query
   (`accountId`, `all`, `includeShared`) — compare response LENGTH.
4. Role in body on invite/membership: `POST /teams/{id}/members {email, role:"OWNER"}`.
5. Downgrade API version (`/v1/` deprecated still live without newest authz patch).

## Tier 3 — Business logic on the money surface
Read the Terms/pricing page first — every claimed limit is a candidate bug:
1. Price/amount/quantity tamper (negative, float `1e10`, `0.001`), diff server recompute.
2. Coupon/referral: self-referral, stacking, replay-after-refund, cross-account reuse.
3. Idempotency half-2: same key + DIFFERENT body must NOT overwrite.
4. State machine: every illegal transition (draft→completed skipping paid).
5. Trial/entitlement: premium feature via API after downgrade; `data-free-order`-style flags.
6. KYC/verification gate skip: sensitive action before "approved" status.

## Tier 4 — Race / TOCTOU (parallel on the money surface)
Single-packet HTTP/2 where possible, else parallel aiohttp `gather()`. Target:
redeem, apply-coupon, invite (slot), seat-booking, withdrawal, trial-activate.
Evidence = END state (balance/kuota/ledger row), not "2× 200". Re-run 3×, fresh state;
`1,1,3` = scheduler luck → drop. (Full technique: `hunt-race-condition`.)

## Tier 5 — Session / token lifecycle battery
1. Rotation: login→refresh, is the RT value different? (expect yes)
2. Replay: restore OLD RT, refresh again — 200+fresh AT = old RT not invalidated.
3. Revocation: logout, replay EVERY captured RT — post-logout 401 = sound.
4. Scope: RT/AT from account A must not read B (differential).
5. Password-change must invalidate tokens / sessions ("tokens survive password change"
   = a real capability-gain finding).

## Tier 6 — Sensitive-data exposure (the "export is the read" rule)
1. Per-object export to FILE (`?format=pdf|xlsx|json|csv`) — often bypasses page-level authz.
2. Aggregate exports / firm/client CSVs.
3. Response-field over-disclosure: BOPLA (fields present in body but hidden in UI).
4. Authenticated file cached publicly: fetch an authed file, then SAME URL no-cookie —
   must 401/redirect, never the file (`CF-Cache-Status` + no-cookie redirect = clean).

## Tier 7 — Injection on authed input
1. Stored XSS via profile/display-name/notes (server-side escaping? re-read raw JSON).
2. File upload (SVG/HTML/svg-in-png) + filename in `Content-Disposition` (CRLF → header XSS).
3. Template/SSTI in "name templates" (invoice, email subject) — `{{7*7}}` / `${7*7}`.
4. SSRF via any "import from URL" / webhook / avatar-fetch feature → interactsh.

## Exit gate — the three-part negative (same as unauth)
1. `tested` list with COUNTS, 2. `NOT tested` naming the specific gate per item,
3. tool artifacts on disk for every class claimed clean.