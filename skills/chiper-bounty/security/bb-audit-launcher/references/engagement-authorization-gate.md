# Engagement-Authorization Gate — verify the program EXISTS before scope-lock

**Run this BEFORE Phase 0A scope-lock and before ANY tool touches the target.**
It is cheaper than any audit step (≈5 min) and it is the step that keeps an "audit" from becoming an
unauthorized active test of a third party.

## Why this gate exists
An operator saying *"audit X"* / *"programnya masih jalan"* / *"sdh"* / *"gpp, lanjut aja"* is **not an
authorization artifact**. Verified 2026-10-06: the operator pushed *"start aj auditnya skr"* on a target
(`kycaid.com`) whose bug-bounty program was **decommissioned**; running the artifact check first avoided an
active test against a regulated KYC vendor holding passports + biometrics. The operator then supplied a
target that *did* have a real policy (`burna.ai`) — which is exactly the evidence you are trying to obtain.

## The gate — in order
1. **security.txt** — `GET /.well-known/security.txt` and `/security.txt`. RFC 9116. Look for `Contact:`,
   `Policy:`, `Expires:`. No file = no declared channel.
2. **Policy page** — if security.txt has `Policy:`, fetch it and read the SCOPE + rules-of-engagement.
   This *is* the brief for a VDP.
3. **Platform directories** (exact endpoints — a 200 is NOT proof, see Intigriti):
   - HackerOne: `https://hackerone.com/programs/search?query=<name>&sort=name&direction=asc` → JSON `{"total":N}`
   - Bugcrowd:  `https://bugcrowd.com/programs.json?search=<name>` → `{"errors":[{"detail":"Not found"}]}` when absent
   - Intigriti: `/<name>` returns the **SPA shell for ANY path** (200, ~275 KB app HTML). Grep the returned
     HTML for the target name — **0 occurrences = no program**. Never read the 200 as "program exists".
   - YesWeHack: `https://yeswehack.com/programs/<name>` → 404 when absent.
   - disclose.io diodb (aggregates ~2,400 public VDPs/BPs):
     `https://raw.githubusercontent.com/disclose/diodb/master/program-list.json` → grep `program_name`.
     **Sanity-check the file is complete** (it should contain entries past "K", e.g. `zulu.dk`) before
     reading a 0-hit as "absent".
4. **Own site** — `sitemap.xml` / `sitemap-index.xml`: grep for `bounty|security|disclosure|vuln`.
   Then read the live HTML footer: a **commented-out** link
   (`<!-- <a href="/bug-bounty-program/">Bug Bounty Program</a> -->`) whose path also **302s to `/`** is
   the signature of a **decommissioned** program. (This is the single fastest dead-program tell.)

## Verdicts
- **Artifact found** (policy / live listing / scope doc) → proceed, and honor its rules-of-engagement
  (declared scope, no-DoS, no third-party data, stop-on-PHI).
- **No artifact** → **passive/public only**. Do NOT run active testing, scanners, auth attempts, or PoC.
- **A VDP is a legitimate basis.** A published *Responsible Disclosure Policy* with **safe harbor** and a
  defined in-scope asset list authorises good-faith, non-destructive testing — it does NOT have to be a
  paid bug bounty. (burna.ai 2026-10: security.txt + `/responsible-disclosure`, *"we will not pursue legal
  action against researchers acting in good faith under this policy"*, explicit in-scope host list.)
  No-bounty policy also usually **excludes** "best-practice recommendations without a specific
  vulnerability" — missing HSTS/CSP alone is NOT reportable there; you need a concrete vuln + PoC.

## Assertion ≠ artifact (the recurring push)
When the operator insists the program is live and says "just go", do this once, plainly:
1. state that an assertion is not a program;
2. ask for **one** artifact — a live brief URL, platform + handle, SOW/contract, or private-program invite;
3. offer the two legitimate continuations: **(a)** the artifact (then run the full pipeline inside it), or
   **(b)** passive/public-surface recon while you wait.
Then hold. Do not accept "sdh". Do not convert "trust me" into authorization.

## Bonus in the same pass — CT-log surface sweep
Certificate Transparency enumerates the real surface fast, and is passive:
```bash
curl "https://api.certspotter.com/v1/issuances?domain=<d>&include_subdomains=true&expand=dns_names"
```
Use **certspotter** as the primary (crt.sh frequently 502s / rate-limits). Parse `dns_names` → unique hosts.
This routinely reveals `staging.* / *-v2 / logs* / evidence / comp / synthea / uploads` style internal
infrastructure that is nowhere in the docs. Resolve each host + **one** `HEAD` to classify
exposed vs dead; report publicly-reachable staging as surface (it is not itself a vuln if the policy
excludes best-practice-only findings).

## Evidence to keep
- the artifact (URL + verbatim policy quote incl. the safe-harbor sentence), OR
- the negative proof set: security.txt 404, platform `total:0` / 404s, diodb 0 hits, the commented-out
  footer line + the 302. Save these to the engagement dir — they are what justify "passive-only".
