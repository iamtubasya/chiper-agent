# Patch-lag differential and leaked-host chains

Two chain families that turn an info-level primitive into a payable finding. Worked examples from
Deutsche Telekom (2026-10-29), where seven primitives were walked and exactly one completed.

---

## 1. Patch-lag differential — "old version" → missed rollout → Medium

### Why the differential is the whole finding

"Host runs Roundcube 1.6.17" is hygiene. Every mature estate runs something stale; triagers close these
as informational. What converts it is a **sibling that is patched**:

```
bwm.sgp.telekom.de        rcversion 10617 -> 1.6.17 (2026-07-05)   prod
bwm-beta.sgp.telekom.de   rcversion 10617 -> 1.6.17               beta
bwm-test.sgp.telekom.de   rcversion 10620 -> 1.6.20 (2026-10-19)  TEST IS PATCHED
```

That single line establishes three things no version string can: the organisation knows about the
update, has validated it in test, and did not roll it to production. It becomes a *missed production
rollout with a named owner*, not an unknown risk. 106 days, three consecutive **security** releases.

### Recipe

1. **Enumerate siblings.** `prod/beta/test/dev/staging/uat/preprod/qa`, `-test`/`-dev`/`-staging`
   suffixes, `www` vs bare, and the same app under a second region code (`sgp`, `fra`, `ams`, `vie`).
   Subdomain brute-force will not find these reliably — they come from looking at the app's own
   hostname pattern once you have one instance.
2. **Pull the version unauthenticated.** It is usually on the login page or a JSON bootstrap:
   - Roundcube: `"rcversion":10617` = `major*10000 + minor*100 + patch`
   - GitLab: `gon.gitlab_version`; Nextcloud: `oc_version`; WordPress: `?ver=` on assets
   - Jira/Confluence: build number in `/secure/AboutPage.jsp` or meta
   - Spring Boot: `/actuator/info`; Dependency-Track: `/api/version`
   - JetBrains IDE Services: `info.version` in `/api-docs`
3. **Diff against the vendor's own release feed — do not use memory.**
   `GET https://api.github.com/repos/<org>/<repo>/releases?per_page=8` and compare `published_at`.
   Memory of "is 1.6.17 current" is wrong about half the time; the feed is not.
4. **Read the intervening release bodies.** Filter for the security lines:
   `grep -iE 'secur|CVE|XSS|RCE|inject|vulnerab|escape|sanitiz'`. A body that opens
   *"This is a security update … fixes to recently reported security vulnerabilities"* plus a named
   bug class **is** the evidence. Quote it verbatim in the report — paraphrasing reads as speculation.
5. **Score by what the fixes cover, and name the hop you could not prove.** In the Roundcube case the
   three releases covered RCE (markasjunk `cmd_learn`), zero-click stored XSS (TNEF MIME tag
   injection), cross-user contact-group access (SQL address book), object injection in
   `rcube_session::unserialize()`, and IMAP command injection. That reads Critical — but proving any
   one of them reachable needed one of:
   - an authenticated mailbox (IDOR / IMAP injection) — not held, not going to be obtained;
   - delivering crafted TNEF mail to an employee (zero-click XSS) — that is social engineering,
     prohibited by most RoE;
   - confirming the plugin and its `cmd_learn` driver are configured (RCE precondition).

   None available ⇒ **report Medium and say so in one explicit sentence**. Understating a proven fact
   is survivable; claiming a compromise you did not perform is not.

### Chain-killers to check before writing

- Is the unpatched host actually internet-facing? An internal-only sibling is not the finding.
- Is the vulnerable component enabled? Roundcube plugins are per-instance config (`plugins` array in
  the page bootstrap); a fix for a plugin you do not run is not a live vuln.
- Does the vendor already document the lag as accepted risk? Check for a security-advisory page.

### Report framing that survived triage

Lead with the differential table, not the version. Title it by the consequence
("Business Webmail runs Roundcube 1.6.17 — three security releases behind, test instance patched"),
not by the version ("Outdated Roundcube"). Include a **"proven vs not proven"** section; it is what
makes a version-lag report read as research rather than scanner output.

---

## 2. Leaked-host chain — public spec → third-party base URL

### The primitive

An unauthenticated OpenAPI document is Low. It becomes a chain when `servers[].url` — or an OAuth
`authorizationUrl`/`tokenUrl` in `securitySchemes` — points at a host the vendor **does not own**.

```
GET https://adminapi.dih.telekom.com/api-docs   -> 200, 19,810 B
servers: [{'url': 'http://dih-cloud.net/api/v1'}]      # plaintext HTTP
securitySchemes: bearerAuth -> http/bearer, JWT
```

