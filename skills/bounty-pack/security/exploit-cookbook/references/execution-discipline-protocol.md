# ⛔ EXECUTION DISCIPLINE PROTOCOL (MANDATORY)

## Senjata Audit — Hukum yang TIDAK BISA DILANGGAR

---

## CONFIG CONTEXT
```
context_length: 1,000,000 tokens
threshold: 0.80 → compression at 800K tokens
max_iterations: 200
max_tool_calls: 300
max_turns: 200
```

## WORDLIST LOCATIONS
```
D:/data hermes/wordlists/
├── 0B-recon/subdomains/     (3 files: 5K, 20K, 100K entries)
├── 0B-recon/directories/    (4 files: common, medium, large, raft)
├── 0B-recon/files/          (3 files: common, medium, large)
├── 0B-recon/params/         (1 file: 6453 params)
├── 0C-sqli/                 (auth bypass payloads)
├── 0C-xss/                  (polyglots + filter bypass)
├── 0C-ssrf/                 (cloud metadata + internal IPs)
├── 0C-nosqli/               (MongoDB injection)
├── 0C-cmdi/                 (command injection)
├── 0C-path-traversal/       (LFI payloads)
├── 0C-xxe/                  (XXE injection)
├── 0C-jwt/                  (JWT attacks)
├── 0C-graphql/              (GraphQL payloads)
├── 0C-waf-bypass/           (WAF evasion)
├── 0C-sensitive-files/      (config + admin wordlist)
├── 0C-web3/                 (smart contract attacks)
├── 0C-passwords/            (common passwords)
└── references/              (protocol files)
```

---

## RULE 1: LOADING ≠ EXECUTING

**The Rule:** Skill_view('X') WAJIB diikuti minimal 3 tool execution calls dalam 2 turn berikutnya. Kalau tidak → VIOLATION.

**Enforcement:**
```
skill_view('exploit-cookbook')        ← load
terminal('ffuf -u https://target.com/FUZZ -w wordlist.txt')  ← execute
terminal('nuclei -u https://target.com -t cves/')           ← execute
terminal('subfinder -d target.com')                           ← execute
```

**Checkpoint:** Setelah load skill, TULIS "EXECUTING NOW:" lalu langsung run tools. Jangan presentasi tabel dulu.

**Violation indicator:** 
- Load skill → presentasi tabel → load skill lain → presentasi tabel lagi
- Context habis 80% tanpa 1 tool execution
- Claim "ready to test" tapi belum run 1 command

---

## RULE 2: TIMEOUT = RETRY WITH STRATEGY, NOT SKIP

**The Rule:** Tool timeout WAJIB retry dengan strategy berikut. Skip hanya setelah 4 method gagal DAN documented.

### Timeout Values (2x Default)

| Tool | Timeout | Max Retry | Reasoning |
|------|---------|-----------|-----------|
| nuclei | 600s (10 min) | 4x | Paling sering timeout, butuh waktu |
| ffuf | 240s (4 min) | 3x | Quick scan |
| sqlmap | 600s (10 min) | 3x | Deep scan butuh waktu |
| subfinder | 120s | 2x | Fast tool |
| httpx | 180s | 2x | Medium |
| katana | 240s | 3x | JS crawl |
| gau | 180s | 2x | Archive pull |
| dalfox | 240s | 3x | XSS scan |
| amass | 600s | 2x | Deep enum |
| naabu | 180s | 2x | Port scan |
| Manual curl | 30s | 3x | Quick probe |
| WSL tools | 360s | 2x | Cross-platform overhead |
| Echidna | 600s | 2x | Contract fuzzer |
| Slither | 360s | 2x | Static analysis |
| Mythril | 600s | 2x | Symbolic execution |

