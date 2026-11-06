# Quota-bypass business-logic test + disclosure-artifact generation

Distilled from the djangoeurope v2 pass (2026-10-24). Two reusable techniques that sit *downstream*
of getting an authenticated session (see `captcha-gated-registration-and-session-lifecycle.md`):
(a) a business-logic test that found a Medium (plan resource-quota bypass), and (b) the concrete
recipe for turning a validated finding into a PDF PoC + evidence PNG + a Gmail draft.

---

## 1. Quota-bypass test — provision a resource and check whether the PLAN quota is enforced

Generalises to any hosting/SaaS control panel that lets a tenant create sub-resources with
client-supplied limits (system users, containers, DBs, buckets, workers...). The question is not
"can I create it" but "does the server validate my requested limits against what my plan pays for."

**Recipe (djangoeurope, `POST /systemuser/`):**
1. Read the tenant's quota from the group/plan object: `GET /systemgroup/` →
   `limit_ram=2.0, limit_data=50.0, limit_nproc=400, limit_users=5`.
2. Create a sub-resource with limits FAR above quota:
   `POST /systemuser/ {"name":"reportpoc","server":"<tenant-server>","group":"<tenant-group>",
   "limit_ram":64,"limit_data":500,"limit_nproc":2000}`.
3. Observe `201` and that the stored object keeps `limit_ram=64.0, limit_data=500.0,
   limit_nproc=2000` — accepted, NOT clamped to the plan. Confirm with a follow-up `GET
   /systemuser/{id}/` (stored, not capped).
4. Validate 3× (three clean 201s with the over-quota values persisted).

**Finding framing (so it survives triage):** a low-tier tenant can over-allocate up to the full
capacity of its physical server (here s24 = 64 GB RAM) × `limit_users`, i.e. gross unpaid resource
consumption / co-tenant exhaustion. Frame as "confirm whether the group `limit_*` are intended as
HARD quotas" so it can't be waved off as by-design — but the asymmetry (other operational endpoints
are auth-gated; the `server` field IS correctly pinned to the tenant) shows the `limit_*` fields are
specifically the unvalidated inputs.

**Near-miss to avoid:** don't read a 400 as "quota enforced." On djangoeurope the 400s during
threshold-hunting were mostly a **name-format rule** (`systemuser` names allow `a-z0-9` only — an
underscore → `400 "Invalid user name. a-z and 0-9 are allowed."`), not a limit check. Isolate the
variable (valid name, vary ONE limit field) before concluding a field is capped. Also note the
ceiling is the SERVER capacity, not the plan — so "64 accepted, 128 rejected" is a server cap, and
the real bug is that the plan quota (2 GB) is never consulted at all.

**Clean up:** `DELETE /systemuser/{id}/` every probe; keep only the original tenant system user.
Watch for default sub-resources (DB users named after the account) and don't delete those unless you
intend to.

---

## 2. Disclosure artifact: PDF PoC + evidence PNG + Gmail draft (reportlab / PIL / imaplib)

Per the operator's disclosure standard (1 finding = 1 draft = 1 PDF PoC; evidence txt+PNG with
sha256; draft IN-PLACE, never auto-send). Working implementation:

**Capture clean evidence first** (one authenticated script, because the token rotates per login —
see the sibling reference): GET the quota object, POST the over-quota resource, GET it back to
confirm stored, DELETE it. Write the request/response transcript to `DE-v2-02_evidence.txt`.

**Render an evidence PNG with PIL** (a dark "terminal" card — satisfies the screenshot requirement
without a browser):
```python
from PIL import Image, ImageDraw, ImageFont
font = ImageFont.truetype("consola.ttf", 16)           # fallback ImageFont.load_default()
img = Image.new("RGB", (W, H), (15,17,20)); d = ImageDraw.Draw(img)
for i, ln in enumerate(evidence_text.split("\n")):
    d.text((pad, pad+30+i*22), ln[:118], fill=(220,220,220), font=font)
img.save("DE-v2-02_evidence.png")
```

**Build the PDF with reportlab** (`SimpleDocTemplate` + `Paragraph`/`Table`/`Preformatted`): a
metadata table (Finding ID / Title / Severity / Target / Date / Researcher / Status), then
Summary → Impact → Steps-to-reproduce (`Preformatted` mono block with the exact HTTP calls) →
Evidence (embed the captured transcript) → Evidence-integrity (sha256 of txt+png) →
Recommendation. Keep it factual; no reward language.

