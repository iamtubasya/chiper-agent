---
name: unauth-config-disclosure
description: "Use when a target leaks tenant config or API keys pre-auth."
version: 1.0.0
author: hermes-curator
license: MIT
sources: engagement_derived
metadata:
  hermes:
    tags: [security, bug-bounty, cwe-200, info-disclosure, web, saas]
    related_skills: [hunt-brute-force, hunt-idor, triage-validation, evidence-hygiene]
---

# Unauthenticated Configuration / Secret Disclosure

## When to Use

Load this skill when:

- A target serves configuration/status endpoints **before authentication** — typical on SPA
  webmail and mail products (JMAP/IMAP fronts), SaaS settings APIs, and multi-tenant platforms
  where the login page must render branded config.
- You have found such an endpoint and need to triage, mass-enumerate, and report it without
  overclaiming.
- You need **ground-truth evidence** for a rate-limit / lockout finding — the same endpoint
  often leaks the vendor's own `blockDuration` / lockout setting.
- A leaked third-party API key or OAuth client ID needs an honest usability verdict.
- **A `/metrics` endpoint answers 200** — see Step 1d; it is an *architecture* oracle (integration
  names, callback outcome taxonomy, rate-limit rule labels) rather than a secret leak, and it is the
  cheapest surface map available on a containerised API.
- **An API path answers `302` instead of the data** — a caching reverse proxy may be sitting in front
  of the gated backend, and the proxy's own namespace is often reachable directly. Two namespaces,
  same object, one of them unauthenticated: that asymmetry *is* the finding. The other tell is a
  login page that must render a whole config object (theme, locale, policy, feature flags) before
  auth — developers serialise the **entire** config and drag secrets along with it.
  Full technique, probe set, negatives and severity trap: `references/cache-proxy-unauth-disclosure.md`.
- **A later round returns to the same target** — a disclosure report is already filed and still
  unfixed, and you need to establish whether it is still live and whether anything *new* leaked.
  Run it as a diff (Step 2b), not as a re-discovery.

**Trigger:** a target serves configuration/status endpoints before authentication (SPA webmail
and mail products, SaaS settings APIs, JMAP/IMAP fronts) — or you need ground-truth evidence to
prove a rate-limit/lockout finding. Also load this when you have found such an endpoint and need
to triage, mass-enumerate, and report it without overclaiming.

The class: a product exposes its **tenant configuration** over an unauthenticated endpoint
because the login page itself needs that data (theme, locale, password policy, feature flags).
Developers then serialise the *whole* config object — which drags along third-party API keys,
OAuth client IDs, SSO endpoints, internal hostnames, and the vendor's own security settings.

Two things make this high-value out of proportion to its boring reputation:

1. **It leaks secrets** (CWE-200) without any auth, usually on **every tenant** — so one
   finding covers an entire fleet in production *and* staging.
2. **It is ground truth for other findings.** If the same response carries the lockout /
   throttle setting, you no longer have to *infer* a missing rate limit from behaviour — the
   vendor has published the value. `"blockDuration": 0` is a stronger sentence in a report
   than sixty failed logins.

---

## Step 1 — Find the endpoint

Any product where a pre-auth page must render personalised config is a candidate. Probe these
paths with a bug-bounty identity header, on the apex *and* on every subdomain you have:

```bash
PATHS="/api/settings /api/config /api/health /api/version /api/status /api/features
/api/session /.well-known/jmap /jmap/session /api/auth /api/admin /api/user
/api/tenant /api/domains /api/webdomain /api/branding /api/theme /settings.json
/config.json /api/v1/settings /api/meta /api/appconfig"
for h in $(cat hosts.txt); do
  for p in $PATHS; do
    code=$(curl -sk -o /tmp/cfg -w "%{http_code}" -H "X-Bug-Bounty: <you>" "https://$h$p")
    [ "$code" = "200" ] && echo "$h$p -> $(wc -c </tmp/cfg) bytes" && cp /tmp/cfg "cfg_${h}${p//\//_}.json"
  done
done
```

Signals it is the right endpoint: JSON body, no `WWW-Authenticate`, works with no cookie, and
the key names look like product config (`themes`, `endpoints`, `extensions`, `allowX`,
`metaSettings`, `sessionExpirySeconds`).

