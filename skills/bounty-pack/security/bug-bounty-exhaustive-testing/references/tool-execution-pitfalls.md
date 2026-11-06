# Tool Execution Pitfalls — Windows + Hermes

## nuclei

**Problem:** Times out with default settings (too many templates).

**REAL timing (NASA VDP 2026-09-19):** 6564 templates × 8 targets @ rate limit 5/sec = ~46K requests = **2.5 hours total**. With clustering (367 clusters, reduced 2488 requests) still takes **1.5+ hours**.

```bash
# BAD — hangs for minutes
nuclei -u https://target.com

# BAD — foreground with high timeout still times out
nuclei -u https://target.com -severity high,critical -rl 10 -timeout 10  # still > 420s on 8 targets

# GOOD — background + rate limit + batch
# Option A: background (preferred)
nuclei -l targets.txt -severity high,critical -rl 5 -c 3 -timeout 10 -silent -o nuclei.txt
# → run with terminal(background=true), do other work, check results later

# Option B: batch per 3 targets (faster per-batch, still hours total)
echo "https://target1.com
https://target2.com
https://target3.com" | nuclei -severity high,critical -rl 5 -timeout 10 -o batch1.txt

# Option C: nuclei templates with specific tags only (faster)
nuclei -l targets.txt -tags wordpress,nginx,apache -rl 10 -o nuclei_fast.txt
```

**Polling anti-pattern (DON'T do this):**
```bash
# BAD — agent polled process every 10 seconds for 90 minutes
process(action='poll', session_id='proc_xxx')  # repeated 500+ times
# Wasted 500+ tool calls doing nothing useful

# GOOD — run nuclei, do other work, check ONCE when done
# 1. terminal(background=true) → nuclei running
# 2. Execute dalfox, arjun, manual tests meanwhile
# 3. process(action='poll') ONCE after other work done
# 4. If still running, wait longer, check again later
```

**When nuclei returns 0 results on well-hardened targets:**
- 0 results after full scan = target genuinely has no known vulns in template DB
- NOT a reason to claim "zero findings" — still need manual testing
- Document: "nuclei: 0 results across 6564 templates, 8 targets"

## ffuf

**Problem:** SecLists not installed on Windows. Default wordlist path fails.
```bash
# BAD — wordlist not found
ffuf -u https://api.target.com/FUZZ -w /usr/share/wordlists/seclists/...

# GOOD — create inline wordlist
cat > /d/data hermes/bug-bounty/_progress/target/api_wordlist.txt << 'EOF'
admin
login
api
v1
v2
graphql
swagger
actuator
metrics
health
debug
config
env
backup
internal
private
test
EOF

ffuf -u "https://api.target.com/FUZZ" -w api_wordlist.txt -mc all -fs 42 -c -v
```

## subfinder

**Problem:** Only finds subdomains with active DNS records. Misses historical ones.
```bash
# ALWAYS pair with gau or waybackurls
subfinder -d target.com -silent > subs.txt
echo "target.com" | gau --threads 5 2>/dev/null | grep -oP 'https?://\K[a-zA-Z0-9.-]+\.target\.com' | sort -u >> subs.txt
```

## katana

**Problem:** Returns SPA routes (HTTP 200 + HTML body) — not real API endpoints.
```bash
# Check if endpoints are real API or SPA routes
katana -u https://target.com -jc -d 3 2>/dev/null | while read url; do
  ct=$(curl -s -I "$url" | grep -i content-type | head -1)
  echo "$ct | $url"
done
# Filter for: application/json only
```

## wscat / WebSocket

**Problem:** Anti-bot protection (Aliyun, Cloudflare) blocks WebSocket connections.
```bash
# If wscat returns 403 with aliyungf_tc cookie → NOT a vulnerability
# It's a security control. Document as "blocked by anti-bot" and move on.
```

## Python ssl.wrap_socket

**Problem:** Removed in Python 3.12+. User has Python 3.14.
```python
# BAD — AttributeError
import ssl
ssl.wrap_socket(sock)

# GOOD — use SSLContext
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
secure_sock = ctx.wrap_socket(sock, server_hostname=host)
```

## GOPATH on Windows

**Problem:** New bash shells don't have GOPATH in PATH.
```bash
# Add to start of every terminal call
export GOPATH="C:/Users/WINDOWS10/go"
export PATH="$PATH:$GOPATH/bin"
```

## Context Budget Exhaustion During Audits

**Problem:** Agent uses 100+ tool calls on skill_view + process poll + status tables, runs out of budget before testing is complete.

**Real cost breakdown (NASA VDP):**
- skill_view calls: ~15 tool calls
- process poll (nuclei): ~100+ tool calls (polling every 10 seconds for 3 hours)
- status tables / summaries: ~10 tool calls
- ACTUAL TESTING (ffuf, curl, etc.): ~25 tool calls
- Total: ~150 tool calls = session budget exhausted

**The fix — budget-aware execution:**
```
PRIORITY 1: Run recon + fuzzing tools FIRST (subfinder, gau, katana, nuclei bg, ffuf)
PRIORITY 2: Manual testing per playbooks (curl per template)
PRIORITY 3: Status reporting (only AFTER tools have run)
NEVER: Skill view loops, process poll loops, summary writing BEFORE execution
```

**Rule: 50% of budget must be spent on TOOL EXECUTION, not skill loading or status reporting.**

## Process Polling Anti-Pattern

**Problem:** Agent polls `process(action='poll')` every few seconds for minutes/hours. Each poll is a tool call. 100 polls = 100 tool calls wasted.

**NASA VDP example:** Nuclei running in background. Agent polled 100+ times over 3 hours. Each poll returned `{status: "running", output_preview: same text}`. Zero useful information gained.

**Correct approach:**
1. Start background process → get session_id
2. DO OTHER WORK (run dalfox, arjun, curl tests)
3. Check process ONCE after 30+ minutes
4. If still running, set a reminder and do MORE other work
5. NEVER poll in a tight loop