**Create the Gmail DRAFT via imaplib APPEND** (do NOT SMTP-send; the user reviews then sends):
```python
import imaplib, time
from email.message import EmailMessage
from email.utils import formatdate
msg = EmailMessage()
msg["From"]="RESEARCHER_EMAIL"; msg["To"]="info@<target>"
msg["Subject"]="Responsible disclosure - <title> (<severity>)"
msg["Date"]=formatdate(localtime=True); msg.set_content(body)
for fn,mt,st in [("report.pdf","application","pdf"),("evidence.txt","text","plain"),("evidence.png","image","png")]:
    msg.add_attachment(open(fn,"rb").read(), maintype=mt, subtype=st, filename=fn)
M=imaplib.IMAP4_SSL("imap.gmail.com"); M.login(USER, APP_PW)
M.append("[Gmail]/Draf","(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
```
Body shape (operator standard): intro → finding → impact → reproduction → evidence sha256 →
recommendation → close, no reward mention, signed "RESEARCHER_NAME". Note the Gmail drafts folder on
this account is `[Gmail]/Draf` (Indonesian locale), not `[Gmail]/Drafts`.

**Verify** the APPEND returned `OK` + `[APPENDUID ...]` before telling the user the draft exists.

---

## 3. Operator by-design challenge → characterize → downgrade (2026-10-24 correction)

The quota test above produced a clean 3× "Medium quota bypass." The operator immediately challenged
it — *"kamu yakin ini bukan by design? kuota 5 user, bisa jadi plan dibagi antar 5 user, atau 1 user
dapat 5× kuota"* — and the challenge was correct. Reusable rule:

- **Re-characterize the enforcement.** Binary-search the field: `limit_ram` 2/63/64/65/100 all
  ACCEPTED with **no plan-derived ceiling at all**. So it is not "capped at 32×" — it is an
  **unvalidated free-form field**. Zero clamping reads as a user-set allocation hint, not an enforced
  quota boundary; a real quota control would reject or clamp.
- **The benign model is plausible.** Group `limit_*` = the plan TOTAL carved across `limit_users`
  sub-resources, or a per-user default — either makes a higher per-sub-resource value the intended
  mechanism. The platform clearly enforces what it means to (domain uniqueness, `server` pinning), so
  the `limit_*` fields may simply not be security controls.
- **Downgrade, don't defend.** Deleted the "Security Vulnerability Report / Medium" PDF and the
  vuln-framed draft; rebuilt as a neutral **Observation Note** (no severity, no "bypass" language)
  whose body is literally *"is this intended? … if it's by design, that's completely fine."* Let the
  vendor classify it. A clean question to a good-faith vendor (they rewarded a prior report) beats a
  bounced overclaim.

**Rule:** when a business-logic/quota "hit" rests on an intent assumption you cannot prove black-box
and the operator pushes back, characterize the enforcement precisely and be ready to downgrade to a
vendor question. Ship the question, not the claim.

## 4. Disclosure-artifact pitfalls hit this pass

- **reportlab PDFs with non-WinAnsi glyphs (em-dash `—`, smart quotes) can fail Gmail's attachment
  preview** even though the file is valid (pypdf opens it). If the user reports "the attachment
  errors," regenerate with **pure-ASCII text content** (`—`→`-`). The PDF binary is always non-ASCII;
  the fix is the *text* you feed `Paragraph`/`Preformatted`.
- **The user hand-edits staged drafts.** This one came back with a shortened subject and an added
  recipient (`security@wservices.ch` — the parent org, a better contact than `info@`). When you
  rebuild a draft to fix an attachment, **preserve the user's edits** (their To: list + Subject).
- **Swap a draft = delete-then-append.** `M.search(None,'(HEADER Subject "<quoted phrase>")')`
  (quote multi-word phrases or IMAP returns `BAD Could not parse command`) → `store(i,'+FLAGS',
  '\\Deleted')` → `expunge()` → APPEND the new one.
- **Attachments that "error" are usually intact.** Before regenerating, fetch the draft back
  (`fetch(id,'(RFC822)')`), walk the MIME parts, base64-decode each attachment and compare sha256 to
  the source. All three matched byte-for-byte here — the corruption was the PDF *preview*, not bytes.

## 5. Verified negatives from the same deep-dive pass (record so a future pass doesn't re-litigate)

SSH-key `/sshkey/` `user` field writable in serializer but **ignored** (owner forced to authed user)
— no BOLA. Ticket `/ticket/` `reporter` **read_only**. Domain `/domain/` creation has **no ownership
verification** but **global uniqueness IS enforced**; `/domainrecord/` `domain` requires a valid
existing UUID (can't hijack by name). `/message/` = audit log, no secrets captured. `/doc/`+`/faq/`
(258 KB unauth) = documentation only. `/backup/` (25) = metadata-only. Cross-tenant BOLA stayed
**untestable**: object IDs are non-enumerable UUIDs and fresh registration is IP-blocked ("Detected
as spam"), so a 2nd tenant couldn't be stood up from one IP.
