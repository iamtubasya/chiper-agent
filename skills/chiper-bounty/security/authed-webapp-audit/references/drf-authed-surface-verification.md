# Systematic verification battery for DRF / JSON-API authenticated surfaces

Distilled from the djangoeurope hosting-panel audit (2026-10-19): a Django REST Framework API
behind an Angular SPA where every object-level permission held. The value of the round is the
**battery itself** — a repeatable sweep that produces defensible negatives ("N classes verified
negative with evidence") instead of ad-hoc pokes. Run it once you have one authenticated session
(see the parent skill for account provisioning; `bot-protected-target-testing`'s
`references/altcha-and-fingerprint-antiautomation.md` when registration is CAPTCHA/anti-fraud gated).

## 0. Session mechanics that gate everything

- DRF token auth may require BOTH `Authorization: Token <key>` AND cross-origin cookies
  (`credentials: 'include'`). Header-only → `Invalid API token` / `API token has expired` even
  with a valid token.
- Tokens can carry a **request budget** (~10 rapid requests, then 401 mid-sequence). Space
  probes ~500 ms, or re-login when 401s start. Read the token fresh from `document.cookie`
  before each in-page fetch.
- Multi-request sequences (list → delete-each) break when the budget dies halfway: do the
  mutation loop in one in-page `evaluate` and tolerate partial completion, then verify.

## 1. Detail-endpoint differential sweep (the core IDOR battery)

For every collection the API root exposes, probe the detail route with TWO UUID classes:

```
GET /<resource>/00000000-0000-0000-0000-000000000000/   (never-existed)
GET /<resource>/<uuid-of-something-not-mine>/           (exists, other tenant)
```

Read the matrix:

| random | foreign | verdict |
|---|---|---|
| 404 | 404 | object-level filtering correct (queryset scoped to request.user) |
| 404 | 200 | **IDOR** — foreign object readable |
| 403 | 403 | blanket permission (admin-only endpoint), not object-level — check the body |
| 200 | 200 | list-style detail route or missing scoping — investigate |

djangoeurope: 30/30 resources uniform 404; `/expense/` and `/finance/transaction/` answered
403 for both classes = admin-only (consistent, not a leak). A 403-vs-404 *difference* between
the two classes is the signal worth chasing.

## 2. Filter tampering on collections

`?user=1`, `?user__id=1`, `?user=<foreign-uuid>` on list endpoints. Correct behaviour: the
param is ignored and the queryset stays ownership-scoped (you see only your own rows). Seeing
another tenant's row through a filter = IDOR even though the path looks "list".

## 3. Parent-override on nested creation

Hosting/CRM-style APIs nest resources (`domainrecord` under `domain`, `mailuser` under
`systemuser`). POST a child with a **foreign parent UUID** and read the validation message:

- `"Invalid pk ... object does not exist"` / `"System user does not exist."` = existence check.
- `"Domain does not exist. Add the domain and make sure you have access to it."` = existence
  **plus ownership** — the strongest cheap signal that parent scoping is server-side.
- 201 with the foreign parent attached = **IDOR on creation** (you just wrote into another
  tenant's object).

## 4. Mass-assignment boundary probe

PATCH your own profile/account object with a mixed payload: privilege fields
(`is_staff`, `is_superuser`, `user`, `id`), business fields (fee rates, vat rates), and a
cosmetic field as the canary. Read back which moved:

- Canary moved, privilege/business fields unchanged = serializer field-allowlist correct.
- `user` re-linked to another id = critical (account takeover primitive).
- Fee/vat fields writable = business-logic finding (self-discounting).

djangoeurope: only a display-only `ckey` moved; fees, user-link and role flags all protected.

## 5. Input-validation control checks (RCE surface on system-level fields)

For any endpoint whose field reaches a shell, a config file, or `authorized_keys`, **verify the
control instead of assuming it** — one probe each, all cheap:

| field class | probe | pass looks like |
|---|---|---|
| SSH public key | submit `command="...",no-pty ssh-ed25519 AAAA...` | options **stripped**; stored value is bare `type key` |
| system/DB/mail user names | `detest;id`, `detest$(id)`, backticks, `\|id` | character whitelist error (`a-z0-9 _ -`) or length cap |
| hostnames / destinations | `127.0.0.1;id`, `$(id)` | `Invalid host name` |
| free-text profile fields | same metachar set | serializer 400 |
| ticket/message bodies | `<img src=x onerror=...>` | stored verbatim → **stored-XSS candidate** (confirm the *staff* render before claiming) |

A 500 on a creation endpoint with an incomplete-account payload is a robustness note, not a
finding — get the payload fully valid before concluding anything about the handler.

## 6. Access-granting / impersonation features

`/su/`-style switch-user or "grant access" endpoints: try POST with user id, foreign UUID, and
email variants. 404/400 on all = no grant bypass. If a grant succeeds for an arbitrary target,
that is the finding (cross-account read without the victim's consent).

## Reporting bar

A clean battery is a deliverable: ship `reportable_findings: 0` plus the verified-negative list
with the probe matrix on disk. Do not inflate a 403-vs-404 inconsistency or a 500 into a
finding — record it as an observation with the exact repro and the benign explanation.