## Step 1b — Ask the login page for its OWN endpoint list (do this before wordlist fuzzing)

A hand-written path wordlist misses the endpoints that matter, because they are product-specific
and unguessable. The pre-auth page already knows them: it calls them. **Capture every request the
unauthenticated SPA makes and read the list off the wire.**

This is not a nice-to-have. On the worked Atmail case a 215-name product-aware wordlist plus an
~900-path sweep found nothing new, while a single browser load of the login page surfaced
`GET /auth` (returning 200 JSON on **143/176** hosts) and
`GET /auth/spa/config?app=webmail` (returning a per-tenant `authorizeUrl` + `clientId` on
**52/176** hosts) — two unauthenticated endpoints that no wordlist contained.

Playwright recipe (set the bug-bounty identity header on **every** request, not just the
navigation, and record the response status so you can sort reachable-unauthenticated from 401):

```python
ctx = br.new_context(ignore_https_errors=True,
                     extra_http_headers={"X-Bug-Bounty": "<you>"})
page = ctx.new_page()
page.on("request",  lambda r: rec(r.method, r.url, r.resource_type, r.post_data))
page.on("response", lambda r: rec(r.request.method, r.url, "RESPONSE", status=r.status,
                                  ct=r.headers.get("content-type")))
page.goto(url, wait_until="networkidle", timeout=45000)
time.sleep(4); page.mouse.wheel(0, 1200); time.sleep(3)
```

Then filter to `resource_type in ("xhr","fetch")` or URL containing `/api/` `/auth/`, dedupe on
`(method, url-without-querystring)`, and **keep the query strings** — the SPA's cache-busting and
per-app parameters (`?cachebust=<epoch>`, `?app=webmail`, `?app=account-portal`) tell you which
variants exist and which ones the server actually answers differently per app.

Repeat on each distinct product front end (webmail SPA, auth/login SPA, account/billing portal):
they call different endpoints, and a `200` on one is often a `404` on another.

`scripts/preauth_spa_capture.py` is a ready-to-run version of this — it takes a list of URLs,
captures the pre-auth surface, and prints the deduped `method + URL + status` table plus any
POST bodies (the POST bodies are how you learn a login/API request shape).

Two things this technique reliably produces:

- **A capability endpoint** that returns the same body on every host (`{"methods":[...]}`) —
  product capability only, no per-tenant value, so it is *not* separately reportable. Say that
  explicitly rather than padding the report.
- **A per-app config endpoint** that returns tenant-specific values (`authorizeUrl`, `clientId`)
  — the same CWE-200 class as the main payload. Fold it into the main finding as an additional
  affected endpoint instead of filing it separately, or it gets closed as a duplicate.

Cross-check what you captured against the shipped bundle too: grepping the pre-auth JS for
quoted path literals finds the aliases (`"/api/.well-known/jmap-settings"`, `"/config.json"`,
`"/auth/password-policy"`) that the network trace only shows if that code path ran.

## Step 1b — Let the pre-auth page enumerate ITS OWN endpoints (do this before any wordlist)

Wordlist fuzzing and `katana` both under-cover a JS SPA: the page fetches its config from paths no
dictionary contains (`/auth`, `/auth/spa/config?app=…`, `/api/.well-known/jmap-settings?cachebust=…`,
`/config.json`). The login page itself is the best endpoint oracle you will get — drive it in a real
browser, record every request, and every one of those is by definition reachable **without
authentication** (the page is pre-auth).

Minimum viable capture: Playwright/Chromium, `extra_http_headers` carrying your bug-bounty identity
header, listeners on `request` + `response`, then filter to `resource_type in (xhr, fetch)` or a
`/api/`, `/auth/` path and print unique `(method, path, status, body-prefix)`. Visit the webmail
root, the login host, and any account/portal host — they expose different surfaces.

Then mine the JS bundles for path literals (`grep -ohE '"/[a-zA-Z0-9_/{}.:-]{3,70}"' *.js`), which is
where template-built URLs and rarely-called endpoints show up.

Full recipe, the exact script, and the worked case: `references/preauth-spa-surface-discovery.md`.

## Step 1d — Prometheus / exporter endpoints are an ARCHITECTURE disclosure, not a secret one

