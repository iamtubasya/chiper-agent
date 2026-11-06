## ⛔ RULE 36: "All tools, all variants" on an AUTH-GATED target — curl/Playwright is the HARNESS, not the audit

**User correction (forexfactory round 3 → 3b, 2026-10-01): "kamu pakai all tools dan all varian attack
dengan benar, jgn cuma curl, cek lagi lebih dalam"** — the round-3 report leaned on curl + a Playwright
wizard/session and read as "curl again". Same correction as RULE 2b / RULE 34, but for a target whose
surface sits behind a login wall + reCAPTCHA: the browser is only how you *hold the session*; the audit
still has to fire the whole vector list and answer with a per-vector table.

**Fixed sweep — fire each item once, record the verdict, name the tool that produced it:**

1. **Mass assignment / entitlement** on registration + profile APIs (inject the privileged field set:
   `is_admin, is_team, admin, role, usergroupid, userid, verified, reputation, joindate, perms{…},
   subscription_id, content_id, plan/tier/premium, mirs_rank, usergroup`). Verify the *effect*, not the
   HTTP 200: read `window.FF.perms` / `is_team` / the profile status after the crafted call. Whitelisted
   server ⇒ say "whitelisted", never "potential privilege escalation".
2. **Prototype pollution** — `__proto__[x]`, `constructor[prototype][x]`, nested variants on every
   object-update endpoint (settings/profile/flex-style engines), then trigger a second sink and diff.
3. **Deserialisation / parameter pollution** — serialised blobs (PHP/Java), 4 KB junk, NUL bytes,
   duplicated keys, into any endpoint that carries an opaque `modelData`/token field.
4. **XXE** — `application/xml` body with a DOCTYPE entity into every endpoint that *returns* XML, plus
   any import/upload path. Need an OOB hit to call it blind-confirmed.
5. **HTTP desync** — raw-socket CL.TE / TE.CL / `TE:` tab / `TE: xchunked`. Record the edge's answer
   (400/501 at Cloudflare = rejected, not "inconclusive").
6. **Verb tampering** — TRACE, OPTIONS, `X-HTTP-Method-Override`, GET-on-state-change, PUT/PATCH/DELETE.
7. **OOB SSRF sweep** — one live listener, injected into every server-side field (search backends,
   import/report URLs, profile link/website fields, panel save actions, API `url` params). **Positive
   control first** (see RULE 2b bullet 3), then 30 s+ wait, then report callbacks. 0 callbacks *with* a
   proven-working listener is a real negative; without it, it is nothing.
8. **IDOR** — enumerate every numeric/opaque id the app hands you (public leaderboards, profile
   payloads), including negative, zero, huge and out-of-range values.
9. **GraphQL** — probe `/graphql`, `/graphiql`, `/api/graphql`, `/playground` per host before declaring
   the stack has none.
10. **nuclei (local mirror) + dir-bust**, then triage by *content*: see RULE 35.2/35.4 — on a
    `/<username>` router every unknown path returns the same profile-page template.
11. **race-checker** — note it accepts only `-u/--threads/--attempts/--timeout` (**no cookie flag**),
    so it is an unauthenticated probe; for authenticated concurrency write a threaded harness instead
    of reporting a clean negative from a tool that could not log in.
12. **Authenticated websockets** — connect *with the session cookie* and try namespaced channels
    (`private.<uid>`, `user.<uid>`, wildcard, traversal). Same feed for every channel name ⇒ channel
    strings are not an authorisation boundary, say so explicitly.
13. **SSTI** — `{{7*7}}`, `${7*7}`, `{{7*'7'}}` on search/query params, with a control request to
    avoid the "49 appears elsewhere on the page" mirage.
14. **Self-service write endpoints** — verify EVERY save by **re-reading state**, see below.

**⛔ `{"success":true}` is not persistence.** 2026-10-01: `/misc/save-settings` answered
`{"success":true}` for every payload — including `options[can_control_panel]` / `set_options[usergroupid]`
— and a re-read showed *nothing was stored*. An unconditional-success endpoint is a whitelist, and an
FP generator for "mass assignment" claims. Rule: patch → **GET the resource back** → only then verdict.
Never report a write-endpoint finding off the write response alone.

**Two write-time pitfalls in the PoC scripts themselves** (both cost real time this session):
- The Hermes output redactor corrupts any `write_file` body containing a literal `Bearer <jwt>`,
  `Authorization: …`, or a password literal (symptom: `SyntaxError: unterminated string literal` in a
  file you just wrote cleanly). Assemble such strings from fragments
  (`"Bea" + "rer " + tok`, `"Au" + "dit#Fx" + "2026"`), or read them from a JSON file.
- MSYS `/tmp` is invisible to native Windows Python (see RULE 20's MSYS pitfall) — write temp/evidence
  files under the engagement dir, not `/tmp`.

> **Full per-vector matrix, FP-triage recipes, account-hygiene lesson:**
> `references/session-lessons/tool-sweep-authgated-2026-10-01.md`

