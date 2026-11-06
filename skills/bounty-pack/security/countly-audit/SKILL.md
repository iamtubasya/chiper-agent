---
name: countly-audit
description: "Use when auditing the Countly (count.ly) bug-bounty program."
author: RESEARCHER_NAME
license: MIT
version: 1.0.0
metadata:
  hermes:
    tags: [security, bug-bounty, countly, codebase, nodejs, mongodb]
    related_skills: [codebase-bounty-review, security-tooling-setup, audit-runbook]
---

# Countly — bug-bounty engagement

## When to Use

Trigger when the operator names Countly / count.ly as the bug-bounty target, or asks to audit the
`Countly/countly-server` repo or a Countly SDK. This is a white-box source-code engagement (PoC on
a deployment you control), not a live-host pentest.

Countly (https://count.ly) = self-hosted **single-tenant** mobile/web analytics platform.
Node.js + Express + MongoDB (driver v7). Source lives in public repo `Countly/countly-server`
(+ `countly-sdk-js`, `countly-sdk-nodejs`, `countly-sdk-web`, etc.).

## Program facts (verify against live SECURITY.md each run)

- **Channel:** email `security@count.ly` ONLY (no GitHub issue, no H1/BC listing). See `github.com/Countly/countly-server/security`.
- **Scope:** source code of public repos, **tested on a deployment YOU control**. Marketing site,
  demo/hosted instances, their infra, third-party services = OUT (no reward). SDK `app_key` is NOT an
  account for severity purposes (it ships inside customers' apps).
- **One reward per root cause**, first actionable report wins, private disclosure required (publishing before fix = forfeit).
- **PoC is MANDATORY** — "findings from source reading, static analysis or automated scanners alone" are excluded.
  XSS must show actual script exec in an authenticated dashboard session.

### Severity ladder (ordered by what the attacker already has)
- **Critical** — no account, no special conditions, full takeover.
- **High** — no account + needs extra info/special condition (a shipped SDK key is "no account").
- **Medium** — has an account, impact = end-user data collected by an app, or a credential, or permission escalation.
- **Low** — no reward (cosmetic, version disclosure, chained-low-likelihood, header/CSRF hygiene etc.).

### Exclusions worth internalizing (long list in SECURITY.md)
Deployment/server config · findings needing privileged/already-sufficient access ("global admin can X" is by design) ·
**already-known-to-us** (huge — see below) · non-default plugins (not in `plugins/plugins.default.json`; `consolidate`
and `errorlogs` OOS even though default; heatmap `/o/actions` OOS) · no-PoC · DoS/resource-exhaustion · compromised-client
/network-position · third-party deps without a Countly exploit · best-practice/informational · Hooks custom-code sandbox.

## ⚠️ The dominant strategic fact: vendor runs DAILY AI security review

`git log` shows essentially every recent commit is `[fix] ...` authored by **`Claude <as@count.ly>`** on
`Countly/claude/*` branches (HEAD as of 2026-11-03 is a mass-assignment/dotted-field fix). Countly is
continuously combing its own codebase with an AI agent. Consequences:

1. **Exclusion #3 ("already known to us") is enormous** — most things you'd find by static analysis are
   already patched or pending review with no public record.
2. **The live frontier is the *newest* hardening class.** When you audit, first read the last ~40 commits
   (`git fetch --unshallow; git log --oneline -60`) and identify what class they JUST fixed (mass-assignment
   / dotted-field-name / prototype-pollution / app-scoping). Then hunt the *sibling* plugins that have NOT yet
   received the same `pickWritable*Fields` / field-name guard. That inconsistency is the realistic find.
3. Expect a mostly-clean result with full coverage. A "0 findings" here after exhaustive differential testing
   is legitimate, not a miss.

## Codebase map (where the meat lives)

| File | Role |
|---|---|
| `api/utils/requestProcessor.js` (4204 lines) | All `/i/*` (ingest) + `/o/*` route dispatch. `case '/i/...'` blocks + `validateAppForWriteAPI`/`validateAppForFetchAPI` (SDK `app_key` gate) + `validateUser*` wrappers. |
| `api/utils/rights.js` (2035 lines) | THE authz core. `validateUser` / `validateAppAdmin` / `validateGlobalAdmin` / `validateRead/Update/Create/Delete`, `applyTokenScope`, `intersectPermission`, `isPermissionSubset`, `principalAllows*`, `hasAdminAccess`. |
| `api/utils/authorizer.js` | `auth_tokens` mint/verify; `can_login` + `token_permission` (scoped-token) model; `validateUserForMgmtReadAPI` = `validateUser`. |
| `api/utils/ssrf-protection.js` | `isUrlSafe` (parse-time) + `safeLookup` (connect-time DNS-rebinding) + `getSsrfSafeOptions` (`followRedirect:false`). Very thorough. |
| `api/utils/common.js` (4148 lines) | Sanitizers: `mergeableKeys`→`isForbiddenFieldName` (`__proto__`/`constructor`/`prototype`), `findUnsafeMongoOperator` (`$where`/`$function`/`$accumulator`), `parseUserQuery`, `sanitizeProjection`, `stripRequestCredentials`, `getDescendantProp`, `resolvePathInBase`. |
| `api/parts/data/exports.js` | `/o/export/db` + `EXPORT_REDACTIONS` (members→password/api_key/two_factor_auth; auth_tokens→_id), cursor-level redaction. |
| `frontend/express/app.js` + `frontend/express/libs/members.js` | Dashboard routes; login/forgot/reset/`/login/token/:token`; `loginWithToken` does `req.session.regenerate` (anti-fixation); reset claims `findOneAndDelete` + 10-min expiry. |
| `plugins/<name>/api/api.js` | Per-plugin routes (`/i/remote-config`, `/i/feedback/*`, `/i/views`, `/i/crashes`, `/i/hook`/`/i/alert`). |

Ingest hardening (verified): event `segmentation` keys are dotted-`$`-`__proto__` sanitized before DB write;
`device_id`/`app_key`/`old_device_id` are stringified as scalars (no `$ne` operator injection); `mergeQuery`
drops `isForbiddenFieldName` keys; `deepMerge` in `fetch.js` guards with `isMergeableKey`.

## Verified-clean surfaces (tested live, do NOT re-report — see references for detail)

*Live differential run 2026-11-04 on a self-hosted deployment (see `references/native-wsl-deployment.md`):*
- NoSQLi `device_id=$ne` — neutralized (stringified literal).
- Cross-tenant BOLA (`userB` read-only on app A → app B) — `User does not have right`.
- Scoped token → mint child with `can_login=true` / without stating permission / `/o/render` — all refused.
- `/o/export/db` on `members` — `api_key`+`password` redacted (cursor-level, projection-proof).
- `remote-config add-parameter` stores dotted/`$where` keys as inert fields (no query impact); `$set` with
  `$`-prefixed key → MongoServerError code 52 (DB self-defend); `__proto__`/`api_key`/`auth_token` stripped.
- `remote-config` `condition.condition` is eval'd via `remoteConfig.processFilter()` (in-memory JS), NOT a Mongo query.
- Token authz model (`intersectPermission`/`isPermissionSubset`/legacy-scope bounding) is very clean.

## Supporting files

- `references/native-wsl-deployment.md` — the working recipe to stand up Countly for live PoC (mongod via fastdl
  tarball, nodesource Node, `plugins.json` quirk, SIGHUP survival, seed + differential probe scripts).
- `scripts/seed.js` — seed admin + 2 apps + non-admin members + a scoped token, directly into MongoDB.