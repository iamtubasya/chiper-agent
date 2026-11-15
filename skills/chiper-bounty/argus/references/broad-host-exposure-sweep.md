# Broad-host exposure sweep (bounded, FP-filtered)

The cheap way to answer "did any in-scope host leave an internal doc, config or dev file
exposed?" across a large host inventory — without triggering a program's rate limits.

Runnable: `scripts/host_exposure_sweep.py` (this skill).

## When to use it

- You have 50–500 in-scope live hosts and the exposure class is your best-value lead
  (stray `README.md` / `.env` / `config.json` / swagger / source maps).
- The program caps request volume account-wide, or forbids aggressive scanning.

## Why NOT full-template nuclei here

Measured (2026-09, 260-host inventory):

| Approach | Requests | Time | Result |
|---|---|---|---|
| `nuclei -tags exposure,disclosure,takeover,default-login,misconfig` | ~1,540,000 advertised | **32 min → 8,254 req, 0%** | aborted (11.5k errors, unusable at 4 rps) |
| bounded sweep, 260 hosts × 14 paths | ~3,600 | **508 s** | 99 raw hits → 35 after filtering |

Nuclei is still the right tool for a *small* host set (its earlier 22-host priority run
found the real finding in ~5 min). Match the tool to the inventory size; do not run the
full template corpus over hundreds of hosts under a rate cap.

## False-positive filtering (the actual value)

The naive sweep reported 99 "hits". Real breakdown:

| Bucket | Count | Verdict |
|---|---|---|
| Cloudflare Access login pages (`Sign in ・ Cloudflare Access`, ~48 KB) served for *every* path on gated hosts | 45 | noise — filter by body marker |
| duplicate (host, body-hash) pairs | 19 | dedupe |
| `ai-assessment.rapyd.org/README.md` — genuine internal project README | 1 | **P4 finding** |
| vendor/template READMEs (`WordPress/Pantheon`, stock Cloudflare `remote-mcp-server`) | 4 | NOT findings — public upstream content |
| front-end `config.json` (base URLs, Google reCAPTCHA **site keys**, Google OAuth **client_id**, feature flags, currency aliases) | 20 | NOT findings — designed to be public, no secrets |
| SPA shells that differ slightly from the root doc | rest | noise |

Two filters do almost all the work:
1. **Compare with the host's own root document** — same sha (or near-identical length) ⇒ SPA
   catch-all, drop it.
2. **Drop interstitial markers** (`Cloudflare Access`, `cf-access`, `Access denied`) and shell
   markers (`__next`, `data-next-head`, `<div id="root">`, `ng-v`).

Then read the survivors by hand. Rule of thumb: *internal documentation* = finding;
*public site key / vendor template / SPA shell* = noise. Say which one it is in the report —
claiming a `config.json` with only public keys as "secret exposure" gets the submission closed.

## Scope + manners

- One root fetch + N path fetches per host, `--rps` default 4, `X-Bugcrowd:` header on every
  request. No directory brute-force wordlists, no fuzzing params — this is a document sweep.
- Keep the host list to in-scope hosts only (filter out the program's out-of-scope hosts first:
  community/support/docs/sandbox and partner subdomains are commonly excluded).
- Save the JSON summary next to the raw log; the "what wasn't there" half is evidence too.

## Complementary checks this sweep does NOT cover (worth a small nuclei run instead)

- CVE/tech-specific templates on individual interesting hosts.
- Takeover signatures (use `dnsReaper`), open redirects, exposed graphql/swagger UIs.
