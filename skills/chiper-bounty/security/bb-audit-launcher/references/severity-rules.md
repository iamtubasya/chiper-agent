# Severity Rules & Finding Quality

## Hard Rule: NO SEVERITY INFLATION

**Severity WAJIB match dampak NYATA. Bukan assumed.**

```
CRITICAL: Financial loss proven, account takeover proven, full data exfil proven
HIGH: Privilege escalation proven, significant data access proven, auth bypass proven
MEDIUM: Business logic abuse proven, limited data access proven, state manipulation proven
LOW: Minor issues, requires chaining, theoretical only
INFORMATIONAL: Best practice violation, no security impact, by-design

LOW/INFO findings: MAX severity = LOW/INFO (TIDAK BOLEH diinflasi ke MEDIUM/HIGH)
CORS misconfig: MAX severity = P3 low note (TIDAK BOLEH jadi primary finding)
CSRF: MAX severity = P3 low note (TIDAK BOLEH jadi primary finding, butuh victim login + click)
Clickjacking: MAX severity = P3 low note (TIDAK BOLEH jadi primary finding, butuh victim visit)
SSL/TLS: MAX severity = INFORMATIONAL (TIDAK BOLEH diinflasi)
Suggestion header: MAX severity = INFORMATIONAL (TIDAK BOLEH diinflasi)
Open redirect: MAX severity = LOW (TIDAK BOLEH diinflasi ke MEDIUM)
```

**Jika severity inflated → report TIDAK SAH. Ulangi severity calibration.**

## Hard Rule: NO OVERCLAIMING

**Overclaiming = reputasi hancur + bounty ditolak + wasted tokens.**

```
❌ OVERCLAIMING PATTERNS (JANGAN LAKUKAN):
- "Critical RCE" padahal hanya command injection yang ter-block
- "Account Takeover" padahal hanya bisa akses data, tidak bisa login
- "Full data exfiltration" padahal hanya bisa akses 1 field
- "Privilege escalation" padahal hanya bisa lihat role, tidak bisa ubah
- "SQL injection" padahal hanya boolean blind, tidak bisa extract data
- "SSRF" padahal hanya bisa internal scan, tidak bisa akses cloud metadata
- "Business logic flaw" padahal hanya bisa manipulasi quantity 1-2 item
- "Mass assignment" padahal hanya bisa tambah field kosong, tidak bisa ubah role
- "Authentication bypass" padahal hanya bisa bypass rate limit
- "Session fixation" padahal hanya bisa fix session sendiri

✅ UNDERCLAIMING PATTERNS (TETAP PAKAI INI):
- "Low severity information disclosure" untuk info leak
- "Medium severity business logic flaw" untuk price manipulation
- "High severity authentication bypass" untuk real auth bypass
- "Critical severity account takeover" untuk full ATO chain

SEVERITY MUST MATCH PROVEN IMPACT, NOT ASSUMED IMPACT.
"Would be critical if X worked" = NOT CRITICAL (X doesn't work)
"Could be high if attacker has token" = NOT HIGH (attacker doesn't have token)
```

**Jika overclaiming ditemukan → report TIDAK SAH. Ulangi severity assessment.**

## Rule 7: SOCIAL ENGINEERING / PHISHING ≠ BOUNTY FINDING

**"User harus klik link" = OUT OF SCOPE di 95% program bounty.**

CORS misconfiguration yang butuh victim klik phishing link:
- ❌ TIDAK masuk report sebagai finding utama
- ❌ TIDAK claim severity HIGH/CRITICAL
- ✅ CATAT sebagai "low priority note" saja
- ✅ Fokus ke finding yang EXPLOITER langsung DAPAT akses tanpa interaksi user

**Prioritas temuan yang MASUK bounty (tanpa social engineering):**

