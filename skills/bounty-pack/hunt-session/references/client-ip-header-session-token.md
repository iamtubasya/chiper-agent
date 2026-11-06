# Client-IP header → session token / Set-Cookie (the "Vietnam2Session" pattern)

A real bug class found on legacy Java app tiers (Jetty 6 + RingoJS/Stick era, 2026-10). Two distinct
manifestations of ONE root cause: the application treats a **client-supplied request header** as if it
were the connection peer address, and then uses that value where it must not.

## 1. The trigger — three requests, no payloads

Send a unique marker in each candidate header and watch the `Set-Cookie` value:

```bash
curl -sD - -o /dev/null -H 'X-Forwarded-For: 1.2.3.4' https://<host>/<path>
# Set-Cookie: Vietnam2Session=127.0.0.<something built from 1.2.3.4><random>; Path=/; Domain=.orf.at
```

Header precedence varies per app. Test all of, in this order, and record which one wins:

| Header | Result on the live target |
|---|---|
| `X-Forwarded-For` | **honoured** (value lands in the token) |
| `Client-IP` | **honoured** (appended alongside the real IP) |
| `X-Real-IP`, `True-Client-IP`, `Forwarded`, `X-Client-IP` | ignored — real egress IP used |

A non-IP value proves there is no parsing step at all: `X-Forwarded-For: hello` produced a token with
no `hello` in it, while `1.2.3.4` produced `127.0.0.1.2.3.<random>` — i.e. the app concatenates a
prefix, a filtered copy of the header, and a random suffix. Do not over-model the filter; report only
what reproduces.

## 2. Cookie attribute injection (the reportable half)

On `bits.orf.at` and `boa.orf.at`, `/filehandler/` (HTTP 303) put the header into the cookie value
VERBATIM apart from CR/LF stripping, so cookie-attribute syntax survived into the response header:

```
X-Forwarded-For: 1.2.3.4; Domain=evil.example
-> Set-Cookie: Vietnam2Session=127.0.0.1.2.3.4; Domain=evil.14wftnua8jcfo; Path=/; Domain=.orf.at
X-Forwarded-For: 1.2.3.4 ; Domain=x.example
-> Set-Cookie: Vietnam2Session=127.0.0.1.2.3.4 ; Domain=x.11blxy4y6fzo9; Path=/; Domain=.orf.at
```

The cookie was issued with `Domain=.orf.at` — **domain-wide**. Reproduced 3/3 with the identical
payload; a control request without the header returns the normal short value.

Payloads whose FIRST attribute was `Path=`, `Max-Age=`, `SameSite=`, `secure` or `expires=` were
truncated and did NOT survive. Only the `Domain=` form reproduced. Whatever you find, sweep the
attribute names one per request and report the survivors — do not assume they all work.

## 3. The decisive test: does anything DECIDE on that IP?

This is the gate between Low and High. An attacker-influenced address is only worth a High if some
endpoint makes an authorisation (or rate-limit / allow-list) decision on it.

Sweep every in-scope host x a handful of paths, **twice** — clean vs `X-Forwarded-For: 127.0.0.1` —
comparing status + body length + body sha256:

```
42 hosts x 5 paths (/ , /admin/ , /static-api/ , /api/ , /actuator/health) x 2 = 420 requests
XFF-SENSITIVE ENDPOINTS: 0
```

Zero diffs means **the Low→High path does not exist** on the tested surface, and the honest severity
is Low/low-Medium. Say so in the report. A single diff is the finding — escalate it immediately.

Also test the obvious concrete bypass directly: `X-Forwarded-For: 127.0.0.1` / `10.0.0.1` /
`192.168.1.1` against any 403 endpoint, and again while supplying a matching IP-derived token. On the
live target every combination stayed 403.

## 4. What to rule out before writing it up (all negative here — do not re-claim them)

| Test | Method | Result |
|---|---|---|
| CRLF / HTTP response splitting | raw socket, `X-Forwarded-For: 1.2.3.4\r\nX-Marker: 1` | server truncates at CR, marker absent |
| Cache poisoning | repeat request, read `X-Cache` | always `MISS` on the Set-Cookie endpoint |
| Session fixation | supply `Cookie: <name>=ATTACKERCHOSEN` | server always mints a fresh token, ignored |
| XFF-based ACL bypass | 403 endpoints with internal XFF values | 403 regardless |
| Attribute override by ordering | legit `Path=/; Domain=<apex>` is appended LAST | RFC 6265 last-wins, injected Domain/Path do not take effect |

The honest impact statement: an intermediary that sets the header on a victim's request (proxy, NAT,
load-balancer misconfiguration) can inject attributes into a cookie scoped to the whole domain family,
and attributes with no legitimate counterpart (`Max-Age`, `Expires`, `SameSite`, `Secure`, `HttpOnly`)
are the ones that would take effect. Without an XFF-controlling intermediary there is no third-party
impact — write that down rather than implying otherwise.

## 5. Breadth sweep (cheap, and it is what makes the report land)

Request `/` and one app path on EVERY in-scope host with a marker value and record every `Set-Cookie`
whose value embeds `127.0.0.<marker>`. Here 16 of 42 hosts minted `HopSession=127.0.0.<marker><rand>`
while only 2 reflected the attribute portion. Reporting "16 hosts share the construction, 2 of them
also leak attributes" is far stronger than one host, and it is still ONE root cause → ONE report.

## 6. Pitfall that cost a cycle — redirect chains hide the header

Fetching with redirect-following ON records only the FINAL response's headers. The IP-derived cookie
was set on the **303** from `bits.orf.at/filehandler/`, which then redirected to
`websys.orf.at/admincenter/` and returned a plain `JSESSIONID`. The sweep therefore looked clean while
the bug was live. Use a no-redirect opener (`urllib.request.build_opener(NoRedirect)`, `curl` without
`-L`) when you are harvesting cookies, and re-check any host whose `/filehandler/`-style path 303s.
