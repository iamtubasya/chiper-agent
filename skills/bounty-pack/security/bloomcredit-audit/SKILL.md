---
name: bloomcredit-audit
author: RESEARCHER_NAME
description: "Bloom Credit (bloomcredit.io) bug-bounty engagement — scope, API/auth surface map, core business, findings, and blockers. Load to resume or re-run this fintech credit-data target."
metadata:
  hermes:
    tags: [bug-bounty, security, fintech, credit-data, api, idor, auth, rag, llm]
    related_skills: [bot-protected-target-testing, security-recon, hunt-idor, hunt-llm-ai, hunt-ato]
version: 1.0.0
---

# Bloom Credit — bug bounty audit

Credit-reporting infrastructure (furnisher + data access). High-stakes target: anything here touches
consumer SSN / DOB / tradelines / credit scores, so IDOR and authz bugs are Critical-class.

## Scope (VDP)
- **IN**: "Any Bloom developed web service that handles sensitive user data" → Bloom APIs, Bloom web app.
- **OUT**: www.bloomcredit.io, developers.bloomcredit.io, clients.bloomcredit.io (portal), COTS not
  handling user data, third-party-hosted domains, SMTP.
- **Submit**: security@bloomcredit.io (PGP available), **1 finding = 1 email**, bundle all occurrences.
- **Reward**: up to $10,000 (discretionary).
- **Rejected (non-qualifying)**: CSV injection w/o vector, content spoofing, CSRF on non-sensitive
  forms, DoS, missing CSP/SSL/SPF best-practice, version/banner disclosure, scanner output w/o PoC,
  rate-limit on NON-auth endpoints. (Rate-limit/brute on AUTH endpoints is implicitly in-scope.)

## Core business / money flow
Bloom lets fintechs/lenders (B2B) pull credit reports and *furnish* (report) tradelines to the bureaus.
Products: Furnishment API (Metro2), Data Access API (pull reports/scores), Enablement Services
(GraphQL: rent/utility reporting + Plaid + open/close tradeline), Dispute Manager (dmx), My Credit
Score+ / Consumer Permissioned Data (CPDS). Model is **B2B2C** — consumers onboard via partners, NOT
self-service.

## Attack surface map
- **authn.bloomcredit.io** — Ory Kratos (email+password, registration DISABLED). Anti-enum hardened.
- **api.bloomcredit.io** — main API (Envoy/KrakenD), `POST /v2/otps/send|verify`, `/v2/dmx/*`,
  `/v2/organizations/{slug}`, `/v2/users/{id}/authenticate`, `/v2/users/{id}/credit-score/share-links`.
  B2B = OAuth2 `client_credentials` at `authn.bloomcredit.io/oauth2/token` (audience `api.bloomcredit.io`,
  scopes `data-access:all furnishment:all bloomplus:all`).
- **api.bloomplus.com** — CPDS (consumer). OTP login gated by `TurnstileBearer` (JWT issued after CF
  Turnstile).
- **dmx.bloomcredit.io** — Dispute Manager SPA (Ory login), calls `/v2/dmx/organizations/`.
- **satori.bloomcredit.io** — "Satori" = credit-reporting domain-expert **RAG chatbot** (FastAPI +
  LlamaIndex + Qdrant). Google OAuth @bloomcredit.io, JWT bearer validated via JWKS. Frontend at `/chat`.
- **sandbox**: sandbox.bloom.dev / api.bloomplus.dev / authn.bloomcredit.dev (also CF-protected;
  `client-portal`/`dmx`.bloom.dev behind Cloudflare Access Zero Trust).
- **Data model (from bloomTypescript/GitHub)**: consumers {ssn, dob, addresses, emails, phones},
  orders → `credit_data_order_by_pk(order_id)` GraphQL, tradelines/inquiries/scores/bankruptcies/
  OFAC/MLA statuses.

## Key endpoints (from open SDKs + docs)
- `/v2/core/consumers`, `/v2/core/organization`, `/v2/data-access/orders`, `/v2/data-access/graphql`
  (POST `FullOrderReport` query by order_id → **IDOR candidate**), `/v1/cpds/graphql`,
  `/v1/cpds/graphql/enroll|relay`, `/v2/users/submit-onboarding`, `/v2/otps/send|verify`,
  `/v2/users/{id}/credit-score/share-links`, `/v2/invite-tokens/processor-tokens` (BYOT PATCH).

## Findings so far (2026-11-02)
1. **LOW — Satori unauthenticated info disclosure**: `GET /api/health` →
   `{chat_enabled, ingest_running, eval_mode_available}`; `GET /api/feedback/config` →
   `{eval_mode_enabled}`; `/openapi.json` + `/api/openapi.json` leak internal arch (docstore + Qdrant,
   `engine.load_storage_context_for_turn`, AgentCore, modes REGULATORY/PROCEDURE/ANALYSIS/LOOKUP/
   REFUSAL/SELF_INFO). Likely rejected as "low value".
2. **UNPROVEN LEAD (potential High) — Satori `hd` enforcement**: frontend sets Google Sign-In
   `hosted_domain="bloomcredit.io"` (CLIENT-side only). Backend verifies JWT signature via JWKS
   (confirmed: alg:none→"token signing key not found", no-kid→"token missing kid header", garbage→
   "malformed token"). **NOT confirmed** whether backend rejects tokens missing the `hd` claim. If it
   doesn't, any Google account → internal RAG access → prompt-injection data exfil. Prove by signing in
   with a non-@bloomcredit.io Google account and POSTing /api/chat.

## Reusable technique (this engagement's unlock)
Cloudflare bot-mgmt makes curl return `000` and httpx GET-only. Bypass with Playwright
**`ctx.request`** (APIRequestContext) — real Chrome TLS + no CORS + readable POST bodies. Full recipe in
`bot-protected-target-testing` → `references/playwright-request-context-bypass.md`.

## Blockers / next steps
- No B2B client creds (needs onboarding contract) AND no self-service account (registration disabled →
  partner-provisioned). High-value IDOR/business-logic untested as a result.
- Next: (a) request sandbox creds via security@ ("contact us for sandbox creds" is in the docs — but
  don't fabricate identity), (b) prove Satori `hd` gap with a real Google test account, or (c) repick.