A different member of this family, and it shows up on nearly every containerised API: an
unauthenticated metrics endpoint. Probe `/metrics` first — it is the single highest-hit-rate
unauthenticated path on modern Node/Go/Rust APIs, and `nuclei -tags exposure` flags it as
`prometheus-metrics`.

```bash
for h in $(cat hosts.txt); do
  code=$(curl -sS -o /tmp/m_$h -w "%{http_code}" "https://$h/metrics")
  [ "$code" = 200 ] && grep -q '^# HELP' /tmp/m_$h && echo "$h /metrics $(wc -c </tmp/m_$h)b"
done
```

**Never stop at "the endpoint is open". The value is in the LABEL SET.** Custom application metrics
are written by the developer and therefore encode their mental model of the system. On a crypto
casino (Binobi 2026-10) a single 24 KB dump handed over:

- `…_rate_limit_decisions_total{provider="<name>",rule="callback-burst|callback-minute|api-burst|api-minute|default",outcome="allowed|rejected|storage_error"}`
  — the `provider` label enumerated **17 payment-service integrations** (moneygrator, avepay, bestpay,
  dns-pay, expay, fxmb, paysage, repay, settle, antrpay, 100hp, amatic, slotegrator-casino,
  slotegrator-betting, twilio, promotions, api). That is the PSP attack surface, named, with the
  throttling rule names attached.
- `…_callback_events_total{outcome="received|authenticated|invalid_signature|configuration_error|status_error|duplicate|deposit_credited|deposit_failed|review"}`
  — the **callback outcome taxonomy**, i.e. the exact error vocabulary the deposit handler returns,
  plus a live ratio (`invalid_signature` 843 / `received` 901) that tells you the signature check is
  real and already being hammered by attackers.
- `…_auth_refresh_events_total{outcome="rotation|retry|replay"}` — the operator's own refresh-token
  model, with a live `replay` counter proving they *track* replay (so replay is a known worry).
- `…_ws_decisions_total{rule="origin",outcome="denied"}` and `connections{kind="authenticated|guest"}`
  — confirms a Socket.IO gateway that admits **guest** sockets.
- Plus `process_*` / `nodejs_*` for runtime and version fingerprinting.

Mining recipe — dump once, then bucket the labels, don't read the whole file:

```python
import re, collections
txt = open("metrics.txt").read()
for name in ("provider","rule","outcome","operation","status","kind","job"):
    vals = sorted(set(re.findall(rf'{name}="([^"]*)"', txt)))
    print(name, len(vals), vals)
# then the non-process series only:
print("\n".join(l for l in txt.splitlines()
                if l.startswith("binobi_") or (l and not l.startswith(("#","process_","nodejs_")))))
```

**Report it honestly.** On its own this is CWE-200 of *operational* metadata with no customer
identifiers — Informative-to-Low on almost every programme, and arguing otherwise gets closed. Its
real job in your engagement is as the **surface oracle**: every name in those labels is an endpoint,
a provider, or an error string you can now go attack directly (see
`security/crypto-casino-audit` §5d for the callback chain this unlocked). Write it up as
"unauthenticated metrics endpoint disclosing internal integration topology" and use it as the map,
not the treasure.

Also check the sibling exporters, same invocation style: `/metrics` on every API host **and every
mirror** (edge rules differ per hostname — on Binobi `api.binobi.com` and `api.binobi.io` both
answered), plus `/health`, `/healthz`, `/ready`, `/livez`, `/status`, `/debug/vars` (Go expvar),
`/actuator/{health,env,metrics}` (Spring), `/-/healthy` (Prometheus itself).

## Step 2 — Mass-enumerate, write to disk, count

Never eyeball a handful of hosts and stop. These endpoints are usually deployed per-tenant
from one image, so the interesting hosts are the ones with **non-default** config — customer
tenants and staging builds leak far more than the reference deployment.

- Loop the full host list, write **each raw response to its own file** (you will need the
  untruncated values later), then aggregate in Python.
- Report the count: "returned 200 without credentials on N hosts, including production."
  N is the impact multiplier.
- Track which hosts have *non-default* values — a populated `googleDrivePickerConfig`,
  a real `authUrl`, a verbose `maintenance` block.

## Step 2b — Returning to the target later: run it as a DIFF, not a re-discovery

