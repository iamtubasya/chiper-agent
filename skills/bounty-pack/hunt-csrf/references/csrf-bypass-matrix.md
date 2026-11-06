# CSRF Bypass Matrix — defense × bypass, with proof bar

Katalog eksekusi cepat untuk `hunt-csrf`. Detail + harness + BFF Duende surface tetap di SKILL.md;
di sini setiap defense dipetakan ke bypass variant + proof bar. Additive-only.

**Prinsip (dari SKILL.md):** CSRF bayar hanya kalau state-changing action yang **seharusnya
dilindungi** bisa dipicu dari **origin penyerang** tanpa token valid. Read-only CSRF = N/A.

---

## A. Defense → Bypass matrix

| # | Defense di target | Bypass variant | Proof bar |
|---|---|---|---|
| A1 | Token absent (no CSRF token) | form POST langsung dari attacker origin | aksi state-change (email/password/transfer) jalan |
| A2 | `SameSite=Strict` | — (jarang bypass murni) | — |
| A3 | `SameSite=Lax` | top-level GET navigation + method-override/POST-upgrade | aksi liebat via GET/submit |
| A4 | `SameSite=None` (default di beberapa stack) | token absent → CSRF klasik | sama A1 |
| A5 | Token ada tapi not bound | token A dipakai di sesi B (reuse/cross-session) | aksi jalan pakai token lain |
| A6 | `Content-Type: application/json` enforced | JSON CSRF via `text/plain` + paksa parse; atau `application/json` via CORS-permissive | aksi ter-auth dari origin jahat |
| A7 | Referer/Origin header check | hapus header (meta referrer), atau origin yang lolos (regex weak) | aksi jalan tanpa referer valid |
| A8 | Double-submit cookie | cookie bisa di-set via subdomain/other → token+value match | aksi jalan |
| A9 | Custom header (`X-Requested-With`) | CORS preflight allow header (chain) | aksi via CORS-write |
| A10 | Duende `X-CSRF: 1` (per-SKILL.md) | cross-role replay (token tak user-bound) | role lain replay sukses |
| A11 | Cookie-domain wildcard (`Domain=.target.com`) | subdomain takeover → set cookie → fix/hijack | sesi target termanipulasi |

---

## B. Mobile-app / deeplink CSRF (custom scheme)

`custom-scheme://callback` deeplink yang mengeksekusi aksi tanpa verifikasi source → CSRF dari
halaman web yang mengarahkan ke deeplink. Android deep-link hijack (lihat SKILL.md §Mobile).

---

## C. SignalR / WebSocket carve-out (BFF Duende surface)

`/negotiate` / websocket connection sering **carve-out** dari antiforgery → aksi realtime tanpa
token. Probe `/negotiate` unauth → cek apakah channel/stub bisa di-invoke tanpa token. Ref
`hunt-websocket` untuk CSWSH.

---

## D. Ready-made harness (dari SKILL.md, diulang untuk cepat copy)

```html
<!-- save as csrf.html, serve from attacker origin, open in logged-in victim browser -->
<form action="https://<TARGET>/api/account/email" method="POST">
  <input name="email" value="attacker@evil.com">
  <input type="submit" value="go">
</form>
<script>document.forms[0].submit()</script>
```

JSON-CSRF bypass `Content-Type`:
```html
<form enctype="text/plain" method="POST" action="https://<TARGET>/api/update">
  <input name='{"email":"attacker@evil.com","x":"' value='"}'>
</form>
```

---

## E. Fingerprint quick-ref (urutan cek tercepat)

1. `POST /api/<state-change>` tanpa token → masih 200 & efek jalan? (A1/A4)
2. Baca `Set-Cookie` `SameSite` attribute (A3/A4/A11).
3. Replay token A di sesi B (A5).
4. Hapus `Referer`/`Origin` header → aksi tetap jalan? (A7)
5. Coba `enctype="text/plain"` + JSON body (A6).

## Refusal-pattern

- Read-only CSRF → N/A.
- Token absent tapi content-type `application/json` = form POST dari browser tak bisa default
  → belum tentu exploitable; butuh CORS-write / text-plain bypass nyata.
- `SameSite=Lax` tanpa cara upgrade ke POST / tanpa top-level navigation → downgrade, jangan High.