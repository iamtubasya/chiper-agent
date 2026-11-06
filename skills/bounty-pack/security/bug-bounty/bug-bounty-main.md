---
name: bug-bounty
author: RESEARCHER_NAME
description: "Use when hunting bug bounties or authorized testing. UNIFIED: covers web/API, smart contracts, DeFi, SaaS, LLM red-teaming, all platforms."
metadata:
  hermes:
    tags: [bug-bounty, security, web, api, blockchain, defi, saas, redteam, audit]
version: 4.0.0
---

# Bug Bounty — ROUTER

> **This SKILL.md is a lightweight router.** Content lives in split files below.
> Agent MUST load the correct split file per phase.
> 
> **⚠️ NEVER load all skills at once.** Use the phased matrix below.

> **Reconciling "use ALL skills and tools" with phased loading.** The operator's standing
> kickoff is *"pakai semua skill dan tools yg ada, lalu periksa target X, cari dari segala
> sisi, tanpa kecuali, termasuk bisnis logicnya."* Read that as **full COVERAGE across the
> whole run**, never as "load every skill simultaneously". The budget table below is
> absolute: loading everything at once triggers context compression, skills get pruned
> mid-run, and the audit dies with nothing to show. Full coverage is delivered by working
> the phased matrix to completion and then publishing the **TOOL-COVERAGE LEDGER** (stop
> rule 23) that proves every tool ran — coverage is demonstrated by the ledger, not by
> how many skills were opened. Same reading applies to the sub-skills: load the one that
> governs the phase you are in, then evict.
> **⛔ NEVER skip to report. Phase 0C must be marked COMPLETE in PHASE_LOG.md before Phase 0F (report) loads.**
> **⛔ Phase transitions require PHASE_LOG.md verification. Read it first if resuming.**
> **⛔ Startup: ALWAYS create/read PHASE_LOG.md before ANY work.**
> Each phase loads ONLY its listed skills, then EVICTS before next phase.
>
> **📚 REFERENCE SHELF — MANDATORY CONSULT EVERY AUDIT: `bugbounty-playbook`.** A 186-page
> mirror of bugbounty.info (TTPs, chains, recon, methodology, reporting). It is NOT bulk-loaded
> and does NOT count against phase budgets — read ONE page on demand with
> `skill_view(name='bugbounty-playbook', file_path='references/<...>')`. Consult it every audit
> (0B → `references/recon/`, 0C → `references/attack-surface/<track>/` + `references/chains/`,
> 0F → `references/reporting/`); never stored-and-skipped. Owner rules (this file, triage-validation)
> always override it.
>
> **⚡ IMMUNEFI SCOPE EXTRACTION (step 0 of every Immunefi audit):** do NOT rebuild scope from rendered
> HTML or web_search. `references/immunefi-recon-workflow.md` §"Phase 0" has a working parser for the
> Next.js flight stream (`self.__next_f.push(...)`) that yields the program's own JSON — rewards,
> `assets[]` + Primacy-of-Impact flag, `impacts[]`, `knownIssues[]`, `audits[]`, out-of-scope text.
> Also note `web_extract` cannot extract Immunefi (the `ddgs` backend is search-only).
>
> **⚡ BUGCROWD SCOPE EXTRACTION (step 0 of every Bugcrowd audit):** the engagement page is a JS SPA
> and the brief is login-gated in HTML, but the changelog endpoint serves the full brief as JSON with
> a `.json` suffix: `/engagements/<slug>/changelog/<id>.json` (find `<id>` in the page HTML). Yields
> `data.brief` (rules, OOS) + `data.scope` (target groups, targets, per-tier `rewardRangeData`,
> `inScope`). Enforce the programme's REAL scope — do not treat it as allow-all. Details, egress
> triage and the unauthenticated-`/metrics` hunt vector: `references/bugcrowd-program-brief-and-exposed-metrics.md`.

---

## Pipeline (PHASED loading — avoid context compression)

