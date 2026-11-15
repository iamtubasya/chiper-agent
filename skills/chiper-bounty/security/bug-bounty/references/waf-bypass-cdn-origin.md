# WAF Bypass & Infra Pivot — Field Notes

Condensed technique bank from live sessions (Nykaa, Sep 2026). Class-level patterns, not target gossip.

## T1: Same-path probe on CDN/static sibling subdomains
When the main domain 403s (Akamai `errors.edgesuite.net` reference pages), re-issue the **identical path** against every static/CDN sibling before giving up on the endpoint:
- candidates: `images-static.*`, `cdn.*`, `asset.*`, `adn-static1/2/3.*`, `images.*`, plus typo/sibling TLDs (`images-static.naikaa.com` type lookalikes)
- Confirmed repro (3/3): `www.nykaa.com/ReactConfig.php` → 403, same path on `images-static.nykaa.com` → 200 JSON. Origin routing skips the WAF rule set for the static edge.
- Discipline: verify ≥3 runs. Severity follows **data impact**, not bypass novelty — a bypass returning static `form_key` + all-null customer object is LOW misconfig, never HIGH.

## T2: Error-message backend fingerprinting (free recon)
- POST with valid JSON Content-Type to gateway routes → `502 {"error":"could not JSON decode Lambda function response: statusCode must be a number"}` = **AWS Lambda behind API Gateway**.
- GET 404 `{"message":"no Route matched with those values"}` = Kong-style API Gateway, not a web server.
- `Server: awselb/2.0` on a 503 = ELB-fronted service, down but real.
- POST without Content-Length → 411 with `errors.edgesuite.net` = Akamai in path.
- Classify INFO unless the leak yields data or a working route.

## T3: Django DEBUG 404 page = urlconf + hostname mine
- Oversized 404 body (15–19 KB) with "Page not found at ..." = **DEBUG=True**. Dump contains full URLconf (every route name) and internal hostnames (e.g. `preprod-user-service.nyk00-int.network`).
- Also check `/docs/`, `/swagger/`, `/redoc/` — Swagger UI can be 200 while data endpoints are not.
- **Critical gate:** a leaked URLconf is a route *list*, not reachability. Preprod gateways prefix routes; leaked paths 404 externally → the chain is dead at the gateway. Dead chain = INFO. Writing HIGH off a leaked urlconf alone is severity inflation.
- Where the schema download "fails", the saved file may actually be a DEBUG 404 page (check first bytes for `<!DOCTYPE html>` + "Page not found") — that page is often more valuable than the schema would have been.

## Pitfall: "no findings" verdict issued without reloading target state
Before any final verdict, ALWAYS: (1) re-read `_progress/<target>/target-state.json` and the progress dir artifacts, (2) live-verify each high-value item found by prior recon, (3) only then classify confirmed/dead.
This session nearly shipped a "zero impact" verdict while a prior recon thread (`pp1-api.nykaa.com/docs/` → 200 Swagger) was still live and unexploited. The recon data existed on disk the whole time.

## Verdict template (use verbatim)
- CONFIRMED: endpoint + code + 3x repro + what data (if any) it exposes
- DEAD CHAIN: reachable-looking path blocked at gateway/WAF → INFO, explicitly not reported as high
- Record both in `_progress/<target>/target-state.json` under `findings` before reporting to user.
