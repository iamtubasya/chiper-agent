---
name: disclosure-contact-discovery
version: 1.0.0
author: Hermes Curator
license: MIT
description: "Use when finding/verifying a disclosure contact email."
metadata:
  hermes:
    tags: [osint, disclosure, bug-bounty, contact-discovery, recon, email]
---

# Disclosure Contact Discovery & Verification

Find the correct contact for a vulnerability disclosure — **and prove the mailbox is real and
belongs to the target** before sending. An address that looks right but is dead (or belongs to a
different company) silently voids the report, and worse lets you *claim* you disclosed when you
did not.

Everything here is public-source. No email is ever sent during discovery.

## When to use

- "find the security email / contact for <target>"
- "where do I submit this bug for <target>"
- a target has a repo/`SECURITY.md` but no obvious security mailbox
- before sending any disclosure email (verify, don't guess)

## Core order of preference (most official first)

1. **Registered program** — HackerOne / Bugcrowd / Immunefi / HackenProof. Check even if you
   found the bug outside it. Expect gates (see §5).
2. **Dedicated security channel** on the target's own site — `/.well-known/security.txt`
   (RFC 9116), `/security`, `SECURITY.md`, imprint/legal page.
3. **Verified general mailbox** — `info@` / `abuse@` from their legal docs. **Prove it answers**
   (§1) and that the domain is really the target (§2).
4. **Maintainer / owner direct** — commit authors, package maintainers, verified social.
5. **Coordinator** — CERT/CC, national CERT, disclose.io.

## `security.txt` is the SCOPE document too — read it before you test anything

`/.well-known/security.txt` is not only a mailbox lookup; it is the fastest path to the program's
**Policy** URL, and that URL is the authoritative scope list. Fetch it first, every engagement, before a
single probe: `curl -s https://<apex>/.well-known/security.txt`.

**The host the operator names is frequently out of scope — and often it is the host that serves the
policy.** Verified on Aghanim (2026-10-27): the operator said `support.aghanim.com`; that host is
**Helpjuice SaaS**, and the policy itself lives on it (`Contact: https://support.aghanim.com/bounty-program`)
while §4.3.1 excludes third-party services. Auditing it would have been three wasted hours on someone
else's product. The real scope was 19 API hosts (`api`, `dashboard-api`, `pay-api`, `s2s-api`, `upload`,
`*.aghanim.app`, …). State this in the first paragraph of the deliverable.

**Fingerprint the helpdesk/doc host before treating it as the target:**

| tell | product | verdict |
|---|---|---|
| `Server: Heroku` + `Via: heroku-router` + `Nel: {"report_to":"heroku-nel"…}` + cookie `_helpjuice_session_v4` | Helpjuice | third-party KB → OOS |
| `x-zd-*` headers, `*.zendesk.com` | Zendesk | third-party → OOS |
| `intercom` script/`intercom-session-*` cookie | Intercom | third-party → OOS |
| Docusaurus shell (`__docusaurus`, `/assets/css/styles.<hash>.css`) | docs site | usually in scope as `<apex>` but **check the policy** |
| `X-Powered-By: Next.js` + `dpl_…` asset suffix | Vercel-hosted app | likely first-party |

Rules:

1. **A `Contact:` that is a URL to the policy page on a third-party domain means "policy host ≠ scope."**
   Do not confuse the two; the scope table is inside that page, the host is not in it.
2. **A third-party docs site can still be a first-class recon source, not a target.** Docusaurus/KB sites
   frequently expose the product's **full OpenAPI spec at the docs root** — `https://docs.<apex>/openapi.json`
   returned a 1.1 MB, 97-path spec on Aghanim (and `sitemap.xml` on the same site lists every API guide).
   Harvest the spec and the integration guides, then hunt the in-scope hosts.
3. **Read the policy's exclusion list before choosing a surface** — §4.2.14 (identifier guessing),
   §4.2.5 (client-side PSP keys), §4.4.6 ("login by Player ID" is by-design) each pre-kill a whole
   finding class. A policy read takes 5 minutes and changes which classes you spend the day on.