```
Phase 0A: bb-audit-launcher (20KB) — evict after target type determined
Phase 0B: security-recon (25KB) + recon.md (17KB) — evict after surface mapped
Phase 0C: ONE TRACK ONLY (see matrix) — evict after testing complete
Phase 0D: verify-tool-usage gate (11 checks, HARD BLOCK)
Phase 0E: finding_gate → validate-findings → triage_gate  (aggregate/chain = 0C-C7)
Phase 0F: bug-report-delivery + report.md (40KB) — ABSOLUTE LAST

NOTE: the block above is the MANUAL/skill pipeline. The AUTOMATED pipeline
(audit-pipeline-orchestrator.py / audit-run-all.py) runs 0A→0F:
0D = verify-tool-usage GATE, 0E = findings (filter+validate: finding_gate→validate→triage); aggregate→weaponize→chain = 0C-C7,
0E-REVIEW = candidates 3x check (only survivors reach the report), 0F = report.
Read audit-execution-discipline skills/security/audit-execution-discipline/references/audit-pipeline-phases-and-fresh-run.md
before invoking it (full-URL + --scope required; stale resume state lives in
~/AppData/Local/hermes/trackers/, not only in poc-plans).

⚠️ BUDGET: peak cumulative WITH eviction = 120KB (under 162KB threshold)
⚠️ WITHOUT eviction = 249KB → compression fires → skills pruned → audit dies
```

## Split Files

| File | Phase | Size | Content |
|------|-------|------|---------|
| `bug-bounty-main.md` | All | ~25KB | Rules, tool map, workflow overview, overclaiming patterns |
| `bug-bounty-recon.md` | 1-4 | ~18KB | Scope, recon, analyze, verify/exploit, deepdive gate |
| `bug-bounty-testing.md` | 4.5 | ~41KB | 10 layers, 736 refs, external repos, tool chains |
## Phase Definitions

| File | Phase | Budget | Content |
|------|-------|--------|---------|
| `bug-bounty-main.md` | All | ~25KB | Rules, tool map, workflow overview |
| `bug-bounty-recon.md` | 0B | ~17KB | Scope, recon, analyze, verify/exploit |
| `bug-bounty-testing.md` | 0C | ~41KB | 10 layers, 736 refs, tool chains |
| `bug-bounty-report.md` | 0D | ~8KB | 219-box checklist, severity, report |

## New Skills (Phase-specific — evict previous before loading)
| Skill | Phase | Budget | Repos |
|-------|-------|--------|-------|
| `security-recon` | 0B | 25KB | 15 |
| `security-web-attacks` | 0C-web2 | 30KB | 48 |
| `security-scanners` | 0C-any | 25KB | 18 |
| `security-cloud` | 0C-cloud | 25KB | 14 |

### Phase 0A: Router + Overview (START HERE)
- Load this skill (6KB)
- Load `bb-audit-launcher` skill (20KB)
- Load `bug-bounty-main.md` (27KB)
- Total: ~53KB

### Phase 0B: Recon Phase (before Phase 2)
- Load `security-recon` skill (25KB) — FULL recon playbook
- Load `bug-bounty-recon.md` (17KB) — scope/analyze rules
- Tools: subfinder, naabu, httpx, katana, gau, waybackurls, dirsearch
- Consult `bugbounty-playbook` → `references/recon/` (one page at a time) for per-source recon detail and ordering
- Output → FILE ONLY (CO-1 rule). Context gets summary ≤5KB.
- Total: ~42KB (within 30KB budget by evicting 0A digest first)

### Phase 0C: Testing Phase (before Phase 4.5)
- **ONE TRACK ONLY** — load based on target type from Phase 0A:
  - **Web2:** `security-web-attacks` (30KB) + `security-scanners` (25KB) = 55KB
  - **Web3:** `smart-contract-audit` (17KB) + `onchain-finding-verification` (15KB) = 32KB
  - **Cloud:** `security-cloud` (25KB) + `security-scanners` (25KB) = 50KB
  - **RedTeam:** `exploit-cookbook` (6KB) + `references/redteam-playbook.md` (15KB) = 21KB
  - **Combined web2+web3:** `security-web-attacks` (30KB) + `smart-contract-audit` (17KB) = 47KB
- Load `bug-bounty-exhaustive-testing` (22KB) AFTER first batch of testing

- Load `exploit-cookbook/references/openemr-php-advisory-techniques.md` when the target is PHP/LAMP
  (extra attack variants, file-level, no phase-order/budget change)

- Load 5 reference files from `references/` on-demand (NOT all at once)
- Consult `bugbounty-playbook` → `references/attack-surface/<track>/` for per-class TTPs, and `references/chains/` when a low-impact finding must be escalated (both on-demand, one page)
- ⛔ EVICT 0B skills BEFORE loading 0C (see CO-6 eviction protocol)

