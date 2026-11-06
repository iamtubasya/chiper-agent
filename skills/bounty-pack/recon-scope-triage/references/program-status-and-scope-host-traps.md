# Program STATUS gate + scope-host traps

Worked cases from the 2026-10-23 target-triage session (CDN77 → suspended; SendSafely → active
but www-only scope). Companion to SKILL.md §"Program STATUS is a separate gate from program
EXISTENCE" and §"Scope-host-wording trap". Read BEFORE investing recon/scan budget in any new
target.

## 1. Suspended ≠ decommissioned ≠ active

A program page can look fully authorized while not accepting new work. Three live shapes:

- **CDN77 (SUSPENDED):** `www.cdn77.com/bug-bounty` served a full page **and**
  `BugBountyProgramTerms.pdf` (5 pages, updated 1 Jun 2026) with complete scope / rules /
  out-of-scope / reward tiers. BUT the page opened: *"Due to an increased volume of invalid
  reports, we are temporarily suspending our bug bounty program. All reports submitted prior to
  June 30, 2026 will be reviewed and compensated in accordance with the original agreement."*
  and every section (Scope / Out-of-scope / Taxonomy) was stamped **"(applicable to prior
  reports)"**. Safe harbor (§7) is conditioned on reporting *through the Bug Bounty Program* —
  which is suspended. Conclusion: **no authorization for new testing**; the detailed terms
  describe a closed window.
  - Lesson: read the TOP of the program page for a status banner before the scope. A rich scope
    doc is not a green light.
  - A live `security.txt` does NOT imply an active bounty — CDN77 had one (Contact:
    bugbounty@cdn77.com + marek.fiala@cdn77.com, Expires 2027-05) while suspended.

- **SendSafely (ACTIVE, narrow scope):** `www.sendsafely.com/security/bug-bounty` — active
  program, Bugcrowd VRT, first-to-find (must trigger a code/config change), rewards P1 $1500 /
  P2 $500 / P3 $200 (P4+ unlikely cash), partial safe harbor. Real program, but see §2.

## 2. The www-only scope trap (SendSafely)

Scope verbatim: *"All URLs hosted under www.sendsafely.com are included… Only pages and URLs
hosted under www.sendsafely.com are included. Systems within any other sub-domain of
sendsafely.com are out of scope, as are all 3rd party systems (Zendesk, Github, Stripe,
Hubspot, etc)."*

Reality map:
- `www.sendsafely.com` → 301 → `explore.sendsafely.com` (marketing/docs/content site, CloudFront)
- `app.sendsafely.com` → `/secure/home/` (the actual secure-file-transfer product; Apache, HSTS,
  X-Frame SAMEORIGIN, Service-Worker-Allowed) — **OOS**
- `api.sendsafely.com` → REST API (`access-control-allow-origin: *` on the 404 body) — **OOS**

Net: the entire product core (login, file transfer, workspaces, the split-key crypto,
trusted-device keys, Dropzone backend, REST API) is out of scope. Only the content site + the
Dropzone widget as embedded on content pages (e.g. the bug-report form) are testable. The juicy
business-logic targets all live behind OOS hosts:
- **Split-key crypto**: AES key = Server Secret (256-bit, server-held) + Client Secret (256-bit,
  never sent to server, carried in the URL `#fragment`). Server-Secret leak + fragment = full
  decryption of others' files.
- **Trusted Device Keys**: RSA-2048 per browser; private key in localStorage, public key uploaded
  to server; server hands your public key to senders so they can encrypt the Client Secret to you.
  Public-key substitution → intercept Client Secrets.
- Recipient identity-verification bypass, workspace/folder IDOR, webhook forgery, entitlement
  (trial→limited), Dropzone misconfig.

Scope-clarification triggers spotted:
- Program says *"create a test account (free Pro Trial; Last Name = SendSafelyBountyHunter)"* —
  but account creation happens on `app.sendsafely.com`, an OOS host. A rule that requires an OOS
  host to comply is a contradiction → ask.
- Program explicitly invites it: *"If you are unsure of exploitability, please contact us and one
  of our security engineers will work with you to verify it safely."*
- `www`→`explore` redirect means "www-only" literally covers almost no first-party content; the
  intent is probably the content site, but the literal wording excludes the product. Confirm
  before probing `explore.*`.

## 3. Finding the real policy pages when the nav is gated

`explore.sendsafely.com` returns **403 for every path** (including `/responsible-disclosure`,
`/security-policy`, `/bug-bounty`, and a random label) — so path-probing the marketing site for a
disclosure page is useless. The real policy URLs came from the aggregator
`bug-bounties.as93.net/sendsafely/` (which also gave safe-harbor = partial, bounty + recognition
flags):
- `www.sendsafely.com/security/bug-bounty`
- `www.sendsafely.com/security/bug-report`

Technique: when a vendor's own site 403-walls or hides its disclosure page, check a bounty
aggregator / disclose.io diodb for the canonical policy URL + safe-harbor status, then fetch that
URL directly. The marketing-site nav grep (in SKILL.md Step 0) fails here because the whole host
403-walls.

## 4. The 403 catch-all baseline

Before treating any 403 as meaningful, fetch a random nonsense path on the same host:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://explore.sendsafely.com/zzz-random-nonexistent-xyz/
# 403  →  403 is the catch-all; the /responsible-disclosure 403 is NOT "page exists but blocked"
```
Uniform 403 across real + junk paths = the host 403s unknown paths by default. Zero signal.
(Distinct from the soft-404 control, which is about HTTP 200 + identical byte-size.)

## 5. Submission-channel reality

SendSafely requires submission via its own **Security Bug Reporting Form** (end-to-end encrypted
through their platform; attachments encrypted client-side via the Dropzone widget), NOT email, and
PoC must NOT be posted publicly (no YouTube/Imgur). Rule: responsive within 7 days or the
submission is closed. When a program mandates its own encrypted submission channel, the
"draft a Gmail + PDF PoC" default must adapt — build the PoC PDF, but submit through the program's
mandated form. support@sendsafely.com is the fallback contact.

Excluded (no reward) so a future pass doesn't chase them: social engineering / physical; UI/UX /
typos; DoS/DDoS; stack traces / descriptive errors; HTTP 404 / non-200 pages; fingerprinting /
banner / robots.txt; CSRF on anonymous forms + login/logout; autocomplete / save-password; lack of
HttpOnly; login brute-force (unless CAPTCHA bypassed); OPTIONS method; missing
X-Content-Type-Options; SHA-1 cert / TLS 1.0.
