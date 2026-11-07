---
name: gmail-draft-pdf-delivery
description: "Draft Gmail bug-bounty: body + attach PDF langsung via API."
metadata:
  hermes:
    tags: [bug-bounty, reporting, delivery, gmail]
---

# Gmail Draft + PDF PoC Delivery (standar)

## Trigger
Mau kirim temuan bug-bounty via email (vendor). Buat draft Gmail (body + PDF PoC)
LANGSUNG ke Gmail — JANGAN simpan `.txt` draft lokal dulu (lambat, ganda).

## Rules WAJIB
1. **1 finding = 1 draft + 1 PDF.** Jangan gabung dua temuan dalam satu draft/PDF.
2. **Langsung create/update ke Gmail via API.** Tidak ada file `.txt` draft lokal.
3. **MIME WAJIB set `m["To"]` + `m["Subject"]`.** Kalau lupa, `drafts.update`/`create`
   menghasilkan draft yang header-nya KOSONG (subject + tujuan hilang). `From` diisi
   otomatis oleh Gmail.
4. PDF attach via `MIMEBase("application","pdf")` + `encoders.encode_base64`.

## Steps

1. Generate PDF PoC (reportlab — pola `gen_pdf.py`, lihat skill `reportlab-security-pdf`).
2. Build MIME (contoh):

```python
import base64, html
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

m = MIMEMultipart("mixed")
m["To"] = "security@unito.io"                  # WAJIB
m["Subject"] = "<judul deskriptif>"            # WAJIB
alt = MIMEMultipart("alternative")
alt.attach(MIMEText(body, "plain", "utf-8"))
alt.attach(MIMEText(html.escape(body).replace("\n", "<br/>"), "html", "utf-8"))
m.attach(alt)

att = MIMEBase("application", "pdf")
att.set_payload(open(pdf_path, "rb").read())
encoders.encode_base64(att)
att.add_header("Content-Disposition", "attachment", filename="<nama>.pdf")
m.attach(att)

raw = base64.urlsafe_b64encode(m.as_bytes()).decode("ascii")
```

3. Upload lewat `gmail_ops`:

```python
import sys
sys.path.insert(0, r"~/.chiper/scripts")
from gmail_ops import pick_service
label, svc = pick_service("RESEARCHER_USERNAME")   # akun utama

# baru:
res = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
# atau attach ke draft existing (update):
res = svc.users().drafts().update(userId="me", id=draftId, body={"message": {"raw": raw}}).execute()
```

4. **VERIFY (wajib, jangan skip):**

```python
d = svc.users().drafts().get(userId="me", id=draftId, format="full").execute()
msg = d.get("message", {})
hdr = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
assert hdr.get("to") and hdr.get("subject")   # pasti ada
# cek attachment ada di msg["payload"]["parts"] dengan "filename"
```

## Pitfalls (kesalahan nyata)
- **Lupa `m["To"]`/`m["Subject"]`** → draft jadi tanpa recipient + tanpa subject (Gmail
  menampilkan body doang). Ini yang terjadi saat `drafts.update` dengan raw yang tak berheader.
- **Subject di file `.txt`** baris pertamanya `Subject: ...` → strip dulu jadi `m["Subject"]`,
  jangan ikut masuk body.
- **Body html** wajib `html.escape` dulu sebelum disisipkan.
- **`encode_mime` bawaan gmail_ops.py TIDAK dukung attachment** — selalu bangun MIME manual
  (mixed) untuk temuan yang butuh PDF.
- send-draft: `svc.users().drafts().send(userId="me", body={"id": did})` — akun DEFAULT
  balas 404 "not a draft", pakai akun `RESEARCHER_USERNAME`.

## Akun
`RESEARCHER_USERNAME` = akun utama (`RESEARCHER_EMAIL`). Re-auth PKCE port 8765 kalau token expired.