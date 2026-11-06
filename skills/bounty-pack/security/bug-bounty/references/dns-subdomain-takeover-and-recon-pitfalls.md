# DNS Sweep & Subdomain Takeover Verification

Learned during a `*.teamviewer.com` audit (Sept 2026). Mechanism-level, reusable on any wildcard-scope program.

## 1. DNS truth = DoH, never the local resolver

A local VPN/proxy resolver poisons `nslookup`/`getent` results and silently breaks batch recon:
- **Cloudflare WARP** answers every A query with a sinkhole address (`127.0.2.2`) and the first `Address:` line in `nslookup` output is the **DNS server**, not the resolved IP — a naive parser reports "all hosts at 127.0.2.2".
- Fix: query DoH directly, one call per record type, and parse JSON:

```
curl -sk "https://cloudflare-dns.com/dns-query?name=$HOST&type=A"  -H "accept: application/dns-json"
curl -sk "https://cloudflare-dns.com/dns-query?name=$HOST&type=CNAME" -H "accept: application/dns-json"
```

- `Status: 0` = NOERROR, `Status: 3` = NXDOMAIN. Cross-check any interesting NXDOMAIN against `https://dns.google/resolve?name=...&type=A` before believing it.
- Sweep pattern that scales: for every host, record `(hasA, hasCNAME, cnameTarget)`; then for hosts whose CNAME points at an external service, query **the CNAME target itself** as a second step. Dead target + live CNAME = dangling DNS.

## 2. Dangling CNAME ≠ finding. Gate the report on claimability.

Triage class before severity:

| CNAME target | Claimable by attacker? | Action |
|---|---|---|
| `*.s3.amazonaws.com`, `*.elasticbeanstalk.com` | yes | confirm 404 `NoSuchBucket`/`NXDOMAIN` → takeover, report |
| `*.herokuapp.com`, `*.github.io`, `*.azurewebsites.net`, `*.cloudapp.net` | yes (with caveats) | report |
| `*.trafficmanager.net` (Azure Traffic Manager) | **disputed** — profile-name re-registration rules changed; historically NOT claimable | verify against `can-i-take-over-xyz`, do not claim HIGH on this alone |
| `*.cloudfront.net`, `*.fastly.net` | no (CDN, needs partner access) | info only |
| 3rd-party SaaS CNAME (e.g. `onvanilla.net`) | no | info only |

Authoritative list: `https://raw.githubusercontent.com/EdOverflow/can-i-take-over-xyz/master/README.md` — fetch it and grep for the target's service name **before** writing any takeover report. A NXDOMAIN CNAME target for a service marked "not vulnerable" on that list is a housekeeping note, not a submission.

Also: staging hosts that simply **time out** on 443 but resolve are firewalled, not dead — they don't qualify as takeover either.

## 3. execute_code stdout truncates on large batches

Parallel HTTP sweeps inside `execute_code` come back as `(1 lines output)` with bodies missing. Pattern that works:
- run the batch, **write full results to a file** under the project evidence dir (e.g. `ceksemua/03_dns_sweep.txt`), then `read_file` it;
- in the script, print only counts/first N rows, never raw multi-MB dumps;
- keep `--max-time` ≤ 12 and cap workers ~16 — 100+ workers with 12s timeouts blows past the 5-min script limit; one hung TLS handshake per worker serializes the tail.

## 4. Obfuscated client-side "secrets" in JS bundles

`login-config.js`-style bundles build anti-CSRF tokens from chains of `return "prefix"+NS.<next>(x)` string fns plus `atob()`. Two lessons:

- **Deobfuscation is cheap**: extract the namespace block, execute in Node with a stub `window` (`var window={atob:s=>Buffer.from(s,'base64').toString('binary')}` + empty `tv.config`), resolve the chain, print the assembled string. Don't waste cycles hand-parsing with regex — regex misses defs (e.g. `$pi` prototype methods) and silently returns `<UNKNOWN:...>`.
- **Static-looking token ≠ vulnerability.** Re-fetch the script 4× cache-busted and compare the chain/namespace: if the token and the namespace name differ per response, it's server-generated per session and the CSRF control is *working* — that's a negative result, not F2. Only a value that repeats across fetches from different sessions is a leaked secret.

## 5. Cheap auth-flow checks that came back clean (run them anyway)

- Open redirect: inject `redirectUri` variants (`//evil.com`, `https://evil.com`, `javascript:`, `teamviewer.com.evil.com`) into login/SSO/consent URLs; check **both** the JS `redirect` target and the `Location:` header — an allowlist that ignores invalid values returns 200 with no redirect (correct, not vulnerable).
- Username enumeration on SRP/auth endpoints: identical `captchaRequired`/400 responses for real vs random emails = no enumeration.
- ASP.NET `customErrors` off looks alarming but the stock "Resource not found" page leaks nothing — verify the body has no stack trace before calling it info.
- `411 Length Required` from IIS on a POST: curl sends no `Content-Length` for header-only POSTs — add `-d ""`.
- `UnsupportedHttpVerb` XML error from Azure fronted endpoints: GET returns the SPA HTML (200), POST gives that error — this is static hosting behavior, not an API to attack.
- CSP `/csp-violation-report/` endpoints answering `OK` to unauthenticated POST: by-design log sink, not a finding.
- Versioned public config blobs (`static.../client-ui-<ver>/environment.json`): enumerate old versions — but public client analytics keys (Grafana **Faro** `instanceKey`, **Pendo** `apikey`, reCAPTCHA site keys) are designed to be public. Sending forged telemetry with a leaked Faro key "working" (202 Accepted) is not a valid submission.

## 6. Scope hygiene for leaked non-target infra

Source maps commonly disclose infra on *other* domains (e.g. `*.tvwebservices.org`, `*.tvremote2.com`). Probe only the contracted wildcard. The **disclosure itself** (internal hostnames + staging paths in a public source map) is the reportable content — it strengthens the source-map finding; it is not a separate scope violation.
