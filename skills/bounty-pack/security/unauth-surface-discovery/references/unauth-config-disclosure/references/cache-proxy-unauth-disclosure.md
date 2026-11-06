# The cache-proxy variant: same object, two namespaces, one of them unauthenticated

A second shape of the same CWE-200 class, distinct from a naive `/api/settings` endpoint. Worked case:
**netplus.ch SA / dev.netplus.tv** (GObugfree · SUISSEDIGITAL umbrella, 2026-10-13). Load this when a
target's API base **302-redirects** instead of answering, or when the SPA talks to `/api/<base>` and
you suspect a caching reverse proxy in front of a gated backend.

---

## The tell: a 302 on an API path is an invitation, not a dead end

The client bundle used base `/api/mobile`. Every call under it answered:

```
GET /api/mobile/profile/    -> 302  Location: /api/cache/cache/mobile/profile/
GET /api/mobile/channels/   -> 302  Location: /api/cache/cache/mobile/channels/
GET /api/mobile/lineup/     -> 302  (to the auth page — this one really was gated)
```

Following the first redirect returned **the full JSON object with no credentials at all**. The
proxy namespace is directly reachable and the cached object was written without re-checking identity.

**Rule: whenever any in-scope host answers `302` on an API path, read the `Location` and hand-walk the
destination namespace before moving on.** That one habit produced the only reportable finding of the run.

```bash
curl -s -D - -o /dev/null "https://<host>/api/<base>/profile/" | grep -i '^location:'
curl -s -D - -o /dev/null "https://<host>/api/cache/cache/<base>/profile/"    # the destination, by hand
```

---

## The comparison IS the finding — report the asymmetry, not the single 200

A lone unauthenticated JSON file is a shrug. The finding is that **the same logical resource answers
two different ways depending on which namespace you ask**:

| path | auth expectation | observed |
|---|---|---|
| `/api/mobile/auth/login/` | gated | `401` |
| `/api/mobile/auth/fork/` | gated | `401` |
| `/api/mobile/auth/device/code/verify/` | gated | `401` |
| `/api/mobile/lineup/` | gated | `302 → auth` |
| `/api/mobile/profile/`, `/channels/`, `/version/`, `/play/`, `/vod/`, … | gated | `302` |
| **`/api/cache/cache/mobile/<same>`** | nothing | **`200` + full JSON body** |

Put that table in the report. It converts "a public file" into "broken access control on a cache proxy",
which is what the program's own impact list invites (*"Data/information leaks"*,
*"Possibility of data/information exfiltration"*, *"Information Leakage and Improper Error Handling"*
— from the netplus/SUISSEDIGITAL policy verbatim).

---

## Probe set

```bash
# 1) which cached objects exist? 404 = absent, 200 = cached and served unauthenticated
for n in profile channels lineup epg vod subscription subscriptions subscriber customer user users \
         account invoice invoices billing payment order orders stb devices session tokens rights \
         entitlement entitlements content config backupconfig version time status health; do
  printf '%-16s %s\n' "$n" "$(curl -s -o /dev/null -w '%{http_code} %{size_download} %{content_type}' \
     "https://<host>/api/cache/cache/<base>/$n/")"
done

# 2) hash each 200 so the report can prove stability (see "evidence format" below)
curl -s "https://<host>/api/cache/cache/<base>/channels/" | sha256sum
```

Observed hits on the worked case (all without credentials):

| endpoint | bytes | sha256[:12] | what it exposed |
|---|---|---|---|
| `channels/` | 62 279 | `873224d086bd` | 168 channels × 14 fields: name, number, EPG id, language, `channel_encrypted`, `channel_recordable`, `channel_replayable_hours`, transport types, pad in/out |
| `epglive/` | 66 582 | `c4574e19d4f1` | full EPG — **303 distinct network keys** |
| `profile/` | 2 154 | `c18975683934` | `operator_code`, `network_code`, `network_name`, `subscription_id`, `subscriber_tv`, `permissions[]`, `country_locked`, `cast_allowed`, category map, every CDN image template |
| `people/suggestions/` | 1 032 | `89100c4e9710` | unique actor list with airing counts |
| `backupconfig/` | 36 | `edacae6fab54` | config blob + timestamp |

Note `Cache-Control: public, max-age=60` on an identity-bearing endpoint — quote the header.

---

## Negatives to close BEFORE reporting (all confirmed negative here)

Run these, then say in the report that you did. Each one is a claim a triager can otherwise push back on:

1. **Cache poisoning / cache-key injection.** Replay the same URL with `Garfield-Version` (the product's
   own version header), `Accept-Language`, `X-Forwarded-Host`, `X-Original-URL`, `Authorization`, and
   arbitrary `X-*` headers; `md5sum` every body. All identical ⇒ the cache key is the path alone
   ⇒ **no poisoning vector**. Do this before you so much as mention cache poisoning.
2. **Traversal / SSRF through the proxy.** `/api/cache/../../../etc/passwd`, `%2e%2e%2f` variants,
   `/api/cache/http://169.254.169.254/latest/meta-data/`, `/api/cache/<scheme>://…`, `/api/cache/static/`.
   All `404`, and the proxy matches a **route table** — it does not fetch URLs. **Do not report SSRF.**
