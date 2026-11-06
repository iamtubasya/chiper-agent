---
name: email-template-injection
description: "Hunt HTML/link injection in transactional email (invitation, password reset, security alert, notification, receipt) where user-controlled fields — display names, org names, subjects — are interpolated into the email template unescaped. Covers template enumeration, the escaping map that pins the root cause, DKIM/SPF delivery proof for the phishing-impact argument, and the header-injection test you must run to avoid overclaiming. Use when a target sends templated mail containing user-supplied data and you can receive that mail at an address you control."
metadata:
  hermes:
    budget_kb: 20
    tags: [email, html-injection, phishing, template-injection, bug-bounty, evidence]
---

# Email / Transactional Template Injection

Server-rendered HTML in a **branded transactional email** is a different animal from web HTML
injection: the escape happens in the mail template, the "response" arrives in a mailbox, the
victim can be a third party who never visited the site, and the delivery path (DKIM/SPF) is part of
the impact story. This skill is the pipeline for that channel.

Sibling skill: `hunt-html-injection` covers raw HTML injection in web responses; use that for the
in-app rendering surfaces, this for the mail channel. Reporting format: `bugcrowd-reporting` /
`report-writing`. Related lead-capture habit: only escalate what you can prove (see Pitfalls).

## When to use
- The app lets you set a display name / org name / subject-like string that later appears in email.
- The product sends invitations, password resets, "password changed", "new login" alerts, receipts,
  or member-management notifications.
- You have (or can create) a mailbox you control — the flow usually needs multiple invitations.

## Workflow

### 1. Get mail in
- Plus-addressing gives unlimited distinct recipients into one inbox: `you+tag@gmail.com`. Use a
  distinct tag per test (each member/invite gets its own tag) so you can attribute later emails.
- Corporate aliases that forward (`@BC_ALIAS.com` → your Gmail, via a `forward-bot` relay) work
  too but arrive with a wrapped Subject (`[Relayed on behalf of …]`) — match on recipient, not subject.
- Do NOT mass-generate accounts. One owner + one low-privilege member is normally enough to prove the
  whole class.

### 2. Enumerate every template (not just the obvious one)
Trigger each flow that renders user-controlled data and record **which templates exist**: invitation
(and its *resend*), password reset, "password changed", login/security alert, welcome/onboarding,
role change, member removal, receipts. A template that silently sends nothing is a **scoping result**
— write it down, it bounds the finding honestly.

### 3. Marker payload
Use one payload that is unambiguous in both raw and escaped form and survives field normalisation
(no quotes, no newlines — many UIs collapse them):

```
<b>MK</b>{{7*7}}<a href=https://evil.example/v>Verify</a>
```

`<b>MK</b>` → raw vs `&lt;b&gt;MK&lt;/b&gt;`; `{{7*7}}` catches template engines that evaluate;
the quote-free anchor is the practical phishing primitive.

### 4. Build the escaping map (this pins the root cause)
Fetch the raw message (IMAP) for every template and classify **each** rendering of the stored value:

| Template | Field | Raw or escaped |
|---|---|---|
| invitation — invitee name | `Hi <name>,` | … |
| invitation — inviter name | `<name> has invited you…` | … |
| password changed | `Dear <name>` | … |
| password reset / login alert | `<name>` | … |

A table where one field is RAW and siblings are escaped is the strongest possible root-cause evidence:
it shows an escaping helper already exists and one call site simply missed it. Triagers cannot answer
that with "maybe they never escape". Fill this table before writing the report.

### 5. Delivery authenticity (the impact argument)
From the raw headers, print and quote: `From`, `Return-Path`, `Message-ID`, `Received-SPF`,
`Authentication-Results`, `DKIM-Signature` (`d=`, `header.i=`). The phishing claim stands on
`dkim=pass header.i=@<brand>` + `spf=pass`. Without that, the finding is "HTML in an email" and
nothing more.

### 6. Repeatability
Show the payload is **stored** and re-rendered: use the product's resend/re-fire action (or its API,
e.g. a resend-invitation endpoint) and confirm the same anchor arrives again. Stored + re-fireable =
repeatable at scale, which is what lifts it above a one-shot injection.

### 7. Capability ladder (don't lead with the script tag)
`raw text` → `raw tags` → `working <a href>` → `remote <img>` tracking pixel → `layout/CSS overlay`.
Email clients strip `<script>` and usually `<form>`, so the reportable primitive is the **clickable
link inside the brand's own template**, not payload JavaScript. State which rung you actually proved.

## Negatives you MUST test (and then document)
1. **Header/SMTP injection.** Put CRLF in the value (`AA\r\nX-Inj-Test: 1`, `\r\nBcc: you@example.com`)
   and inspect the received raw headers. Most web forms collapse CRLF (→ harmless literal text);
   the API may not — test both and say which path you proved. Never claim header injection from a
   body-only reflection.
2. **Stored XSS in the web UI.** The same stored value usually appears in a member/user list. If the
   app escapes it there, say so explicitly — it narrows the bug to the mail template and *increases*
   credibility.
3. **Who can trigger it.** Check the role/permission model (owner/admin vs viewer/editor). If the
   write endpoint is permission-gated, verify rather than assume; if the UI hides it, the API may
   still allow it (or vice versa).

## Severity framing
- Baseline for a real, repeatable unescaped interpolation: **P4 (Low)**.
- Argument for **P3**: (a) the program lists email-template injection as a submitted/focus class;
  (b) delivery is DKIM-authenticated for the brand domain; (c) the recipient is a third party chosen
  by the attacker; (d) the payload renders as a real styled link. Cite the program brief by name.
- Never claim: data compromise, session theft, arbitrary `From` domain, or that CRLF worked when it did not.

## Pitfalls
1. **Invite/activation tokens ≠ reset tokens, but test the overlap.** Check single-use and reuse on
   the same endpoint, and cross-flow confusion (invite token presented to the reset endpoint and vice
   versa). Cheap tests, occasionally a real bug.
2. **Password-reset side effect — do not reset the account you are working in.** A reset *request*
   can immediately invalidate the current password (logins start returning a generic
   `…ERROR_LOGIN` / "incorrect") while **live sessions keep working**. If you must rename a confirmed
   account to test the reset template, have the reset link ready first, complete it, then revert the
   name — otherwise you lock yourself out until the mail arrives.
3. **Reset/invite mail is throttled.** A second request may send nothing *and* invalidate the
   previous link (so the older link reports expired). Poll the mailbox with retries (IMAP drops with
   `socket error: EOF` under load — retry with backoff) before concluding anything.
4. **Captcha-gated send endpoints.** Gated invites/resets need a token per request. With a real
   browser you usually get **one usable widget token per page load**, and the app may solve the widget
   internally so reading `grecaptcha.getResponse()` or the hidden textarea returns empty. Capture the
   app's own request (CDP `Network.enable` + `Network.requestWillBeSent`) rather than hand-building
   the token, and re-load the page before each attempt.
5. **ESP click-tracking rewrites hrefs** (Mandrill/others wrap the URL in base64). Decode before
   quoting — see `scripts/extract_mail_links.py`.
6. **"In the raw source" ≠ "renders in every client".** Say what the raw bytes prove (unescaped
   interpolation, live anchor) and label client-rendering as untested unless you checked it.

## References
- `references/method-and-evidence.md` — worked example end-to-end (escaping map, payloads, header
  fields, negatives, report skeleton).
- `scripts/extract_mail_links.py` — decode Mandrill/ESP tracking links and list all links from a
  saved email HTML/EML.
