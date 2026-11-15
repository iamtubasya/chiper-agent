# Worked example + evidence kit (email template injection)

Session-derived detail for the skill in `SKILL.md`. Target names are kept because they make the
recipe concrete; the reusable parts are the payloads, the table shape, and the header list.

## 1. Setup used

| Piece | Value / how |
|---|---|
| Attacker-side account | owner of a self-serve organisation (registration is enough) |
| Mailbox | one Gmail inbox; recipients created as `user+tag@gmail.com` (distinct tag per test) |
| Raw message access | IMAP (`imap.gmail.com`, app password) — read `m.html`, `m.headers`, `m.date_str` |
| Re-fire path | the product's "resend invitation" action / `POST /users/invitation {mpu_email}` |
| Low-priv test account | created *via the invite flow* rather than signup (skips SMS verification) |

## 2. Payloads that shipped successfully

```
<a href=https://evil.example/v>Verify</a>              # quote-free anchor (survives normalisation)
<b>MK</b>{{7*7}}<a href=https://evil.example/v>Verify</a>
<img src=https://evil.example/t.png>
```

Rendered result observed in the received email source (verbatim):

```html
<strong>Hi <a href="https://mandrillapp.com/track/click/31039703/evil.example?p=…"
  style="…color:#007C89;font-weight:normal;text-decoration:underline;">Verify</a>,</strong>
<strong>Hi <b>MK</b>{{7*7}}<a href=…>Verify</a>,</strong>
```

Note the ESP rewrites the href for click tracking but **keeps the attacker destination**.

## 3. The escaping map that pinned it

Same stored value, same account, several templates:

| Template | Field | Result |
|---|---|---|
| Invitation — **invitee** name | `Hi <name>,` | **RAW** ← vulnerability |
| Invitation — inviter name | `<name> has invited you…` | escaped (`&lt;b&gt;…`) |
| User Password Changed | `Dear <name>` | escaped |
| Forgot Password | `<name>` | escaped |
| "Did you attempt to login to your account?" | `<name>` | escaped |

Conclusion sentence that belongs in the report: *"The escaping helper exists and is used at four
other call sites — the invitation template's invitee interpolation simply misses it."*

## 4. Header fields to print for the delivery-authenticity claim

```
From:                             clientportal@<brand>
Return-Path:                      <bounce-md_…@mandrillapp.com>
Message-ID:                       <…@mail145-31.atl61.mandrillapp.com>
Received-SPF:                     pass (… designates <ip> as permitted sender)
Authentication-Results:           dkim=pass header.i=@mandrillapp.com …;
                                  dkim=pass header.i=@<brand> …;   ← the one that matters
DKIM-Signature:                   v=1; a=rsa-sha256; d=mandrillapp.com; s=mte1; h=From:Subject:To:…
```

`dkim=pass header.i=@<brand>` = the mail client shows it as a genuine brand email → phishing credibility.

## 5. Negatives (document these, they are part of the report's honesty)

- **CRLF/header injection — failed.** The invite form collapsed `"AA\r\nX-Inj-Test: 1"` to
  `AA X-Inj-Test: 1`; the stored value never reached a header, so no `Bcc:`/extra header appeared.
  Name is interpolated in the message body only.
- **Stored XSS in the portal — failed.** The same payload renders as literal text in the member list
  (framework escaping), so the flaw is mail-template specific.
- **Role-change / member-removal notifications — do not exist.** Changing a member's role and
  deleting a member produced no email at all → the affected surface is the invitation family only.
- **API-side payload with CRLF — could not be proven.** The send endpoint is captcha-gated; the
  widget token is obtained by the app internally (`grecaptcha.getResponse()` / hidden textarea read
  empty), and the app's own request body was not reachable from the page's fetch/XHR hooks. Left
  explicitly untested rather than claimed.

## 6. Report skeleton (paste-ready)

```
Title:      HTML / hyperlink injection in the <product> <invitation> email (<field> rendered unescaped)
Root cause: escaping map table (see §3) — one missed interpolation, siblings escaped
Delivery:   raw headers showing dkim=pass header.i=@<brand> + spf=pass (see §4)
Repro:      numbered steps, payload, expected vs observed email source
Repeatable: resend endpoint re-renders the stored payload
Negatives:  §5 — what was tested and did not work
Severity:   P4 baseline; P3 request argued on (focus class + DKIM-authenticated delivery +
            third-party recipient + real styled link). No data-compromise claims.
Remediation: escape at render time in the invitation template (reuse the existing helper) and
             validate the name server-side.
```

## 7. Helper snippets

Decode an ESP click-tracking link (Mandrill `p=` wrapper) — see `scripts/extract_mail_links.py`:

```python
p = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)["p"][0]
inner = json.loads(json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)).decode())["p"])["url"]
```

IMAP fetch with retry (sockets drop under load):

```python
for i in range(4):
    try:
        mb = MailBox("imap.gmail.com").login(user, app_pw); mb.folder.set("INBOX"); break
    except Exception:
        time.sleep(3 + 3 * i)
```
