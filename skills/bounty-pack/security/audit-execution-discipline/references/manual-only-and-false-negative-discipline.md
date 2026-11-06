# Manual-only engagements & false-negative discipline

Source: freeagent.com Responsible Disclosure engagement (2026-10-01/02). 45 vectors executed,
0 exploitable findings, 2 near-findings **actively disproven**, 3 robustness nits recorded as
non-findings. Use this when a program forbids tooling, or whenever a probe suggests a control is
missing.

---

## 1. When the vendor forbids automated scanning

FreeAgent's program states (binding): *no automated vulnerability/scanning tools* (IP can be
permanently blocked) and *no mass brute force / account enumeration*. It also keeps "absence of
rate limiting" **in scope when authentication is affected**.

That directly contradicts the launcher's "30 vectors, each with a real tool" mandate. Handle it
explicitly — do not fake it and do not silently skip:

- Do NOT run them **brutally**. Run the SAME tools **GENTLY**: nuclei with `-rl`/`-c 1`, sqlmap
  `--delay`, ffuf `-rate`/`-c 1..2`, dalfox `--delay`, `--random-agent`, own accounts only.
- **MANUAL / curl-only is a HARD PROHIBITION — NEVER switch to it** (operator, 2026-10-10). If a tool
  genuinely cannot run even gently, record an explicit **GAP**.
- Record Phase 0D from the **gentle evidence** (a tool that ran → PASS; one that could not → GAP).
  Never narrate an untested area as "clean".
- In the report, state coverage as **"gentle automated (rate-limited, non-brutal)" + explicit GAPS** —
  never as "all tools / all variants run" (overclaim users have pushed back on).
- Still cover the classes the scanners would have: BOLA/IDOR across two own tenants, BFLA via
  permission levels, OAuth redirect_uri, stored/injected HTML, state machines, brute-force
  controls, shadow API, URL/verb/header authz mutation.

## 2. False negatives: "a missing control" needs a POSITIVE control

Verified failure mode this session: 6 sequential wrong-password attempts produced **no**
lockout message, constant ~8.8 s round-trip → looked like "no rate limiting". Submitting the
**correct** password immediately afterwards returned
`Login attempt failed too many times` — the lockout existed, the threshold was simply >15.

Rules:
1. After any probe that suggests a control is ABSENT, run the **legitimate success path** and
   re-read the response before calling it absent. "Locked out at the end" is the proof the
   control exists.
2. Bounded probes are fine (own accounts only, deliberately stop early), but the honest verdict
   is *"not observed within N attempts"*, never *"no control"*.
3. Same shape as the tool-evidence rule: a probe that never reached the threshold is
   indistinguishable from a probe that proved nothing.
4. Also report the control you DID observe: FreeAgent's OTP step locks at ~10 failures, the
   password step at >15 — that asymmetry is the interesting, honest sentence.

## 3. By-design vs bug: judge intent against the authoritative artifact

The account-lock case: creating/editing/deleting a **draft** invoice dated inside a locked
period succeeded, while the same dates were refused for expenses (`422 dated_on is in a locked
period`). That looked like an integrity-control bypass. Two checks killed it:

- `GET /v2/accounting/balance_sheet?as_at_date=<lock date>` was **identical before and after**
  → drafts do not post to the ledger.
- Posting was still blocked: `mark_as_sent` → `403 Invoice is locked.`; re-dating an already
  posted invoice into the lock → `422 dated_on is in a locked period`; credit note → `403
  Credit note is locked.`

Rules:
- For accounting/financial products, judge intent by the **ledger artifact** (balance sheet /
  trial balance / P&L), not by the document API alone.
- A state you can *create* but cannot *transition to its posted state* is not a bypass.
- Before writing an "inconsistent enforcement" finding, enumerate which operations the product
  DOES block and check whether the allowed ones are exactly the ones with no posting effect.

## 4. Test the newest endpoints first

Docs are versioned (`https://dev.freeagent.com/docs/<resource>?version=2026-09-01` — the page
**302s without the version param**). Newest resources are the least-tested code path and the
highest hit-rate for missing tenancy/permission checks. On this engagement the newest endpoint
(`GET /v2/bank_transaction_explanations/:id/attachments`, min version 2026-09-01) was still
clean, but that is where to spend the first probes, together with `Changelog`-listed additions.

## 5. Probe batteries that are cheap and keep paying

| Battery | Shape | What a hit looks like |
|---|---|---|
| Cross-tenant BOLA | create object in own tenant B, `GET` it with tenant A's token | 200 instead of 404 |
| Permission ladder | set a user to level N, sweep every resource, diff against owner | 200 where the UI says "not allowed" |
| URL/verb/header mutation | trailing `/`, `//`, `/./`, `..`, `.json/.xml/.js`, `%2F`, `%00`, uppercase, `?format=`, HEAD/OPTIONS, `X-HTTP-Method-Override`, `_method=`, content-type swap | 200 on a path that 403'd |
| Tenant-key mass assignment | inject `company_id` / `account_id` / `subdomain` / `id` on PUT /company and on create bodies | object lands in the other tenant, or company switches |
| Field-level shaping diff | fetch the same resource as owner vs low-priv and diff the key set | low-priv response that *omits* fields = permission-aware = by design, NOT a bug |
| Self-escalation | limited user raises own level / creates a higher-privilege user | level actually changes (it gets clamped in a correct impl) |

## 6. Execution traps that cost real time here

- **MSYS converts a bare `/v2/...` argv into a Windows path.** `python cli.py GET /v2/company`
  produced host `api.freeagent.comc` and a `getaddrinfo failed` error that reads exactly like
  DNS breakage. Fix: `MSYS_NO_PATHCONV=1`, or keep all paths inside the script. Diagnostic: print
  the assembled URL/host before blaming DNS.
- **Run python with `-u`** when the command may be killed by `timeout`; otherwise buffered prints
  are lost and the run looks like it produced nothing.
- **Chromium stderr floods stdout** (`[pid=...]` lines from page console). Filter with
  `grep -v "^\[pid"` or your own evidence lines get truncated away by `tail`.
- **OAuth on a tenant-subdomain app**: the login session cookie is host-only
  (`login.freeagent.com`), so navigating straight to `api.../v2/approve_app` ALWAYS bounces to
  the login form. You must do the full login (email+password, then the e-mail OTP) in the same
  context; the approval page then renders on the tenant subdomain. Capture the redirect with a
  Playwright **response listener on the `Location` header** — route interception of the
  final `https://localhost:...` hop does not reliably fire.
- **OTP-from-mailbox helper**: keep `creds`+state per account and filter mail by the plus-address
  token (`user+tag@gmail.com`); a stale state file silently makes an authenticated probe look
  like "the target refuses everything" (all-401 battery = session expired, re-login first).
- **Evidence layout that survives review**: one directory per class
  (`evidence/<class>/<probe>.json`) plus the raw received artifact (email HTML, response body)
  — the negative is only worth something if the artifact is on disk.

## 7. Signed-URL / attachment analysis recipe

`content_src` is a presigned S3 URL (time-boxed). `content_src_medium/small` is
`…/thumbnail/<bucket>/<payload>` where payload = **base64(JSON key header + signature blob)**,
and the raw URL percent-encodes `+`/`/`/`=`, so `unquote()` before decoding. Split at the first
`}`: header is `{"key","region","width","height"}`. Rebuilding the URL with a swapped key or a
zeroed signature returns `403` → signature is bound to the key, no unauthenticated IDOR. Do the
whole test in one process immediately after fetching the attachment: the URL expires in seconds,
and an expired control URL 403s and makes every tampered result meaningless.