A continuing engagement (report filed, vendor has not shipped a fix, a later round revisits the
host) asks a different question. Round 1 asked *"what leaks?"*. Later rounds must answer, in
order: **is it still live** (then the standing report still holds), **did anything NEW leak**
(new tenants, new schema fields, staging promoted), and **did a value change meaningfully**.

Re-dump the **current** host list against every known alias into a *new dated directory* so the
previous round's evidence stays diffable, then compute the **key-path union** across all dumps
and count on how many hosts each dotted path appears:

```python
rare = [(k, n) for k, n in keys.items() if n <= 3 and not k.startswith("themes")]
```

The rare-key list is where a field that only exists on the newest deployments shows up. Exclude
per-tenant keyed namespaces (`themes.*`, one entry per host) first, or they swamp the output.
Worked case: 8254 distinct paths across 142 hosts, only two present on `<=3` hosts, both benign —
a clean result, and worth one line in the log ("no field is present on only some deployments").

Then rebuild the credential inventory as `key -> distinct value -> host list`, printing only
`len` + `sha256[:10]` + hosts (never the value), and compare it to the previous round: *"identical
credential set — no new tenant, no new key"* or *"a fourth `devKey` appeared on host X"*.

Finally re-read the control fields that are evidence **for other findings** (`blockDuration`
distribution, `allow2FA`, monitoring keys) — and check their *values*, because a key that exists
but is empty everywhere (`airbrakeProjectKey: ""` on all hosts) kills a chain you might otherwise
have built on it.

If the delta is empty: **do not create a new report and do not resubmit.** The correct output of
this pass is the refreshed evidence bundle, the host count, and a log line. Full recipe, including
the "what this pass is NOT" list: `references/reverifying-a-live-disclosure.md`.

## Step 3 — Triage the leaked keys

Walk the parsed JSON recursively and bucket every leaf:

| Bucket | Examples | Reporting weight |
|---|---|---|
| Third-party credentials | `googleDrivePickerConfig.devKey`, `dropboxPickerConfig.appId`, airbrake keys, `globalGAKey` | The actual finding |
| Vendor security settings | `blockDuration`, `maxLoginAttempts`, `lockoutDuration`, `allow2FA`, `sessionExpirySeconds` | Ground truth for other findings; also shows control is off |
| Auth/infra topology | `authUrl`, `logoutUrl`, SSO callback URLs, `endpoints.*`, internal hostnames | Context, aids chaining |
| Operating metadata | extensions list, license state, theme definitions, reset-flow copy | Low value alone |

```python
# recursive walk, flag credential-ish AND security-setting keys
import re, json, glob
SENS = re.compile(r"(pass|secret|key|token|cred|user|apikey|license|registry|smtp|imap|client|appid|devkey|signature|salt|auth)", re.I)
SEC  = re.compile(r"(blockDuration|maxLoginAttempts|loginAttempts|lockout\w*|throttle\w*|allow2FA)", re.I)
def walk(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, f"{p}.{k}" if p else k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, f"{p}[{i}]")
    else: yield p, o
```

## Step 3b — Rule OUT cross-tenant access before you claim it

The tempting overclaim is "one tenant's front end returns another tenant's config". Test it
properly, because on shared-front-end deployments the answer is usually no:

1. **Query-parameter selection.** Fuzz `?webdomain= / ?domain= / ?tenant= / ?host= / ?realm= /
   ?server= / ?accountId= / ?id=` with the hostname of a *different known tenant* and diff the
   response signature against the caller's own baseline. Real cross-tenant read = the body
   changes to the other tenant's values.
2. **Path suffix.** `/api/settings/<other-tenant>`, `/api/<other-tenant>/settings`, `//`, `..;/`,
   `%2f`, case variants.
3. **Host-header selection.** Resolve a shared front-end IP and replay with `Host: <other-tenant>`
   *and* with a random/non-existent host. Three outcomes matter:
   - other tenant's real config returned → you are reading their data (check whether you needed
     the hostname, which is public DNS anyway → usually no privilege gained);
   - **generic default config** returned (boring values, `theme: default`, no credentials) → no
     cross-tenant read; the node serves a neutral fallback;
   - same signature for random and real hostnames → **no tenant-existence oracle** either.
