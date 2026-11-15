# Estate-scan triage & re-verification (nuclei over a whole-domain estate)

Case (2026-10-12, Vana): `nuclei -l recon/nuclei_targets2.txt -tags exposure,misconfig,config,default-login,ssl,tech
-severity info..critical` over **42 hosts / 3,546 templates / 282,282 requests / 6h16m** → **651 matches**.
Published split: **624 info · 7 low · 0 medium/high/critical**. The deliverable is the TRIAGE, not the count —
a 651-match line with no split is noise, and a "no findings" line from it is a coverage claim you cannot defend.

## 1. Split by severity, then by `template-id`, and say what the info mass was
```
429x http-missing-security-headers (all 42 hosts)   90x tls-version   42x ssl-issuer   42x ssl-dns-names
+ ~30 misc (tech-detect, waf-detect, keycloak-openid-config, jwk-json-leak, openapi, swagger-api, readme-md)
```
Naming the dominant info templates is what makes "624 info" a measurement instead of a dismissal.

## 2. Re-verify every non-info hit BY HAND before it becomes a row
Findings rot between scan time and triage time, and a scanner line is never the evidence.
- `expired-ssl` on `data-gateway.vana.org` (expiry 2026-09-19) → at triage the host answered Vercel
  `404 DEPLOYMENT_NOT_FOUND`: the deployment had been **removed** (it was the host from an already-sent
  finding). Verdict: appears remediated on that host; **not** a new finding. Never re-report a host from a
  stale scanner line — re-request it first.
- `weak-cipher-suites` (TLS 1.0/1.1 + `ECDHE_RSA_WITH_AES_128_CBC_SHA`) on `oauth.`, `server.`, `storage.`
  → reproducible by hand → a real low, reportable.
- The same host can also be a **second instance of an already-sent finding**: `session-relay.vana.org/README.md`
  returned `200 / 3,718 B / text/markdown` — same class as the report already sent for the data gateway.
  Correct move is a one-line **addendum to the existing finding**, not a new report (and say the other host
  now looks fixed).

## 3. Address the calibration rule that stops an over-claim
Before writing up an unauthenticated "disclosure" endpoint, ask: **is the response derivable or public anyway?**
Worked example — `GET /api/v1/identity?address=<x>` returned `200` with
`{user_address, personal_server.address, public_key}` for arbitrary addresses (incl. `0x0`), and a bounded
burst (10 random addresses) showed **no 429, no `Retry-After`, median 0.40 s**.
Two measurements then decided severity:
- on-chain `ownerServers(<that wallet>)` → **count 0** (the registry has nothing for it);
- `eth_getCode(<the returned personal-server address>)` → **0 bytes, nonce 0** (no live infrastructure).
⇒ the endpoint returns a **derived** record, not someone's live deployment; public keys are public by design.
Verdict: **informational → DROP** (record it in the coverage notes). The only honest reportable sliver would be
"no rate limit on an identity-resolution oracle" — hardening, low, and only if the ids are low-entropy/enumerable.
Generalise: *public key ≠ secret, mapping ≠ leak, derivation ≠ disclosure — measure the state, then decide.*

## 4. Cheap probes that keep you out of the write path
Use a deliberately INVALID body to separate auth from validation, without creating anything:
- `422 {detail:[{loc:["body","app_signature"],msg:"Field required"}]}` → validation ran; an auth gate was never
  reached. `422 string_too_short … min_length:132` on a bogus signature also reveals the expected shape.
- `401/403` → an auth gate exists.
- Also useful: a **published OpenAPI spec with zero `securitySchemes`** is a hint, not proof — read the real
  per-request schema (`signature`, `app_signature`) and probe. Never fire a valid write (operation creation,
  upload, SMS-OTP trigger) just to prove that auth is absent; "reachable, not exercised" is the honest claim.

## 5. Ledger row shape for scanner work
`tool | scope (N hosts / N templates / N requests) | numbers by severity | verdict per non-info hit | artifact path`
Keep the raw JSONL + a triage directory; each verdict must name the file that supports it.
