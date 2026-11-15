---
name: argus
description: Argus — the all-seeing scanner suite. Six automated scanners for high-value web + LLM bug classes — CORS misconfiguration (origin reflection / null / credentialed read), CRLF & host-header injection, NoSQL injection (operator auth-bypass / $where blind), JWT attacks (alg:none / RS256→HS256 confusion / secret crack), out-of-band confirmation of blind SSRF/XXE/SQLi/RCE/Log4Shell via interactsh, and an LLM red-team corpus (prompt-injection / jailbreak / system-prompt leak / exfil / indirect injection). Use when a target exposes a JSON API, a login endpoint, JWT auth, a parameter that might reach the server, a chatbot/agent, or any endpoint suspected of a blind/out-of-band bug.
---

# ARGUS — THE ALL-SEEING SCANNER SUITE

> Named for Argus Panoptes, the hundred-eyed giant. Six "eyes" that surface what
> ordinary scans miss: two of the most common web2 classes (CORS, CRLF), the
> NoSQL "db" surface, JWT forging, **blind-bug confirmation via OOB** (the eye
> that sees the invisible — unblocks an entire severity band), and automated LLM
> red-teaming. All pure-Python, no new deps. Core logic is offline-testable.

---

## 0. ROUTING — which tool for what

| Signal on the target | Tool / command |
|---|---|
| API reflects `Origin`, or `ACAO`/`ACAC` headers seen | `/cors` |
| Param reaches a redirect / `Location` / log / response header | `/crlf` |
| JSON login or `{user,pass}` body, Mongo/Mongoose stack | `/nosqli` |
| `Authorization: Bearer ey...` / JWT in cookie or storage | `/jwt-scan` |
| Suspected **blind** SSRF/XXE/SQLi/RCE (no in-band signal) | `/oob` |
| Chatbot / agent / LLM feature | `/llm-redteam` |
| 50–500 in-scope hosts, hunting leftover internal docs / configs / dev files | `/sweep` → `scripts/host_exposure_sweep.py` |
| Dead-feature sweep, but hit rate is zero after filtering | `references/broad-host-exposure-sweep.md` |

---

## 1. CORS — `/cors`

```bash
tools/cors_scanner.py https://api.target.com/me --cookie "session=..."
tools/cors_scanner.py -l recon/target.com/urls/api.txt --json
```

Sends crafted `Origin` headers, classifies `Access-Control-Allow-Origin` /
`Access-Control-Allow-Credentials`:

- **CRITICAL** — reflects attacker origin **with** `ACAC: true` → cookie-auth'd cross-origin read (account-data exfil).
- **HIGH** — `null` origin trusted with credentials.
- **MEDIUM** — reflects without creds (exploitable when auth = non-cookie token), or trusts http downgrade.
- Probes suffix/prefix regex bypass (`target.com.evil`, `notarget.com`) and subdomain trust (chains with [takeover](../../commands/takeover.md)).

**Always pass `--cookie` with a live session** — the credentialed path is the win.

## 2. CRLF / host-header — `/crlf`

```bash
tools/crlf_scanner.py "https://target.com/r?u=x" --host-header
```

Injects encoded CRLF (`%0d%0a`, double-encoded, UTF-8 overlong `%E5%98%8A%E5%98%8D`)
trying to land `Set-Cookie: crlftest=1` in the response. `--host-header` also tests
`Host` / `X-Forwarded-Host` / `Forwarded` injection and flags attacker-host
reflection in `Location` (password-reset poisoning). Impact: session fixation,
open redirect, cache poisoning, reset poisoning.

> `urllib` strips raw `\r\n` from URLs by design — the **encoded** variants are
> what actually go on the wire.

## 3. NoSQL injection — `/nosqli`

```bash
tools/nosqli_scanner.py --login https://t/api/login --user-field email --pass-field password
tools/nosqli_scanner.py --query "https://t/api/items?id=1"   # emits bracket variants
```

- Operator auth-bypass: `{"email":{"$ne":null},"password":{"$ne":null}}`
- Bracket syntax (Express/qs): `email[$ne]=&password[$ne]=`
- `$where` time-based blind: `{"$where":"sleep(5000)"}` → server-side JS eval = **CRITICAL**

Sends a wrong-credential baseline first, flags a finding when status flips
401→200, body length jumps >25%, or the `$where` payload delays the response ≥3.5 s.

## 4. JWT attacks — `/jwt-scan` (offline)