4. Check whether a fallback/default config *enumerates other tenants* (e.g. a `themes` map keyed
   by webdomain). Dump its keys and foreign hostnames before declaring it neutral.
5. Look for a listing endpoint (`/api/webdomains`, `/api/tenants`, `/api/realms`) that would turn
   a per-tenant leak into a fleet-wide enumeration. Usually 404/401.

If the honest answer is "per-tenant, not cross-tenant", say exactly that and switch the impact
wording to **fleet-wide exposure** (same root cause on N hosts, each exposing its own secrets) —
which is still worth reporting, and is much harder for a triager to close as a stretch.

**Endpoint aliasing counts — and aliases live on OTHER TIERS, not just other paths.** A second path
can reach the same payload (`/api/.well-known/jmap-settings` → `301` → `/api/settings`,
`/api/settings.json`, trailing slash, `/.well-known/jmap-settings`). List the aliases in the report
so the fix covers all of them, and so a triager's own curl on the "other" path reproduces.

Do not stop at path variants on the host you already found. On a product with a **dedicated API
tier**, the same serialised object is frequently served on a *different* path there — the webmail
gateway answered `/api/settings` while the three `jmap-api.*` hosts answered plain `/settings`
(no `/api` prefix), unauthenticated, and 404'd the `/api/settings` form. Enumerate the sibling
tiers explicitly and probe the bare word as well as the prefixed one.

**Re-run the enumeration after you fix any tooling artifact.** The run that is merely "cleaner"
is often the run that *finds the thing*: the third path above only appeared after overriding a
scanner's User-Agent (see `bot-protected-target-testing` §3a — the default ffuf UA was being
403'd into a fake "nothing here"). A tooling fix is a reason to re-fire the scan, not just the
one command that failed. Likewise, a mid-session DNS/connection outage silently turns several
tools into instant false negatives — re-verify those before you record them.

### Framing when the program's wording is "across tenants"

Triage of this class often invites a report with wording like *"if the endpoint discloses sensitive
data **across tenants**"*. That phrase has two readings and they are different findings:

| Reading | Status on a typical deployment | How to establish it |
|---|---|---|
| Every tenant's own sensitive data is world-readable (fleet-wide exposure) | Usually **TRUE** and demonstrable | One host list + one GET each; show N hosts returning *different* per-tenant values |
| Tenant A can read tenant B's configuration (isolation break) | Usually **FALSE** | §Step 3b: parameter selection, path manipulation, `Host` override on a shared front end |

Report the first, state plainly that you tested and could not achieve the second, and ask them to
assess on that basis. Two reasons this is the right move: it pre-empts the "you overclaimed"
rejection, and the *negative* is itself useful evidence — a triager who assumed isolation was
broken will otherwise close your report as unreproducible when their own cross-tenant test fails.

A practical harvest-cost line strengthens the fleet-wide reading: "one GET per hostname, over a
list already public in certificate-transparency logs". That is the concrete difference between
"one tenant's config is public" and "every tenant's config is public".

## Step 4 — Test whether the secrets are actually usable

A leaked key is only half a finding. Test it **once, benignly**, and classify the answer. Use the
provider's **correct** probe form for the credential type — getting this wrong produces a
confident, false "the key is inert" verdict:

- Google API keys: pass the key as the **`?key=` query parameter** (NOT the `X-Goog-Api-Key`
  header) against an endpoint that actually validates keys — `drive/v3/files?key=<k>&pageSize=1`
  is the reliable one. Probe **without** a Referer and **with** an allowed-looking one, and put a
  well-formed-but-invented key in the same run as a control:
  `400 INVALID_ARGUMENT "API key not valid"` = the value is malformed/masked;
  `403 … "Requests from referer … are blocked"` = the key is **real** and Google applied its
  restriction; a *project/permission* error after supplying a Referer = the gate was passed.
- **Do not use Maps + `X-Goog-Api-Key` to classify a key.** It answers
  `REQUEST_DENIED "You must use an API key …"` for *every* value, including a correct key and an
  empty one, so it cannot distinguish anything. This exact probe produced a wrong "restricted to a
  different API family → inert" conclusion in an earlier round.
- Picker/OAuth client IDs alone: no data access without a user OAuth grant → disclosure only.
- AWS keys: `aws sts get-caller-identity` (read-only) rather than anything that mutates.

