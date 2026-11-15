# Proxy / client-IP header trust — testing and honest severity

Class of finding: a server takes the client IP from an **untrusted request header** (`X-Forwarded-For`,
`Client-IP`, `X-Real-IP`, `True-Client-IP`, `Forwarded`) and uses it in something observable — a session
token, a `Set-Cookie` value, an audit log, a rate limiter, an ACL, a geo lookup.

Most of these look alarming and are **Low**. The whole job is to run the escalation ladder and stop at
the first rung that actually fails, then say so. Written from a live VDP engagement (2026-10) where a
`Set-Cookie` header injection turned out NOT to escalate — reported honestly as Low rather than dressed up.

## 1. Confirm the reflection and WHICH headers are honoured

Send a distinctive value per header, one header at a time, and diff the response. Do not assume XFF is
the only one — one target honoured *both* `X-Forwarded-For` and `Client-IP`, and the observed cookie
contained the real IP **and** the injected one.

```bash
UA="Mozilla/5.0"
for hdr in "X-Forwarded-For: 1.2.3.4" "X-Real-IP: 9.9.9.9" "True-Client-IP: 8.8.8.8" \
           "Forwarded: for=7.7.7.7" "Client-IP: 6.6.6.6" "X-Client-IP: 5.5.5.5"; do
  c=$(curl -s -A "$UA" -H "$hdr" -D - -o /dev/null "https://TARGET/path" \
      | grep -iE '^set-cookie' | tr -d '\r')
  echo "[$hdr] -> $c"
done
```

Read the response **without following redirects** (`-D -`, no `-L`) — see the pitfall at the end.

## 2. The escalation ladder — cheapest rung first

| # | Test | Pass = real bug | Observed on the live case |
|---|---|---|---|
| a | **CRLF / response splitting** — put a raw `\r\n` inside the header value | a marker header appears in the response | server truncates at CR, marker absent (use the raw socket below — `curl` refuses CRLF in header values) |
| b | **Cookie attribute injection** — `; Domain=x.example`, `; Max-Age=…`, `; SameSite=None` | the attribute lands in `Set-Cookie` | landed for `Domain=`/whole-value payloads, but the legitimate `Path=/; Domain=<parent>` is appended AFTER, and per RFC 6265 the **last** attribute wins — so it did not override |
| c | **Cache poisoning** — is the response cacheable and shared? | `X-Cache: HIT` replay of your injected header | always `MISS` on the endpoint that sets the cookie; not cached |
| d | **Session fixation** — supply your own session id, see if the server adopts it | server accepts your value | server minted a fresh token every time, ignored the supplied cookie |
| e | **ACL bypass** — repeat a 403 path with `X-Forwarded-For: 127.0.0.1` / `10.0.0.1` / `192.168.1.1` | status changes | identical 403 with and without |
| f | **⭐ Differential sweep (the decisive one)** — see §3 | an endpoint's answer changes with the header | **0 of 420** requests differed |

Rung (f) is the one that decides severity. Everything above it is a *primitive*; (f) is the *impact*.
Run it before you write a word of the report.

### Raw-socket CRLF probe (curl cannot send CRLF in a header value)

```python
import socket, ssl
def raw(host, path, xff_value):
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=20) as s:
        with ctx.wrap_socket(s, server_hostname=host) as ss:
            ss.sendall(b"GET " + path.encode() + b" HTTP/1.1\r\nHost: " + host.encode() + b"\r\n"
                       b"User-Agent: Mozilla/5.0\r\nAccept: */*\r\n"
                       b"X-Forwarded-For: " + xff_value + b"\r\nConnection: close\r\n\r\n")
            out = b""
            while True:
                c = ss.recv(65536)
                if not c: break
                out += c
                if len(out) > 200000: break
            return out
r = raw("TARGET", "/path", b"1.2.3.4\r\nX-MARKER: injected")
print(b"X-MARKER" in r)      # False = CRLF filtered, no response splitting
```

Percent-encoded newlines (`%0d%0a`) are NOT re-decoded by the header parser — if they come back literal,
that is also a negative, not a positive.

## 3. The differential sweep — does any endpoint decide AUTHORISATION on this header?

Two requests per endpoint: clean, then with `X-Forwarded-For: 127.0.0.1`. Compare **status + body
sha256 + length**. Any difference is the Low→High path and is worth chasing. Zero differences is a
finding in itself and belongs in the report.

Keep it modest — this is not a scanner and most programs forbid volumetric testing:

```python
PATHS = ["/", "/admin/", "/static-api/", "/api/", "/actuator/health"]   # 5 paths
# 42 in-scope hosts x 5 paths x 2 variants = 420 requests at ~0.35 s spacing  (~ 4 min, harmless)
```

Build the opener with a redirect handler that **refuses** redirects, or a 302 with `Location` will be
followed and you will compare the wrong server's response.

## 4. Reporting it honestly

State the precondition that actually gates the severity, because it is what a triager will push back on:

> The value is reflected into a `<Domain=<parent>>`-scoped cookie without sanitisation. Turning this
> into impact on a third party requires an attacker to control the victim's `X-Forwarded-For`, i.e. an
> intermediary (proxy / NAT / mis-configured CDN) in the request path. CRLF is stripped, the response is
> not cached, the session id is regenerated per request, and a 420-request differential sweep across 42
> hosts found no endpoint whose answer depends on the header.

Then list the negatives explicitly. A report whose "what I could NOT escalate" section is longer than the
finding itself is the correct shape for this class — and on an unpaid VDP it is the difference between a
Hall-of-Fame credit and an auto-closed "non-exploitable" ticket.

## Pitfalls

- **Never follow redirects while capturing the header you are testing.** With urllib's default opener, a
  `303 -> https://other-host/...` returns the *second* server's headers, so the injected `Set-Cookie`
  from the first hop is invisible and the sweep silently reports "no reflection". Use `-D -` without `-L`
  in curl, or a no-redirect handler in Python. This cost a whole sweep run.
- **Same payload, different result? Re-run it three times before believing either.** Cookie-injection
  payloads are parser-sensitive: on the live target `; Domain=evil.example` reproduced 3/3, while
  `; Max-Age=`, `; Secure`, `; expires=` and `; Path=` never appeared. One run of one payload is not
  evidence in either direction.
- **A `Vary: Origin` header is not CORS.** Seeing `Vary: Origin` on a response is common and means
  nothing on its own — check for an actual `Access-Control-Allow-Origin` echo of a foreign `Origin`.
- **Don't claim the cookie is "set for the whole domain" as impact by itself.** `Domain=.orf.at` scoping
  is real, but the injected attributes lose the last-wins rule to the legitimate ones. Enumerate which
  attributes have **no legitimate counterpart** (Max-Age / Expires / SameSite / Secure / HttpOnly) — only
  those actually take effect.
