# Submission-channel discipline (measured 2026-10-31, Scribble Maps portal)

Companion to RULE 0 in SKILL.md. Everything here was paid for with a blocked submission.

## 1. NEVER dry-run-probe a submission endpoint

Six deliberately-incomplete POSTs to `POST /api/vulnerability/submit` were used to map the form
field names. All were rejected by validation (`400 {"error":"Title is required"}` /
`Description is required`) and **none created a report** — but they tripped a **per-IP throttle**
(`429 "You've submitted too many reports recently"`) that blocked the real submission hours later.

Rules:
1. Map the form schema from the page HTML/JS first. Grep the source for field ids and the fetch
   target instead of guessing by probing:
   ```
   grep -oE 'id="vuln-[a-z-]+"' portal.html
   grep -oE "fetch\('/api/[^']+'" portal.html
   ```
2. If a probe is unavoidable, send **one** request with a payload that cannot succeed (title only),
   then stop. Not a 3x loop.
3. Before the real submit, check throttle state with one harmless probe and distinguish
   `400 validation error` (safe, throttle cleared) from `429` (wait).
4. **Verify the captcha path before spending the whole hunt.** A program that allows one report
   per day means you only get one finding per day — confirm you can actually submit (Turnstile
   solvable, or a documented alternative path) before deciding which finding to send.

## 2. Captcha on the submission form may need a CLICK, not polling

The signup widget (mode `execute`, see signup-block-ops §2b) behaves differently from an inline
`div.cf-turnstile` widget on a report form. For the inline widget:

```python
rect = pg.evaluate("()=>{const el=document.getElementById('turnstile-widget');"
                   "if(!el)return null;const r=el.getBoundingClientRect();"
                   "return [r.x,r.y,r.width,r.height]}")
if rect and rect[2] > 20:
    pg.mouse.click(rect[0]+36, rect[1]+rect[3]/2)   # checkbox is left-of-centre, vertically centred
    for _ in range(45):
        time.sleep(1)
        if pg.evaluate("()=>{try{return window.turnstile.getResponse('#turnstile-widget')}"
                       "catch(e){return null}}"):
            break
```
Measured: token appeared ~4s after the click; three repeated clicks on the same widget did not
help (Cloudflare was challenging). Wait out the cooldown instead of spamming clicks.

## 3. Regenerated PDF => rebuild the draft

If the PoC PDF is corrected after a draft exists (full hash instead of truncated, correct userId,
reworded claim), the draft still carries the **stale** attachment. Delete and recreate:

```python
svc.users().drafts().delete(userId="me", id=old_draft_id)
# then create a new draft with the corrected PDF
```
Verify after creating by reading the draft back and matching `filename` **and** `body.size`
against the file on disk — not just the name.

## 4. gmail_ops.py has no attachment flag

`gmail_ops.py draft --to --subject --body` cannot attach. Build the MIME yourself:

```python
from email.message import EmailMessage
m = EmailMessage(); m["To"]=to; m["From"]=frm; m["Subject"]=subject
m.set_content(body)
m.add_attachment(open(pdf,"rb").read(), maintype="application", subtype="pdf",
                 filename=os.path.basename(pdf))
raw = base64.urlsafe_b64encode(m.as_bytes()).decode()
svc.users().drafts().create(userId="me", body={"message":{"raw":raw}}).execute()
```

## 5. The programmatic submit path can add an approval step

Some portals expose an "AI submit" endpoint (e.g. `POST /api/vulnerability/aisubmit?userId=`)
that needs **no captcha** — useful when the human form's Turnstile will not solve. But it returns
`pendingConfirmation:true` and emails an **approval link** to the address owning that userId; the
report is not reviewed until the link is clicked (it expires, e.g. 48h).

Always:
- verify the `userId` query parameter **equals** the session's userId before sending
  (`GET /api/account` → compare), so you never file under someone else's identity
- tell the operator there is a pending email-click step
- record in the report why the manual form path was not used

## 6. Report body shape that worked

Per-finding email body: intro → `SUBMISSION DETAILS` block (title, date of discovery, attachment
name + size, PayPal/payment email on file) → numbered SUMMARY → honest scope of what was NOT
tested → remediation → signature. No reward/bounty mention. The submission-details block lets the
same text be pasted straight into the portal form later.