Then write the honest sentence, e.g. *"the key was probed once, was accepted by the provider, and
returned no data to an API-key-only caller, so this is unauthorised disclosure of a live
third-party credential, not account takeover."* State separately whether each restriction you
observed was actually satisfied — an unsatisfied allowlist is reported as **not bypassed**.

## Step 5 — Use it as ground truth elsewhere

Check the leaked values against your other findings before you write them up:

- `blockDuration: 0` / absent lockout keys → corroborates a missing-rate-limit finding, and
  shows the control is off on *that* host rather than "did not fire during my test".

  **Do NOT write "disabled deployment-wide" from one host's value — measure the distribution
  first.** This is the one sentence in this class that a triager kills with two curl commands.
  A real measurement over 137 hosts returned `0` on 112, `60` on 2 (cheesepies,
  webmail.pc3), `3000` on 1 (pc5), **not exposed on 21** (the admin panels answer 502 for
  `/api/settings`), and absent on 1. Write the distribution, name the exceptions, and count only
  the hosts you actually queried:

  ```python
  # tally the value per host, print the histogram — never a single sample generalised
  from collections import Counter
  dist = Counter()                      # host -> json
  for h, body in dumps.items():
      m = re.search(r'"blockDuration"\s*:\s*(\d+)', body)
      dist[m.group(1) if m else "absent"] += 1
  print(dist)                           # -> {'0': 112, '60': 2, '3000': 1, 'absent': 1, ...}
  ```

  If the host you are actually claiming the bug on does **not** expose the setting (the admin
  panels here returned 502), label the value as **supporting evidence from sibling deployments**
  and rest the finding on your own behavioural measurement. An "all hosts" claim that the vendor
  can disprove in one loop costs you the entire report.
- `allow2FA: false` → MFA-bypass framing is weaker than it looks.
- Session expiry, reset-flow required fields, and throttle copy tell you what reset/OTP flows
  will accept before you probe them.

---

## Pitfalls (each one costs a report)

**"The endpoint is public" is NOT the bug — say which half is the bug.** The login page
needing config pre-auth is normal and intended. The oversight is that **secrets are in that
payload**. A triager will close you instantly if you argue the endpoint shouldn't be reachable;
frame it as CWE-200 with a concrete secret named.

**Ignoring the program's "informative" list.** Most programs sweep up "software version
disclosure", "verbose settings", and "enumeration without PII" as Informative. Those clauses
do **not** cover a third-party API key. Name the secret, state that it is not a version string,
and quote the clause you believe does apply.

**Duplicate risk is real.** Settings endpoints are the first thing every researcher hits.
Check your own prior notes and any earlier engagement on the product before submitting; if an
older session already logged the same endpoint, the *new* value is the specific secret, not the
endpoint.

**Never print the secret in full.** Terminal output, logs, screenshots and reports all end up
in triage. Reference it as `prefix + length` (e.g. `D9K5nA… (24 chars)`) and keep the raw value
only in the evidence file.

**⚠️ Your own tooling may REDACT the secret in tool output — never re-test a value you read off
the screen.** Agent runtimes (and this one) run an output-layer secret redactor. A 39-char
`AIzaSy…` key can be rendered as `AIzaSy...PRgQ` and look exactly like a masked placeholder the
product returned. Testing *that* string returns `API key not valid` for every input and produces a
completely false "the key is inert / the finding is weak" conclusion — which then survives into a
report as a wrong correction. Always re-read the value **programmatically from the saved evidence
file** and print only the classification:

```python
k = json.loads(j["googleDrivePickerConfig"])["devKey"]     # from the raw file on disk
print(len(k), hashlib.sha256(k.encode()).hexdigest()[:16]) # length + hash, never the value
```
If the length is the provider's real format (39 for `AIza…`), the key IS disclosed in full even
though the terminal shows an ellipsis. Cross-check `file_size`/`len(content)` too — a redacted
*display* never changes the byte count of the response.

**Verify key usability with a negative control.** If you can obtain the real value, probe it once
benignly **and** probe a well-formed-but-invented key in the same run:

