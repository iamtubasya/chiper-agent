# Program scope + exclusion intake (Step 0)

Read the target's own published rules **before** touching a scanner. The scope + exclusion list
decides reward vs $0 and defines authorised footing. Getting this first turns "fire everything" into
"spend effort where it pays".

## The three lists to extract
1. **In-scope assets** — exact hostnames / wildcards; write down the *explicit excludes* too.
2. **Reward tiers** — which asset class pays most, so you prioritise correctly.
3. **Exclusions / non-qualifying** — the highest-signal list. It names every finding triage will
   close as informational / $0 regardless of PoC quality.

## Recurring exclusion patterns (kill scanner volume on sight)
Vendor programs re-use the same non-qualifying list almost verbatim:
- vulnerability-scanning reports that don't describe the impact
- missing security headers / cookie flags
- banner grabbing / software version disclosure
- open redirect alone (informational unless chained into something bigger)
- reflected XSS / self XSS
- user enumeration (unless you demonstrate the absence of rate limits)
- most brute-force, DoS, phishing / fake-site / fraud
- issues requiring a MITM position or user network control
- local privilege escalation that isn't chained to a network vuln
- theoretical findings without a standalone PoC (raw screenshots / Burp replays alone are rejected)
- root cause in upstream open-source / third-party, not vendor code
- findings from QEMU / emulator environments

**Implication:** volume scanners mostly produce reports that get auto-closed on these programs.
Lead with manual, impact-first work on the highest-tier asset.

## Worked example — Synology (recorded 2026-10)
- `https://www.synology.com/.well-known/security.txt` → `Policy: https://www.synology.com/security/bounty_program`
- Three tiers:
  - **OS** (DSM 7 / SRM 1.3 / Camera fw / BeeStation OS): up to **$30k** — but tested on *your own*
    device/VM, not their infra. This is where most DSM CVE research actually happens.
  - **Software & C2 cloud** (`*.account.synology.com`, `*.identity.synology.com`,
    `*.c2.synology.com`): up to **$10k**.
  - **Web services** (`*.synology.com`, excluding `openstack-ci-logs`, `router`, `ask`): up to **$5k**.
- Exclusions matched the generic list above, plus: directory traversal on `*archive.synology.com`,
  reflected file download, version disclosure, and 0-days disclosed within 90 days.
- **Takeaway:** "audit synology.com" literally = the $5k web tier. The $30k lives in self-hosted
  DSM research.

Non-intrusive auth-surface notes gathered with single public requests only (OIDC discovery):
`identity.synology.com` is the OIDC provider (Hydra-style:
`/.well-known/openid-configuration` + `/.well-known/jwks.json`); the chain is
`account → identity/oauth2/auth → signin.synology.com?login_challenge=…`; `c2` and `account` both
expose `/api/c2`; community/event apps are Laravel (`eyJpdi…` session cookies). These are leads, not
findings — surface mapping only.

## Intigriti program pages — the whole programme is in the HTML, one request

`app.intigriti.com/programs/<org>/<prog>/detail` is an Angular + Stencil SPA, and `web_extract` can
fail on it (`DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content`). You do not
need a browser and you do not need an account: the fully rendered programme — description, bounties
table, asset/scope table, Rules of Engagement, Known Issues, FAQ — is server-rendered into the HTML
response. Measured: **475 KB HTML → 15 KB of text**, containing everything.

```bash
curl -sS -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0" \
     -o detail.html -w "%{http_code} %{size_download}\n" \
     "https://app.intigriti.com/programs/<org>/<prog>/detail"

python - <<'EOF'
import re
h=open('detail.html',encoding='utf-8',errors='ignore').read()
t=re.sub(r'<script[\s\S]*?</script>','',h)
t=re.sub(r'<style[\s\S]*?</style>','',t)
t=re.sub(r'<[^>]+>','\n',t); t=re.sub(r'\n{2,}','\n',t)
open('detail.txt','w',encoding='utf-8').write(t)
EOF

grep -n -iE "in scope|out of scope|tier|bounty|validation time|known issues" detail.txt
```

What to lift, and where it actually lives:

| Section | Marker in the HTML | What you get |
|---|---|---|
| Assets / Domains | `Assets` … `Expand all` block, rows `URL` / `iOS` / `Android` + `Tier 1`/`Tier 2` | the authoritative in-scope list, per-asset tier. `In scope` is followed by `Out of scope` + *"Any domain that is not listed in the Domains section, is out of scope"* — treat that sentence as the binding boundary |
| Bounties | `Tier 1` / `Tier 2` rows under `Bounties` | per-severity €, and which tier pays more |
| Rules of Engagement | `<app-program-testing-requirements-detail>` | `@intigriti.me  Required`, `User agent`, `Automated tooling  max. N requests/sec`, `Request header` |
| Known Issues | `Known Issues (date last updated: …)` | the vendor's own auto-close list, often longer and more specific than the generic exclusion list |
| FAQ | `FAQ` block | **sometimes publishes shared test credentials with an account balance, plus the exact reservation/test-account rules** |

Three things this changes about the run:

1. **The rate limit is a hard number, not a vibe.** A page that says `max. 2 requests/sec` means
   every scanner gets `-rl 2`/`-rate 2` from the first command, and "do not use automated test-tools
   on our domains, IP will be blocked" means gentle-automated, not manual-only.
2. **Read the FAQ before you fight the signup form.** A programme that hands out
   `intigriti-N@<target>` accounts with a balance exists specifically so the purchase flow is
   testable; discovering that after 40 minutes of registration attempts is wasted work (the reverse
   is also true — if those accounts are dead, say so in the report rather than silently skipping the
   paid flow).
3. **Known Issues is where your best recon lands.** An item like *"Account activation without access
   to the email inbox of the account due to exposing the activation code from the API is known"* tells
   you that class is already claimed — and, by implication, that the activation-code path has been
   mapped before you, so target the adjacent step instead.