A client configured from that spec sends its Bearer JWT to a non-vendor host over cleartext.

### Recipe

1. **Sweep every live root** for specs:
   `/api-docs`, `/v3/api-docs`, `/v2/api-docs`, `/openapi.json`, `/swagger.json`,
   `/api/v1/openapi.json`, `/swagger/v1/swagger.json`, `/api/openapi.json`.
   Require `d.get("openapi") or d.get("swagger")` in the parsed body. A `200` with
   `content-type: application/json` and no spec key is a SPA bootstrap — the single most common
   false positive in this sweep.
2. **Extract every absolute host** with `re.findall(r'https?://([a-zA-Z0-9._\-]+\.[a-zA-Z]{2,})', text)`,
   dropping `w3.org`/`googleapis`/`json-schema`/`swagger.io`/`apache.org` noise.
3. **RDAP ownership-check each host.**
   ```
   https://rdap.verisign.com/com/v1/domain/<d>    # .com
   https://rdap.verisign.com/net/v1/domain/<d>    # .net
   https://rdap.org/domain/<d>                    # fallback (404s on many ccTLDs)
   ```
   Compare `registrar` and `nameservers` against the vendor's own domain:

   | | vendor-owned | squatted / suspicious |
   |---|---|---|
   | registrar | the vendor itself (`Deutsche Telekom AG`) | retail (`GoDaddy.com, LLC`) |
   | registrant | present | redacted / empty |
   | nameservers | vendor NS (`pns.dtag.de`, `ns1.telekom.net`) | `*.ns.cloudflare.com` |
   | registration date | long-lived | days/weeks old |

   Worked comparison: `itenos.biz` → registrar "Deutsche Telekom AG", NS `pns.dtag.de` = **theirs**,
   chain dies. `dih-cloud.net` → GoDaddy, redacted registrant, Cloudflare NS, registered
   2026-09-05 = **not theirs**.
4. **Check whether it is already claimed — before drafting anything.**
   ```
   GET http://dih-cloud.net/api/v1/
   -> {"status":"captured","msg":"PoC - dih-cloud.net owned by researcher"}
   ```
   A researcher PoC announces itself in the body. 3/3 rounds identical. **A claimed domain means the
   finding is already filed** — the registration date is your duplicate detector. Record it in the
   negatives ledger and do not spend a submission slot.
5. **RFC1918 results are dead ends, not pivots.** `172.19.40.240`, `10.x`, `192.168.x` in a spec is an
   internal-topology leak. The chain dies at "not routable from the internet" — say that, do not
   imply reachability.

### Scoring honestly

The *domain claim* is the other researcher's proof, not yours. The finding is
"the vendor publishes an API contract directing clients to a non-vendor host over HTTP". A triager
merges the two. So: if unclaimed → real Low→Medium/High, report it. If claimed → duplicate, drop it.

---

## 3. The bogus-path control — decides "unauth" vs "auth-before-routing"

Run this on every host where you are tempted to write "unauthenticated API". It takes one request and
has killed more false Mediums than any other check.

```
GET /api/authentication/identity-providers   -> 401
GET /api/configs                             -> 401
GET /api/automation-tokens                   -> 401
GET /api/zzz-notreal-x4hd2k9pq   (control)   -> 401   <-- auth fires BEFORE routing
```

- **Control 401, real 401** ⇒ no unauthenticated surface. The public spec is the only exposure.
  Report at most a Low hardening note, and say the auth model is sound.
- **Control 404, real 401/403** ⇒ auth is per-route. Now enumerate sibling route generations and
  legacy paths — that is where the missing ACL usually lives.
- **Write path 401 with a bogus identifier** ⇒ auth precedes the identifier lookup, so no BOLA.
  `POST /vistacockpit/stopProduct/<bogus>/<bogus>` → 401 rather than 404 is the tell. Never fire a
  destructive call with a real identifier to distinguish 401 from 403; the bogus-id result is enough.

---

## 4. Result distribution — what to expect

Seven primitives, one completed:

| chain | outcome |
|---|---|
| patch-lag differential | **COMPLETE → Medium** |
| leaked third-party host | real, **already claimed** → dropped |
| spec → internal OAuth host | DIES (vendor-owned domain, internal-only) |
| spec → destructive ops | DIES (401 before identifier lookup) |
| version → known CVE | DIES (all CVEs need auth; uniform login errors = no enum oracle) |
| spec → vendor-internal host | DIES (RFC1918) |
| auth differential → BOLA | UNPROVEN (backend datasource down) |

1-in-7 is the normal ratio on a well-maintained estate. That is a result, not a failure — the point of
the chain table is that each death has a **named fact**, so the engagement closes honestly instead of
claiming either "0 findings" or an inflated chain.
