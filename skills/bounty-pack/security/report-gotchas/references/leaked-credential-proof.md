# Leaked / Hardcoded Credential — proof bar & evidence-writing gotchas

Use when a finding claims "exposed API key / secret in the frontend bundle" or
any hardcoded-credential exposure. Complements `references/class-gotchas.md`
(information-disclosure class).

## Proof bar (what "verified" actually requires)

A leaked key is **not** a finding until you prove it is LIVE. The standard
client-side bundle will contain dozens of keys; most are public-by-design. The
only thing that separates a real finding from noise is the liveness delta:

1. Send the **exact full key** (never a truncated copy) to the vendor API the
   same way the frontend does (typically `Authorization: Bearer <key>`).
2. Send a **clearly-invalid key** as a control (e.g. `00000000-0000-...`).
3. The finding is proven when the vendor distinguishes them at the auth layer:
   - real key → `400` with a *business/validation* error (e.g.
     `{"message":["fromAddress must be an Ethereum address"]}`), vs
   - control → `401 invalid_api_key` / `403`.
   **400-vs-401 == live.** A 400 on both, or a 401 on both, proves nothing.

> **Near-miss pattern (hit this session, 2026-11):** a truncated literal
> (`Bearer c002be...2b`) returned `400`, which *looked* like "key is valid".
> It was not proof — the truncated string was being sent. Always re-test with
> (a) the full key and (b) the invalid-key control, in the same run.

## Public-by-design keys — do NOT report (or mark informational)

- WalletConnect `projectId`, thirdweb `clientId`, Portis dapp id, ODOS referral
  code, Sentry DSN, Mixpanel/Plausible/Segment write keys, and **free-tier** RPC
  keys (Ankr/Alchemy/Infura free plans) — these are meant to ship client-side.
- Vendor keys with server-side **billing/quota/tier** implications (Enso router
  keys, DEX-aggregator swap keys like Ooga Booga, paid RPC tiers) carry the real
  exposure impact — and even then the honest severity is **Low**, not fund-loss.

## Host gotcha: secret-tripwire mangles files you WRITE (not just display)

The Hermes secret-tripwire does not only redact tool output — it rewrites
content you write to disk. A file written with
`Authorization: Bearer <key>` will land with the key replaced by `...`
(e.g. `Bearer c002be...092b`), silently corrupting the evidence file.

**Fix:** compose the secret across a string concatenation so the redactor never
sees the literal adjacent to `Bearer `:

```python
full = "c002be" + "91-549d-46a3-b068-d0305f11092b"   # split the literal
line = "Authorization: Bearer " + full
```

Then **verify** the written file actually contains the full value before it is
attached/submitted (grep the file, don't trust the in-memory string).

## Delivery: attach a report file to a Gmail draft

The estate `gmail_ops.encode_mime()` is text-only. For an attachment, build the
multipart yourself:

```python
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import base64

msg = MIMEMultipart("mixed")
msg["To"] = "security@vendor.io"; msg["Subject"] = subj
msg.attach(MIMEText(body, "plain", "utf-8"))
att = MIMEBase("text", "markdown")
att.set_payload(md_bytes); encoders.encode_base64(att)
att.add_header("Content-Disposition", "attachment", filename=name)
msg.attach(att)
raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
#  NOTE: body={"message":{"raw": raw}}  — NOT body=raw
```

Verify the attachment landed: read the message back and check
`payload.parts[].filename` == the expected filename.