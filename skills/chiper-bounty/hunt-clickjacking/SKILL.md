---
name: hunt-clickjacking
description: "Hunt Clickjacking — missing X-Frame-Options / CSP frame-ancestors lets an attacker embed the target page in an invisible iframe and trick victims into clicking buttons they cannot see (UI redressing). Targets: login flows, money transfers, account settings, OAuth confirmation pages. Confirm by fetching the page, then PROVE it frames in a real browser and a sensitive state-changing action survives the cross-site context (SameSite cookies / framebusting JS can defeat it) — header-absence alone is not a finding."
sources: hackerone_public, public_research
report_count: 6
---

## What is Clickjacking

Clickjacking (UI Redressing) lets an attacker load a target page inside a transparent iframe on a malicious site. The victim sees the attacker's decoy UI but clicks the hidden target UI beneath it. No JavaScript on the target is required.

**Highest-value targets:**
- Login / authentication pages — force login with attacker credentials
- Money transfer / checkout / "confirm payment" buttons
- Account settings (email change, password change, 2FA disable)
- OAuth / social-login "Authorize app" confirmation dialogs
- Admin actions (delete, promote user, change role)

## Protection Headers

Two mechanisms prevent framing:

```
X-Frame-Options: DENY              # strongest — blocks all framing
X-Frame-Options: SAMEORIGIN        # allows same-origin frames only
Content-Security-Policy: frame-ancestors 'none'     # CSP equivalent of DENY
Content-Security-Policy: frame-ancestors 'self'     # CSP equivalent of SAMEORIGIN
```

If NEITHER is present, the page is frameable from any origin.

## How to Test

Header-absence is the **trigger for investigation, not the finding**. Two steps:

**Step 1 — Header check (screening).** Fetch the target page and inspect the response headers:

```
curl -sI https://target.example/account/transfer | grep -iE 'x-frame-options|content-security-policy'
```
If BOTH `X-Frame-Options` and CSP `frame-ancestors` are absent, the page is a *candidate*. If either is present and restrictive (`DENY`/`SAMEORIGIN`/`frame-ancestors 'none'|'self'`), stop — it's protected.

**Step 2 — Prove it actually frames and clicks (required for a real finding).** Build a minimal PoC and load it in a real browser:

```html
<!doctype html>
<h1>Win a prize — click below</h1>
<iframe src="https://target.example/account/transfer"
        style="opacity:0.1;position:absolute;top:0;left:0;width:1000px;height:800px"></iframe>
```
Confirm ALL of the following, or it is not exploitable:
- The page **actually renders inside the iframe** (no framebusting JS that blanks/redirects it — e.g. `if(top!==self)` breakout, or a `Sec-Fetch-Dest`/JS frame check).
- The **sensitive action still works while framed** — critically, the action must succeed *cross-site*. If it relies on a session cookie set `SameSite=Lax` or `SameSite=Strict` (the modern default), the cookie is **not** sent on the cross-site framed request, and the clickjack fails. Verify the victim's authenticated state carries into the frame.
- The target is a **state-changing action** (transfer, settings/email/password change, 2FA disable, OAuth authorize, admin action), not a read-only page.

**Strategy:** target the most sensitive action pages first — severity scales directly with what the victim is tricked into doing.

## False Positives

- Public, read-only pages (home/marketing) lacking frame protection are low/informational — no sensitive action to redress.
- APIs and non-HTML endpoints (JSON, images) are not clickjacking targets.
- **Header-absence alone is NOT a finding.** SameSite cookies, framebusting JS, or the lack of any sensitive framed action can each fully defeat it — which is why Step 2 is mandatory.

## Proof Requirements

A valid clickjacking report shows: (1) the target page rendered inside an attacker-controlled iframe in a real browser, (2) a sensitive state-changing action reachable by a framed click while the victim is authenticated (cookies survive the cross-site context), and (3) a screenshot/recording of the overlay. Reporting missing headers with no working frame PoC is a documentation-quality issue, not a vulnerability.


## Runnable probes

Commands you can paste. `<TARGET>`/`<RPC>` are placeholders — fill them
from recon, do not guess endpoints.