4. If the named host is OOS and the real scope is a 19-host estate, say so early and ask the operator
   whether to proceed on the declared estate — do not silently substitute targets.

## The four verifications (proven — DeXe Protocol case, 2026-10-11)

### 1. Probe the mailbox with SMTP `RCPT TO` (never sends)

`RCPT TO` only asks "does this mailbox exist?". Cheap, rerunnable.

```python
import smtplib, socket
socket.setdefaulttimeout(8)
host = "aspmx.l.google.com"        # from: nslookup -type=MX <domain>
for c in ["security", "abuse", "info", "support", "contact", "admin",
          "psirt", "disclosure", "report", "vulnerability", "research"]:
    try:
        s = smtplib.SMTP(host, 25, timeout=8); s.ehlo("m.t")
        s.mail("test@example.com")
        code, msg = s.rcpt(f"{c}@<domain>")
        print(f"[{code}] {c}@<domain>", msg.decode(errors="replace")[:50]); s.quit()
    except Exception as e:
        print(f"[ERR] {c}@<domain>", type(e).__name__, str(e)[:40])
```

- **`250 … OK`** → exists. Use it.
- **`550 5.1.1 … does not exist`** → dead. Do not send.
- **`[ERR] TimeoutError`** → refused/rate-limited. **Do not conclude dead** — try another MX host
  or fall back to a form/policy page.

Pitfalls:
- Keep to ~6 names per call, socket timeout 6-8 s — one hanging MX blows the `terminal` 180 s timeout.
- **STARTTLS may be mandatory before any VRFY/RCPT** (observed 2026-10: `530 5.7.0 Must issue a
  STARTTLS command first` on both). Call `s.starttls()` + `s.ehlo()` again before probing; with a
  self-signed cert use an unverified context (`check_hostname=False, verify_mode=CERT_NONE`) and
  connect by the MX hostname, not IP (certificate IP mismatch otherwise).
- **The sender domain must resolve** or RCPT answers `450 4.1.8 Sender address rejected: Domain
  not found` for EVERY recipient — that is a sender rejection, not a dead mailbox. Use a real
  resolvable sender (`you@gmail.com`) before drawing conclusions.
- **VRFY is a parallel vector** when RCPT is uninformative: `252` = exists, `550 User unknown` =
  dead. Same STARTTLS/sender rules apply. Note that a mail server answering VRFY/RCPT
  differentially is itself a low-severity finding (mailbox enumeration) — log it separately.
- Expect a partial control: some servers close the connection after ~30 probes (enumeration still
  succeeds within that budget — record how many you got before the drop).
- **There is often no `security@` at all.** On DeXe, `security@`/`psirt@`/`disclosure@`/`report@`/
  `vulnerability@`/`research@`/`support@`/`contact@`/`legal@` were ALL **550**; only `info@`,
  `abuse@`, `admin@` answered 250. Never assume the canonical `security@` exists.

### 2. The near-miss domain trap (HARD pitfall)

A similar-looking domain is **not** the target. A researcher reported a DeXe Protocol vuln to
**`info@dexe.com`** and told the team he'd emailed them. `dexe.com` is a **Chinese shampoo
manufacturer** (MX `mxbiz2.qq.com`, Tencent QQ — not Google Workspace). The report vanished.

- **Who is behind the domain:** `curl -sL https://<domain> | grep -io "<title>[^<]*"`.
  `dexe.com` → shampoo; `dexe.network` → DeXe Protocol.
- **Match the MX/provider.** A real crypto target is usually Google Workspace
  (`aspmx.l.google.com`) or comparable; odd MX (Tencent/QQ, parker) = wrong domain.
- Mirrors that get confused: `dexe.network` vs `dexe.io` vs `dexe.com` vs `deex.exchange`
  (old DeeX exchange — a **different** entity, now dead). **`deex` ≠ `dexe`.**

### 3. The authoritative address often lives only in a legal PDF

The site may expose zero addresses (no `mailto:`, `/contact` → 404). The official, legally
binding contact is in the legal documents:

