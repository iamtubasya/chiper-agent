# Internal-Infrastructure Disclosure — recon that produces a (low) finding

On a hardened target, recon-to-finding almost never comes from attacking the app. It comes from
**internal infrastructure leaking into public sources**. This is the single highest-yield
low-severity class, and it is read-only.

## Three sources, one finding class (CWE-200)

### 1. CT-log → resolve → flag RFC1918  (highest yield)

crt.sh lists every name ever seen in a certificate. Resolve them; any **public A record that
answers with a private address** is a leaked-internal-record / split-horizon finding.

- crt.sh query form matters: **bare `?q=TARGET` works; `?q=%25.TARGET` sometimes returns 404.**
  If one 404s, try the other before concluding CT has nothing.

```python
import json, socket
names = set()
for e in json.load(open('crt.json')):                      # curl -s "https://crt.sh/?q=TARGET&output=json"
    for n in (e.get('name_value') or '').split('\n'):
        n = n.strip().lower()
        if n.endswith('.TARGET') and '*' not in n:
            names.add(n)
priv = []
for h in sorted(names):
    try: ip = socket.gethostbyname(h)
    except Exception: continue
    p = ip.split('.')
    if p[0] == '10' or (p[0] == '172' and 16 <= int(p[1]) <= 31) or p[:2] == ['192', '168']:
        priv.append((h, ip))
print(f"{len(names)} names, {len(priv)} private-IP answers")
for h, ip in priv: print(f"  {h} -> {ip}")
```

Verified 2026-10 on a hardened target: 591 unique names, **19 with RFC1918 answers**
(one internal `/24`), plus role-revealing names (`argocd`, `c2-k8s-harbor`, `*-grafana`,
`*-prometheus`, `*-jaeger`, `*-tidb`, `*-alertmanager`, `rmaadmin`, `identitytest`, `dev.*`).

### 2. Internal / staging hostnames hard-coded in served JS

```bash
curl -s https://app.TARGET/js/main.js -o app.js
grep -oE 'https://[a-zA-Z0-9.-]+\.[a-z.]+' app.js | sort -u \
  | grep -Ei '(test|dev|stg|stage|preprod|internal|ec-|next|admin)'
# then resolve the hits the same way as (1)
```

### 3. Email-security posture (2-min quick kill — don't report if clean)

```bash
nslookup -type=TXT TARGET 8.8.8.8 | grep -i spf1   # want: ... -all   (softfail/hardfail = fine)
nslookup -type=TXT _dmarc.TARGET 8.8.8.8            # want: p=reject|quarantine, not p=none
```
Strong SPF (`-all`) + DMARC (`p=quarantine`/`reject`) = clean; **do not report**.

## Framing rules (be honest, do not inflate)

- CWE-200; CVSS 3.1 `AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` (5.3) — but **rate it Low/Informational**.
- Impact = reconnaissance only (names, internal subnet, service roles). No auth bypass, no data read.
- **Many programs EXCLUDE "internal IP / internal hostname / version disclosure."** Tell the operator
  this explicitly; a padded submission costs reputation more than it earns.
- **One root cause = one report.** A JS-bundle leak and a public-DNS private-IP leak are two root
  causes → two findings, not one merged doc.
- **Never probe the leaked internal hosts or private ranges** — the answers are not internet-routable
  anyway, and hitting third-party infra is off the table. Read-only `GET /` of the public names only.

## Negative-test vocabulary that belongs in the report

> None of the leaked hosts exposed an unauthenticated service (all 403/404/NXDOMAIN). No
> authentication or exploitation was attempted; activity was passive CT/DNS plus a read-only
> `GET /` against the public hostnames.

## Tool-coverage + the "maximal attack" anti-pattern (operator preference)

Use the whole tool family, not curl-only: CT/DNS (passive), static JS, browser/CDP for SPAs, email
records, CORS probe. But **"run all attack variants maximally" against a LIVE production target is the wrong goal** — automated scanners, fuzzing and DoS are forbidden by most program rules and generate noise, not signal. Substitute a *thorough, targeted* pass over the classes above rather than volume. Thorough ≠ loud.

---

## Scale-up: CT alone is ~0.6% of the surface (measured 170×)

Measured on one bank: certspotter/crt.sh gave **85** names. `subfinder -d <apex> -all` over the same
7 apexes gave **14,410**. Do not let a CT-only pass define "the surface" — and do not let a slow
`subfinder -all` run be cancelled; let it finish in the background, it is the highest-yield single
command in this class.