### Fallback Chain (4 Methods)
```
Method 1: Run as-is dengan timeout penuh
  → timeout:600 nuclei -u target -t cves/
  → if timeout → METHOD 2

Method 2: Rate limit + long timeout
  → terminal(background=true, notify=true, timeout:1200)
  → nuclei -u target -t cves/ -rl 5 -c 3
  → poll setiap 120s
  → if timeout → METHOD 3

Method 3: Subset approach
  → timeout:600 nuclei -u target -t cves/ -severity critical,high
  → if timeout → METHOD 4

Method 4: Lightweight alternative
  → httpx instead of full scan
  → curl manual probing instead of nuclei
  → subprocess with custom timeout

SKIP: Only after all 4 methods attempted AND documented:
  "Attempted: [method1 result], [method2 result], [method3 result], [method4 result].
   All failed because [specific reason — WAF, rate limit, network, etc]."
```

**Checkpoint:** Sebelum skip, TULIS "Attempted: [method1 result], [method2 result], [method3 result], [method4 result]. All failed because [reason]."

**Violation indicator:**
- nuclei timeout 600s → "skip" tanpa retry
- Tool error → "gak jalan" tanpa alternative
- 1 attempt lalu give up
- Skip tanpa documenting 4 attempts

---

## RULE 3: RELOAD REFERENCES AFTER COMPRESSION

**The Rule:** Setelah context compression fires (output "[CONTEXT COMPACTION]"), WAJIB reload top 5 reference files sebelum lanjut testing.

**After Compression Checklist:**
```
1. read_file('exploit-cookbook/references/proven-exploits.md')
2. read_file('exploit-cookbook/references/vuln-chaining.md')
3. read_file('exploit-cookbook/references/graphql-attacks.md')
4. read_file('exploit-cookbook/references/html-injection-rules.md')
5. read_file('exploit-cookbook/references/sqli-auth-bypass-payloads.txt')
```

**Checkpoint:** TULIS "RELOADED after compression: [list files]" sebelum continue testing.

**Violation indicator:**
- Compression fires → lanjut testing tanpa reload
- Claim "sudah reloaded" tapi tidak ada read_file call
- Testing tanpa playbook knowledge

---

## RULE 4: VERIFICATION GATE BEFORE "COMPLETE"

**The Rule:** Sebelum claim "Phase 0C: COMPLETE", WAJIB TULIS:

```
VERIFICATION LOG:
- ffuf: [output file path] → [X results]
- nuclei: [output file path] → [X results]
- nuclei: [output file path] → [X results]  
- gau: [output file path] → [X results]
- katana: [output file path] → [X results]
- sqlmap: [output file path] → [X results]
- dalfox: [output file path] → [X results]
- manual testing: [X vectors tested]
- total tools executed: [X]
- total findings: [X]
- claims: [list]
```

**Enforcement:** Tanpa verification log = TIDAK BOLEH claim COMPLETE. Period.

**Violation indicator:**
- "Phase 0C: COMPLETE ✅" tanpa verification log
- Tabel tanpa file path / tool output
- Claim "tested 30 vectors" tapi gak ada nama 30 vectors

---

## RULE 5: DIVERSIFICATION — JANGAN ANCHOR PADA 1 FINDING

**The Rule:** Maksimal 15% context budget per finding. Sisanya untuk scanning dan exploration.

**Budget Allocation:**
```
Phase 0B (Recon):    20% context
Phase 0C (Testing):  60% context
  - Tool execution:  40%
  - Finding analysis: 15% (MAX per finding)
  - Navigation:      5%
Phase 0F (Report):   20% context
```

**Checkpoint:** Setelah spend >15% context pada 1 finding, WAJIB switch ke testing vector lain.

**Violation indicator:**
- 40% context spent justifying CORS severity
- 1 finding dominates entire Phase 0C
- Skip other vectors karena "udah nemu 1"

---

## RULE 6: SELF-VERIFICATION CHECKPOINT

**The Rule:** Setiap 5 tool execution calls, WAJIB verify:

```
SELF-CHECK (every 5 tool calls):
□ Tool 1: [name] → status: [ran/failed] → output: [file/empty]
□ Tool 2: [name] → status: [ran/failed] → output: [file/empty]  
□ Tool 3: [name] → status: [ran/failed] → output: [file/empty]
□ Tool 4: [name] → status: [ran/failed] → output: [file/empty]
□ Tool 5: [name] → status: [ran/failed] → output: [file/empty]
□ Total executed: [X]
□ Total skipped: [X]
□ Findings so far: [X]
□ Next actions: [list]
```

