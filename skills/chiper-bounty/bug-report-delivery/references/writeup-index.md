# Writeup Index — Curated from 2 Repos
> Immunefi + Google VRP writeup collections for report quality benchmarking.

## Immunefi Writeups
- https://github.com/sayan011/Immunefi-bug-bounty-writeups-list
- ⭐1.2K — Curation of all Immunefi bug bounty writeups
- Covers: DeFi exploits, bridge attacks, oracle manipulation, flashloans
- Use as: severity calibration benchmark for Web3 findings

### Key Patterns from Immunefi Writeups
1. **Clear PoC** — every critical finding has step-by-step reproduction
2. **Impact quantification** — dollar amounts, affected users
3. **Root cause analysis** — not just "what" but "why"
4. **Fix suggestion** — specific code change, not vague advice
5. **CVSS scoring** — justified severity with vector

## Google VRP Writeups
- https://github.com/xdavidhu/awesome-google-vrp-writeups
- ⭐1.7K — Writeups from Google VRP Bug Bounty
- Covers: SSRF, RCE, IDOR, information disclosure
- Use as: report quality standard for Web2 findings

### Key Patterns from Google VRP
1. **Scope awareness** — findings within program scope
2. **Demonstrated impact** — not theoretical
3. **Clean reproduction** — minimal steps, clear screenshots
4. **Appropriate severity** — honest self-assessment
5. **Professional tone** — no hype, no fear-mongering

---

## Report Quality Checklist (from writeups)

### Before Writing
- [ ] All findings verified with working PoC
- [ ] Severity calibrated against VRT/Immunefi benchmarks
- [ ] Impact chain proven end-to-end

### During Writing
- [ ] Title: clear, specific (not "Security Issue Found")
- [ ] Summary: 2-3 sentences max
- [ ] Severity: justified with CVSS vector
- [ ] Steps to Reproduce: numbered, copy-pasteable
- [ ] Impact: quantified ($, users, data)
- [ ] Remediation: specific code/config change

### After Writing
- [ ] Read as triager — is it clear?
- [ ] No overclaiming (see bb-audit-launcher banned patterns)
- [ ] Screenshots/diagrams support the narrative
- [ ] References attached (tool output, logs)

---

## Cross-References
- Report generation → `bug-report-delivery` (Phase 0F)
- Severity calibration → `bb-audit-launcher/references/severity-rules.md`
- 219-box checklist → `bb-audit-launcher/references/checklist-219-boxes.md`