- `https://documents.<domain>/Privacy_Policy.pdf`, `Terms_of_Use.pdf`, imprint pages.
  DeXe's Privacy Policy named the entity + responsible email verbatim:
  *"DeXe Protocol Association … Baarerstrasse 141, 6300, Zug … Email: `info@dexe.network`"*,
  corroborated byte-for-byte by the Terms of Use PDF.
- Extract emails from a compressed-text PDF (regex gate + `zlib.decompress` on stream objects).
  **Write the script to a file** — a heredoc with inline `\(`, `\)`, `[` trips
  `re.PatternError: unterminated character set` under this shell/host combo.
- **Check the entity's legal status** on a company register (Swiss: `moneyhouse.ch`, `help.ch`,
  `local.ch`; otherwise country of incorporation). DeXe Protocol Association was listed
  **"in Liquidation"** (2024-2025) while the protocol kept running — so legal email is not the
  only route.

### 4. Mine the target's GitHub issues for channels + gates

A project with a `SECURITY.md` but a silent team often has a pile of *"Security: Responsible
Disclosure Request"* issues with **no reply**. Read them:

```bash
curl -s -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<org>/<repo>/issues/<n>"
curl -s -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/<org>/<repo>/issues/<n>/comments"
```

Yields other researchers' emails + PoCs + channels tried (including near-miss domains), and the
**platform gate** they hit. If requests pile up unanswered → you need several parallel channels.

### 5. Expect submission gates on the paid platforms

From the DeXe case: **Immunefi required a Whitehat Level**, **HackenProof required 120
reputation points + KYC + a $5 submission fee**. This is *why* researchers fall back to email /
GitHub. Plan for the gate; if you can't clear it, say so and use the verified email instead of
claiming a platform submission you didn't make.

## A published, policy-endorsed address can still be a black hole (proven 2026-10-27, Tacit)

§1–§5 get you to an address. This section is the trap that survives all of them: the address is on the
target's own domain, has valid MX, is printed in **both** `SECURITY.md` and `/.well-known/security.txt`
— and the mailbox was never provisioned.

Tacit published `security@tacit.finance` in `SECURITY.md` and in `.well-known/security.txt`
(`Contact: mailto:security@tacit.finance`, a year-long `Expires`, `Preferred-Languages: en`). MX =
`mx1/mx2.privateemail.com` (Namecheap Private Email). The SMTP RCPT probe **timed out on both hosts**
(port 25 blocked from this box — a timeout, not a verdict), so the report went out on the strength of
the policy text alone. The bounce:

```
554 5.7.1 <security@tacit.finance>: Relay access denied
```

Read bounce codes precisely; they are not interchangeable:

| code | meaning | action |
|---|---|---|
| `554 5.7.1 … Relay access denied` | **mailbox not provisioned on that MX** | dead — find another channel |
| `550 5.1.1 … user unknown` / `does not exist` | mailbox missing | dead |
| `550 5.7.1 … blocked`, `5.7.26`, `421`, `4.7.x` | policy / reputation / greylist | retry or change provider — **not** evidence of death |
| `530 5.7.0 Must issue a STARTTLS` | your probe is wrong | fix the probe, draw no conclusion |

**So: `security.txt` + `SECURITY.md` + valid MX proves INTENT, not a working mailbox.** When the RCPT
probe cannot return a verdict, say delivery is unverified and treat the post-send bounce as the first
real evidence. Do not tell the operator "sent" before a non-bounce has been observed.

### Parse the DSN, do not eyeball the notification
Gmail renders the human text in the account locale (`** Pesan tidak terkirim **`), but the
machine-readable reply is in the body as `[code] [enhanced status] <address>: text`. Regex that line out
of `message.text`; the translated sentence alone will mislead you. A worked reader lives in
`references/dead-mailbox-and-fallback-channels.md`.

### GitHub Private Vulnerability Reporting — an actual API check
`security_and_analysis` is authoritative and costs one request:

```bash
curl -s -H 'accept: application/vnd.github+json' https://api.github.com/repos/<org>/<repo>
# "security_and_analysis": null or {}   => PVR NOT enabled
# populated with advanced_security/secret_scanning statuses => it is on
```

