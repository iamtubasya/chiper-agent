# Report Gate Checklist — 219 Boxes

**WAJIB 100% terpenuhi sebelum generate report. Satu saja unchecked = BLOCKED.**

```
═══════════════════════════════════════════════════════════════
REPORT GATE — ALL must be checked before report generation
═══════════════════════════════════════════════════════════════

PHASE 1 — RECON COMPLETE:
□ Subdomain enumeration done (subfinder/crt.sh/CT logs)
□ Live hosts fingerprinted (httpx)
□ Port scan done (naabu)
□ Directory/URL discovery done (gau, waybackurls, katana)
□ JS bundles analyzed (endpoints, secrets, config)
□ Technology stack identified (framework, WAF, CDN)
□ CSP/headers analyzed
□ All mapped endpoints recorded

PHASE 2 — AUTHENTICATED SURFACE COMPLETE:
□ ≥1-2 test accounts provisioned (or degraded per §1.0)
□ Both sessions captured (cookies + bearer)
□ Authenticated endpoint testing done
□ IDOR/BOLA sweep done (if 2 accounts available)
□ Privilege escalation tested
□ Business logic flows tested

PHASE 3 — ALL VECTORS TESTED (NO EXCEPTIONS):
□ XSS (reflected, stored, DOM)
□ SQLi / NoSQLi
□ SSRF (internal endpoints, cloud metadata)
□ IDOR / BOLA (horizontal + vertical)
□ Race conditions (double-spend, TOCTOU)
□ GraphQL (introspection, batching, alias injection)
□ Authentication bypass (JWT none, OAuth misconfig, session fix)
□ CORS (origin reflection, null, wildcard+creds)
□ File upload (extension bypass, content-type, polyglot)
□ Cache poisoning / deception
□ 403 bypass (all techniques from playbook)
□ Mass assignment / property pollution
□ Password reset poisoning (host header, link manipulation)
□ Broken access control (function-level, method tampering)
□ CSRF on state-changing endpoints
□ Open redirect → XSS / phishing chain
□ Command injection (if user input reaches OS commands)
□ Template injection (SSTI)
□ WebSocket abuse
□ API versioning (old API with weaker auth)
□ Rate limiting abuse
□ Third-party service abuse (Sentry, Segment, Auth0, etc.)
□ Source maps / __NEXT_DATA__ / env-config.js analysis

WEB3 (if applicable):
□ Reentrancy
□ Flashloan attack
□ Access control (unprotected functions)
□ Oracle manipulation
□ Integer overflow/underflow
□ Delegatecall injection
□ Bridge message validation
□ Governance (flashloan voting)
□ Fee-on-transfer edge cases
□ Math/logic errors

PHASE 4 — ALL FINDINGS VERIFIED:
□ Each finding has working PoC (not theoretical)
□ Each finding retested ≥3 times (consistent repro)
□ Chain analysis done (can weak findings combine into strong?)
□ Severity matches PROVEN chain (not assumed chain)
□ By-design analysis done (arguments FOR + AGAINST)
□ Impact assessed (data, financial, account, system)

PHASE 5 — EXHAUSTION CONFIRMED:
□ "Informational" findings — attempted escalation paths checked
□ "By-design" findings — compared across endpoints (consistent?)
□ No vector skipped without documented reason
□ "Nothing found" → documented which 20+ vectors tested
□ Time budget respected (20/60/20 rule: recon/exploit/report)

PHASE 6 — EXPLOIT VERIFICATION (NON-NEGOTIABLE):
═══════════════════════════════════════════════════════════════
Setiap finding WAJIB punya PROOF yang bisa di-duplicate oleh siapapun.
Tanpa ini, finding TIDAK BOLEH masuk report.
═══════════════════════════════════════════════════════════════

□ Finding di-reproduce MINIMAL 3x (bukan 1x lucky hit)
□ Setiap reproduce pakai FRESH session/token (bukan cache)
□ Setiap reproduce hasilnya KONSISTEN (bukan random)
□ PoC pakai curl/Python yang COPY-PASTE bisa jalan
□ Semua variabel di-PARAMETERIZE (URL, token, ID bisa diganti)
□ Request + Response DI-CAPTURE lengkap (header, body, status code)
□ Timestamp dicapture (bukti timing bisa berubah)
□ Jika finding butuh precondition (akun, data), precondition DIDOKUMENTASI
□ Jika finding race condition, timing window DIDOKUMENTASI
□ Jika finding butuh chaining, setiap step di-chain VERIFIED SEBAGAI UNIT

□ Finding VERIFIED by user or independently reproducible
□ Finding bukan "could theoretically" — harus "DID exploit"
□ Finding bukan "might work if X" — harus "WORKS with X proven"

═══════════════════════════════════════════════════════════════
SELF-TEST: Bisa agent lain run PoC ini dan dapet hasil sama?
  YES → INCLUDE in report
  NO  → FIX the PoC or DISCARD the finding
═══════════════════════════════════════════════════════════════

PHASE 7 — SEVERITY CALIBRATION:
→ See: references/severity-rules.md

═══════════════════════════════════════════════════════════════
IF ANY BOX UNCHECKED → DO NOT GENERATE REPORT. GO BACK.
═══════════════════════════════════════════════════════════════
```

### Common Early-Stop Traps (WHY this gate exists):

| Trap | What happens | What SHOULD happen |
|------|-------------|-------------------|
| First finding is informational | Stops, generates partial report | Continue ALL vectors, chain later |
| Cloudflare blocks SQLi | Concludes "WAF blocks injection" | Pivot: business logic, IDOR, auth, CORS |
| Signup blocked | Says "can't test authenticated" | Degradation path: 1-account vertical, anon vectors |
| 5 vectors negative | "Target looks secure" | 20+ vectors remain untested |
| Finding is by-design | Drops it, moves to report | Still check: does it chain? cross-endpoint comparison? |