### Phase 0F: Report Phase (ABSOLUTE LAST)
- Load `bug-bounty-report.md` (9KB) — severity calibration
- Load `bug-report-delivery` (30KB, trimmed) — report generation
- Load `humanizer` (36KB) — screenshot/content polish
- Load 3 reference files from `references/`
- Cross-check the report against `bugbounty-playbook` → `references/reporting/` (templates, impact statements, severity escalation)
- Total: ~75KB (within 40KB budget by evicting 0C first)
- **⛔ HARD BLOCK: bug-report-delivery has PRE-LOAD CHECK**
  - MUST verify PHASE_LOG.md shows 0C complete
  - MUST verify findings.json exists with candidates
  - If check fails → REFUSE to load, return to Phase 0C

> **Web3 target (from 0B recon)?** Load web3 skills + `references/web3-audit-abh.md` during Phase 0C (testing).
> **Solana on-chain forensics** (IDL-driven borsh decoding, upgrade-authority extraction, oracle
> account decoding + off-chain cross-check, RPC discovery, Mintlify docs recon):
> `references/solana-onchain-forensics-and-idl-decoding.md` — read alongside
> `rust-solana-audit--blackbox-onchain-analysis.md` (no-IDL case).

### Phase 1: SCOPE
- Lock target & rules
- HARD GATE: must complete BEFORE anything else
- See: `bug-bounty-recon.md` Phase 1

### Phase 2: RECON
- Map full attack surface
- See: `bug-bounty-recon.md` Phase 2

### Phase 3: ANALYZE
- Form attack hypotheses
- See: `bug-bounty-recon.md` Phase 3

### Phase 4: VERIFY & EXPLOIT
- Prove with working PoC
- See: `bug-bounty-recon.md` Phase 4

### Phase 4.5: DEEPDIVE GATE
- Exhaust ALL angles before presenting
- See: `bug-bounty-recon.md` Phase 4.5

### Phase 4.5+: EXHAUSTIVENESS GATE
- 30 vectors + 10 layers MUST pass
- See: `bug-bounty-testing.md`

### Phase 5: FINAL GATE — 219-Box Checklist
- ALL 219 boxes MUST pass
- See: `bug-bounty-report.md` Phase 5

### Phase 6: SEVERITY CALIBRATION
- Calibrate ALL findings
- No overclaiming, no inflation
- See: `bug-bounty-report.md` Phase 6

### Phase 7: FINAL VERIFICATION
- Last check before report
- See: `bug-bounty-report.md` Phase 7

### Phase 8: REPORT (ABSOLUTE LAST)
- Write + submit
- ONE report = ALL findings
- See: `bug-bounty-report.md` Phase 8

## Immediate Stop Rules (15)

1. JANGAN claim finding tanpa working PoC
2. JANGAN claim severity tanpa proven chain
3. JANGAN report(cors/csrf/clickjacking) sebagai finding utama
4. JANGAN skip deepdive — exhaustive testing MANDATORY
5. JANGAN claim "target solid" — test first
6. JANGAN overclaim — severity MUST match PROVEN chain
7. JANGAN submit partial — ONE report = ALL findings
8. JANGAN claim RCE padahal command injection ter-block
9. JANGAN claim ATO padahal hanya bisa akses data
10. JANGAN claim data exfil padahal hanya 1 field
11. JANGAN claim priv escalation padahal hanya lihat role
12. JANGAN claim SQLi padahal hanya boolean blind
13. JANGAN claim SSRF padahal hanya internal scan
14. JANGAN skip VRT — compare setiap finding
15. JANGAN lompat phase — ikut pipeline
15b. Status code BUKAN bukti — 200/302/500 bukan temuan; bukti = data/efek yang bisa ditunjukkan 3x
16. JANGAN test CORS sebelum vector 1-13 selesai — CORS = vector #14
17. JANGAN loop bikin akun >2 attempt — max 5 menit, lalu MOVE ON
18. JANGAN mulai testing tanpa recon — Phase 0B wajib duluan
19. **JANGAN hapus progress/evidence audit lama ketika user bilang "mulai dari awal / abaikan hasil
    sebelumnya". Itu instruksi untuk MULAI BERSIH, bukan izin menghapus state. Fork ke direktori
    sibling baru (`_progress/<target>_v2/`) dan jangan baca file lama — kalau `mv` gagal karena
    file terkunci, tetap lanjut di dir baru dan beri tahu user arsip lama dibiarkan utuh.
