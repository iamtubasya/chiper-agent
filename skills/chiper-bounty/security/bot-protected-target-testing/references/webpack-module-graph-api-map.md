# Chasing the webpack module graph to a complete API map

Worked case: `toshi.bet` front end (Next.js App Router, 59 bundles, 2.2 MB), 2026-10-18. A
generic endpoint grep over the bundles returned **9 paths**. Following the webpack module graph
returned **23 business-logic endpoints across 8 service hosts, plus a third-party game host
outside the target's own domain.** The difference is entirely method — this is the escalation of
§4 when a plain path grep comes back thin.

## Why the naive grep comes back thin

Minified webpack stores almost nothing as a full URL. The API map lives in three places a
`/api/...` regex never reaches:

1. A **config array** of request descriptors — `{URL:"/meToshi", SERVICE:E.B.USER,
   BASE_URL:i.C.USER, TYPE:l.Q.ME, METHOD:"GET", ...}` — where `URL` is a *relative* segment.
2. A **service→host switch statement** that turns `BASE_URL` into an absolute origin.
3. An **axios instance** whose `baseURL` is computed per-request from that switch.

## The chase, in order

**Step 1 — find the request layer.** Grep the biggest chunks for `baseURL`:

```bash
grep -l "baseURL" bundles/*.js
grep -oE '.{140}baseURL.{200}' bundles/<hit>.js      # bounded context; see the .{120} hang pitfall
```

The hit shows the shape immediately:

```js
let s = r?.SERVICE,
    b = "".concat(r?.SERVICE).concat(r?.URL),          // path = SERVICE + URL
    w = (0,i.$_)((r?.BASE_URL) || f.C.BASE);           // origin = resolve(BASE_URL)
...
N({baseURL: w, url: o, method: s, withCredentials: !1,
   headers: {Authorization: "Bearer ".concat(f),
             "x-request-id": ...getItem(FINGERPRINT_ID),
             "Request-From": "toshibet-frontend",
             "Idempotency-Key": (0,x.o4)(), ...}})
```

Four things fall out of that one snippet: the **auth model** (Bearer JWT from a Redux store or
localStorage, plus a fingerprint header), the **path construction** (`SERVICE` + `URL`), the
**origin resolver** (`$_`), and a **custom header** (`Request-From`) you will need to replay.

**Step 2 — follow the numeric module IDs.** Webpack module references are `r(<id>)`. The snippet
imports `i = r(38577)` and `f = r(77033)`. Jump to each:

```bash
grep -n "38577:" bundles/*.js        # -> re-exports $_ from module 85850
grep -n "85850:" bundles/*.js        # -> the switch statement
grep -n "77033:" bundles/*.js        # -> the service-name enum
```

Module 85850 is the payload:

```js
function o(e){switch(e){
  case l.C.BASE:      return i.env.NEXT_PUBLIC_API_URL;
  case l.C.USER:      return "https://user.toshi.bet/";
  case l.C.WALLET:    return "https://wallet.toshi.bet/";
  case l.C.GAMES:     return "https://slotegrator.toshi.bet/";
  case l.C.KENO: case l.C.MINES: return "https://games.toshi.bet/";
  case l.C.DOJO_DODGE:return "https://dojododge.toshi.bet";
  case l.C.DICE:      return "https://games.toshi.bet/";
  case l.C.BLACKJACK: return "https://blackjack.polearmesto.com/";   // <-- third party
  case l.C.SPORTS:    return "https://sports.toshi.bet/";
  ...
}}
```

**Step 3 — harvest the config array.** It is a plain array of object literals in one chunk, so a
single regex over the biggest files gets all of it:

```bash
grep -oE '\{URL:"[^"]*",SERVICE:[^,]*,BASE_URL:[^,]*,TYPE:[^,]*,METHOD:"[A-Z]+"' bundles/*.js
```

That yielded the full route table (`/meToshi`, `/username`, `/verify-2fa`, `/generate-2fa`,
`/wallet-create`, `/withdraw-request`, `/withdraw-request/cancel`, `/locked-balances/claim`,
`/raback/claim`, `/claim-referral-bonus`, `/change-code`, `/use/{1}`, `/farming/claim`,
`/tasks/claim`, `/trade-gold`, `/get-seeds`, `/solve/{1}`, `/new`, `/reveal`, `/cash-out`,
`/autobet`, `/pump`, `/hit`, `/stand`, `/split`, `/insurance`, …) with method and host attached.

## The `{1}` placeholder convention

`URL:"/{1}"` with `METHOD:"GET"` means the client substitutes a path argument at the call site.
Those are your **IDOR candidates** — find the call site (`render({1: someId})`) and you know both
the parameter position and the type. `GET_USER_INFO`, `GET_LIVE_WINS` and
`GET_ENDED_LEADERBOARD_DETAILS` all used it here.

## What to do with the map

- **Group by `BASE_URL`** — that is your host list, and each host is a separate auth boundary to
  test. Establish a control on one (`401 {"error":"No token provided"}` here), then probe the rest
  unauthenticated.
- **A third-party host in the switch is a scope question, not a target.**
  `blackjack.polearmesto.com` served a real-money game for this casino and appeared in no scope
  list. Note it, tell the operator, do not test it (§5).
- **`RE_FETCH:[...]` arrays leak the query-key graph** — which endpoints the client considers
  related, i.e. which state changes must stay consistent. That is where race conditions live.
- **`ENABLE_RATE_LIMIT` / `RATE_LIMIT` fields are the client's own throttle config** — a hint
  about which endpoints the developers considered abuse-prone (here: `PLAY_DICE` at 500 ms).
- **A GraphQL sibling** often hides in the same chunk:
  `new URLLink("".concat(r,"/graphql"), {headers:{Authorization:"Bearer ".concat(x), ...}})`. Probe
  `/graphql` on every host in the map, not just the apex.

## Pitfalls

- **The config array is split across many arrays** that are concatenated at the end
  (`D=[...s,...S,...n,...o,...R,...T,...d,...A,...r,...I,...c,..._,...u,...C,...m,...O,...L,...]`).
  Grep for the object-literal shape, not for the final array name, or you get one slice only.
- **Non-English comments are a gift, not noise.** This bundle's request layer threw
  `Error("Request Type yanışlıır girildi veya Client Config'de tanımlanmadı!")` — Turkish, from an
  outsourced team. Grep the error strings to find the config module when ID chasing stalls.
- **`i.env.NEXT_PUBLIC_*` values are inlined at build time** in some chunks and left symbolic in
  others. If `NEXT_PUBLIC_API_URL` resolves to nothing, the apex API host is the one value you
  must get from a live request or the HTML shell (§2b / §2c).
- **`grep -oE '.{N}NEEDLE.{N}'` for context hangs on multi-MB single-line bundles.** Use bounded
  context or Python windowed `str.find`.