3. **Geo/auth bypass via client-IP headers.** Send `X-Forwarded-For` / `X-Real-IP` / `Client-IP` with
   `127.0.0.1`, `10.0.0.1`, `8.8.8.8`, a public non-CH IP, and both DC-internal IPs. If the
   discriminator field (`country_locked` here) does not move, there is no bypass — record the negative.

---

## The severity trap this technique sets

The cached `profile/` carried `subscriber_tv: -1` and `subscription_id: -1` — the **anonymous** variant.
So the defensible claim is:

> unauthenticated disclosure of operator configuration and full channel/EPG metadata

…and **not** "this serves customer PII". The tempting overclaim requires a *subscription* account to
observe the non-anonymous object, which you do not have. Log it as a **blocking ask for one test
credential** and keep it out of the finding body. State the proven/not-proven split in the report:
*proven* = operator config + channel/EPG metadata; *not proven* = whether the cache serves a subscriber
profile when `subscriber_tv != -1`.

Also check for a **multi-tenant backend** signature: the EPG returned 303 network keys — a shared
backend, not just the client's own operator. On umbrella programmes this often means the finding is
*one* report, filed once (netplus policy verbatim: *"Found bugs are eligible for reward only once, even
if they are found at several association members (e.g. if the same software is in use)"*). Never
multiply it per member.

---

## Evidence format that re-verifies in one command

Give byte size + sha256 prefix per endpoint (table above), plus the single paste-ready curl. Also
save each response to a per-endpoint file so the hash is reproducible from disk later:

```bash
curl -s -o "recon/cache__channels_" "https://<host>/api/cache/cache/<base>/channels/"
sha256sum recon/cache__channels_
```

---

## Adjacent false positives this engagement produced (same session, same discipline)

- **SPA catch-all.** `dev.netplus.tv` answered `200` @ **67 810 bytes**, byte-identical to `/`, for
  `/package.json`, `/.git/config`, `/assets/*.js.map`, `/static/js/`, **and a random control path**.
  All false positives. Always compare body **size + sha256** to `/`, and fire one deliberate
  random-path control before trusting any `200` from a wordlist.
- **A crawler hit that lives inside a third-party agent bundle.** `katana` returned
  `my.sweez.ch/API/register/` and `/API/logging/` — server-side `404`. Those strings exist only inside
  the bundled **New Relic** browser agent: `["API/register/".concat(a,"/called")]`. Grep the body
  context; if the match sits in a minified vendor bundle it is instrumentation, not a route.
- **A framework error page echo is not XSS.** Express `Cannot GET /<path>` echoes the raw path in
  `<pre>`, but served with `Content-Security-Policy: default-src 'none'` +
  `X-Content-Type-Options: nosniff`. Check CSP and content-type before calling an echo a finding.
- **Error pages can hand you a hardened default.** A `404` here also came with
  `X-Content-Type-Options: nosniff`. Record working controls as controls (see also the
  "account enumeration returned no oracle" note in the engagement log) — a documented negative is
  deliverable, and it stops the next session re-testing it.

## Adjacent finding class: self-referential redirect loop

Found on an in-scope host while probing the signup path. `my.sweez.ch/register/` answered
`302 Location: /register/` — to itself. Prove it, don't eyeball it:

```bash
curl -s -D - -o /dev/null -L --max-redirs 8 \
  -w 'final=%{url_effective} hops=%{num_redirects} http=%{http_code}\n' "https://<host>/register/"
# hops=8 http=302 final == same URL  -> infinite loop
curl -s -D - -o /dev/null -H "Cookie: sessionid=x; csrftoken=y" "https://<host>/register/"  # still 302 → loop
```

Check both slash forms (`/register` → `301` → `/register/` → loop). Real-world result:
`ERR_TOO_MANY_REDIRECTS` for every visitor — the signup funnel of an in-scope product is unreachable.
Frame as **Low/Medium broken functionality on a business-critical path**, never as RCE/ATO; if the
program excludes "best practice" items, say in the body that this is a functional defect on an in-scope
product URL, not a header nitpick, and let triage calibrate.

---

## Tool-run hygiene discovered here

- **`gau` / `waybackurls` returning 0 rows is a SUSPECT RUN, not a negative.** Both returned nothing on
  hosts where `katana` produced 30 139 URLs. Ledger it as *"0 rows — failure suspected, katana used
  instead"*. Never list an empty tool run as evidence that nothing exists.
- **A tool that cannot start is "unavailable", not "no findings".** `graphqlmap` pointed at a
  non-existent local path and emitted a Python traceback; `jsluice`, `whatweb`, `wpscan` were absent.
  Record as unavailable **with the reason**; never count them for or against coverage.
- **`curl -o /dev/null` reports `size_download 0`.** Several probes looked like empty `200`s purely
  because of that. When body size matters, write to a file or pipe to `wc -c`.
- **Never read a probe result from a fixed temp path.** A `/tmp` file left by a *different* target
  produced a fabricated `{"statusCode":400}` reading that had to be retracted mid-engagement. Write
  every probe to a path unique to `<target>_<vector>` and re-read from that file.