Read `has_issues` and `has_discussions` in the same call: `has_issues: false` removes the (bad) public
route, `has_discussions: false` removes a semi-private one. Check **every** repo for the project — the
mirror under the maintainer's personal account can differ from the org repo (Tacit: `z0r0z/tacit` issues
on, `src-company/tacit` issues off; PVR off on both).

### Fallback ladder when the official channel is dead
Descending reliability, all public-source and verifiable:

1. **Commit author/committer email** — `git log --format='%ae|%ce' | sort | uniq -c | sort -rn`. On a
   single-maintainer project this is a real working mailbox whose owner signed the code, and it is the
   strongest signal available. Tacit: 50/50 commits to one Gmail address.
2. **GitHub org profile** — `api.github.com/orgs/<org>` → `email`, `blog`, `twitter_username`.
3. **The maintainer handle the org links to** — fetch the org `blog` and lift the social handles out of
   it; corroborate against the commit author name. This is what licenses messaging a handle directly.
4. **Discord invite via the API** — `discord.com/api/v10/invites/<code>?with_counts=true` returns guild
   name, `approximate_member_count`, `approximate_presence_count`, `expires_at`. A live guild, permanent
   invite (`expires_at: null`) and non-zero presence is a real channel; a dead code 404s. Use it to *ask
   for the private channel*, never to disclose.
5. **Paper author email** — `\author{… \href{mailto:…}}` in a whitepaper `.tex`. Weaker than 1–3: same
   domain, may be just as dead as `security@`.

### When you must use a non-canonical channel, say so inside the report
Do not silently send to the commit author and leave the reader guessing. First paragraph of the body:
name the published address, quote the bounce code and the MX host, state that PVR is off, state why this
address was chosen, and ask to be routed. Mirror it in the PDF metadata (`Sent to`) and in the scope
section so the artifact and the email cannot tell different stories. It is also a fair, small process
note to the vendor: the channel their own policy prints rejects every message.

## Deliver the channel as a FORM, not just an address (proven — ATG/YesWeHack, 2026-10-16)

Finding the address is half the job. The other half is **which shape the deliverable must take**:
a platform web form, or an email with attachments. Building the wrong one wastes the whole
preparation and can sit unnoticed until the operator is ready to submit.

`/.well-known/security.txt` answers this directly — read the `Contact:` lines as a *routing table*,
in order:

```
# Bug Bounty
Contact: https://yeswehack.com/programs/<program>/create-report   <- platform FORM (primary)
Contact: mailto:vuln@atg.se                                       <- email (secondary only)
Policy:  https://yeswehack.com/programs/<program>
```

- **A `Contact:` that is a URL to a report/submit endpoint means the platform form is the primary
  channel.** The deliverable is then: a title (respect the field length — keep under ~120 chars) plus
  a markdown body the operator pastes in. The PDF PoC is attached *through that form*, not emailed.
- **`mailto:` present alongside it is a secondary/fallback channel**, not the one to build for.
- Only when `mailto:` is the sole contact (or the policy says email-only) do you build `.eml` drafts.

Two artifacts per finding in the platform case, and say which is which in your hand-off:
1. `<Program>-<Finding>-<short>.pdf` — the PoC exhibit the form's attachment field takes.
2. `ywh_report_<finding>.md` (or equivalent platform body) — pasted into the description field.

**Do not stage an email draft "just in case" and leave it in the deliverable folder.** A wrong-shape
draft next to the right one is how the operator ships the wrong file. Move it to `superseded/` with a
one-line reason the moment you learn the real channel.

**Check the platform's own house format too.** YesWeHack programs commonly expose a public
hacktivity/report list; when `hacktivity: false` (all 506 reports hidden — ATG), there is no public
known-issue corpus to dedup against, so the first-to-report rule is the only dedup that applies. Note
that in the hand-off rather than claiming you checked.

Verify with `curl`/`urllib` on `https://<host>/.well-known/security.txt` (also try `/security.txt`
and the apex domain — ATG served the identical file on all three). It costs one request and settles
the whole deliverable shape.