Then filter for the part that actually matters — **non-production namespaces**:

```bash
# resolve first, with the RIGHT resolver (see the dig trap below), then probe
dnsx -l subs_merged.txt -silent -a -resp -threads 80 -timeout 5 > resolved.txt   # NOT -retries (unsupported)
httpx -l resolved_hosts.txt -silent -sc -title -td -server -rl 20 -json -o live.jsonl
```

The valuable hits cluster in `dev` / `test` / `stage` / `cd` / `b2b` / per-project subdomains —
CI/CD (`argocd`, `atlantis`, `backstage`, `apps.cd`), BI (`looker`, `openmetadata`, `*-admin`,
`*-mcp`), IT ops (`wifi-user-admin.dcc`, `servicedesk-dashboard.dcc`, `kiosk.dcc`), and one
`api.<project>.dev` / `ops.<project>.dev` / `iap.<project>.dev` / `mcp.<project>.dev` **scheme per
project** (the scheme itself leaks the architecture; the project names leak the roadmap).

## Follow redirects across the estate — a 302 can hand you a whole domain

`argocd.cd-test.<apex>` returned `302 → https://argo.test.cd.<OTHER-DOMAIN>.se/`. That single hop
surfaced a **sibling corporate domain the CT list never contained** and that was absent from the
program's `security.txt` canonical list. Always resolve + enumerate the redirect target as a new apex.

## Confirm ownership before you claim scope — RDAP

```bash
curl -s "https://rdap.identitydigital.services/rdap/domain/<apex>.io"   # .io
curl -s -H 'Accept: application/rdap+json' "https://rdap.iis.se/domain/<apex>.se"   # .se
```
`nntech.io` → registrant org **"Nordnet Bank AB"**. That single field turned "a domain that serves
their infra" into "their domain, in scope" — cite it in the report. (`.se` RDAP may be unreachable
from some hosts; fall back to the in-band redirect evidence.)

## Name the control you observed, and probe it once for a bypass

An internal service that answers 403/302 is **not** the finding — the *disclosure* is. But record
which control, because it changes severity and it tells the vendor what to check:

| signal | control |
|---|---|
| `302 → accounts.google.com` + `x-goog-iap-generated-response: true` | Google Cloud IAP |
| `403` + `via: 1.1 google`, 134-byte body | Cloud Armor / Google LB |
| TCP connect **times out** (name resolves, no HTTP) | network ACL / split-horizon |
| `Server: UploadServer` + GCS `AccessDenied` | GCS bucket, not public |

Then spend ONE request on an IAP-bypass sweep — LB configs sometimes exempt paths:
`/ /healthz /health /api/ /api/v1 /status /metrics /robots.txt /favicon.ico /static/ /_next/
/actuator/health /.well-known/security.txt`. Measured: **every path 302'd** → no bypass, and you can
say so with evidence.

## Adjacent class: "the vendor already hardened the obvious route" (incomplete mitigation)

The strongest unauth finding of the run was a **bypass of a control that exists**. `/wp-json/wp/v2/users`
had been deliberately 404'd — but the oEmbed API still returned `author_url`, and `/author/<slug>/`
resolved 200, and the author slug *is* the WordPress login username. The mitigation was real and
incomplete, which is exactly what makes it reportable: it demonstrates the vendor cares and the
coverage has a hole.

Generalise it: whenever you see a hardening that blocks the known route (404 on a well-known API,
disabled endpoint, filtered param), **enumerate the alternates that reach the same data** before
writing the negative down. "Route disabled" ≠ "data not disclosed".

## Precondition-verification — the discipline that kills a CVSS 9.1 false positive

Found on the way: `nordnetab.com` served **Beaver Builder 2.8.6.1**, inside the affected range of
CVE-2026-92084 (unauthenticated arbitrary shortcode execution, CVSS 9.1) — and 104/120 sampled pages
were running it. Tempting. It was **not exploitable**, and the difference is the whole point:

* the advisory's precondition is a BB page using the **Sidebar module** populated with an
  attacker-controllable widget → scanned 120 sitemap pages: **0 contained `fl-module-sidebar`**;
* the natural payload source (a Recent Comments widget) needs comments → `comment_status: closed`,
  `/wp-json/wp/v2/comments` → `[]`.

So: read the advisory's **exploitation requirement**, then go prove each clause on the target. A
vulnerable version is a **hardening note**, never a finding. The version number alone is what
separates a real report from a credibility-destroying false positive on a *bank*.

