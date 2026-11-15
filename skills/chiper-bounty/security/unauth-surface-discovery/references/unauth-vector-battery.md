# Unauthenticated Vector Battery — the ordered checklist (run this FIRST)

Every unauth surface gets this pass in order, cheapest→most expensive. Each item
produces an artifact (request/response, hit count, or a written negative). Do NOT
gate into authenticated testing until each reachable tier is walked.

## Tier 0 — Fingerprint (1 min, zero noise)
1. Tech stack from headers: `Server`, `X-Powered-By`, `X-AspNet-Version`,
   `X-Generator`, `X-Runtime`, `X-Drupal-Cache`, `lf-Contao-*`. This decides which
   nuclei templates (Spring/Laravel/Django/Rails/WordPress/SharePoint) to load.
2. Favicon hash → identify known framework panels (Spring Boot green leaf, etc).
   `favicon.ico` hash lookup beats guessing the stack.
3. TLS cert SAN list → sibling hostnames (subdomain seeds, cloud-provider names).
   `echo | openssl s_client -connect H:443 -servername H 2>/dev/null | openssl x509 -noout -text | grep -A1 SAN`
4. `OPTIONS H` → `Allow` header (method list = router probe for free).
   `TRACE` echo → XST (rare, but the probe is free).

## Tier 1 — .well-known & standard files
```
/security.txt  /.well-known/security.txt
/.well-known/openid-configuration          -> OIDC => run DCR battery (main skill §1l)
/.well-known/jwks.json                     -> JWT keys (alg confusion lead)
/.well-known/assetlinks.json               -> android deeplink/accepted origins
/apple-app-site-association                -> iOS deeplink
/robots.txt  /sitemap.xml                  -> Disallow = juicy hidden paths
/.well-known/change-password               -> pw reset URL redirect target
```
Every one is a single GET. A `200` on `openid-configuration` hands you the whole
provider surface; a `security.txt` gives the disclosures channel AND often an
internal hostname/nonce leak.

## Tier 2 — Source / config / backup disclosure
```
/.git/config  /.git/HEAD  /.git/logs/HEAD    -> run git-dumper (source white-box)
/.env  /.env.production  /.env.local  /.env.backup
/.svn/entries  /.DS_Store                    -> svn dumper / ds_store path list
/package.json  /composer.json  /yarn.lock  /Gemfile.lock  /poetry.lock
/web.config  /.htaccess  /php.ini  /wp-config.php.bak
backup/extensions: *.bak *.swp *~ *.orig *.old *.save index.php.old config.php~
*.js.map / asset-manifest.json               -> deployed source (main skill §1h)
```
A `.env` here is a Critical on its own (DB/secret keys). A `.git` is white-box for
the whole engagement. Probe the ~30 standard names with a `-mc 200,301,403` filter,
sort by size/status, and triage the hits — do not skip because "looks static".

## Tier 3 — Framework-specific exposure (match to Tier 0 fingerprint)
```
Spring Boot: /actuator /actuator/env /actuator/heapdump /actuator/beans
Laravel:     /_ignition/execute-solution  /telescope  /storage/logs/laravel.log
Django:      /__debug__/  (500 stack trace on DEBUG=True -> /nonexistent/)
Rails:       /rails/mailers/  /rails/db  /rails/info/routes
Jenkins:     /script  /api/json  /manage  /computer/
Grafana:     /api/dashboards/home  (anon login enabled?)
phpMyAdmin/Adminer/Metabase/Swagger:
  /phpmyadmin /adminer.php /metabase /swagger-ui.html /api-docs /v3/api-docs /openapi.json
WordPress:   /wp-json/wp/v2/users  /xmlrpc.php  /?author=1 (user enum)
```
Only test the ones matching the fingerprint; spraying every framework is noise.
A live `/actuator/env` (esp. with `spring.datasource`) or a management REST that
lists Heaps/has anon ends registered is a High/Critical disclosure fast.

## Tier 4 — Discovery ORACLES (the highest-yield tier — main skill detail)
These turn an opaque perimeter into a route map. Run in this order:
1. Page/Vite config mining — `window.VITE_*`, inline `configuration` block (§1, §1b)
2. NotNull error oracle — empty `{}` POST returns field names (§2)
3. Namespace enumeration filtered on ERROR TEXT (§3)
4. Single-dispatcher command sweep `nouns × verbs` (§3b)
5. `/metrics` route-delta oracle — snapshot→probe→re-snapshot (§1f)
6. SPA auth-flag grep — `.unsecured()` / `secure:!0` / `skipAuth` (§1d, §1g)
7. Deployed source maps → white-box route+key read (§1h)

## Tier 5 — Access-control probes on the UNAUTH endpoint set
Once you have endpoint names, test their auth model before ever authenticating:
1. Collection endpoints with NO cookie — `/api/users`, `/api/orders` unauth dump
   (the cheapest, highest-severity primitive; see hunt-idor probe #1).
2. Method override — `X-HTTP-Method-Override: DELETE`, `_method=DELETE`, verb swap.
3. Session-middleware PRESENCE check — `x-session-token: a` flip 401→200 (§1o).
4. Forgot-password / login enumeration — differential 200 vs 400 on email field
   ("no account" vs "email sent"). Call it enumeration, not ATO, unless reset
   token is handed back or host-header poisoning makes it ATO.
5. Registration enumeration — "email exists" oracle on signup.
6. SSO/SAML domain oracle — 200/400 split = customer list + tenant-id (§1i).
7. Unauth OAuth Dynamic Client Registration + metadata impersonation (§1l).
8. Keyset publish read/write asymmetry — gated read + open write = finding (§1n/1p).

## Tier 6 — Injection on reflected surface (ONLY after escaping map, §4)
1. Print the escaping map first — if `< > " ' &` all entity-encoded, no XSS point.
2. Host-header injection → password-reset poisoning (absolute-URL-in-email signal).
3. Open redirect on `next`/`redirect`/`return` params + login/logout flow.
4. SSRF via URL-accepting params → interactsh callback; then cloud metadata.
5. CRLF in header-echoing params; path traversal in file/download endpoints.
6. SQLi NEGATIVE via strict-typing, not sqlmap (§9) — string where number belongs.

## Tier 7 — Infra / DNS
1. Subdomain estate — subfinder + assetfinder + crt.sh + dnsx.
2. Dangling CNAME — anti-reuse posture check BEFORE claiming takeover (§1k).
3. S3/GCS bucket lock verification — 13-op matrix (see s3-bucket-lock-verification ref).
4. RFC1918 IPs in public DNS / TXT records.
5. Cloud metadata endpoints — only if a Tier 6 SSRF gives you a fetch primitive.

## Exit gate — the three-part negative before "unauth surface clean"
1. `tested` list with COUNTS (N probes, M hits), not adjectives.
2. `NOT tested` list where each item names the SPECIFIC gate blocking it.
3. Tool artifacts on disk for every class claimed clean.
If the NOT-tested list is non-empty and reachable, you are not done — see the
engagement-discipline section in the main skill.