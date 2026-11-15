# Working harness: DataDome API access + audio-CAPTCHA account creation

Case: `www.vinted.com` (Bugcrowd `vinted-uab-mbb`), 2026-10-01. Everything below is verified
end-to-end, not theorised. Companion to SKILL.md §2f.

---

## 1. The transport matrix (why the obvious approaches fail)

| Transport | Result |
|---|---|
| `curl` any UA/headers to `/api/v2/*` | `403 <!doctype html>` (DataDome block page) |
| Playwright `ctx.request.get()` | 403 |
| `pg.evaluate("fetch('/api/v2/banners',{credentials:'include'})")` | **403 HTML** |
| Same, plus a byte-for-byte copy of every header the app sends | 403 |
| `page.route()` → `route.continue_(url=<target>)` on a request the app itself makes | **200 JSON** |

The discriminator is **not** headers, cookies, or TLS. DataDome's JS instruments the
*app's own* request path; a request you author never carries that instrumentation. So the only
reliable transport is: let the app issue the request, rewrite its destination in flight.

Corollary: this also defeats the usual "use `ctx.request` for cheap enumeration, drop to
`pg.evaluate` fetch on 403" ladder in SKILL.md §2. On this target **`pg.evaluate` fetch is also
dead** — go straight to route-rewrite.

---

## 2. The harness (~30 lines, reusable)

```python
async def query(ctx, method, path, body=None):
    """Rewrite one app-originated request to `path`; return (status, body)."""
    pg = await ctx.new_page()
    result = {"status": None, "body": None}
    done = asyncio.Event()
    target = path if path.startswith("http") else HOST + path

    async def route_handler(route):
        if not result["status"]:
            try:
                if method == "GET":
                    await route.continue_(url=target, method="GET")
                else:
                    await route.continue_(url=target, method=method,
                                          post_data=body or "",
                                          headers={**route.request.headers,
                                                   "content-type": "application/json",
                                                   "origin": HOST,
                                                   "referer": HOST + "/member/register/email"})
            except Exception as e:
                result["status"] = "ROUTEERR"; result["body"] = str(e); done.set()

    async def resp_handler(resp):
        if resp.request.url == target and not result["status"]:
            result["status"] = resp.status
            result["body"] = await resp.text()
            done.set()

    await pg.route(TRIGGER, route_handler)          # e.g. "**/api/v2/**"
    pg.on("response", lambda r: asyncio.create_task(resp_handler(r)))
    await pg.goto(START, wait_until="domcontentloaded")   # e.g. HOST + "/"
    try:
        await asyncio.wait_for(done.wait(), timeout=20)
    except asyncio.TimeoutError:
        result["status"] = result["status"] or "TIMEOUT"
    finally:
        await pg.close()
    return result
```

Operational notes learned the hard way:

- **Pick a trigger that fires on every page load.** `/api/v2/banners` worked on the home page.
  `**/api/v2/**` is a safer default. A trigger tied to one page stops firing the moment the app
  redirects that page elsewhere (e.g. a restricted account bouncing `/` → `/main/banned` made
  every subsequent query return `TIMEOUT` with a 0-byte file — silently looks like "no data").
- **Supply a concrete path in the trigger pattern, not a bare host**, or the route intercepts
  more than you intended.
- **Force the method explicitly.** Rewriting a GET trigger to a POST target without
  `method="POST"` leaves the original method/body in place and you silently send the wrong request.
- **Let the profile be swappable.** `VINTED_PROFILE` / `VINTED_TRIGGER` / `VINTED_START` env vars
  let you run a clean anonymous profile side by side with an authenticated (possibly restricted)
  one. Once an account gets restricted, its profile is poisoned for recon — do not keep using it.
- **Budget ~3–5 s per query** (one page load each). Loop `page.goto` per path; batching several
  targets per load works by matching request N → target N.

---

## 3. Side-findings worth recording on any such target

- **A CSRF token baked into the bundle is a real observation.** The app set
  `X-CSRF-Token: <uuid>` from a literal inside a minified chunk — identical for every visitor and
  every rebuild. Grep the chunk; do not assume per-session. (Impact is usually low because
  `SameSite` cookies still stop cross-site sends — do not inflate it.)
