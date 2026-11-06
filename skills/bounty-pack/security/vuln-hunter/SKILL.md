---
name: vuln-hunter
description: Autonomous vulnerability hunter for ANY web2 or web3 target. Loads when user sends "1" or asks to hunt vulns on a target. Target-agnostic — drive it with a profile file, not hardcoded domains.
version: "2.1"
created: "2026-08-29"
updated: "2026-09-13"
author: RESEARCHER_NAME
metadata:
  hermes:
    tags: [bug-bounty, vulnerability-research, autonomous, web2, web3, universal]
scope: [ANY-IN-SCOPE-TARGET]
---

# Autonomous Vulnerability Hunter — UNIVERSAL (web2 + web3)

## Core Directive
You are a vulnerability researcher. Go find real, impactful vulns on **whatever target the
operator named**. Orchestrate from the main chat, use dynamic workflows and subagents.
Don't give up till you find and validate one. Don't ask questions, just keep going.
There IS a finding waiting — be creative and thorough. Go ahead.

> **Formerly `bitso-hunter`** — renamed because the old name implied an exchange-specific
> skill. The behaviour is unchanged: it is a generic web2+web3 vulnerability hunter.
>
> ⚠️ **This skill is target-agnostic by design.** Nothing below is tied to one program.
> The target comes from a **profile** (`profiles/<target>.yaml` or the session's `scope.md`).
> Hardcoding a domain into this file is a bug — put it in a profile instead.

## Step 0: Load the target profile (MANDATORY — 30 seconds)

```bash
SK=<bundle>/skills/vuln-hunter      # this skill's folder
ls "$SK/profiles/"                                    # existing profiles
cp "$SK/profiles/_TEMPLATE.yaml" "$SK/profiles/<target>.yaml"   # new target
```
A profile carries everything target-specific: domains, platform, headers, auth model,
already-tested list, and the bounty scale. **The profile is the only place a domain appears.**

```yaml
# profiles/_TEMPLATE.yaml
target: <program-or-domain>
platform: hackerone | bugcrowd | immunefi | vdp | none
scale: web2 | web3 | both
in_scope: [example.com, "*.example.com", api.example.com]
out_of_scope: [blog.example.com]
headers:                     # only if the program requires a marker
  X-Bug-Bounty: <handle>
auth_model: none | single-account | two-account   # drives the IDOR decision
test_accounts_available: true | false
already_tested:              # do-not-repeat list, append every session
  - "CORS on all endpoints — properly configured"
notes: |
  Stack, CDN, framework, known infra. Fill during recon, not before.
```

**Scale routing:**
- `scale: web2` → Phases 1–5 below.
- `scale: web3` → Phases 1–5 + `references/web3-workflow` section; pair with the bug-bounty
  master KB and `$TOOLKIT/web3/*`.
- `scale: both` → run web2 recon on the app, then the web3 track on contracts. Often the
  **intersection** is where the real money is (app trusts an on-chain value it never validates).

## Hard gate before any hunting (the zero-payout lesson)

```bash
python $TOOLKIT/shared/finding_gate.py findings.json --report REPORT-survivors.md
```
Run this **before** you write anything up. It drops info-only / by-design / **dead-chain**
findings even at high score.

> **⚠️ Tool quirk: `finding_gate.py` DROPs on keywords, not only on merit.** Its `DROP_PATTERNS`
> regex includes `\b(by[- ]design|intended behavior|documented|expected behavior)\b` alongside the
> info-phrasing markers. So a finding whose `description` merely *contains* the word **"documented"**
> — e.g. *"the oracle interface is documented as provided by GameRegistry"* — is dropped as
> by-design, **even when the defect is real and proven on-chain.** This cost a full re-run on the
> TimbSwap engagement: a confirmed always-reverting function was DROPped until the wording changed.
>
> Rules for writing `findings.json`:
> 1. Keep `by design` / `intended behavior` / `documented` / `expected behavior` OUT of
>    `description` and `impact`. Put provenance and scope caveats in a **separate field**
>    (`scope_note`), which the gate does not keyword-scan the same way.
> 2. State behaviour mechanically instead of with concessionary words —
>    *"the contract exposes no owner, admin or rescue function"* rather than *"there is no rescue
>    path by design"*.
> 3. After rewording, **re-run the gate** and confirm the verdict flips (`REPORT: n` in the header,
>    not just the banner). Never hand-edit `gated.json` — it is a derived artifact.
> 4. Read the verdict reasons. `DROP` with `why: marked by-design` on a finding you know is proven
>    means the *wording* tripped it; `DROP` with `why: dead exploit chain` means the *finding* is
>    info and rewording would be dishonest.

**The two rules that decide everything:**
1. **IDOR/BOLA needs TWO identities.** Run
   `python $TOOLKIT/web2/idor_harness.py setup -c <path-to>/profiles/<target>.yaml` then `verify`.
   No pair of raw HTTP responses showing B reading A's object → it is informational. Say so.
2. **No account + no write + no money movement = hard P3/info ceiling.** Detect this in
   Phase 1 and pivot to infra (S3, pre-prod, third-party APIs, JS bundles) instead of
   grinding the same unauthenticated endpoints for a month.

## Phase 1 — Recon (inventory, NOT findings)
- Read the profile. Confirm scope. **Payout gate first:** VDP-only = no payout = skip.
- Inventory: subdomain enum, port scan, tech fingerprint, crawl, JS/source-map extraction,
  Wayback, cert transparency, GitHub dorks.
- **Exposed internal tooling** (Gerrit / Helix Swarm / Grafana / Jenkins on public
  subdomains) → read `references/exposed-service-cve-scan.md`: DoH liveness split,
  the curl-vs-browser accessibility matrix (a Cloudflare host that 000s curl may load
  fine in Playwright — never discard a subdomain on curl alone), version-endpoint reads,
  CVE affected-range mapping from 2 sources, 3x version validation, and the
  do-not-exploit-DoS rule for known-CVE findings.
- **Rank before you hunt:** `python $TOOLKIT/web2/scope_narrower.py recon.txt --top 5`
  A 500-host list is not a plan. Work the shortlist.
- Time budget **20/60/20**: recon ≤20% of the window. Recon is inventory.
- Output: asset inventory + ranked test candidates + updated `already_tested`.

## Phase 2 — Attack vectors (prioritised, target-agnostic)
Same vector set for every web2 target; the profile decides which apply.

> **⚠️ EXPLOIT COOKBOOK INTEGRATION**: For each vector below, load `exploit-cookbook` skill
> and follow the corresponding playbook (`/SSRF`, `/IDOR`, `/RACE`, etc.). Each playbook
> contains: DETEKSI → VALIDASI → EKSEKUSI → ESCALATION → SCRIPT. **Use the scripts** —
> don't reinvent. The cookbook contains patterns that have ACTUALLY RESULTED in paid bounties.
> **When exploit-cookbook loads, it auto-loads 6 disclosure reference files (2026 CVEs, 82K+ PoC patterns, HackerOne disclosures). Use these to prioritize testing vectors.**

> **📚 `bugbounty-playbook` (mandatory consult, per vector)**: alongside each cookbook playbook, open the
> matching page of the `bugbounty-playbook` skill (mirror of bugbounty.info, 186 pages) for TTP depth and
> end-to-end chains — `references/attack-surface/web/<class>.md` and `references/chains/` (e.g. IDOR→ATO,
> SSRF→cloud RCE, XSS→ATO, race→financial). Read one page at a time; never bulk-load. Consult it on every
> target — do not store-and-skip it.

1. **Auth matrix / IDOR-BOLA** → `/IDOR` cookbook — horizontal first (needs 2 accounts), then vertical
2. **GraphQL** → `/GRAPHQL` cookbook — introspection, query depth, mutation authz, batching abuse
3. **API versioning** — `/v1 /v2 /v4`, deprecated and internal versions
4. **WebSocket** — subscribe to another tenant's channel; auth-on-connect vs per-message
5. **Business logic** → `/BIZLOGIC` cookbook — price/quantity/state manipulation, race conditions, negative values
6. **Sensitive files** — `.git`, `.env`, backups, source maps, `robots.txt`
7. **Cloud storage** — S3/GCS/Azure enumeration; `AccessDenied` = the bucket EXISTS
8. **Subdomain takeover** — dangling CNAMEs, expired services
9. **JWT/JWKS** → `/AUTH` cookbook — algorithm confusion, `none`, weak keys, kid injection
10. **SSRF** → `/SSRF` cookbook — metadata endpoints, internal ranges, redirect chains
11. **Injection** — SQLi, template, command, NoSQL, header/CRLF
12. **Cache** → `/CACHE` cookbook — web cache deception, cache-key poisoning
13. **CORS / host header** → `/CORS` cookbook — origin reflection, `X-Forwarded-Host` trust
14. **Mobile** — APK/IPA decompile for hardcoded secrets and hidden endpoints
15. **Third-party/analytics** — write-key injection, proxy trust, SDK abuse
16. **Errors** — stack traces, internal paths, debug endpoints
17. **Infra pivots** — pre-prod, staging, internal services found in CSP/JS/DNS
18. **403 Bypass** → `/403BYPASS` cookbook — method override, header spoofing, path manipulation
19. **File Upload** → `/UPLOAD` cookbook — extension bypass, path traversal, webshell

**For web3 add:** storage-collision/upgrade safety, oracle manipulation, exchange-rate
scaling, access-control on privileged functions, invariant breaks, ERC4626/vault rounding,
signature replay, reentrancy across composed protocols.
→ `python $TOOLKIT/web3/diff_vs_upstream.py ./src --upstream-repo <url>` (audit the diff, not the boilerplate)
→ `python $TOOLKIT/web3/invariant_scaffold.py targets.yaml --out test/invariant`

## ⛔ VERIFICATION
Before claiming hunting complete, run:
```bash
python C:/Users/WINDOWS10/AppData/Local/hermes/scripts/audit-checkpoint.py <target_dir> --phase 0C
```
Checkpoint reads actual tool output files from disk.

## ⛔ HUNT ENFORCEMENT (MANDATORY)
Setiap langkah di workflow ini WAJIB dijalankan dengan TOOLS yang tepat — bukan cuma curl manual.
Baca reference files → ikuti panduan attack → jalankan tools → buktikan dengan terminal output.

Workflow enforcement:
1. Recon → semua recon tools jalan (subfinder, httpx, naabu, gau, katana)
2. Fingerprint → whatweb/tech detection jalan
3. Attack surface → semua endpoint di-list
4. Test setiap vector dengan TOOLS yang benar:
   - SQLi → sqlmap, bukan curl manual
   - XSS → dalfox/kxss, bukan payload manual
   - SSRF → SSRFmap/Interactsh, bukan curl internal
   - IDOR → autorize/poweridors, bukan curl ganti ID
   - Race → race-the-web/turbo intruder, bukan curl parallel
   - GraphQL → InQL/graphql-map, bukan curl introspection
5. Chain findings → kombinasi findings jadi exploit chain
6. Verify impact → bukti exploitation, bukan teori

Baca setiap reference file di skill ini → eksekusi tool yang direkomendasikan.
Jangan claim "nothing found" tanpa JALANKAN semua tool dulu.

## Workflow
1. Load profile + recon results from `$BB_DATA/_progress/<target>/`
2. **⛔ GATE CHECK: Profile has auth_model? Endpoint list from recon? If no → Phase 1 recon first.**
3. **⛔ ACCOUNT LOOP BLOCK: Max 2 signup attempts, 5 min total. Failed → auth_model="no-account" → P3 ceiling → next vector.**
4. Pick untested vector → delegate to subagent
5. Validate manually — **repro, evidence, root cause**
6. Confirmed → run the gate → build the chain → report
7. Not confirmed → next vector, append to `already_tested`
8. **⛔ CORS GATE: Do NOT test CORS until vectors 1-13 (IDOR, Auth, PrivEsc, RCE, SQLi, Race, BizLogic, MassAssign, InfoLeak, XSS×3, GraphQL) are tested or skipped with documented reason.**
9. **NEVER conclude "no findings" without testing ALL vectors AND the infra pivots.**
   Equally: never pad. If the gate drops everything, "no reportable finding" is the honest
   answer — see `skill_view(name='bug-bounty', file_path='references/pitfalls-library.md')` §EXHAUSTED for the stop criteria.

## Tools Available
- **Toolkit scripts** (optional, not in bundle): `$TOOLKIT/web2/*`, `$TOOLKIT/web3/*`, `$TOOLKIT/shared/*`
  - If toolkit not available, use nuclei/ffuf/curl directly per exploit-cookbook playbooks
  - Install: extract `BUG-BOUNTY-BUNDLE-v1.zip` → `toolkit/` → set `$TOOLKIT` env var
- curl, python3, nmap, dig, nslookup
- **Native Python 3.14:** Slither, Echidna, Medusa, Halmos, Z3
- **WSL Ubuntu (via wrapper ~/go/bin/):** Aderyn, Mythril
- **Foundry:** forge, cast
- browser tools (navigate, click, snapshot, vision)
- `delegate_task` for parallel subagent work
- `execute_code` for batch analysis

## Output Format
```
🔓 HUNT — <target> [web2|web3]
Vector: [what was tested]
Status: [VULN FOUND / NOT VULN / NEEDS MORE TESTING / BY-DESIGN]
Finding: [description if found]
Impact: [CVSS assessment — only if the chain is live]
PoC: [reproduction steps + raw evidence]
Gate: [survived / dropped — with reason]
```

## Profiles
- `profiles/_TEMPLATE.yaml` — copy this for any new target (the only place a domain belongs)
- `profiles/bitso.yaml` — worked example of a **hardened, exhausted** target: it shows the
  "no test account ⇒ P3 ceiling" stopping condition end to end, plus the full do-not-repeat list.
  Narrative: `skill_view(name='bug-bounty', file_path='references/bitso-2026-complete-session.md')`
  (canonical copy lives in the `bug-bounty` skill's `references/`, not in this folder).

## Where the toolkit lives (read this before running any command below)
This skill ships **inside the bundle**, and the tools are **not** in this folder:

```
bug-bounty-bundle-v1/
├── skills/vuln-hunter/SKILL.md   ← you are here
└── $DATA/bug-bounty/bundle/toolkit/                       ← every `$DATA/bug-bounty/bundle/toolkit/...` path below is relative to THIS
    ├── web2/  scope_narrower.py, idor_harness.py
    ├── web3/  diff_vs_upstream.py, invariant_scaffold.py
    └── shared/ finding_gate.py, chain_builder.py
```
So run the commands from the **bundle root**, not from the skill dir:
`cd <bundle>/ && python $TOOLKIT/web2/idor_harness.py setup -c skills/vuln-hunter/profiles/<target>.yaml`
Sanity check the bundle first: `bash verify.sh` → must print **6/6 PASS**.
If the tools aren't present, say so explicitly instead of silently skipping the gate.



---

## Companion Reference — `poc-technique-atlas` (additive, never overrides)

Method-level technique shelf extracted from a 2,223-repo local PoC corpus (filtered of
malware/scam, deduped) + PortSwigger WSA. **Read ONE class file per phase** — it does NOT
count against the phase context budget (on-demand shelf).

- `skills/security/poc-technique-atlas/references/00-INDEX.md` → 27 classes (RCE 357, IDOR/BOLA 87, SQLi 83, Crypto 75,
  Auth-bypass 68, XSS 59, Info-disclosure 48, LFI 47, Deserialization 22, SSRF 19,
  Cloud 14, SSTI 7, Race 5, XXE 5, Prototype-pollution 2, …). 1,901 techniques total.
- `skills/security/poc-technique-atlas/references/portswigger/00-INDEX.md` → 29 WSA topics.
- Use it to pick the *method* for the class you are testing; owner skill rules still win.