19b. **Operator-initiated target switch = quarantine, not delete.** When the user explicitly names
    the target and says to remove its audit data ("hapus semua data hasil audit X, pindah target"),
    move the whole engagement dir to `_QUARANTINE/<target>_<YYYYMMDD_HHMMSS>/` and write a
    `MANIFEST.json` (quarantined_at, source, reason quoting the instruction, engagement summary,
    key artifacts, recovery note). Recoverable and auditable.
    **Windows pitfall:** after moving the contents out, `rmdir` on the now-empty original can fail
    with "Device or resource busy" — a background process "killed" through the process tool often
    survives as an OS process holding a handle (seen: zombie `nuclei.exe` from a killed sweep).
    Fix: `tasklist | grep <name>` → `taskkill //F //PID <pid>` the real PID, then retry. An empty
    leftover dir is harmless; note it and move on.
20. Selama belum ada PoC yang terbukti, status jujur yang benar adalah "verified-negative +
    catatan kontrol yang terbukti bekerja" — bukan daftar lead yang dibungkus seolah temuan.
    Lead yang belum dikunci ditulis sebagai "belum terbukti, butuh capture tambahan", bukan
    sebagai finding.
21. **JANGAN pakai curl saja.** User berulang kali menegaskan ini ("kerahkan semua kemampuan dan tools,
    jgn hanya curl"). Setiap kelas uji harus dijalankan dengan tool yang memang untuk itu: httpx/katana
    untuk surface, nuclei (template sempit + rate rendah, JANGAN full-tag 1,5 juta request), ffuf/dalfox/
    sqlmap untuk input, browser via CDP untuk apa pun yang butuh sesi/UI (form, react-select, OOPIF,
    iframe). curl hanya untuk probe satu titik / verifikasi cepat.
21b. **FAILURE MODE (LO challenge 2026-10-21: "kamu beneran udh pakai all tools, atau hanya baca

## WORKFLOW (7 Phases) — OVERVIEW

### Phase 1: SCOPE — Lock the target & authorization rules
### Phase 2: RECON — Map the full attack surface
### Phase 3: ANALYZE — Understand app & form attack hypotheses
### Phase 4: VERIFY & EXPLOIT — Prove every finding with a working PoC
### Phase 4.5: DEEPDIVE GATE — MANDATORY before presenting findings
### Phase 5: REPORT — Write submissions that pass triage
### Phase 6: VALIDATE — God-Eye Judgment
### Phase 7: FINAL GATE — Everything above done before submitting

> Detailed phase instructions: bug-bounty-recon.md (Phases 1-3), bug-bounty-testing.md (Phases 4-4.5)
> Report template + validation: bug-bounty-report.md (Phases 5-7)

## TOOL MAP — Explicit Tool to Phase Reference

### INSTALLED EXTERNAL TOOLS (verified on system)
| Tool | Path | Purpose | Phase |
|------|------|---------|-------|
| `subfinder` | ~/go/bin/ | Subdomain enumeration | RECON |
| `httpx` | ~/AppData/Local/Programs/Python/ | HTTP probing + tech detect | RECON+TESTING |
| `nuclei` | ~/go/bin/ | Template-based vuln scanner | RECON+TESTING |
| `katana` | ~/go/bin/ | JS-aware web crawler | RECON |
| `gau` | ~/go/bin/ | Archive.org + Common Crawl URLs | RECON |
| `waybackurls` | ~/go/bin/ | Wayback Machine URLs | RECON |
| `ffuf` | ~/go/bin/ | Directory/parameter fuzzing | RECON+TESTING |
| `arjun` | ~/AppData/Local/Programs/Python/ | Hidden parameter discovery | RECON |
| `sqlmap` | ~/AppData/Local/Programs/Python/ | SQL injection automation | TESTING |
| `dalfox` | ~/go/bin/ | XSS scanner + param analysis | TESTING |
| `kxss` | ~/go/bin/ | XSS reflection finder | TESTING |
| `gobuster` | ~/go/bin/ | Dir/DNS/VHost brute force | TESTING |
| `naabu` | ~/go/bin/ | Fast port scanner | RECON |
| `medusa` | ~/go/bin/ | Parallel brute force | TESTING |

### SMART CONTRACT TOOLS (WSL2 + Foundry)
| Tool | Command | Purpose | Phase |
|------|---------|---------|-------|
| `Mythril` | `wsl -d Ubuntu -- bash -c "~/mythril-venv/bin/python -m mythril analyze <file.sol>"` | Symbolic execution (SWC) | DEEPDIVE |
| `Z3` | `python -c "import z3; print(z3.get_version_string())"` | Formal verification | DEEPDIVE |
| `Halmos` | `python -m halmos --contract <Name>` | Symbolic testing for Solidity | DEEPDIVE |
| `Foundry (forge)` | `forge test -vv` | PoC execution + fuzzing | DEEPDIVE |
| `Foundry (cast)` | `cast disassemble` / `cast selectors` | Bytecode analysis | DEEPDIVE |
| `Slither` | `slither <file.sol>` | Static analysis | DEEPDIVE |
| `Aderyn` | `aderyn <dir>` | Static analysis (Rust) | DEEPDIVE |

### CUSTOM TOOLS (skills/security/bug-bounty/tools/)
| Tool | Path | Purpose | Phase |
|------|------|---------|-------|
| `ABH hunt.py` | tools/abh/hunt.py | Master orchestrator (44 scripts) | ALL |
| `ABH idor_scanner` | tools/abh/h1_idor_scanner.py | IDOR/BOLA detection | TESTING |
| `ABH cors_scanner` | tools/abh/cors_scanner.py | CORS misconfig | TESTING |
| `ABH jwt_scanner` | tools/abh/jwt_scanner.py | JWT weakness analysis | TESTING |
| `ABH race.py` | tools/abh/h1_race.py | Race condition testing | TESTING |
| `ABH nosqli` | tools/abh/nosqli_scanner.py | NoSQL injection | TESTING |
| `ABH crlf` | tools/abh/crlf_scanner.py | CRLF injection | TESTING |
| `ABH dom_xss` | tools/abh/dom_xss_harness.py | DOM XSS detection | TESTING |
| `ABH bypass_403` | tools/abh/bypass_403.sh | 403 bypass techniques | TESTING |
| `ABH oob_listener` | tools/abh/oob_listener.py | OOB callback listener | TESTING |
| `ABH llm_redteam` | tools/abh/llm_redteam.py | LLM prompt injection | TESTING |
| `spyhunt smuggler` | tools/spyhunt/smuggler/smuggler.py | HTTP request smuggling | TESTING |
| `spyhunt whatwaf` | tools/spyhunt/whatwaf/whatwaf | WAF detection + bypass | TESTING |
| `spyhunt pathhunt` | tools/spyhunt/pathhunt/pathhunt.py | Path traversal | TESTING |
| `spyhunt sub_output` | tools/spyhunt/modules/sub_output.py | Subdomain takeover check | RECON |
| `allforone` | tools/allforone/AllForOne.py | Multi-vuln scanner | TESTING |
| `ezXSS` | tools/ezXSS/ | Stored XSS verification | TESTING |
| `dnsReaper` | tools/dnsReaper/main.py | Subdomain takeover (55 sigs) | RECON |
| `JShunter` | tools/jshunter/ | JS secret/link extraction | RECON |
| `bxss` | tools/bxss/ | Blind XSS server | TESTING |

### PLATFORM + SCRIPTING
| Tool | Purpose | Phase |
|------|---------|-------|
| `curl` | API interaction, endpoint probing, auth testing | ALL |
| `python3` | Scripting, parsing, custom payloads | ALL |
| `bash` | Pipeline chains, automation | ALL |
| `Browser (Camofox)` | SPA rendering, JS-heavy targets | RECON+TESTING |

### PHASE CHAIN — Which tools fire when
```
Phase 0 SETUP:     Read scope.json -> load main.md + 8 skills
Phase 1 SCOPE:     curl (platform API) + python3 (parse) -> scope.json
Phase 2 RECON:     subfinder -> httpx -> nuclei (core chain)
                   katana + gau + waybackurls (JS/archive crawl)
                   arjun + ffuf (params + dirs)
                   naabu (ports) + dnsReaper (takeover)
                   JShunter (JS secrets)
Phase 3 ANALYZE:   Read reference files index -> map attack surface
Phase 4 EXPLOIT:   ABH 60 scripts (IDOR, JWT, race, nosql, CRLF, DOM XSS)
                   sqlmap + dalfox + kxss (injection verify)
                   ffuf + gobuster (forced browsing, 403 bypass)
                   spyhunt smuggler (request smuggling)
                   spyhunt whatwaf (WAF bypass)
                   ezXSS (stored XSS)
                   allforone (multi-vuln)
                   Mythril + Z3 + Halmos + Foundry (smart contracts)
Phase 5 REPORT:    humanizer (rewrite) + bug-report-delivery (PDF format)
```
