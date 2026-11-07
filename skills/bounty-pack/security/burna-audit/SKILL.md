---
name: burna-audit
description: Use when hunting Burna AI (burna.ai) clinical SaaS bounty.
version: 1.0.0
author: RESEARCHER_NAME
license: MIT
metadata:
  hermes:
    tags: [bug-bounty, burna-ai, mastra, better-auth, convex, clinical, ai]
---

# Burna AI — Engagement Notes

## Scope (from responsible-disclosure policy, retrieved 2026-11-04)
Domains: burna.ai, app.burna.ai, ctcae.ai, protocolstudio.ai, app.protocolstudio.ai,
api.burna.ai, agent.burna.ai, carejournal.ai (own policy), + mobile apps (CTCAE by Burna, Healthnotes).
Report to: security@burna.ai. Hall of Fame credit (current: "Server-owned fields accepted on visit
updates" 2026-10-26, "Rate limiting on sign-in code emails" 2026-10-21).
**Most-wanted**: guess/forge the enrollment link a site sends a participant; reach patient/participant
records from OUTSIDE their organization/study.
OOS: automated scanner findings WITHOUT working PoC; social eng; DoS; physical; best-practice-only.

## Infrastructure (recon 2026-11-04)
- Next.js apps behind **Cloudflare** (burna.ai, ctcae.ai, protocolstudio.ai, + app.*).
- Backend: **Convex** (convex-main*.burna.ai DNS) + **Mastra** (AI agents) at **agent.burna.ai**
  (Railway `4w2tg178.up.railway.app`). api.burna.ai → `1v323wsc.up.railway.app` (root `/` 404 but
  `/health` 200 `{"ok":true,"service":"api_burna","issuer":"https://api.burna.ai"}`).
- Auth: **Better-auth** session cookie `__Secure-better-auth.session_token` (HttpOnly/Secure/
  SameSite=Lax, domain .burna.ai, 30d) + short-lived JWT (EdDSA, exp ~5min) sent as Bearer to Mastra.

## Auth flow (verified working)
1. `POST /api/auth/email-otp/send-verification-otp` `{"email","type":"sign-in"}` → `{"success":true}`
   (rate-limited: 429 `CODE_SEND_LIMITED`). Signup = firstName/lastName/work email/terms, NO password.
2. OTP (8-digit) → `POST /api/auth/sign-in/email-otp` `{"email","otp":"<8digits>"}` (field is **`otp`**)
   → `200 {"token","user"}` + `Set-Cookie`.
3. `GET /api/auth/get-session` → session (cookie-gated, not bearer).
4. Tenant scoped INSIDE signed JWT: `activeOrganizationId`, `activeOrganizationName` ("<email>'s
   Workspace"), `activeMemberRole:"owner"`, `sub` (userId), `aud:"control-plane"`, `impersonatedBy:null`.
   Org id = ULID `01a...`.

## API map (authenticated)
### api.burna.ai (control plane, better-auth cookie)
- `/api/auth/get-session`
- `/api/auth/organization/list-members?organizationId=<ulid>` → 200 `{members:[{role,user}]}` —
  authz VERIFIED: foreign orgId → 403 `YOU_ARE_NOT_A_MEMBER_OF_THIS_ORGANIZATION`.
- `/api/auth/organization/list-invitations?organizationId=<ulid>`
- RBAC (bundle `0oplqzfblywtb.js`): patient:[view_phi,enroll,withdraw], protocol:[enroll_patients],
  adverseEvent:[grade,report_sae,sign], billing, task.

### agent.burna.ai (Mastra, JWT Bearer)
- `/api/trials`, `/api/trial-pro/notifications`, `/api/trial-pro/submissions`
- `/api/patients/search?limit=25`, `/api/visits?limit=100`, `/api/ehr/connections`
- `/api/prompts` (may expose system prompts), `/api/blind-grading-raters/me`, `/api/demo-allowances`
- Without JWT → 401 `{"success":false,"message":"AUTH_REQUIRED"}`.

### Other
- `/api/api-key/create|delete|delete-all-expired-api-keys`, `/auth/invite/{token}` (most-wanted),
  `/auth/permission-patterns`, `/auth/set-password`

## Secrets
- PostHog `phc_fktpMzdQUZLGrIGitB7WqlmwbGGJambuWvaXWoBzRuc` (public).
- Stripe `pk_test_51Q...` in bundle `032fmyyxoxc4a.js` (test key, Low/info).

## Test accounts (self-provisioned)
- mail.tm inbox `burnadqbx2b2yn7@fldubai.com` (creds `~/.chiper/skills/bounty-pack/burna_acct/mailtm.json`).
- Account A: owner "burnadqbx2b2yn7's Workspace" orgId `01a1a587-5bc1-79d6-aa7a-edaa4d3b3a6a`,
  userId `01a1a587-5bb8-7d78-9f77-fbc1c7af1bc9`, session token `1BY9hWqqSNJA8l0XCXVTgim1Jukf9o1F`.
- Browser profile `~/.chiper/skills/bounty-pack/browser-profiles/burna`.

## OPEN LEADS (unproven)
1. `impersonatedBy:null` → admin impersonation endpoint? (ATO/critical)
2. `/api/prompts` → system prompt leak when authed?
3. Mass-assignment on visit/patient update (HOF precedent).
4. `/api/api-key/*` authz scoping across orgs.
5. `/auth/invite/{token}` forgery/guess (most-wanted).

## Toolchain artifacts (D:/data hermes/campaign-burna)
subs/all_subs.txt(42), urls/live_httpx.txt(17), urls/katana_urls.txt, urls/gau_all.txt(1109),
chunks/*.js(193), chunks/grep_hits.txt, policy.txt.