Same-run corroboration of the same rule: revolution-slider 6.5.7 sat inside CVE-2026-6728's range
(≤7.0.9), but the vulnerable function `get_stream_data()` was **absent from the shipped JS** (grep
empty) → not applicable. Check that the vulnerable *code path* exists, not just the version.
target is the wrong goal** — automated scanners, fuzzing and DoS are forbidden by most program
rules and generate noise, not signal. Substitute a *thorough, targeted* pass over the classes above
rather than volume.

## Field notes 2026-10 — expanding passive DNS into a full infra map

Verified on a hardened bank VDP: the highest-yield pass was **passive DNS expansion of the vendor's
TECHNOLOGY-subsidiary domain**, not the customer-facing hostname. The apex is the shallow end.

**crt.sh unreachable? Use certspotter.** crt.sh often answers `HTTP 000` from a filtered egress.
Drop-in replacement (no key):
```bash
curl -s "https://api.certspotter.com/v1/issuances?domain=<d>&include_subdomains=true&expand=dns_names" \
  | python3 -c "import sys,json;[print(n) for e in json.load(sys.stdin) for n in e.get('dns_names',[])]"
```
Run it per registrable domain, and **include the sibling/parent zones** (`<tech>.io`, the second
corporate domain), not just the merchandising TLD.

**Do not judge `subfinder` by the fast pass.** `subfinder -d <d>` returned 0 rows here; the SAME
command with `-all` (many sources, slow — minutes) later returned **14,404 names** and an entirely
new surface (dev/test envs, CI/CD, BI, ops). Launch it early, in the background, and keep working.

**Verify DNS negatives with a SECOND resolver.** `dig +short` returned EMPTY for names that were in
fact resolvable — empty is not NXDOMAIN. Confirm with `nslookup <h> 8.8.8.8` or
`python -c "import socket;print(socket.gethostbyname('<h>'))"` before writing a name off. A whole
round of "NXDOMAIN, dead" conclusions was wrong because of this. Same family: a `dnsx` run with a
flag the build does not accept exits 0 and writes a 1-line file ("1 resolved of 14,410") — a SILENT
FAILURE, not a negative; re-run without the bad flag and compare counts.

**Sibling-domain discovery via a 302.** A redirect target reveals zones that never appear in the
security.txt `Canonical:` list: `argocd.cd-test.<tech> -> https://argo.test.cd.<sibling-se>` exposed a
second corporate domain. Always read `Location:` on every 3xx and recurse into any new apex.

**Per-project dev-env naming is a repeatable pattern.** `<svc>.<project>.dev.<tech>` with svc in
`{api, hantera, mcp, ops, iap, link, experimentation}`. Enumerate the scheme — the project slugs leak
the product roadmap, and MCP servers (`mcp.<project>.dev`) + LLM tooling (`langfuse.*`) surface here.

**Triage the protection before crying finding.** Four distinguishable controls:
- **Google IAP** — 302 to `accounts.google.com/o/oauth2/v2/auth`, `x-goog-iap-generated-response: true`,
  `GCP_IAP_XSRF_NONCE` cookie. Probe the usual bypass paths (`/sse /mcp /message /jsonrpc /healthz
  /api /static /_next /actuator /robots.txt /.well-known`) — if every one still 302/403, report
  *exposure*, not compromise.
- **Cloud Armor / LB 403** — `403` + `via: 1.1 google`, ~134-byte HTML body.
- **Network ACL** — the name RESOLVES but TCP times out (curl `000`); e.g. `sso.b2b.prod.<tech>`.
  Unreachable is not a finding.
- **GCS bucket** — `AccessDenied` XML with `Server: UploadServer`.

Report shape: one finding, root cause = internal names in the public zone; explicitly state the
controls you did NOT bypass and that no data/credentials were obtained. This keeps it honest and
survives triage. Thorough ≠ loud.

---

## 4. Non-prod / developer environments — the biggest version of this finding

On a large engineering org the highest-yield source is not the apex domain at all: it is the
**tech-subsidiary domain and its non-prod zone**. Verified 2026-10 (Nordnet VDP):

| source | names |
|---|---|
| certspotter, `.se`/`.fi`/`.dk`/`.no`/`.de`/`nordnetab.com` | 85 |
| **`subfinder -all` on the tech-subsidiary domain (`nntech.io`)** | **14,404** |

`-all` costs 15–25 minutes — run it **in the background first thing**, then do everything else while
it fills in. The delta is the whole finding.

