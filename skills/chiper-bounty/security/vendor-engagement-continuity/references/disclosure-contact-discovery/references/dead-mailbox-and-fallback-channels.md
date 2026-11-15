# Dead published mailbox → fallback channels (worked, Tacit 2026-10-27)

Session detail behind the SKILL.md section of the same name. The target published a security address on
its own domain that rejected every message; this is the full detection + fallback chain, re-runnable.

## 1. What "published and valid-looking" looked like

```
SECURITY.md            → Email security@tacit.finance. Include what you found, where it is, and the
                         steps to reproduce it. Please keep it private until it is fixed.
.well-known/security.txt → Contact: mailto:security@tacit.finance
                           Expires: 2027-09-30T00:00:00.000Z
                           Preferred-Languages: en
                           Policy: https://github.com/<org>/<repo>/blob/main/SECURITY.md
MX tacit.finance        → mx1.privateemail.com, mx2.privateemail.com
SPF                     → v=spf1 include:spf.privateemail.com ~all
```

Every signal a checklist would accept: own domain, valid MX, published in two places, a year of validity,
an explicit language preference. All of it was intent. The mailbox did not exist.

## 2. RCPT probe returned no verdict (and that is not a pass)

```python
import smtplib, dns.resolver
hosts = [str(r.exchange).rstrip(".") for r in dns.resolver.resolve("tacit.finance", "MX")]
for h in hosts[:2]:
    try:
        s = smtplib.SMTP(h, 25, timeout=20); s.ehlo("verify.local")
        s.mail("noreply@verify.local")
        print(h, s.rcpt("security@tacit.finance")); s.quit()
    except Exception as e:
        print(h, "EXC", type(e).__name__, str(e)[:80])
# mx1.privateemail.com EXC TimeoutError timed out
# mx2.privateemail.com EXC TimeoutError timed out
```

Two timeouts = **unknown**, not dead and not alive. Outbound 25 is blocked on most consumer/residential
lines, so this outcome is common and carries zero information. Record it as unverified; do not upgrade it
to "exists" because the address is published.

## 3. The bounce is the first real evidence — parse the enhanced status

Gmail DSN arrives with subject `Delivery Status Notification (Failure)` from
`mailer-daemon@googlemail.com`. Body is localized; the machine-readable reply is not:

```
** Pesan tidak terkirim **

Pesan Anda tidak dapat dikirim ke security@tacit.finance karena server jarak jauh
salah dikonfigurasi. …

Tanggapan dari server jarak jauh adalah:
554 5.7.1 <security@tacit.finance>: Relay access denied
```

Reader (IMAP, app-password; see the `bug-report-delivery` skill for the credential path):

```python
import re
from imap_tools import MailBox

with MailBox("imap.gmail.com").login(em, pw) as mb:
    mb.folder.set("INBOX")
    for m in mb.fetch(reverse=True, limit=25):
        subj = " ".join((m.subject or "").split())
        if "Delivery Status Notification" in subj or "mailer-daemon" in str(m.from_).lower():
            body = m.text or ""
            # [code] [enhanced] <addr>: text   — the only line that decides anything
            for code, enhanced, addr, text in re.findall(
                r"(\d{3}) (\d\.\d{1,3}) <([^>]+)>:?\s*([^\n]*)", body):
                print(code, enhanced, addr, text.strip())
            # 554 5.7.1 security@tacit.finance Relay access denied
```

`554 5.7.1 Relay access denied` on the domain's own MX = the server does not host that local mailbox, so
it refuses to relay inward. Distinguish it from reputation/policy (`550 5.7.1 … blocked`, `5.7.26`,
`421`, `4.7.x`) which are frequently transient and must not be reported as dead.

## 4. Confirm the platform gates are really off

```bash
for r in <org>/<repo> <maintainer>/<repo>; do
  curl -s -H 'accept: application/vnd.github+json' "https://api.github.com/repos/$r" | python -c "
import sys,json; d=json.load(sys.stdin)
print(d.get('full_name'),
      '| security_and_analysis:', d.get('security_and_analysis'),
      '| has_issues:', d.get('has_issues'),
      '| has_discussions:', d.get('has_discussions'),
      '| pushed_at:', d.get('pushed_at'))"
done
```

Observed: `security_and_analysis: None` and `has_issues: False` on the org repo; `has_issues: True` on the
maintainer mirror; PVR off on both. So the only private routes were dead-mailbox, or nothing.

`raw.githubusercontent.com/<org>/.github/main/SECURITY.md` returning 404 confirms there is no org-level
security policy overriding the repo one.

## 5. Fallback ladder, with the exact checks

```bash
# 1. commit authors — the strongest signal on a single-maintainer project
git log --format='%ae|%ce|%an' | sort | uniq -c | sort -rn | head
#   49 zrzr8963@gmail.com | zrzr8963@gmail.com | z0r0z     <- one real mailbox, signs every commit

# 2. org profile fields
curl -s https://api.github.com/orgs/<org> | python -c "
import sys,json; d=json.load(sys.stdin)
print(d.get('name'), '|', d.get('blog'), '|', d.get('email'), '|', d.get('twitter_username'))"

# 3. handles linked from the org blog (corroborate against the commit author name)
curl -s https://<org-blog>/ | grep -oE 'https://x\.com/[A-Za-z0-9_]+' | sort -u

# 4. Discord invite liveness
curl -s "https://discord.com/api/v10/invites/<code>?with_counts=true" | python -c "
import sys,json; d=json.load(sys.stdin)
print('guild:', (d.get('guild') or {}).get('name'),
      '| members:', d.get('approximate_member_count'),
      '| online:', d.get('approximate_presence_count'),
      '| expires:', d.get('expires_at'))"
# permanent invite => expires_at None; a dead code => HTTP 404
```

Also mine the repo for addresses other than the dead one — they are frequently present and frequently
better:

```bash
grep -rhoE "[A-Za-z0-9._%+-]+@$(echo <target-domain> | sed 's/\./\\./g')" . \
  | grep -v node_modules | sort -u
# security@tacit.finance   (dead)
# ross@tacit.finance       (whitepaper author — same domain, unproven)
```

## 6. What the deliverable has to say

Because the send went to a non-canonical address, three artefacts were changed together so none of them
told a different story:

- **email body, first paragraph** — the published address, the `554 5.7.1` quote, the MX host, "PVR not
  enabled on either repository", why this address was picked, and an explicit ask to be routed;
- **PDF metadata row** — `Sent to: <addr> (commit author); security@<domain> hard-bounces (554 5.7.1)`;
- **PDF scope section** — the same facts, plus the standing offer to resend through whatever channel they
  prefer.

Plus a short, separate process paragraph in the body: ask them to give the published address a working
mailbox or enable PVR, since a researcher following their own `SECURITY.md` currently cannot reach them.
That is a legitimate finding about the disclosure process, worth one paragraph and no more.

## 7. Reusable checklist

```
[ ] address found via security.txt / SECURITY.md / policy         (intent proven)
[ ] MX exists                                                     (can receive mail)
[ ] RCPT probe 250                                                (mailbox exists) -- if TIMEOUT, mark UNVERIFIED
[ ] GitHub security_and_analysis non-empty                        (PVR avenue)   -- else OFF
[ ] has_issues / has_discussions checked on EVERY repo
[ ] post-send: DSN parsed, enhanced status read, no bounce        (delivery proven)
[ ] if dead: commit author -> org email -> org-linked handle -> Discord -> paper author
[ ] non-canonical channel disclosed in body + PDF meta + PDF scope
```