```bash
tools/jwt_scanner.py "$TOKEN" --analyze
tools/jwt_scanner.py "$TOKEN" --alg-none --set role=admin
tools/jwt_scanner.py "$TOKEN" --confuse --public-key jwks_pub.pem --set role=admin
tools/jwt_scanner.py "$TOKEN" --crack --wordlist secrets.txt
```

- `--alg-none` — strip signature, set `alg` to none/None/NONE/nOnE.
- `--confuse` — RS256→HS256: re-sign with the server's **public** key as HMAC secret.
- `--crack` — brute the HS256 secret.
- `--analyze` — flags `alg=none`, missing `exp`, trust-bearing claims (`role`/`is_admin`/`scope`), `kid` (probe for traversal/SQLi).

Get the public key from `/.well-known/jwks.json` or `/jwks.json`. Replay the
forged token against an authed endpoint — acceptance = **auth bypass / privesc**.

## 5. Out-of-band confirmation — `/oob`  ⭐

The highest-leverage tool. Confirms **blind** bugs that have no in-band signal by
correlating interactsh callbacks to the firing payload.

```bash
# 1. listener (prints your OOB domain, streams interactions)
tools/oob_listener.py --listen > inter.jsonl
# 2. payloads embedding a unique marker per injection point
tools/oob_listener.py --payloads cXXXX.oast.fun --json > payloads.json
# 3. correlate received callbacks
tools/oob_listener.py --correlate inter.jsonl --payloads-file payloads.json
```

Covers blind SSRF, XXE (incl. OOB-DTD exfil), SQLi (MSSQL `xp_dirtree` / MySQL
`LOAD_FILE` / Oracle `UTL_HTTP` / Postgres `COPY…PROGRAM`), RCE
(`curl`/`nslookup`/backticks), and Log4Shell (`${jndi:ldap://…}` + `${lower:j}`
filter bypass). Needs `interactsh-client` (`/arsenal interactsh-client` for the
install hint); payload generation + correlation work offline without it.

**Why it matters:** without OOB you cannot *prove* blind SSRF/XXE/SQLi/RCE — a
whole band of Critical findings is otherwise un-submittable.

## 6. LLM red-team — `/llm-redteam`

```bash
tools/llm_redteam.py --url https://t/api/chat --field message
tools/llm_redteam.py --url https://t/api/chat \
  --template '{"messages":[{"role":"user","content":"{{PAYLOAD}}"}]}' \
  --response-path choices.0.message.content --category jailbreak
```

Fires a categorized corpus — `prompt-injection`, `jailbreak`,
`system-prompt-leak`, `data-exfil`, `indirect-injection`, `guardrail-bypass` —
and uses a **canary token** (`RT_PWNED_xxxx`) for reliable hit detection.
`--header "Authorization: Bearer ..."` for authed bots.

> A bare injection is **Informational** until chained. Escalate to chatbot IDOR,
> data exfil (the markdown-beacon hit proves a channel), or RCE if the agent has
> a code/tool capability. See [web2-vuln-classes §11](../web2-vuln-classes/SKILL.md)
> and [bug-bounty Agentic AI (ASI01–ASI10)](../bug-bounty/SKILL.md).

## 7. Broad-host exposure sweep — `/sweep`

```bash
python scripts/host_exposure_sweep.py --hosts recon/scope_live_hosts.txt \
  --out scans --rps 4 --header "X-Bugcrowd: Bugcrowd-<user>"
```

Bounded replacement for a full-template nuclei run over a large host inventory: the
exposure+misconfig+takeover corpus advertises ~1.5M requests for 260 hosts and sat at
"0% in 32 minutes" at a program-friendly 4 rps. This sweep does 260 hosts × 14 paths
≈ 3.6k requests in ~8.5 min → 99 raw hits, **35** after filtering.

The filters are the whole value: compare every response against the host's **root
document** (identical sha / near-identical length ⇒ SPA catch-all) and drop
**interstitial markers** (`Cloudflare Access` login pages were 45 of the 99 raw hits).
Triage rule: leftover **internal doc** = P4 finding; public site key / vendor template
README / SPA shell = noise — say which in the report. Measured numbers, host-scope
manners and the complementary checks: `references/broad-host-exposure-sweep.md`.

---

## CHAINS

- CORS credentialed read → harvest CSRF token / PII / API key → ATO.
- Subdomain-trust CORS + [subdomain takeover](../../commands/takeover.md) = clean credentialed-read exploit.
- JWT forge (`--alg-none`/`--confuse` + `--set role=admin`) → privesc → IDOR sweep.
- Blind SSRF (confirmed via `/oob`) → cloud metadata → credential theft.
- LLM indirect injection → chatbot IDOR / exfil channel.