```
GET https://www.googleapis.com/drive/v3/files?key=<real value>   -> 403 "Requests from referer <empty> are blocked."
GET https://www.googleapis.com/drive/v3/files?key=AIzaSyAAAA…    -> 400 "API key not valid."
```
The distinction is the proof: a **`403 … referer … blocked`** reply is itself evidence the key is
real (Google resolved it and applied its restriction), because an unknown key returns
`400 INVALID_ARGUMENT — API key not valid`. Setting an allowed-looking `Referer` then moving the
error to a *project/permission* error (`The user does not have sufficient permissions…`) proves the
key was accepted. Also check whether the API is enabled on the project — the same error names the
project number, which is how you tie a leaked key to a real GCP project.

Caveat on the referer gate: it must be satisfied with a value the key actually allows. If every
referer you try still returns `… are blocked`, the allowlist is unknown and **you must not claim a
bypass** — report "valid key, restriction not satisfied during testing".

**Do not confuse a reflected-host value with an exploitable one.** Settings endpoints often echo
the `Host`/`X-Forwarded-Host` inside an error string or a lookup. Before calling it a finding,
check all four: does the attacker benefit from a header they set themselves; is the response
cacheable (`Cache-Control: no-cache, no-store` kills cache poisoning); does anything redirect
(`Location`); is the value escaped (JSON-escaped string = XSS dead). If none hold, it is a
documented negative, not a bug.

---

## Reporting shape

- One finding per root cause. A config endpoint on 121 hosts is **one** finding; list the extra
  hosts inside it rather than filing them separately.
- Lead with the secret, then the fleet size, then the endpoint.
- Include the single paste-ready `curl` that reproduces it, with the identity header.
- State plainly what you could **not** prove about the secret's usability.
- Include the vendor-security-setting leak as supporting evidence for whatever else it
  corroborates (usually the rate-limit finding).

### When a triager names the endpoint and a class, write THAT report

Programs often reply along the lines of: *"endpoint X returning configuration without
authentication — if it discloses sensitive data across tenants, a separate report focused on that
with a concrete demonstration of what is exposed may be eligible under our information-exposure or
missing-authentication classes."* That is an instruction about **document shape**. Restructure to
answer it literally, in this order:

1. **Lead with the concrete demonstration, not the narrative.** A per-tenant table: host →
   the exact values returned → *why it is sensitive*. Show 8-12 different tenants so the reader sees
   the values differ per tenant. Secrets as `prefix + length`; untouched responses in the evidence
   bundle. Put this at section 2, before any methodology.
2. **Quote their own words back and answer them.** If the qualifier was "across tenants", dedicate a
   section to it and give the *measurement*, not an adjective (hosts returning the payload, distinct
   tenants with distinct values, cost to harvest the fleet, whether a tenant-existence oracle
   exists).
3. **Name the class mapping explicitly** in the metadata block: "fits the program's
   information-exposure / missing-authentication classes". Add the second CWE when the endpoint is
   simply unauthenticated (CWE-200 + CWE-306), because that is the vocabulary they used.
4. **Keep a "what I could NOT do" section** (see Step 3b). It is not weakness — it is what stops a
   triager downgrading you for implying an isolation break you never demonstrated.
