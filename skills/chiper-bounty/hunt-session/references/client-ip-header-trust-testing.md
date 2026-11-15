# Client-IP header trust — testing an IP-derived session token (verified 2026-10)

Trigger: a `Set-Cookie` value that looks like it encodes an IP, or a cookie whose value changes shape
when you send `X-Forwarded-For`. Seen live on a broadcaster estate: `Vietnam2Session=127.0.0.<xff>…`
and `HopSession=127.0.0.<xff>…` on 16 sibling hosts of one domain.

## 1. Confirm the header is the source (one request each)

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ..."
C() { curl -s -A "$UA" ${2:+-H "$2"} --max-time 12 -D - -o /dev/null "$1" \
      | grep -iE '^set-cookie' | tr -d '\r'; }

C https://HOST/path                                   # baseline: real client IP
C https://HOST/path 'X-Forwarded-For: 1.2.3.4'        # does the token change?
C https://HOST/path 'Client-IP: 9.9.9.9'
C https://HOST/path 'X-Real-IP: 9.9.9.9'
C https://HOST/path 'True-Client-IP: 9.9.9.9'
C https://HOST/path 'Forwarded: for=9.9.9.9'
```

Observed result worth recording precisely, because it tells you which header the stack honours:
`X-Forwarded-For` and `Client-IP` are accepted; `X-Real-IP`, `True-Client-IP`, `Forwarded` were not.
Note also that a token can contain BOTH the real IP and the spoofed one, which means the app is
concatenating a chain rather than picking one hop.

## 2. Header → Set-Cookie reflection (attribute injection)

Once the value is reflected, test whether cookie-attribute syntax survives:

```bash
C https://HOST/path 'X-Forwarded-For: 1.2.3.4; Domain=evil.example'
# -> Set-Cookie: SESSION=127.0.0.1.2.3.4; Domain=evil.<rand>; Path=/; Domain=.victim
C https://HOST/path 'X-Forwarded-For: 1.2.3.4 ; Domain=x.example'
```

Reproduce the exact working payload **three times** before believing it — in the live run only the
`Domain=` form survived, while `Path=`, `Max-Age=`, `SameSite=`, `secure` and `expires=` payloads were
truncated. Reporting the non-reproducing variants as if they worked is the fastest way to lose
credibility.

Impact framing that survives triage:
- The legitimate `Path=/; Domain=<victim>` is appended **last**, so under RFC 6265 the injected
  `Domain`/`Path` do NOT win. Say that out loud.
- What *can* take effect: attributes the legitimate header never sets — `Max-Age`, `Expires`,
  `SameSite`, `Secure`, `HttpOnly`.
- Realistic preconditions: an intermediary that sets the header on a **victim's** request (proxy, NAT,
  misconfigured LB). Without that, an attacker only influences their own cookie → Low.

## 3. The three checks that decide the severity

Run all three; each is one bounded sweep, and their outcome is what turns Low into High or keeps it Low.

| Check | How | What a hit looks like |
|---|---|---|
| Response splitting | raw socket, put a literal `\r\nX-Marker: 1` inside the header value, then look for the marker in the response | marker present = header injection (High) |
| Caching | repeat the request and compare `X-Cache` / `Age`; a Set-Cookie response should never be shared | `X-Cache: HIT` WITH your reflection = cache poisoning (High) |
| **Authorisation on the spoofed IP** | fetch each interesting path twice — clean, then with `X-Forwarded-For: 127.0.0.1` — and diff status + body hash | any endpoint whose answer changes (High) |

The authz diff is the one people skip and it is the only path from Low to High. Script it:

```python
# ~40 hosts x ~5 paths x 2 variants, 0.35s apart -> ~420 requests, well inside a "no volumetric" rule
a = get(u, None); b = get(u, "127.0.0.1")
if a["s"] != b["s"] or a["sha"] != b["sha"] or a["n"] != b["n"]:
    diffs.append(...)
```

Live outcome on a 42-host estate: **0 XFF-sensitive endpoints**, so the finding stayed Low and the
report said so. An empty result is a result — write it into the report as "tested and ruled out"
rather than dropping it.

## 4. Also test, quickly

- **Session fixation**: send `Cookie: SESSION=ATTACKERCHOSEN` and see whether the server accepts it or
  mints a fresh one. Fresh-mint = no fixation; say so.
- **ACL bypass with the matching token**: get a token while spoofing `127.0.0.1`, then replay it
  against restricted paths both with and without the header. `403` in every combination = no bypass.
- **Cookie scope**: `Domain=.victim` means one subdomain's cookie is family-wide; note it, and note
  that it raises the value of any injection primitive rather than being a finding by itself.

## 5. Reporting shape for this class

Lead with the raw request/response pair (not a summary), then a "what I proved / what I am not
claiming / tested and ruled out" table, then the fix (`build the token from the server-observed
connection; validate and re-serialise an IP before it reaches any header; use a cookie API that
escapes attribute-breaking characters; add Secure/HttpOnly/SameSite`). Name the exact hosts and give
the count of affected hosts from the sweep — breadth measured, not asserted.
