## ⛔ RULE 33: Resume an ENGAGEMENT from its log — never re-derive scope, never re-run settled negatives

**Session (atmail deep-dive 2026-09-30):** a follow-up "deep dive, find more weaknesses" request was
answered in minutes instead of hours because the FIRST action was reading the prior round's artefacts
instead of starting from DNS.

Before the first scanner fires on any target you may have touched before, spend 3-4 reads:

```
_progress/<target>-<date>/ENGAGEMENT_LOG.md     <- scope in/out, confirmed findings, EVERY negative
_progress/<target>-<date>/F*_evidence.md        <- what each finding actually proved
_progress/<target>-<date>/recon/                <- host lists, raw responses, prior tool output
D:/data hermes/bug-bounty/vuln-hunter/profiles/ <- scope yaml (absent => allow-all, RULE 30)
```

**A missing `ENGAGEMENT_LOG.md` / `findings.json` is itself the finding.** If the directory holds
only recon artefacts (mirrored docs, specs, cloned repos, one scanner output) and no log, no
`findings.json`, and an empty `poc-evidence/`, then the previous round did RECON ONLY — nothing
was tested. Treat every artefact there as *untested input*, not as coverage, and say so plainly
before starting ("prior round was recon-only; nothing has been tested"). Do not inherit a
false sense of "already checked" from file count. Same tell for a hidden source–deployment
drift: if the cloned repo's `VERSION()` / doc page disagrees with what `cast call` reports on
the live address, the repo is stale and repo findings are unreleased-code findings until
reproduced on-chain.

What the log gives you, and why it is cheaper than re-testing:

- **Scope, already adjudicated.** In-scope domains, CNAME-excluded third parties, and *verified
  in-scope aliases* were all recorded. Re-deriving them costs hours and risks re-testing an
  out-of-scope host.
- **The negative list is an asset, not a gap.** The log listed ~40 already-tested-and-negative
  vectors (CORS without ACAC, request smuggling blocked by the ELB, host-header tenant confusion,
  open redirect, S3 buckets, extension endpoints, React-Router data leaks …). Reporting on a
  *new* attack variant means first checking that variant is not already in that list — and if it
  is, cite the prior result rather than re-running it.
- **The prior finding's exact evidence**, so an extension round can strengthen it (here: the host
  count went 63 → 121, a second alias path was found, an extra credential type was disclosed)
  instead of duplicating it.

Rules that fall out of this:

1. **APPEND to the existing `ENGAGEMENT_LOG.md`** — a dated `## Deep-dive round N` section at the
   bottom. Never start a second log directory for the same target; the next resume reads one file.
2. **Carry the identity header and dates forward verbatim** (`X-Bug-Bounty: <email>`, source IP,
   researcher name) — inconsistent metadata between rounds invalidates the second submission.
3. **If the prior report is already drafted/submitted, treat its claims as a contract.** Re-verify
   a load-bearing claim before repeating it, and if you cannot reproduce it, say so loudly — an
   *unreproduced* claim in a follow-up round is a downgrade, not a detail.
4. **Report only what is NEW or STRONGER.** A follow-up that re-lists round-1 findings gets closed
   as a duplicate.

> Cross-ref: the secret/credential verification discipline (never re-test a value copy-pasted from
> rendered output; read it from the evidence file; negative control in the same run) lives in the
> `unauth-config-disclosure` skill, `scripts/classify_disclosed_key.py`.

