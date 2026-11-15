# WordPress: username enumeration that survives hardening + version-precondition discipline

Companion to `wordpress-admin-attack-surface.md` / `wordpress-unauth-handler-hunting.md`.

## 1. User enumeration even when `/wp-json/wp/v2/users` is 404

When the REST users route is intentionally disabled, usernames still leak through:

- **oEmbed** (unauthenticated, one request):
  ```bash
  curl -s 'https://SITE/wp-json/oembed/1.0/embed?url=https://SITE/<post-or-page>/&format=json'
  # -> {"author_name":"Sunny Agarwal","author_url":"https://SITE/author/sunny/", ...}
  ```
  The `author_url` slug **is** the WordPress login username.
- **Author archives**: `GET /author/<slug>/` → `200` confirms the username exists.
- **wpscan** classifies these as `Oembed API - Author URL`, `Author Id Brute Forcing - Author
  Pattern`, `Rss Generator`.

**Framing that lands:** the vendor already hardened the obvious route (REST users → 404), but the
mitigation is **incomplete** — the oEmbed + author routes bypass it. Report the *incompleteness*, not
just "user enum exists". Severity Low/Informational; impact = usernames feed targeted password
spraying against `wp-login.php`.

## 2. wpscan — correct no-token invocation, and the abort-vs-block trap

No API token ⇒ **no vulnerability data**; only fingerprinting is available:
```bash
wpscan --url https://SITE --random-user-agent --no-banner --disable-tls-checks \
       --enumerate ap,u,cb,dbe --plugins-detection passive -f json -o out.json
```
Two aborts that **look like a target block but are your own flags**:
- `--api-token ""` → `Scan Aborted: --api-token Empty option value supplied`
- `--enumerate ap,p` → `Scan Aborted: --enumerate Incompatible choices detected: ap, p`
  (`ap` and `p` are mutually exclusive; `vp`/`vt` **require** a token)

**Rule: read the abort reason before blaming the target.** A `Scan Aborted:` line means *nothing was
scanned* — it is NOT evidence of a WAF/Cloudflare block. Never write "blocked by Cloudflare" into the
coverage ledger without seeing an actual HTTP 403 on the requests. Same class of error elsewhere:
`dnsx -retries` (flag absent) → run dies, `1 resolved` reads as a false negative; `dig` returning
empty reads as NXDOMAIN. **Any `0 rows` / aborted run is a suspect run, not a result.**

## 3. Vulnerable version present ≠ exploitable (over-claim guard)

A version inside a CVE's affected range is **not** a finding until the advisory's **precondition** is
verified present. Worked examples:

| Component / CVE | Preconditions the advisory names | Check |
|---|---|---|
| Beaver Builder **CVE-2026-92084** (unauth shortcode exec, ≤2.11.0.5) | a BB page using the **Sidebar module** populated with an attacker-controllable widget | `grep fl-module-sidebar` across sitemap pages; `comment_status` open |
| Beaver Builder **CVE-2026-95865** (blind SQLi ≤2.11.0.5) | authenticated **Contributor+** | — (not unauth) |
| LayerSlider **CVE-2024-2879** | only 7.9.11–7.10.0 | version compare (6.x is out of range) |
| Slider Revolution **CVE-2026-6728** | `get_stream_data()` / stream feature | `grep -a get_stream_data .../rs6.min.js` (absent in 6.5.7) |

When the precondition is absent, record it honestly as a **hardening note** ("vulnerable version
present, exploit path absent — patch anyway"), never as a demonstrated vulnerability. Verify 3×
before reporting anything, and never run an exploit request that would rely on an unverified path.

## 4. No-token version→CVE lookup

With no wpscan token, map plugin versions to CVEs using the public databases (Wordfence threat-intel,
cvefeed.io, sentinelone vuln DB, thehackerwire) **and** the local nuclei CVE templates:
```bash
grep -rli '<plugin-slug>' ~/nuclei-templates/http/cves/
```
The nuclei template's `name:` line states the exact affected range — the fastest authoritative check.