| Priority | Finding Type | Contoh |
|----------|-------------|--------|
| 🔴 P0 | IDOR/BOLA | GET /api/v1/user/{id} → data user lain tanpa auth |
| 🔴 P0 | Auth bypass | Token validation skip, session fixasi |
| 🔴 P0 | Privilege escalation | User → Admin via endpoint |
| 🔴 P0 | RCE/SSRF | Server execute command/req ke internal |
| 🔴 P0 | SQL Injection | Database extract tanpa auth |
| 🟠 P1 | Business logic | Race condition, price manipulation |
| 🟠 P1 | Mass assignment | Add admin=true ke profile update |
| 🟠 P1 | Information disclosure | API keys, internal URLs, PII leak |
| 🟡 P2 | CSRF (state-changing) | POST action tanpa token, tapi BUTUH user login |
| 🟡 P2 | Open redirect | Bisa chain ke OAuth steal |
| ⚪ P3 | CORS (with credentials) | HANYA jika victim sudah authenticated + origin manipulation |
| ⚪ P3 | Clickjacking | UI redressing (jarang dibayar) |

**FILTER RULES untuk report:**

```
IF finding requires:
  ✗ Victim clicking link → OUT OF BOUNTY SCOPE
  ✗ Victim entering credentials → OUT OF BOUNTY SCOPE  
  ✗ Victim already authenticated + attacker trick them → WEAK (P3 max)
  ✗ Victim running malicious app → OUT OF BOUNTY SCOPE
  ✗ Physical access → OUT OF SCOPE

IF finding does NOT require victim interaction:
  ✓ Directly exploitable by attacker → BOUNTY WORTHY
  ✓ Attacker can chain with stolen data → BOUNTY WORTHY
  ✓ Server-side vulnerability → BOUNTY WORTHY
```

**ALTERNATIVE saat CORS testing:**

Jika menemukan CORS misconfig:
1. **Coba exploit TANPA phishing** — bisa direct request dari attacker machine?
2. **Check if endpoint returns sensitive data tanpa auth** — kalau iya, itu IDOR, bukan CORS
3. **Check if API key/secret ter-expose** — itu information disclosure, bukan CORS
4. **Check if endpoint accessible tanpa origin check** — itu BAC, bukan CORS
5. **Jika memang butuh victim interaction** — mark sebagai "potential chain enabler" saja, JANGAN jadi finding utama

**AUDIT PRIORITAS (ubah testing order):**

```
1. IDOR/BOLA testing (direct exploit, no interaction)
2. Auth bypass testing (token/cookie manipulation)
3. Privilege escalation (role manipulation)
4. RCE/SSRF testing (server-side)
5. SQL injection (database)
6. Business logic (race, price, state)
7. Mass assignment (role injection)
8. Information disclosure (keys, URLs, PII)
9. THEN only: CORS, CSRF, clickjacking (if no better findings)
```

## Rule 8: FINDING QUALITY CHECKLIST

Sebelum claim finding, tanya:

```
□ Bisa di-exploit TANPA victim interaction?
□ Attacker DAPAT langsung akses data/action?
□ Bisa di-reproduce oleh orang lain tanpa setup phish?
□ Program bounty BAYAR untuk jenis ini?
□ Severity match dampak NYATA (bkan assumed)?

Jika 3+ jawaban "TIDAK" → finding ini LEMAH, cari yang lebih kuat.
```

## Rule 9: JANGAN BERHENTI SETELAH DAPAT 1-2 TEMUAN LOW/INFO

**Dapat temuan low/info/by-design ≠ AUDIT SELESAI.**

```
❌ TEMUAN LOW DITEMUKAN → STOP → REPORT → SELESAI
✅ TEMUAN LOW DITEMUKAN → DOCUMENT → LANJUT ke vector lain → FIND BETTER

❌ "Saya sudah dapat CORS misconfig, ini cukup untuk report"
✅ "CORS ditemukan, tapi itu P3. Saya harus cari IDOR, auth bypass, race condition"

❌ "Sudah dapat info leak, cukup untuk claim finding"
✅ "Info leak itu INFORMATIONAL. Saya harus cari VULNS YANG EXPLOITABLE"

❌ "Sudah coba banyak, tidak ada yang lebih baik"
✅ "Saya coba approach berbeda: manual testing, chaining, advanced vectors"
```

**Audit baru selesai jika:**
1. ✅ SEMUA vector sudah di-test (bukan hanya 2-3)
2. ✅ SEMUA layer sudah selesai (bukan hanya surface)
3. ✅ 219 checklist boxes PASS
4. ✅ Tidak ada temuan yang bisa di-escalate lebih lanjut
5. ✅ Semua temuan sudah di-verify dengan 3x reproduction

