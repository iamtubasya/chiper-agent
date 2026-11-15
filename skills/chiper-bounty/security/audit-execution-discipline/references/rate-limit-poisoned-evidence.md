# Rate-limit-poisoned evidence — when YOUR scan turns the rest of the run into non-results

A broad scan against a CDN/edge-protected target can trip a rate limiter and then **every later probe
in that window returns the limiter's response instead of the target's**. Those results are not
negatives — they are unverified. Publishing them as "not vulnerable" is a false-negative claim, which
is the one thing an audit must never ship.

Verified 2026-10 (Nordnet VDP, `www.nordnet.*`):

- A broad `nuclei -l live_hosts.txt -t <full template dir>` (14k templates x 73 hosts) ran for ~20 min.
- Afterwards **every** `www.nordnet.{se,fi,no,dk,de}` request returned
  `HTTP/1.1 429 Too Many Requests`, `via: 1.1 google`, no `Retry-After`. Apex `nordnet.se` still 301'd;
  the sibling portal hosts (different LB) stayed healthy.
- The 429 persisted ~45 min after the scan stopped.
- Inside the same window the orchestrator logged: `linkfinder … HTTP Error 429`, `race-checker` 4/50
  requests all 429, `nuclei` rc=-1. Its own `sqlmap` run had already noted `429 (Too Many Requests)`.

## The rule

**Two statuses, never conflated:**

| what you saw | what it is | how to log it |
|---|---|---|
| clean 404 / 200-with-no-sink | a real negative | `NEGATIVE (verified)` |
| 429 / 503 / 403-from-the-limiter / `000` after a limiter trip | **unverified** | `POISONED (rate-limited) — re-run after cooldown` |

A review of the coverage ledger must let a reader tell these apart. Never write "not vulnerable"
against an endpoint that answered 429.

## Detecting it

- `curl -sI https://<host>/` on the *baseline* path — if the plain homepage is 429, the whole host is
  out for you; the per-endpoint results underneath it mean nothing.
- `via: 1.1 google` / `server: cloudflare` + a tiny HTML body titled `429` is the CDN limiter, not the app.
- An evidence file whose body is the limiter page, or whose tool exited non-zero with only a banner, is
  POISONED.

## Recovery

1. **Stop firing at that host family.** Do not rotate egress IPs to keep scanning — that is evading a
   control the program relies on, and on a "no noticeable load" VDP it is the fastest way to lose the
   engagement.
2. Work the *other* hosts in the meantime (different LB / different domain stay healthy).
3. Re-run the poisoned vectors after cooldown, and only then write the negative.
4. If you cannot re-run (engagement ends), say so explicitly in the ledger rather than claiming a pass.

## Prevention — size the scan to the program, not to the tool

- Read the policy first. "Do not jeopardise availability" / "no noticeable load" means **targeted
  templates at a low rate**, not `-t <everything>`.
- Prefer several narrow passes (`http/exposures`, `http/misconfiguration`, `http/exposed-panels`,
  `http/takeovers`, `ssl`) over one full-template sweep; keep `-rl` low and `-c` small.
- A 14k-template x N-host sweep is ~1M requests. At 30 rps that is ~9 h of load, and it *will* trip a
  bank's edge. That is not thorough — it is loud, and it destroys your own coverage.
- Broad recon (`subfinder -all`, `amass`, `katana`, `waymore`) is passive/read-mostly and is fine to run
  wide; **fuzzers and scanners are not the same category.**

## Related

- `msys-path-and-tool-invocation-traps.md` (Symptom O) — the `000`/empty-result variants of the same
  "unverified ≠ negative" rule.
- `tool-health-and-invocation-truth.md` — run failure is not a result.
