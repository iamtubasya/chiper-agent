# Cloudflare JS challenge + local DNS/routing failure

Worked case: `toshi.bet` (crypto casino, Next.js front end + Express API microservices),
2026-10-18, Windows 10 / git-bash. The apex and every API subdomain sat behind a Cloudflare
**managed JS challenge**, and the machine's routing to the resolved Cloudflare IPs was broken.
Neither problem alone is unusual; together they produce a very misleading symptom set.

## The symptom chain (and what each step actually proves)

```
DoH 1.1.1.1  -> toshi.bet  A 172.67.71.220, 104.26.1.49, 104.26.0.49   # name is fine
curl https://toshi.bet/                      -> 000, timeout after 20s   # NOT "site down"
curl https://172.67.71.220/                  -> 403 (5.5 KB)             # IP reachable, edge filtering
curl --resolve toshi.bet:443:104.26.1.49 ... -> 403 + `Cf-Mitigated: challenge`   # <-- the answer
```

Three separate facts, in order:

1. **DoH resolving proves nothing about reachability.** Use it to get the IP set, then stop
   trusting the name.
2. **A bare-domain timeout next to a working direct-IP request means your resolver handed you an
   IP you cannot route to.** Cloudflare returns three A records; one was dead from this network.
   `curl --resolve <host>:443:<working-ip>` pins a good IP **while keeping the correct SNI**,
   which is the only way to reach a Cloudflare-fronted host by IP — a bare `curl https://<ip>/`
   fails TLS with `SSLV3_ALERT_HANDSHAKE_FAILURE` because the SNI no longer matches.
3. **`Cf-Mitigated: challenge` in the response headers is the fingerprint.** It distinguishes
   "the edge is challenging this client" from an application 403. Once you see it, every
   non-browser client gets the ~5.5 KB `Just a moment...` interstitial and nothing else.

## The working client: SeleniumBase with a pinned resolver

`browser_exec` / plain Playwright inherit the broken system DNS and die with
`ERR_CONNECTION_TIMED_OUT`. SeleniumBase's `Driver` accepts a Chromium flag that overrides
resolution for the whole browser:

```python
from seleniumbase import Driver

RESOLVER = ("--host-resolver-rules="
            "MAP toshi.bet 104.26.1.49,"
            "MAP www.toshi.bet 104.26.1.49,"
            "MAP api.toshi.bet 104.26.1.49,"
            "MAP user.toshi.bet 104.26.1.49,"
            "MAP wallet.toshi.bet 104.26.1.49")   # one MAP per host you will touch

d = Driver(headless=True, uc=True, incognito=True, chromium_arg=RESOLVER)
```

`uc=True` (undetected-chrome mode) matters here: it is what gets the managed challenge solved
rather than looped. `incognito=True` keeps the clearance cookie out of your everyday profile.

## Passing the challenge — poll the title, do not sleep-and-hope

```python
d.get("https://toshi.bet/")
for i in range(6):
    d.sleep(6)
    if "moment" not in d.title.lower():
        break
    try:
        d.uc_gui_click_captcha()
    except Exception:
        pass
# success looks like: title == "Instant Withdrawal Casino No Verification | Toshi.bet"
# and d.get_cookies() now contains cf_clearance
```

The tell that you are through is the **title**, not the status code — the interstitial is also a
200. Save the cookie jar (`d.get_cookies()`) if you want to replay authenticated calls later.

## Downloading the real JS bundles — fetch from INSIDE the page

This is the §2 trap in its purest form. `curl --resolve` against `/_next/static/chunks/*.js`
returns the **challenge HTML**, byte-for-byte the same ~5.8 KB page for all 53 bundles. It looks
like a successful download (non-zero size, rc=0) and it contains no JavaScript at all. Do not
analyse those files.

Fetch them from inside the cleared page instead — the browser has the clearance cookie and the
right fingerprint:

```python
srcs = d.execute_script(
    "return Array.from(document.querySelectorAll('script[src]')).map(s=>s.src)")
for s in srcs:
    if not s.startswith("https://toshi.bet"):
        continue                                    # third-party: GTM, CF insights, Intercom
    txt = d.execute_script(
        "const r = await fetch(arguments[0], {credentials:'include'}); return await r.text();", s)
    if txt and len(txt) > 200:
        open("bundles/" + s.split("/")[-1], "w", encoding="utf-8").write(txt)
```

59 real bundles, 2.2 MB, versus 53 challenge pages from curl. **Always sanity-check the first
download**: if every file is the same size and starts `<!DOCTYPE html>`, you fetched the wall.

## API subdomains: 429 JSON is the rate-limit signal, not a 403

Once the apex is cleared, the API subdomains behave differently from the apex and from each other:

| Host | Response | Reading |
|---|---|---|
| `user.toshi.bet/`, `wallet.toshi.bet/` | `200 {"api-version":"1.0.0"}` | live Express API, no challenge |
| `user.toshi.bet/notifications` | `401 {"error":"No token provided"}` | auth enforced, route exists |
| `user.toshi.bet/meToshi` | `404 Cannot GET /meToshi` (Express) | wrong path — the real route is namespaced |
| `track.toshi.bet/`, `statics.toshi.bet/` | `429` with `content-type: application/json` | **rate limited** |
| `api.toshi.bet/`, `websocket.toshi.bet/` | `403` HTML (challenge) | edge-challenged |

A single burst of ~8 requests across subdomains was enough to earn a 429. Drop to **one request
per host with 2.5–3 s between hosts** and the JSON 200/401 answers come back immediately. That is
§3a-1's budget pattern, and the JSON content-type is the cheap tell that you are being throttled
rather than challenged.

## Windows / MSYS specifics that cost time here

- **`/tmp` does not exist** in this git-bash. `curl -o /tmp/body.txt` silently writes nothing and
  the follow-up `head` fails with *cannot open*. Use `$LOCALAPPDATA/Temp` or a relative path.
- **Native Windows programs do not get MSYS path translation.** `python script.py` reading
  `C:/Users/...` works; `node /tmp/a.js` does not. Pass forward-slash native paths.
- **`urllib`/`requests` with `context` tweaks still fail** where `curl --resolve` succeeds, because
  the failure is the resolved IP, not the TLS stack. Reach for `--resolve` before rewriting the
  client.
- **`web_extract` and `web_search` were both unavailable** in this session (search-only backend /
  timeout). The browser + `--resolve` path replaced them entirely; do not treat a dead
  `web_extract` as a reason to stop.

## Transferable rule

When a Cloudflare-fronted target times out on the bare domain: **DoH for the IP set →
`curl --resolve` against each IP to find a routable one → read `Cf-Mitigated` to confirm the
challenge → move the whole engagement into SeleniumBase with `--host-resolver-rules` → fetch
bundles in-page → go GENTLE on the API hosts.** Never conclude "the site is down" from a
bare-domain timeout, and never analyse a bundle you did not verify is JavaScript.