## Automated ladder for bulk discovery (proven 2026-10-25, early-project pipeline)

When you are resolving contacts for **many** domains at once (a discovery pipeline), run this
fixed ladder and record which tier produced the address. Cheap tiers first; every tier is a
plain HTTP GET, so the whole ladder for one domain is ~10 requests.

| tier | source | how |
|---|---|---|
| 1 | `/.well-known/security.txt`, `/security.txt` | take the `Contact:` line only; accept `mailto:` and bare addresses |
| 2 | `/security`, `/contact`, `/about`, `/responsible-disclosure`, `/bug-bounty` | regex `mailto:` + plain addresses out of the body |
| 3 | GitHub `SECURITY.md` | `raw.githubusercontent.com/<org>/<org>/main/SECURITY.md`, `…/<org>/.github/main/SECURITY.md`, then `api.github.com/orgs/<org>` |
| 4 | RDAP | `https://rdap.org/domain/<d>`; if it does not return JSON, fall back to `https://rdap.verisign.com/<tld>/v1/domain/<d>`. Registrant email is **often redacted** — empty is normal, not an error |
| 5 | role pattern `security@` / `contact@` | **ONLY** if tier-independent MX validation passes (below). Weakest tier; mark it `guessed: true` |

### MX-gate the guessed tier, always

A domain with no MX record cannot receive mail, so a synthesised `security@` there is guaranteed
bounce. Gate it:

```bash
dig +short example.com MX      # empty output => no mail; do NOT use the guessed tier
```

`dig` may not exist on a stock Windows box; `winget install ISC.Bind` provides it (alongside
`whois` via `winget install Microsoft.Sysinternals.Whois`). Resolve the binary under
`~/.local/share/…` if the PATH alias has not taken effect yet.

### HARD pitfall: a platform account is not the project's website

Discovery pipelines resolve "the website" from a project's social bio/links. If the blocklist is
incomplete, a **platform** gets recorded as the target domain — and then the guessed tier happily
emits that platform's security mailbox. Measured 2026-10-25: a project whose only link was Twitch
resolved to `twitch.tv` and produced `security@twitch.tv`. Sending there discloses to the wrong
company.

Two independent guards, keep both:

1. **Blocklist platform/social/hosting domains** when extracting a website: socials (`x.com`,
   `t.co`, `discord.gg`, `t.me`, `linktr.ee`), video/live (`twitch.tv`, `kick.com`, `youtube.com`),
   stores (`steampowered.com`, `opensea.io`, `gumroad.com`), web3 launches (`pump.fun`,
   `dexscreener.com`, `galxe.com`, `zealy.io`), PaaS (`vercel.app`, `netlify.app`, `herokuapp.com`,
   `replit.app`, `onrender.com`, `fly.dev`, `railway.app`), and docs/CDN hosts.
2. **Require the email's domain to equal the target domain** (or be a sub/parent of it). Apply this
   to the guessed tier too — the blocklist alone is not enough because the list is never complete.

Also drop junk mailboxes that appear verbatim in page templates: `@example.com`, `@domain.com`,
`@sentry.io`, `@wixpress.com`, `@squarespace.com`, `@shopify.com`, `@schema.org`, and
`your@`/`name@`/`user@` placeholders.

### Report the tier, not just the address

A future reviewer must be able to tell a `security.txt` address (authoritative) from a guessed
`security@` (fabricated by pattern). Print `email + source + whether MX validated + guessed:true`.
Never present a guessed address as verified.

## Reporting the result

State **which mailbox you verified (250) and which returned 550**, and that the domain was
confirmed to belong to the target. A later reviewer must be able to see the contact was proven,
not guessed. Also state **the channel form** (platform form vs email) and where that was read from.

## Related skills

The end-to-end disclosure workflow (triage → PoC → report → coordination), email templates, and
PGP/Gmail-draft mechanics live in the user-owned `bug-bounty-disclosure` skill — read it for the
write-up side. This skill owns the **contact discovery + verification** step specifically.