What the extra names revealed (all publicly resolvable, all internet-facing):
- `*.dev.<tech>` per-developer / per-project environments — `api.<project>.dev`, `ops.<project>.dev`,
  `iap.<project>.dev`, `experimentation.<project>.dev` (247 live hosts from one org).
- `cd.` / `cd-test.` CI-CD estate — `argocd`, `atlantis.{org,nnx}`, `apps.cd`, `backstage.apps.cd`,
  `openmetadata-api`, `mobile-ota`, `dbt-artifact-parser`.
- BI / data-admin — `looker.analytics`, `nettie[-mcp].bi-apps.analytics`, `dataland-file-upload-admin`,
  `incident-admin.rad-apps.analytics`, `looker-access-lookup`.
- IT-ops — `*.dcc.<tech>` (`wifi-user-admin`, `servicedesk-dashboard`, `kiosk`, `lh`).
- Integrations — `<partner>.b2b.prod.<tech>` (e.g. a bank partner, a payments partner).

**Sibling domain via redirect chain.** A 302 on an infra host leaks another corporate domain that no
security.txt or CT query for the primary domain would surface:

```
argocd.cd-test.<tech>  --302-->  https://argo.test.cd.<other-domain>/
```

Always follow the redirect target of any `argocd` / `backstage` / portal host and CT-enumerate the
new domain in turn.

### 4a. Recognise the CONTROL — report exposure, not a fake compromise

Almost every one of these answers with a control rather than content. Name it explicitly in the
report ("control verified, NOT bypassed"), because that is what keeps the finding honest:

| response | control | how to tell |
|---|---|---|
| 302 → `accounts.google.com/o/oauth2/v2/auth` | **Google Cloud IAP** | header `x-goog-iap-generated-response: true`, cookie `GCP_IAP_XSRF_NONCE_…` |
| `403` with `via: 1.1 google` | Google LB / Cloud Armor | tiny `<title>403</title>` body |
| TCP connects never complete (`000`, "connection timed out") | network ACL / allow-list | `curl -v` shows `Host … was resolved` then timeout — record as **unreachable**, do not call it "no service" |
| `<Error><Code>AccessDenied` + `Server: UploadServer` | GCS bucket (private) | `X-GUploader-UploadID` present |

Attempt the **IAP bypass-path probe** once on each IAP host — LB config sometimes excludes a path:
`/ /healthz /health /api/ /api/v1 /status /metrics /robots.txt /favicon.ico /static/ /_next/ /actuator/health
/.well-known/security.txt`. All-302 (or all-403) = control consistent → say so.

Also try `<host>/api/version` and `/api/v1/session/userinfo` on an `argocd` host: a bare 404 from the
LB means the service is *not* publicly served, even though a sibling host 302s to it.

### 4b. Do NOT conclude "NXDOMAIN" from one tool

The 14k-name → 492-resolve funnel is only trustworthy if the resolver is. On this host `dig` returns
**empty** (not NXDOMAIN) for names that resolve perfectly, which manufactures a whole false
"everything is dead" conclusion:

```bash
dig +short argocd.cd.<tech>          # (empty)  ← WRONG conclusion: NXDOMAIN
nslookup argocd.cd.<tech> 8.8.8.8    # 34.102.184.52   ← the truth
python3 -c "import socket;print(socket.gethostbyname('argocd.cd.<tech>'))"
```

Same trap in the bulk tool: `dnsx -l names.txt -a -resp -retries 1` fails **silently** because
`-retries` does not exist — it printed `1 resolved` of 14,410 and looked like a clean negative. The
number was absurd for a live org, which is the tell. Re-ran without the flag → 492.

Rules: (1) always run a **wildcard test** first (`zdqvkxj9999.<zone>` must NXDOMAIN) so names are
proven real; (2) cross-check any "0 / all-dead" DNS result with a second resolver before writing it
down; (3) an implausibly small resolve count is a **tool failure**, not a finding. See
`audit-execution-discipline/references/msys-path-and-tool-invocation-traps.md` (Symptom O) for the
bash-loop variants of the same class.

### 4c. Report framing for this shape

One finding, root cause = "internal service names published in the public DNS zone(s)". Impact is
reconnaissance only — say that plainly, and state that no auth was attempted. Scope note to settle
first: the tech-subsidiary domain and any sibling domain found via redirect are usually the same
operator, but confirm they are not a separately-run entity before treating them as in-scope.