```bash
# 0) does the sensitive page set frame protections?
for u in /account/settings /account/email /billing /admin; do
  printf '%-22s ' "$u"
  curl -sS -D - -o /dev/null "https://<TARGET>$u" | grep -iE 'x-frame-options|content-security-policy' | tr '\n' ' '; echo
done

# 1) frame-busting JS present? (client-side protection is bypassable with sandbox)
curl -sS https://<TARGET>/account/email | grep -oiE 'top *[!=]==? *self|frameElement|onbeforeunload' | head

# 2) build the PoC — needs a SENSITIVE action, not a search page
cat > poc.html <<'HTML'
<style>iframe{opacity:.0001;position:absolute;top:0;left:0;width:1000px;height:800px;z-index:9}
button{position:absolute;top:320px;left:380px;z-index:10}</style>
<iframe src="https://<TARGET>/account/email"></iframe>
<button>Click for a prize</button>
HTML

# 3) verify the action actually fires (browser, not curl)
python -m http.server 8080 --directory . &
# open http://127.0.0.1:8080/poc.html while logged in, click the overlay, then check
# whether the email/state ACTUALLY changed.

# 4) if the page is protected, try the bypass set before giving up
#    - sandbox="allow-scripts allow-forms" (kills frame-busting JS)
#    - nested iframe, double-framing
#    - same-site cookie check: does SameSite=Lax even matter for a GET-framed page?
```

**Proof bar:** the forced action must be **sensitive and demonstrated** (email
changed, transfer made, account deleted). Clickjacking on a search page or a
privacy policy is N/A on every program.

---

## 2026 sweep 3 (dork pass 2026-10-18 — web2, 1 repo)

- CVE-2026-54477 — admin panel missing security headers (clickjacking / XSS). Low severity on its own; worth reporting only when an admin action can be framed.
  - CVE-2026-54477: Admin Panel Missing Security Headers (clickjacking / XSS)

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Halaman aksi sensitif tanpa `X-Frame-Options`/`frame-ancestors` | Prasyarat dasar |
| 2 | Frame-busting JS bisa dilewati (`sandbox`, `iframe` bersarang) | Proteksi client-side lemah |
| 3 | Aksi benar-benar sensitif (transfer, ganti email, hapus) — bukan logout/search | Severity dari aksi, bukan mekanisme |
| 4 | Drag-and-drop / multi-click UI redress kalau butuh 2 langkah | Bypass interaksi ganda |
| 5 | `SameSite` cookie tidak mengganggu framing (hanya mengganggu cross-site POST) | Jangan salah kira SameSite melindungi |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Korban yang mengunjungi halaman penyerang akan tanpa sadar menekan tombol hapus akun di target" — PoC HTML harus benar-benar melakukan aksi.
2. **Apa yang hilang dari korban?** Aksi yang dipaksa harus sensitif (ganti email, transfer, hapus). Aksi reversibel bernilai rendah = Low.
3. **Bisa direproduksi 10 menit dari nol?** Halaman PoC harus bisa dibuka dan aksinya terlihat. Sertakan status cookie `SameSite`.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** klik paksa korban

**Teknik pengembangan:** aksi satu-klik (hapus/transfer); prefilled form

**Eskalasi ke:** `hunt-ato` · `hunt-auth-bypass`

**Depth target:** L2 -> L4

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.



## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Clickjacking Critical hanya kalau aksi yang bisa dipicu adalah **ireversibel dan bernilai**:

| Aksi di balik iframe | Severity |
|---|---|
| Transfer dana / withdraw / ubah rekening | Critical |
| Ubah email/password / matikan MFA | Critical |
| Setujui OAuth grant / permission sensitif | High-Critical |
| Hapus data / tutup akun | High |
| Tambah ke keranjang, ubah preferensi | Low |

**Kalibrasi wajib:** `X-Frame-Options: DENY` atau CSP `frame-ancestors` yang benar = bukan temuan.
Uji dengan iframe aktual, bukan hanya baca header — header bisa ada di satu path dan hilang di
path lain.

## 2026 sweep

- **CSP `frame-ancestors` hanya di halaman login** — halaman aksi sensitif tanpa proteksi.
- **Multi-step action tanpa token per-step** — clickjacking bisa mengklik langkah 1, user
  mengklik langkah 2 sendiri; tanpa token per-step, rantai lengkap.
- **Drag-and-drop + clickjacking** — serangan yang menggabungkan klik paksa dengan drag file/data.
- **`X-Frame-Options: ALLOW-FROM`** — sudah deprecated dan diabaikan browser modern; jangan
  anggap sebagai proteksi.