**Checkpoint:** Self-check setiap 5 calls. Jangan tunggu sampai selesai baru verify.

**Violation indicator:**
- 10+ tool calls tanpa verify
- Skip tool tanpa document
- "Tool jalan" tapi gak cek output

---

## SUMMARY

| Rule | Violation | Consequence |
|------|-----------|-------------|
| 1. Load ≠ Execute | Skill load tanpa tool execution | STOP → execute 3 tools immediately |
| 2. Timeout = Retry | Skip tanpa 4 method documented | STOP → retry with fallback chain |
| 3. Reload After Compression | Testing tanpa reload references | STOP → reload top 5 files |
| 4. Verification Gate | Claim COMPLETE tanpa log | STOP → generate verification log |
| 5. Diversification | Anchor pada 1 finding | STOP → switch to new vector |
| 6. Self-Verification | 5+ calls tanpa check | STOP → run self-check |

## HOW TO USE

1. **Start of audit:** Print this protocol
2. **Every skill load:** Check Rule 1
3. **Every timeout:** Check Rule 2
4. **After compression:** Check Rule 3
5. **Before claiming COMPLETE:** Check Rule 4
6. **Every finding:** Check Rule 5
7. **Every 5 tool calls:** Check Rule 6

> "These are not suggestions. They are enforcement rules. Follow them or stop claiming COMPLETE."

## RULE 7: TRACK EVERY REF FILE EXECUTION

**The Rule:** Setiap ref file execution WAJIB di-track di audit tracker. Update tracker SETIAP selesai execute 1 ref file.

### Tracker Update Format
```
[timestamp] File: [filename]
  Status: ✅ executed
  Code blocks tested: X/Y
  Payloads injected: X/Y
  Results: [findings/no findings]
  Notes: [timeout/blocked/etc]
```

### Verification Before COMPLETE
```
□ Tracker shows 84/84 refs executed
□ Total code blocks tested: X
□ Total payloads injected: X
□ Total findings documented: X
□ All findings verified (double-check)
□ Report generated with evidence
```

### Zero Findings Rule
```
ZERO FINDINGS hanya boleh claim jika:
  □ 84/84 refs executed di tracker
  □ Semua code blocks tested
  □ Semua payloads injected
  □ Semua results documented
  
Kalau ada ref belum executed → gak boleh claim zero findings
```

## WORDLIST RULE
```
1. Use FOCUSED wordlist FIRST (<2000 lines)
2. If results found → continue with focused
3. If NO results → try FULL wordlist
4. Document: which wordlist used, how many results
```

### Focused Wordlists
```
D:/data hermes/wordlists/0B-recon/focused/
├── directories/common-focused.txt (2000 lines)
├── files/common-focused.txt (2000 lines)
└── subdomains/subdomains-focused.txt (1000 lines)
```

### Full Wordlists (only if focused returns nothing)
```
D:/data hermes/wordlists/0B-recon/
├── directories/raft-large-directories.txt (62K lines)
├── files/raft-large-files.txt (37K lines)
└── subdomains/subdomains-top1million-20000.txt (20K lines)
```

## RULE 8: ZERO SKIP PROTOCOL
```
╔══════════════════════════════════════════════════════════════╗
║  EVERY FILE = LOAD → EXECUTE → DOCUMENT → VERIFY → NEXT     ║
║                                                              ║
║  Timeout? → RETRY 4 methods. NOT skip.                      ║
║  Context full? → Evict recon output. NOT references.         ║
║  "Already know"? → Execute anyway. NOT skip.                ║
║  "Not applicable"? → Check first. THEN skip with evidence.  ║
║                                                              ║
║  See: phase-execution-enforcement.md for full protocol.      ║
╚══════════════════════════════════════════════════════════════╝
```
