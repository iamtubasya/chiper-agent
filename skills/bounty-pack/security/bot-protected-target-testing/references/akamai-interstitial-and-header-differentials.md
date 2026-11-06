# Akamai interstitial POW + the differentials that unblock a "403 estate"

Worked on finanzen.net (2026-10-16). Four independent walls looked identical from outside
("Access Denied" / empty probes) and each had a different, cheap key. Work through them in
this order before calling any host blocked.

## 1. The Akamai interstitial POW (per-path, solvable headlessly)

Symptom: one deep path (e.g. an article URL) returns **200 with a ~3 KB HTML page** instead of
the app, carrying:

```html
<meta http-equiv="refresh" content="5; URL='/path?bm-verify=AAQAAAAO...=='" />
<script> var i = 1792120260; var j = i + Number("7246" + "91756"); </script>
... POST /_sec/verify?provider=interstitial  body {"bm-verify": "<token>", "pow": j}
```

Recipe (one requests session, keep its cookies):

1. GET the page; treat it as the challenge if `"bm-verify=" in body[:1500]` (check for the
   marker — my first condition tested for the word "interstitial" and inverted, silently
   returning the challenge page as if it were content).
2. Parse `var i = (\d+);` and `var j = i + Number("(\d+)" + "(\d+)");` -> `pow = int(i)+int(a+b)`.
3. POST `https://<host>/_sec/verify?provider=interstitial` with JSON `{"bm-verify": <token>, "pow": pow}`,
   same-session cookies, `Content-Type: application/json`, `X-Requested-With: XMLHttpRequest`,
   `Origin`/`Referer` = the challenged URL -> `200 {"reload": true}`.
4. Sleep ~1 s, re-GET (2..3 tries) -> real content. The challenge is per-path and per-session;
   other paths keep working meanwhile.

## 2. Header-completeness differential (same host, same minute)

The edge scores the whole header set, not the UA alone. On the SAME host:

| Headers | Result |
|---|---|
| UA + Accept only | `403 Access Denied` (~394 b) |
| + Accept-Language, Sec-Fetch-Dest/Mode/Site, Sec-Fetch-User, Upgrade-Insecure-Requests | **200** |
| + sec-ch-ua / sec-ch-ua-mobile / sec-ch-ua-platform (needed on some hosts) | **200** |
| asset fetch (`/_content-assets/*.js`) without `Referer` + `Sec-Fetch-Dest: script` | **403**; with them -> 200 |

Build ONE browser-identical header dict and reuse it everywhere; a per-path 403 that survives it
is usually cookie-dependent (section3), not header-dependent.

## 3. Cookie-dependent paths: warm the session first

Member paths (`/myfinanzen/*` style)403'd even with the full header set until the same cookie jar
first fetched the homepage (`curl -c jar` -> home -> member path, `Sec-Fetch-Site: same-origin`,
`Referer: <home>`). Fresh jar + direct deep GET =403; warmed jar = 200. Always chain: home -> target.

## 4. Per-host UA-CLASS split (desktop blocked, mobile allowed)

`www.finanzen.ch/.at`: desktop Chrome UA -> **403** (root AND robots); mobile UA
(`Mozilla/5.0 (Linux; Android 14; Pixel 8) ... Chrome/126.0.0.0 Mobile Safari/537.36`) -> **200**.
The rule is per-host config, so before declaring a host unreachable, rerun the identical request
with the other UA class (and the reverse). A "403 everywhere" matrix on one host can be a UA
artifact while its sibling passes with the same client.

## 5. TLS-stack split (native curl vs WSL curl)

Windows-native curl (Schannel) got `403` from the apex of a host that WSL curl (OpenSSL,
`--http2 --compressed`) fetched with 200 using the SAME headers. Two stacks, two verdicts — try
every TLS stack on the box before writing a coverage-gap line, and keep `--compressed` (some edge
rules treat a no-accept-encoding client differently).

## 6. Scanner implication: a uniform 403 is a block page, not a result set

An ffuf POST sweep of a guessed endpoint wordlist returned `403 / ~400 b` for EVERY entry,
including endpoints hand-proven 200 seconds earlier. The endpoints were real; the CLIENT was the
problem (UA matrix in the main skill). One status + one size across a whole wordlist = canary with
a known-good URL from the same client, then rediscover the surface from CLIENT CODE (handler JS
under the scripts/static host names the real endpoints — `window.userApiEndpoint` + `strFunction`
beat any wordlist) and replay with the working client.

## 7. Artifact persistence when probing through WSL

WSL stops between `wsl -e bash -lc '...'` invocations and `/tmp` comes back EMPTY on the next
call — lost probe bodies mid-analysis twice. Save every response under `/mnt/c/Users/<user>/...`
from the first fetch, and pipe output through `tr -d '\000' | grep -a` (page bodies with binary
bytes make plain `grep` drop the whole stream as "Binary file matches").

## 8. Do not confuse any of this with an egress block

All four walls above respond to client shaping; an egress/reputation block does not (main skill
section3a-0). If a real-browser client gets the same body, switch the diagnosis to egress instead
of iterating headers.

## 9. Per-host WAF-vendor split — fingerprint each host, do not assume one edge (finanzen 2026-10-16)

`wafw00f` over the in-scope list: `www.finanzen.net` = **Akamai Kona SiteDefender**, `www..ch/.at`
= Akamai, `login.finanzen.net` = **Amazon CloudFront**, `api.finanzen.net` = "no WAF detected"
while still answering 403 to every client. Three different postures inside one programme — a rule
learned on `www` does not transfer to `login` or `api`, and "no WAF detected" plus a live 403 is
itself a diagnostic (edge rule without a matching fingerprint, or a deny list per path).

Tool quirk that costs a round: **`wafw00f -H` expects a HEADERS FILE path, not a header string.**
`-H "X-Bug-Bounty-Researcher: me@x"` prints a misleading
`CRITICAL: Headers file "X-Bug-…" does not exist!` and scans nothing. Write
`headers.txt` (`Name: value` lines) and pass `-H headers.txt`, including the programme's
identification header so fingerprinting traffic stays identified.

## 10. Real headless Chrome can still be denied — and the deny page is reusable evidence

The interstitial-solved flows and full headers still got `403` from `api.finanzen.net` under real
headless Chrome (`chrome --headless=new --dump-dom <api-url>` → the Akamai deny page). Treat an
`api.`/`geo.` host that answers every client — curl, WSL curl, warm cookies, headless Chrome —
as a **coverage wall**: record the exact deny body as evidence instead of escalating client
effort. (`headless=False` real Chrome, main skill §1, remains the one escalation not tested there.)

Reusable evidence property: the Akamai deny page **quotes the requested URL**
(`You don't have permission to access "http://<host>/" on this server.` plus an
`errors.edgesuite.net` reference id). When proving a client-side open redirect, the off-site host's
deny page as the final document is valid proof of where the browser landed — attach the
`--dump-dom` text next to the screenshot (bug-report-delivery rule 0d /
`references/live-evidence-renderer.md` has the full capture pattern, including the mitmproxy
flow-chain excerpt).