- **API gateway vs app host.** The marketplace host was DataDome-walled, but
  `api.www.vinted.com` and `api.vinted.com` answered plain `curl` with
  `{"code":"NOT_FOUND","message":"Route not found."}` — no challenge at all. **These were
  unlisted subdomains, therefore out of scope, therefore not enumerated.** Record the discovery
  and the scope decision; do not "just take a look".
- **Trace where an XHR actually lands.** `www.vintedgo.com`'s in-scope tracking form issued
  `GET https://carrier.vintedgo.com/public/v3/tracking_events/<n>` — also unlisted, also not
  tested. An in-scope front end calling a host does not make that host in scope.

---

## 4. Audio-CAPTCHA solve (account creation behind DataDome)

Trigger: the registration POST answers
`403 {"url":"https://geo.captcha-delivery.com/captcha/?...&t=fe&..."}` from **every** transport,
including an app-originated route-rewritten POST.

The challenge page carries a full audio alternative. Selectors:

| Element | Selector |
|---|---|
| switch to audio | `#captcha__audio__button` |
| play | `.audio-captcha-play-button` |
| six digit boxes | `.audio-captcha-inputs` (`data-index` 0..5, `maxlength=1`) |
| submit | `.audio-captcha-submit-button` |
| WAV | `https://dd.prod.captcha-delivery.com/audio/<date>/<lang>/<hash>.wav` (regex it out of the HTML; the hash is also inline as `captchaAudioChallenge`) |

Sequence that works:

1. `page.goto(captcha_url)`; regex the `.wav` URL out of `page.content()`; download it.
2. Transcribe with a **pre-loaded** faster-whisper model. Audio reads
   `"Please type the numbers you hear."` then six digits. `base` is accurate; voting across
   base/small/tiny makes it robust.
3. Click the audio switch, play, then type **one digit per box** (`ins[i].click()` +
   `keyboard.type(ch, delay=55)`). `.fill()` alone does not always satisfy the widget — read the
   boxes back (`eval_on_selector_all(".audio-captcha-inputs","e=>e.map(x=>x.value)")`) to confirm.
4. Click submit. The ticket arrives on
   `GET geo.captcha-delivery.com/captcha/check?cid=...` as
   `{"cookie":"datadome=<value>; Max-Age=31536000; Domain=.vinted.com; Path=/; Secure..."}`.
5. **Graft it yourself** — the browser will not apply a cookie that arrives from a
   `captcha-delivery.com` origin for a `vinted.com` domain:
   `ctx.add_cookies([{"name":"datadome","value":v,"domain":".vinted.com","path":"/","secure":True}])`
6. Retry the registration request → **200**.

### Two failure modes that cost real time

- **Cold model load blows the challenge TTL.** Loading `WhisperModel()` after fetching the
  captcha left ~106 s between challenge creation and answer; the submission was rejected.
  Pre-load the model *before* the challenge exists. Budget ~2 min per attempt end-to-end.
- **`ctx.add_cookies` on the wrong domain silently no-ops.** Grafting only to
  `www.vinted.com` did nothing; the tag must be `.vinted.com`. Confirm with a cookie dump after.

### The account gets restricted anyway — plan for it

Registration returned `200` with a real user id, then the **very next navigation** served
`/main/banned`. The state is machine-readable:
`GET api.www.vinted.com/restrictions/api/v1/user-restrictions` →
`{"permitted_actions":[1,2],"restriction_type":2}`.

A solved-CAPTCHA registration from a datacentre/VPN egress is exactly the pattern the target's
own anti-fraud scores. Do **not** create a second account to route around it — report the block
and ask the program contact to unblock, which is what their own rules require. Either the
operator signs up from a residential IP and hands you the session, or the program unblocks.

---

## 5. What to write into the engagement log

Because almost every result here is a *negative*, the log is the deliverable:

- the transport matrix (proves the surface was reachable at all)
- every endpoint queried with its status and byte length
- which hosts were discovered but **not tested**, and the scope clause that excluded them
- the restriction check + raw response for the blocked account
- the coverage gaps (NXDOMAIN hosts, edge-RBAC-denied hosts) named explicitly
