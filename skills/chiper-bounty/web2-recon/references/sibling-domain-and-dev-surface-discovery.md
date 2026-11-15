# Sibling-domain + dev-environment surface discovery

The single biggest surface expansion in a 2026-10 bank engagement came from moves a plain
`subfinder -d target.com` misses. The brand's public marketing apex can be a dead end while the
company's *engineering* domain is a 14k-name estate.

## 1. Enumerate the TECH-ORG domain, not just the brand domain
- `subfinder -d target.com -silent` returned **0 rows** for the marketing apex.
- `subfinder -d <techorg> -all` (the engineering subsidiary domain seen in the CSP and asset URLs)
  returned **14,404 names**. certspotter on the brand TLDs gave **85**.
- Run BOTH, merge, dedupe. `-all` costs time but on a tech-org domain it is the difference between
  73 live hosts and 378.

## 2. Find the SIBLING corporate domain through redirects
A cross-domain `Location:` hands you a whole new zone:
```
argocd.cd-test.<techorg>  --302-->  https://argo.test.cd.<OTHER-CORP-TLD>/
```
`<OTHER-CORP-TLD>` was **not** in the `security.txt` canonical list. Always `curl -sI` every
interesting host and read `Location:`; then run CT on the new zone as well. Corporate groups own
multiple TLDs (`.com`, `.se`, `<brand>tech.se`, …).

## 3. certspotter as the CT source when crt.sh is unreachable
crt.sh sometimes answers **HTTP 000** from certain egresses. certspotter needs no key:
```bash
curl -s "https://api.certspotter.com/v1/issuances?domain=<d>&include_subdomains=true&expand=dns_names" \
 | python3 -c "import sys,json;d=json.load(sys.stdin);[print(n) for e in d for n in e.get('dns_names',[])]"
```
Apply it to every TLD **and** the tech org.

## 4. Verify a bulk-resolution count before trusting a negative (CRITICAL)
A bulk resolver reporting `1 of 14410 resolved` is a **run failure**, not a result. Two independent
traps produced that exact false number in one session.

Cross-checks that catch it:
- **Spot-check hosts you KNOW are live** (`www.<brand>`, an app host) through the same pipeline.
- **Compare resolvers**: one returned empty for *every* name while `nslookup <h> 8.8.8.8` and
  `python -c "import socket;print(socket.gethostbyname('<h>'))"` resolved fine.
- **Count sanity**: ~500 of 14,410 resolving suits a CT-shadow list; 1 of 14,410 does not.
- **Confirm every flag exists** before the run. One unsupported flag (e.g. a `-retries` that the
  binary does not define) makes the whole invocation exit with a usage error — the empty output file
  then reads as "nothing resolved".

Rule: **a resolver returning nothing is NOT proof of NXDOMAIN.** Confirm with a second resolver and,
where possible, an actual TCP connect, before writing "NXDOMAIN" into a ledger. A wrong NXDOMAIN
sweep silently deletes an entire branch of the attack surface.

## 5. Fingerprint the controls on the discovered surface (don't just list it)
Once hosts are live, classify each by what blocks it. Record the control — that's the difference
between "exposed admin tool" and "exposed admin tool, correctly IAP-gated":

| Control | Fingerprint | Bypass test |
|---|---|---|
| Google Cloud **IAP** | `302 -> accounts.google.com`, header `x-goog-iap-generated-response: true`, cookie `GCP_IAP_XSRF_NONCE_*` | probe `/healthz /api /static/ /actuator/health /.well-known/ /sse /mcp /jsonrpc` — all 302 ⇒ no bypass, record as working control |
| Cloud Armor / LB | flat `403` (`via: 1.1 google`, ~134-byte HTML), or `text/plain` `fault filter abort` | — |
| Network ACL | host resolves, TCP **times out** | — |
| GCS custom domain | `Server: UploadServer`, XML `AccessDenied`, `Access-Control-Allow-Origin: *` | try `?list-type=2`, `storage.googleapis.com/<bucket>` |

The reportable item here is the **exposure** (internal service names in public DNS) when nothing is
bypassable — use the framing rules in `internal-infra-disclosure.md` and do NOT inflate it into an
access finding.

## 6. What the NAMING itself leaks (often the actual finding)
Per-project dev schemes disclose roadmap and architecture even when every host is 403/IAP:
```
api.<project>.dev.<org> | hantera.<project>.dev | mcp.<project>.dev | ops.<project>.dev
iap.<project>.dev      | link.<project>.dev    | experimentation.<project>.dev
```
Project codenames observed leaked the product roadmap (`trade-stock`, `flat-crypto`, `paper-broker`,
`buy-index`, `bullish-helper`, …) plus service classes (MCP servers, `langfuse` LLM observability,
`testkube` dashboards, `argocd`/`atlantis`/`backstage` CI-CD, `looker`/`openmetadata` BI, `dcc` IT
ops with `wifi-user-admin` / `servicedesk-dashboard` / `kiosk`). Capture the scheme + the list.

## Pitfalls recap
- Never conclude "NXDOMAIN" from one resolver with an unverified flag set.
- Never let a failed bulk job's partial output become your asset list.
- Sweep the full sitemap for a feature's presence (e.g. `fl-module-sidebar`) before concluding a
  version-based CVE is exploitable — see `security-scanners` → "A vulnerable VERSION is not an
  exploitable TARGET".
