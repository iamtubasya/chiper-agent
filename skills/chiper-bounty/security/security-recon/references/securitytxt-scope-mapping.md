# security.txt-defined scope: deriving the scope set objectively

## The policy shape this solves

Some programs (ORF.at is the worked case, 2026-10) define scope **conditionally**:

> "Only domains/subdomains which have a security.txt file in their root (i.e.
> https://shop.orf.at/security.txt) are in scope. Currently, the scope is limited https://orf.at"

Two sentences that can disagree. The right move is to (a) enumerate which hosts actually serve the
canonical file, (b) pick a reading of the narrowing sentence and record it, (c) state the reading and
the untouched hosts in the report.

## The measured case (ORF.at, 2026-10)

| step | number |
|---|---|
| subfinder subdomains | 267 |
| live hosts (httpx) | 150 |
| hosts serving the CANONICAL security.txt | **41** (+1 found later via a redirect pivot) |

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
: > securitytxt_map.txt
while read -r line; do
  host=$(echo "$line" | awk '{print $1}' | sed 's#https\?://##' | cut -d/ -f1)
  [ -z "$host" ] && continue
  out=$(curl -s -A "$UA" -L --max-time 12 "https://$host/.well-known/security.txt")
  if echo "$out" | grep -q "Contact: mailto:ciso@orf.at"; then
    st="IN-SCOPE (canonical)"; else st="out"; fi
  echo "$host :: $st" >> securitytxt_map.txt
done < live.txt
grep "IN-SCOPE" securitytxt_map.txt | sed 's/ :: .*//'
```

Runtime: ~150 hosts, `-L` + 12 s cap, a few minutes. Well inside any "no noticeable load" rule.

## The four decisions

1. **Content, not status.** `grep` for the program's own `Contact:` (or `Canonical:`) value. A bare
   `200` proves nothing.
2. **302 → canonical is IN scope.** `www`, `der`, `on`, `sport`, `news`, `oe1`, `fm4`, `topos`, `help`
   all 302'd their `/security.txt` to `https://orf.at/.well-known/security.txt` and returned the
   identical 267-byte body. Read that as the vendor asserting those hosts are covered
   (RFC 9116 `Canonical:`).
3. **Soft-200 HTML is NOT a security.txt.** `shop.orf.at` returned **200** at
   `/security.txt` — but the body was a Shopware `"Sales Channel Not Found"` HTML page. It is a
   third-party shop behind nginx; both the "3rd-party providers are excluded" clause and the
   "no security.txt" test put it out of scope. Same for SPA catch-alls that answer every path with the
   app shell. **This one false positive would have pulled a whole unrelated platform into scope.**
4. **The narrowing sentence wins if it is narrower.** The policy said scope was "currently limited to
   https://orf.at". Resolution used: the security.txt rule plus the canonical aliases (`orf.at` and
   the host family that redirects to it), everything else untouched. State this in the report.
   If you cannot justify the broader reading, take the narrower one — safe harbour is worth more than
   the extra surface.

## Late-discovered hosts: the trap that matters most

The most interesting targets are usually **not** in passive enumeration. On ORF.at these appeared only
inside a JS bundle on a host that *was* in scope:

```
konto.orf.at · konto-api.orf.at · anmeldung.orf.at · on-newsletter.orf.at · data-<hash>.orf.at
```

Every one of them returned no canonical security.txt → **out of scope, not tested**. Also found this
way and out of scope: `api-tvthek` / `api-qa|stage|test-tvthek`, `tvthek`, `admin.contentsales`,
`adinsights`, `beschaffung`, `appmeta`, `afeeds`, `adtech-*`.

**Rule: check scope for a host the moment you learn it exists, before the first request.** One
incidental read happened before a scope check in this run (a `GET /health` on an out-of-scope API);
the honest handling is to stop immediately, record the single request in the log, and mention it.

## What a scope map like this then exposes (reusable leads)

The ORF.at map was worth building because the in-scope set shared one backend: a **legacy Jetty 6.1.22
+ Helma estate** (`Server: Jetty(6.1.22)`, `Problem accessing /helma/`) on bits / boa / aurora / wetter
/ oe3, all setting a `Domain=.orf.at` cookie, all redirecting `/filehandler/` into
`https://websys.orf.at/admincenter/` (an ADFS/OIDC SSO Java admin portal).

Two techniques generalise from that map — run them on every in-scope host set:

- **Forwarding-header trust sweep.** Send each header separately —
  `X-Forwarded-For`, `X-Real-IP`, `True-Client-IP`, `Forwarded`, `Client-IP`, `X-Client-IP` — with a
  distinct marker IP, and see which one the app believes and *where it lands*. On ORF.at the value was
  both used to build the session token (`Vietnam2Session=127.0.0.<value><rand>`, `HopSession` on 16
  hosts, cookie scoped `Domain=.orf.at`) and reflected **verbatim into the `Set-Cookie` header**, so
  `X-Forwarded-For: 1.2.3.4; Domain=evil.example` produced a genuine injected
  `; Domain=evil.<rand>` attribute (3/3 reproducible). Then prove the negatives before claiming
  severity: raw-socket CRLF (server truncates → no response splitting), `X-Cache` (never cached),
  fixation (server always mints a fresh token), and an **XFF-authorisation diff sweep**
  (every in-scope host × a few paths, fetched with and without `X-Forwarded-For: 127.0.0.1`, comparing
  status + body hash). On ORF.at that sweep was 420 requests and returned **0 XFF-sensitive endpoints**
  — which is exactly what kept the finding at Low instead of overclaiming High.
- **Legacy error-page reflection sweep.** Old app servers echo the decoded request path into their
  handler-not-found page unescaped. One marker request per in-scope host
  (`/<random>%3Cscript%3Ealert(1)%3C/script%3E` **and** the same under any prefix the host is known to
  serve) finds them; 44 requests produced exactly two hits on ORF.at (`pipe.orf.at` and
  `bolek.orf.at`, `/fcmbridge/api/*` → RingoJS + Stick `Error: Unhandled request:` page). Confirm in a
  real browser with **two independent payloads** — a dialog (`alert(document.domain)`) *and* a silent
  DOM mutation (`document.title='XSSED-'+document.domain`) — so the proof does not depend on a dialog
  being capturable. Check `Content-Security-Policy` for a missing `script-src` before rating it.
