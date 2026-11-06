# Metrics-oracle route discovery — using an exposed telemetry endpoint as a coverage oracle

Origin: binobi.com engagement, 2026-10-28. A 1,934-path wordlist sweep returned **0 hits** on a live
NestJS payment API. The callback route that mattered — `POST /moneygrator/callback` — was found in
minutes by a completely different method. That method is the subject of this file.

---

## 1. The premise

An exposed Prometheus (`/metrics`) or health/telemetry endpoint often exports **per-route counters
with outcome labels**. Those counters are a side channel: if you can name a route, you can send one
request to it and read the counter delta. The target's own monitoring tells you whether you hit a
real handler, even when the response body is a generic 401/404.

This beats wordlist fuzzing when:
- the route name is a **provider/product name** you can derive from other telemetry (not a guessable
  dictionary word),
- the endpoint answers identically for "not routed" and "routed but unauthenticated",
- you need a **precise yes/no**, not a broad sweep.

## 2. Read the registry for structure, not just for the finding

```bash
curl -s https://api.<target>/metrics -o metrics.txt
grep '^# HELP' metrics.txt | sed 's/# HELP //' | awk '{print $1}' | grep -vE '^(process_|nodejs_)'
```

Then, in order:

| What to look for | Why it pays |
|---|---|
| `*_events_total{outcome="received" / "authenticated" / "invalid_signature"}` | names a callback handler **and** gives you a multi-state oracle |
| provider / tenant labels (`provider="moneygrator"`, `provider="avepay"`) | enumerates the integration list = your route candidates |
| rate-limit decisions with `rule="callback-burst"` | proves the route is registered in the gateway, and gives you its burst budget |
| auth operation counters (`operation="refresh",status="401"`) | tells you which auth verbs exist and how often they fail in the wild |
| `*_ws_decisions_total{rule="origin",outcome="denied"}` | reveals WebSocket guards and their names |

Measured yield on binobi: 15 payment providers, `moneygrator_callback_events_total` with 9 outcome
states, `auth_refresh_events_total{outcome="replay"}` (which is what later proved finding F2), and the
WebSocket protection rule names.

## 3. The oracle loop

```python
def metric(key):
    # fetch /metrics, return the float for an exact "key value" line
    ...

baseline = metric(K_RECEIVED)
status, body = probe("POST", "/candidate/path", data=b"{}")
after = metric(K_RECEIVED)
if after > baseline:            # the counter moved -> this IS the route
    print("HIT", status, body)
```

Rules that make it reliable:

1. **Prove the counter is quiet first.** Poll 3× ~6 s apart with no traffic. A counter that drifts on
   its own (background workers) is not usable as an oracle for that key. binobi's callback counters
   were perfectly still; a `*_ws_stats_updates_total` counter would not have been.
2. **One request, then read.** No batching — you need to attribute the delta to a single path.
3. **Any delta counts, whichever direction.** `received` +1 with `invalid_signature` +1 means "routed,
   rejected auth" — exactly what you want to learn. A 404 never moves these counters.
4. **Use the whole outcome tuple as the fingerprint.** `received` incrementing with no corresponding
   `authenticated` increment proves the auth guard is real and is rejecting you, which redirects your
   effort from "find more paths" to "attack the signature scheme".
5. **The counter name usually contains the product name** — that's your wordlist for the sibling
   routes. `moneygrator_callback` → try `/moneygrator/callback`, `/moneygrator/notify`,
   `/moneygrator/deposit`, and the *other providers named in the same metric family*.

## 4. From oracle to route inventory

Once one provider route is confirmed, the sibling enumeration is cheap and does not need the oracle:

```python
for prov in PROVIDERS_FROM_METRICS:      # 100hp, amatic, avepay, bestpay, dns-pay,
    for suf in ("callback","callbacks","notify","webhook","deposit","bet","win"):   # expay, fxmb,
        probe(f"/{prov}/{suf}")          # moneygrator, paysage, repay, settle, slotegrator…
```

On binobi this produced `/avepay/callback` (400 "Missing signature header"), `/fxmb/callback`
(400 with the full DTO), `/bestpay/callback` (410 "provider is disabled"), `/games/callback` (200
`{"error_code":"INTERNAL_ERROR","error_description":"Invalid sign"}`) — none of which the wordlist
sweep found, because the *path* is the provider name, not a dictionary word.

## 5. What the oracle does NOT tell you

- It does not prove auth is bypassable. On binobi every callback held: HMAC, magic-hash, type
  juggling, prototype pollution, non-hex, oversized values and JWT-bearing requests were all rejected.
  The oracle only proved the route exists — that is a **recon** result, not a finding.
- An exposed `/metrics` is itself usually **Low/Medium** (information disclosure) and often excluded
  by program rules as "banner/version disclosure". Report it on its own merits (it leaks the provider
  list and internal rule names) and *separately* record that it enabled the discovery — never
  inflate it to Critical by association.
- Do not confuse a metrics hit with a rate-limit finding. The registry advertising
  `X-RateLimit-Limit-callback-burst: 300` is a **control**, not a weakness.

## 6. Generalisations of the same idea

Any surface that reports "what the server did" works as an oracle. In priority order of how often
it's actually exposed:

1. `/metrics` (Prometheus), `/actuator/prometheus`, `/internal/metrics`.
2. Per-route request logs or `/health` detail blocks that name dependencies.
3. A **response-header oracle**: a rate-limit header only present on routed paths
   (`X-RateLimit-Limit-callback-burst` appeared on `/moneygrator/callback` and nowhere else).
4. A **timing oracle**: routed-but-rejected vs not-routed differs measurably (weaker, needs many
   samples — do not rely on one).
5. An **error-shape oracle**: the framework's 404 body (`{"message":"Cannot POST /x"}`) versus a
   guard's 401. Cheapest of all, and it is what makes `-fc 404 -fr "Cannot"` the right ffuf filter —
   but note the 400 matcher trap documented in `security-scanners`.

## 7. Side lessons from the same session

- **A removed front end does not mean a removed API.** `/vault` and `/transfer` both 404'd, yet their
  backing endpoint `POST /exchange` was fully live (and, per its DTO, trusts a client-supplied `fee`).
  When `gau` history shows a page that no longer exists, probe its **API** paths, not just the page.
- **`gau` output needs locale-stripping before it is useful.** 784 URLs, 0 of them API paths, because
  every hit was `/{lang}/{page}`. Strip the locale prefix, then de-dupe by path; the query-parameter
  union (`cid, clickid, msr, sub1, sub2, r`) is itself useful for affiliate-tracking IDORs.
