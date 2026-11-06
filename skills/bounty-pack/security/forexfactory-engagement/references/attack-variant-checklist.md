# Attack-variant checklist for a hardened target (Cloudflare + WAF + reCAPTCHA)

Run every row, record the result **including negatives**, and say which tool actually produced the
artifacts. Derived from three rounds against forexfactory.com where everything below came back
negative — so use this as a "have I really covered it" list, not a list of expected wins.

| # | variant | tool / command | acceptable evidence | FF result |
|---|---|---|---|---|
| 1 | mass assignment / entitlement | craft the JSON body of the signup or profile endpoint with `is_admin, role, usergroupid, userid, verified, perms{}, subscription_id, content_id, plan`… | new account's `FF.perms`/`is_team`/profile status unchanged ⇒ whitelist | ignored ⇒ negative |
| 2 | prototype pollution | `__proto__[x]`, `constructor[prototype][x]`, nested flex keys into the settings/save endpoint | a downstream sink changes | no effect |
| 3 | deserialisation / param pollution | php-serialised blob, 4 KB junk, NUL bytes, duplicated `do=` in the model blob | 500 + stack trace, or changed state | clean |
| 4 | XXE | `application/xml` body with `<!DOCTYPE … SYSTEM "http://<oob>/x">` to every XML-returning endpoint | OOB callback | no callback |
| 5 | blind SSRF | push the interactsh host into every server-side parameter (broker `server`, search backend, `url=`, `website=`, `path=`, `referer=`, `filename=`) | DNS/HTTP hit on the listener | 0 callbacks over 20+ params |
| 6 | HTTP desync | raw socket: CL.TE, TE.CL, `Transfer-Encoding:\tchunked`, `xchunked` | 200 with desync behaviour | 400/501 at the edge |
| 7 | verb tampering / CSRF-via-GET | TRACE, `X-HTTP-Method-Override`, OPTIONS, GET on state-changing routes | state change via GET | 405 / ignored / 400 unauth |
| 8 | IDOR (excluded class — still map it) | swap ids on read APIs, `ticket`/`id`/`uid` enumeration | other users' data | rejected (and excluded anyway) |
| 9 | SQLi (legacy + app params) | `sqlmap`, `ghauri -u URL --batch --level=2` (no `--risk`), numeric-cast probes `id'`, `and 1=1`, `1e5`, `%00` | differential/error | cast-only, negative |
| 10 | XSS reflected | `dalfox file urls.txt --skip-bav` | **verify every hit**: a `[G] BUILTIN` grep hit is a false positive until the payload is seen reflected | 1 FP confirmed |
| 11 | XSS stored | write + read-back on every free-text field (signature, status, profile custom fields, explorer title, notes) | raw HTML on a page another user loads | surface not reachable for member accounts |
| 12 | DOM XSS | sink inventory (§7 of legacy-surface-archaeology.md); postMessage origin check | attacker-controlled source → sink | no first-party handler |
| 13 | SSTI | `{{7*7}}`, `${7*7}`, `{{7*'7'}}` on refletive params; compare against a control render | 49 rendered *and* payload not reflected | not reflected |
| 14 | GraphQL | `graphqlmap`, POST `{"query":"{__typename}"}` to `/graphql`, `/graphiql`, `/api/graphql` | 200 + data | 404 everywhere |
| 15 | file upload | plupload/avatar endpoints, extension + content type matrix; check where the file is served from and with which `Content-Type` | served as text/html, traversal, or accepted non-image | WAF 403 on `.php`/`.svg`, server rejects `.html` |
| 16 | CSRF-freeness | significant POST with no token / cross-site `Origin`+`Referer` | state change | 400 or `<error>` |
| 17 | clickjacking | `x-frame-options` / `frame-ancestors` on auth + settings pages | missing on actions | SAMEORIGIN + `'self'` |
| 18 | open redirect (not excluded) | `//host`, `%2f%2fhost`, `\host`, `path//host`, `?next=|?url=` | `Location: https://evil` | canonical/404 |
| 19 | secrets / source leak | `trufflehog filesystem <js dirs>` (never the URL dumps) + key regexes + `.map` probe | live key, internal host | nothing |
| 20 | buckets / ports | `s3scanner scan --bucket <name>`, `naabu -top-ports 100` | public bucket / non-CF port | none / all-CF |
| 21 | dir-bust on every host | `ffuf -w D:/data hermes/wordlists/<category>/*.txt`, `dirsearch -e php,do,action -x 404,403` | real 200/301 with a sensible `<title>` | only soft-404 profiles |
| 22 | legacy/zombie endpoints | `gau --subs` → mine paths+params → liveness → probe | live legacy handler | only `attachment.php` + a stub |
| 23 | race | `race-checker.py -u URL --threads 8 --attempts 25` (no cookie support → unauth) + manual reasoning | inconsistent success | uniform 403 |
| 24 | automation/captcha | is the invisible reCAPTCHA Enterprise actually enforced server-side? | API accepts an empty token | enforced ⇒ captcha is a real control |

## Rules learned

* **Excluded classes first.** Read the program page and quote the exclusion list in the log; it stops
  you sinking hours into TLS, CORS, cookie flags, session, IDOR, rate-limit, or enumeration findings.
* **A control sample beats a single hit.** One 200 is not access control; the 403/400 class next to
  it is what tells the story (attachments, unknown ids, guest vs session).
* **Verify tool output.** Empty file ⇒ check the tool actually ran (ffuf help page, nuclei counters).
* **Captcha-gated flows** (registration, password reset) need a real browser; drive the site's own
  wizard instead of fighting the API. See the umbrella's §§2–3.
* **Watch the vendor's anti-abuse**: after enough registration/posting activity accounts flip to
  "Membership Denied" and the settings UI disappears — do stored-content work on one older account.
