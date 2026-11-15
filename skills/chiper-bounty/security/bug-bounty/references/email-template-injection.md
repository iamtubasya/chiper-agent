# Email / Notification Template Injection (HTML injection in transactional mail)

Class: user-controlled text is interpolated **unescaped** into an HTML email that the target's own
domain sends. Cheap to test on any product with invites, shares, team management, alerts or reminders,
and it is a *named focus area* on several payment programs ("email template injections" is the #1
submitted class on Rapyd's Bugcrowd brief). Payload delivery is what makes it more than self-XSS: the
attacker picks the recipient address, so the mail arrives from the vendor's DKIM-valid sender.

## Where the sink lives

Any flow where **your** input is later re-rendered by a mailer your target controls:

| Flow | Typical injected field | Mail lands at |
|---|---|---|
| Invite teammate / share object | invitee **display name** | the address you typed (third party) |
| Re-send invitation | same stored name, re-rendered | same |
| Role/permission change notice | member name in the notification body | the member |
| Reminder / alert / "assigned to you" | object or actor name | configured recipient |
| Support / ticket contact forms | name, subject, custom fields | support inbox |

## Test recipe

1. **Get the injection point into the record first.** Invite a mailbox you control
   (`you+tag@yourmail` — plus-addressing keeps it in one inbox) and put a payload in the display-name
   field. Payload ladder, cheapest first:
   ```
   X{{7*7}}<b>INJT</b> Y                     # plain tag: proves no escaping at all
   <a href=https://evil.example/v>Verify</a>  # unquoted attr survives name-splitting on spaces
   <img src=x onerror=...>                    # quotes survive better as one no-space token
   ```
   Spaces in the payload are usually fine in the *display* name (the server splits first/last for its
   own fields but the mail often renders the full name), so keep `href=` unquoted when you need
   spaces inside the anchor text.
2. **Read the raw message, not the rendered one.** Pull the mail over IMAP and grep the HTML part for
   your marker: `&lt;b&gt;` = escaped (safe), a literal `<b>` / `<a href=` = injected. Save the raw
   `.html` as evidence — the triager can see the unescaped interpolation in one glance.
3. **Find the sibling field that IS escaped — this is what turns a "wontfix" into an accepted bug.**
   In the Rapyd invite mail the *inviter* name was escaped (`&lt;b&gt;INJ2&lt;/b&gt; X has invited
   you…`) while the *invitee* name was not (`<strong>Hi <a href="…">Verify</a>,</strong>`) in the very
   same template. That proves escaping exists in the codebase and one interpolation was missed, which
   forecloses "that's by design / harmless text". Always capture both lines side by side.
4. **Prove it re-renders on demand.** Trigger the notification again (e.g.
   `POST /users/invitation {mpu_email}` re-sends the invite). If the same malicious anchor arrives
   again, the payload is stored and re-fireable — stronger than a one-shot send.
5. **Check the link is actually clickable end-to-end.** Mail providers/ESP click-tracking may rewrite
   `href`; if the rewritten URL still resolves to the attacker's host (Mandrill does this), the PoC is
   a working phishing link, not dead markup. Note the rewrite in the report so nobody dismisses it.
6. **Negative control in the app UI.** Open the member/user list: React (or any auto-escaping
   template) shows the payload as literal text — record that as "not stored XSS in the app", so the
   finding is scoped to the mail template only.

## Three checks that are always worth one request each

**1. Delivery authenticity — capture it, it feeds the severity argument.** Pull the raw headers over
IMAP (`Authentication-Results`, `DKIM-Signature`, `Return-Path`, `Received-SPF`) and paste them into the
report. Real example (Rapyd invite): `From: clientportal@rapyd.net`, `dkim=pass header.i=@rapyd.net`,
`spf=pass` via Mandrill. The sentence "the attacker's link arrives inside a DKIM-valid mail from the
target's own domain" is what lifts this from cosmetic to brand-phishing.

**2. Header/SMTP injection is a SEPARATE test — usually negative, and worth saying so.** Put a CRLF
payload in the same field (`QA\r\nX-Inj-Test: 1`) and inspect the raw headers for your injected header.
On Rapyd the invite form strips CR/LF (the value stored as `AA X-Inj-Test: 1`) and the name is only
interpolated into the *body*, so there is no Bcc/Subject injection. Reporting the negative result stops
a triager from assuming the worst and stops you from claiming SMTP header injection.

**3. Build an escaping MAP, not a single diff.** Walk every transactional template that renders the same
field — invite, resend, "password changed", "forgot password", "did you attempt to log in", reminders —
and record escaped vs raw for each. On Rapyd four templates escaped the stored name and only the invitee
interpolation did not; a table like that is the strongest possible root-cause evidence ("the escaping
helper exists and one call site missed it"). Also note which flows send **no** mail at all (role change
and member removal sent nothing) so you don't chase templates that don't exist.

## Scoping / severity honesty

- Real but bounded: no data compromise, no session theft, sender domain stays the target's
  (SPF/DKIM unchanged). It is a **brand-phishing / content-spoofing** primitive.
- Usable by any account that can trigger the flow (self-serve signup usually grants it), aimed at an
  address the attacker chooses → not self-XSS.
- Typical honest rating: Low/P4 standalone; ask for P3 when the program's own brief lists email
  template injection as a focus/top class AND the mail reaches a third party. Lead the body with a
  severity-request paragraph citing that focus area, and keep the "not P2/P3: no data compromise"
  sentence in — the downgrade-honesty is what keeps the triager on side.
- Root cause to state: missing output-encoding on one interpolation; fix = escape at render time
  (the value is stored and reused by other templates, so validating on input alone is insufficient).

## Case evidence (Rapyd, 2026-09)

- `POST /v1/merchants-portal/users/user {invitedUsersList:[{email,role,full_name}],recaptcha_token}`
  → invite mail from `clientportal@rapyd.net` contained
  `<strong>Hi <a href="https://mandrillapp.com/track/click/…evil.example…">Verify</a>,</strong>`.
- Escaped sibling line and re-send reproduction both captured; raw mail HTML kept as evidence.

## Round 2 (Quarterwise, 2026-10): REST-mailbox loop, throttled alerts, and a vendor that strips tags

### Read the mailbox over REST when the program hands you disposable inboxes
When your test accounts use a disposable-mail provider (mail.tm and friends) you do not need IMAP —
and this is often the *only* inbox you can read:

```python
tok  = S.post("https://api.mail.tm/token",
              json={"address": addr, "password": inbox_password}).json()["token"]   # inbox_password
H    = {"Authorization": f"Bearer {tok}"}                                            # lives in creds.json
msgs = S.get("https://api.mail.tm/messages", headers=H).json()["hydra:member"]        # newest first
full = S.get(f"https://api.mail.tm/messages/{msgs[0]['id']}", headers=H).json()
html, text = full.get("html") or "", full.get("text") or ""                           # check BOTH parts
```
Poll in a loop (10 × 15 s) rather than sleeping once — delivery lag varies per template.

### Trigger catalogue — what fires immediately, what is gated or throttled
| Trigger | Sink field | Reality on the target |
|---|---|---|
| Change password | profile name in the body | fires within seconds; the change also signs you out on other devices (disclose; restore the password and re-login) |
| "Security alert: data export downloaded" | account name | **throttled ~1/day** — API export and the UI "Export my data" link both produced NO new mail after the first send, even with a changed name |
| "Adviser/accountant invited" | **inviter's** name + email | reachable even when the UI dialog's submit will not fire under automation: replay the server-rendered invite form statically (bare field names, `$ACTION_*` from that form) |
| "Property … deleted from your account: <name>" | object (property) name, in the SUBJECT too | good vector when the account is not at its free-tier source cap |
| "X now has access to your books" | the acceptor's name + email | lands in the *owner's* inbox — proof that one user's profile fields reach another user's mail |

Lesson: pick the trigger by what is *not* gated. Profile-name-changing flows and password-change alerts
are immediate; export/security digests may be rate-limited per day; property-alert mails need a spare
property slot (a free account capped at 1 source cannot create the scratch object the UI needs, and a
firm-plan account may have no personal property grid at all) — and *deleting* that scratch property is
itself MFA-gated: a delete replay without `mfaCode` is refused with `Enter the current 6-digit code from
your authenticator app.`, so pass a fresh `pyotp.TOTP(secret).now()` in the same POST or the alert never
fires. Verify the deletion really happened by re-listing the objects; the confirm control can no-op
silently while the flow prints success.

### When the vendor strips tags — close the lead instead of inflating it
The profile-name field stored `Mr <b>INJMARK7</b> <a href="…">CLICK7</a> Fz` verbatim (re-read from
`/app/account` shows the tags), and the name *did* reach the mail body — but the delivered HTML rendered
`<strong>Mr INJMARK7 CLICK7 Fz</strong>`, i.e. **the tags were removed at mail-render time** while the
plain text survived. That is a mitigation, so the correct verdict is *informational / closed*, not a
finding. Two details that make the call defensible:
- Proving the strip (rather than escaping) matters: escaped output would show `&lt;b&gt;`; a *missing*
  tag proves sanitisation. Grep the delivered part for both forms.
- Keep the earlier raw-text evidence in the same write-up (e.g. an alert whose text part began with the
  stored `=HYPERLINK("http://evil.test/x","click")` name) so the triager sees you tested the sink and the
  guard, not that you skipped it.

### Third-party mail rule
Many self-hosted/VDP programs forbid mailing anyone but yourself. Satisfy the vector *without* a real
victim: hold a **second test mailbox of your own** (a second free tenant) and invite/notify that address.
The cross-user reach is still demonstrated — the mail lands in a different user's inbox than the sender's
— while every message stays inside your own accounts. Revoke the invite afterwards and verify it is gone
from the app's adviser/access list. Exact replay format for the server-rendered invite/remove forms
(bare field names, `$ACTION_ID_*` vs `$ACTION_REF_N`, why the `_1_` prefix 500s): see
`references/nextjs-action-replay-and-authz.md` §2 and the MFA note in §4.
