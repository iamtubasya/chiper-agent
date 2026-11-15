# Deutsche Telekom IoT — M2M Customer API: error-layer authz differential

Date: 2026-10-29
Host: `customer-rest-services.api-docs.iot.telekom.com`
Scope: in-scope — Deutsche Telekom public program covers `*.telekom.com`
Owner (from spec `info.contact`): Deutsche Telekom IoT GmbH, `iot_technology_operations-m2m-api@telekom.de`

## Why this reference exists

This is the clean worked example of §1b: an unauthenticated request that dies **inside the
persistence layer** proves the auth filter was never consulted, and the sibling write routes
answering `403` prove the filter exists elsewhere in the same app. The backend's datasource was
dead, so no data could be read — the finding is the missing check plus the layer proof, not
exfiltrated records.

## Surface map (free, from the public spec)

`GET /v3/api-docs` → 200, 498 KB, `M2M Customer API REST Service` v1.0.0, 46 paths.

Also served at `/api-docs` on some Spring hosts — probe `/v3/api-docs`, `/api-docs`,
`/swagger-ui/index.html`, `/swagger-ui/`, `/api/swagger/v1/swagger.json`.

Declared `components.securitySchemes` = **empty**, global `security` = **absent**. Per §7 that means
"no declaration", not "explicitly anonymous" — so live probing decides, and it did.

Endpoints of interest (all `/v1/partners/{partnerId}/…`, `partnerId` is a small integer):

```
GET  /v1/partners                                   list all partners
GET  /v1/partners/{partnerId}                       partner detail
GET  /v1/partners/{partnerId}/apiusage              usage/billing counters
GET  /v1/partners/{partnerId}/pools                 SIM pools
GET  /v1/partners/{partnerId}/sims                  SIM inventory
GET  /v1/partners/{partnerId}/sims/{iccid}          single SIM
POST /v1/partners/{partnerId}/sims/actions/activation
POST /v1/partners/{partnerId}/sims/actions/block
POST /v1/partners/{partnerId}/sims/actions/termination
POST /v1/partners/{partnerId}/sims/actions/suspension
POST /v1/partners/{partnerId}/sims/actions/limitoverride
POST /v1/partners/{partnerId}/sims/actions/simtransfer
POST /v1/partners/{partnerId}/sims/sim/sms          send SMS via a SIM
POST /v1/partners/{partnerId}/sims/sim/sessionhistory
```

## The differential (2 clean rounds, plus earlier observations)

```
GET  /v1                                  -> 500  HikariDatasource$HikariDataSourceHolder
GET  /v1/partners                         -> 500  HikariDatasource$HikariDataSourceHolder
GET  /v1/partners/1                       -> 500  HikariDatasource$HikariDataSourceHolder
GET  /v1/partners/1/sims                  -> 500  HikariDatasource$HikariDataSourceHolder
GET  /v1/partners/1/pools                 -> 500  HikariDatasource$HikariDataSourceHolder
GET  /v1/partners/1/apiusage              -> 500  HikariDatasource$HikariDataSourceHolder
GET  /v1/partners/1/sims/8949…            -> 500  HikariDatasource$HikariDataSourceHolder

POST /v1/partners/1/sims/actions/block    -> 403  Forbidden
POST /v1/partners/1/sims/actions/activation -> 403 Forbidden
POST /v1/partners/1/sims/sim/sms          -> 403  Forbidden
POST /v1/partners/1/sims/actions/termination -> 403 Forbidden
```

No `Authorization` header on any request. Timestamps differ per request, error shape is
byte-identical — so this is the app's real behaviour, not a cached artifact.

Reading it:

| observation | proof |
|---|---|
| GET reaches `HikariDatasource` construction | no authn/authz filter on the read path |
| POST returns `403 Forbidden` | an authz filter exists and runs on the write path |
| same host, same deploy | the gap is selective, not "the app has no security" |

## Evidence artifact

`D:\isplab\telekom\evidence\iot-api-authz-differential.json`

```json
{
 "host": "customer-rest-services.api-docs.iot.telekom.com",
 "in_scope": "*.telekom.com (public program)",
 "observations": "2/2 completed rounds identical; 3rd round failed at TLS layer",
 "differential": {
   "GET_read":  "500 reaches persistence layer (HikariDatasource init) -> no authentication/authorization filter in chain",
   "POST_write":"403 Forbidden -> authorization filter present for mutating actions"
 },
 "records": [ {"round":1,"label":"read-endpoint","method":"GET","path":"/v1/partners",
               "status":500,"len":202,"body":"…","authorization_sent":false}, … ]
}
```

## Reproduce

```bash
H='-H "User-Agent: Mozilla/5.0" -H "Accept: application/json"'
curl -s -o /dev/null -w '%{http_code}\n' $H https://customer-rest-services.api-docs.iot.telekom.com/v1/partners
curl -s -o /dev/null -w '%{http_code}\n' $H -X POST -H 'Content-Type: application/json' -d '{}' \
     https://customer-rest-services.api-docs.iot.telekom.com/v1/partners/1/sims/actions/block
```

Expect `500` then `403`. Both unauthenticated. If the read side starts returning `401`, the
datasource recovered AND a filter was added — re-test before reporting.

## Honest severity

**Medium today.** Missing check proven; data exposure NOT demonstrated (datasource down, zero
records retrieved — and Telekom's RoE explicitly forbids accessing data, so the PoC must never
retrieve a record even after recovery).

Escalation path, **conditional** and must be labelled as such: `partnerId` is a small integer with
no apparent caller-binding, so a recovered DB would give cross-partner BOLA over SIM
block/terminate/SMS — i.e. remote kill-switch on other operators' subscriber SIMs. Do not write that
as impact until it is demonstrated on a live datasource.

## Session-level pitfalls hit here

- `dnsx -retry 0` aborts with `[FTL] retries must be at least 1`. Minimum is 1.
- `dnsx -cname` without `-resp` prints hostnames only — no CNAME target. Use `-cname -resp` and parse
  `host [CNAME] [target]`.
- Mass-probing `/.env`, `/.git/config`, `/actuator/env`, `/v3/api-docs` across ~250 hosts returned 535
  "200 OK" rows of which ~534 were SPA shells or a WAF `Request Rejected` page. Triage by
  content-type + body diff against a random-path baseline BEFORE reading any of them; the single real
  hit (this host's 498 KB JSON spec) was only visible because of its `application/json` +
  size differential.
- A JS secret sweep flagged 14 `-----BEGIN OPENSSH PRIVATE KEY-----` hits on `coder.orbit.otc-service.com`
  / `git.orbit.otc-service.com`. All were i18n placeholder strings (`sshPrivateKeyPlaceholder`). Grep
  the surrounding 200 chars before believing a private-key hit.