5. **State the severity ceiling you can defend**, then say plainly which single fact would raise it
   (here: "if the program treats disclosed live third-party credentials as C:H, raising
   confidentiality is defensible on the same evidence"). Give the CVSS arithmetic.

### "Across tenants" is two different claims — never let one imply the other

- **Fleet-wide per-tenant exposure** — one endpoint, N hosts, every tenant's own secrets returned to
  an unauthenticated caller, harvestable at one request per hostname over a public CT-log host list.
  This is demonstrable and is usually what the program means.
- **Isolation break** — tenant A's front end returning tenant B's configuration. Test it (Step 3b);
  on shared-front-end deployments it is usually negative.

Write the first, state the second's result, and say in one sentence which one you are reporting.
If you cannot tell which the program means, report the first and note the second's negative result
in the same document rather than asking — the reviewer can then accept either reading.

Severity anchor: unauth disclosure of third-party credentials + per-tenant config —
`AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N` (Medium, ~5.3). Escalate only with demonstrated use of
the secret.

---

## Related skills

- `hunt-brute-force` — the `blockDuration`-style leak is the strongest available evidence for
  a missing-rate-limit finding; pair the behavioural burst with the leaked config value.
- `hunt-idor` — leaked `endpoints.*`, account IDs, and internal hostnames are the seed material
  for post-auth and cross-tenant IDOR testing once you have any account.
- `triage-validation` — run the severity gate before submitting; this class is very easy to
  overclaim and very easy to be honest about.
- `evidence-hygiene` — secret-bearing responses are exactly what needs redacting before any
  screenshot or report attachment.

## Supporting files

- `references/atmail-2026-09-example.md` — a full worked case, including the two false-positive
  classes that looked like findings and were not.
- `scripts/classify_disclosed_key.py` — re-runnable credential classifier with a **negative
  control**. Reads the candidate secret programmatically from the saved evidence file (never from
  your rendered tool output), prints only `prefix...(len, sha256)`, probes the real value and an
  invented well-formed control in the same run, and reports a verdict
  (`INVALID` / `REAL_KEY_REFERER_BLOCKED` / `REAL_KEY_API_DISABLED` / `REAL_KEY_GATE_PASSED`).
  Use it instead of hand-typing a probe — this is the discipline that prevents both the "live
  key!" overclaim and the "the key is masked" false correction.

  ```bash
  python classify_disclosed_key.py --evidence raw/settings_full/ \
      --json-key googleDrivePickerConfig --sub-key devKey --json-out verdicts.json
  ```

See `references/fleet-config-endpoint-deepdive.md` for the follow-up round on the same endpoint:
the fleet count, the alias path found by grepping the pre-auth bundle, the three-way cross-tenant
ruling-out battery (with the Host-override matrix that produces the negative), the negative-control
key classification, and the reusable list of variants that were already tried and failed.

## Support files

- `references/cache-proxy-unauth-disclosure.md` — the **cache-proxy variant** of this class: a 302 on an
  API path is an invitation (hand-walk the destination namespace); the auth-asymmetry table is what you
  report, not the single 200; the cached-object enumeration loop; the four negatives to close first
  (cache-key injection, traversal/SSRF through the proxy, client-IP geo bypass, tenant-vs-single-operator);
  the severity trap when the cached object is the *anonymous* variant (`subscriber_tv: -1`) and the
  overclaim it invites; **plus** the adjacent SPA-catch-all / crawler-hit-inside-a-vendor-bundle /
  framework-error-echo false positives, the self-referential redirect loop finding class, and the
  tool-run hygiene rules (`gau` 0 rows = suspect run; a tool that won't start is "unavailable", not
  "no findings"; `curl -o /dev/null` reports size 0; never read a probe from a shared temp path).
- `scripts/fleet_config_sweep.py` — enumerate a host list against a config/status endpoint, write
  one raw JSON body per host, build the `key -> value -> hosts` field map, and **warn you when
  >90% of responses share one (status, length)** — the signature of a burst/WAF block page.
- `scripts/classify_disclosed_key.py` — read a disclosed key **from the evidence file**, probe it
  once against the provider *with a well-formed invented control in the same run*, and print only
  length + sha256 + classification. It also flags a value whose length does not match the provider's
  format, which is how you catch an output-layer-redacted or product-masked string.
- `scripts/preauth_spa_capture.py` — load a login/webmail/portal front end in a real browser,
  capture **every request the unauthenticated SPA makes**, and print the deduped
  `method + URL + status (+ POST body)` table. This is the Step 1b technique and it finds the
  endpoints a wordlist cannot guess.
- `references/preauth-auth-endpoint-triage.md` — what to do with the auth/SSO endpoints that
  capture hands you: capability endpoints (`GET /auth`, identical body everywhere) are not
  reportable; per-app config endpoints (`/auth/spa/config?app=`) fold into the main finding; the
  `/authorize` **relative-Location open-redirect false positive** and how to disprove it; a table of
  what is genuinely testable pre-auth vs the post-auth boundary; and the archive/scope trap.
- `references/reverifying-a-live-disclosure.md` — the **later-round pass**: re-dump the current
  host list into a new dated directory, compute the key-path union and rare-key diff, rebuild the
  credential inventory as `len + sha256 + hosts`, re-check the control fields, and write the delta.
  Ends with "what this pass is NOT" (do not resubmit, do not split per host, do not re-test the
  keys against a redacted display string).