**Jika masih ada vector yang belum di-test → AUDIT BELUM SELESAI.**

## Rule 10: REPORT HARUS BERISI FINDINGS YANG BOUNTY-WORTHY

**Report yang berisikan low/info/by-design = SAMPAH.**

```
✅ REPORT GOOD:
- 3-5 findings yang EXPLOITABLE (bukan theoretical)
- Severity match dampak NYATA
- PoC yang bisa di-reproduce
- Chaining analysis (jika ada)

❌ REPORT BAD:
- 10+ findings yang mostly low/info
- Severity inflated (low dipresentasikan sebagai medium/high)
- PoC tidak bisa di-reproduce
- Tidak ada chaining analysis
- CORS/CSRF/clickjacking sebagai findings utama
```

**Jika report hanya berisi low/info findings → AUDIT BELUM SELESAI. Cari yang lebih baik.**

## Finding Priority Order (HARUS diurutkan):

**Report WAJIB urutkan findings dari paling langsung exploitable:**

```
1. Direct data exposure (IDOR, information disclosure)
2. Auth bypass / privilege escalation
3. RCE / SSRF / SQL injection
4. Business logic abuse (race condition, price manipulation)
5. Mass assignment
6. Chain-enabled findings (requires chaining to exploit)
7. Low-priority notes (CORS, CSRF, clickjacking — if any)

WEB3-specific (if applicable):
- Direct exploit (reentrancy, flashloan, access control)
- Bridge exploit
- Governance attack
- Oracle manipulation
- Low-priority notes (unverified contract, minor issues)
```

**CORS/CSRF/Clickjacking HANYA masuk sebagai "Low Priority Notes" di bagian akhir report, BUKAN sebagai finding utama.**

---

## Calibration by example — why this pattern stops at that tier

The tier comes from **demonstrated impact**, never from the shape of the bug. Each row below shows the
sentence that keeps it at its tier; if you cannot break that sentence with evidence, the tier stands.

### Stops at LOW

| Pattern | Why it stops there |
|---|---|
| Self-XSS with no way to force a victim session | no cross-user consequence |
| dApp UI shows a wrong balance/price, nothing signed is affected | cosmetic, no exploitable path |
| Function reverts on odd input, retryable, no fund loss, no DoS beyond that call | UX issue |
| Bridge missing an event on a state change | observability gap only |
| Swap math rounds down by dust, consistently, no profitable size | theoretical only |
| Rounding that favours the protocol | no attacker profit path |

### Stops at MEDIUM

| Pattern | Why it stops there |
|---|---|
| IDOR read of another user's private object, authenticated, read-only | private data leak, no write |
| dApp shows "approve 10" but calldata requests unlimited allowance | future risk; drain not demonstrated |
| Missing `onlyOwner` on a fee-recipient setter | redirects FUTURE revenue, cannot touch principal |
| Bridge withdrawal with no rate limit, but validator signature check is sound | amplifies another bug, alone enables nothing |
| Sandwich on a low-liquidity pool with no on-chain min-out | per-trade loss, not systemic drain |
| Reward accrual precision drift, not triggerable on demand | fairness issue, no deterministic profit |

### Reaches HIGH / CRITICAL

| Pattern | What pushes it up |
|---|---|
| Stored XSS rendered in other users' authenticated pages | executes in the victim's session origin → High (the cross-user line is the whole difference from self-XSS) |
| SSRF returning metadata/internal content, or acting on it | credential theft / internal pivot → High; Critical when the credential yields infra control |
| SQLi that actually extracts records | mass breach → Critical |
| Logic flaw letting an attacker log in as ANY user | full ATO at scale → Critical |
| Reentrancy/ordering drain proven by fork PoC (attacker up, protocol down) | principal loss → Critical |
| Oracle manipulation with extraction demonstrated | principal loss → Critical |

Rule of thumb for the argument: **name the victim, name the gain, name the unit** (records, accounts,
currency). If any of the three is missing, you are describing a pattern, not a finding.
