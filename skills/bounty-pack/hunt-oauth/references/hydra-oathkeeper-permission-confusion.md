# Consent-layer permission confusion — Hydra + Oathkeeper (Ory) estates

Kelas bug bernilai tinggi (pernah mencuri dana nyata; insiden 2026-09-19, 6.61 BTC): **rantai izin di tiga
lapis**, masing-masing percaya lapis lain sudah memvalidasi. Relevan untuk setiap estate Ory Hydra +
Oathkeeper + consent app custom. Clone publik upstream (`GaloyMoney/galoy`) memuat bentuk pra-fix-nya —
berguna sebagai referensi BENTUK bug, bukan deskripsi deployment saat ini (clone bisa tertinggal setahun).

## Model tiga lapis (L1 → L2 → L3)

| Lapis | Bentuk rentan | Bukti di source |
|---|---|---|
| **L1 — consent page** | Halaman consent mempercayai daftar scope **dari browser** dan meneruskannya ke Hydra tanpa mengiris dengan `requested_scope`. | `apps/consent/app/consent/page.tsx`: `const grantScope = form.getAll("grant_scope")` → `acceptOAuth2ConsentRequest({grant_scope: grantScope, …})`. Fix = irisan `body.requested_scope` + `grant_access_token_audience: body.requested_access_token_audience`. |
| **L2 — gatekeeper (Oathkeeper)** | Rule API istimewa memakai `authenticator: oauth2_introspection` + `authorizer: allow` **tanpa audience check** → token apa pun yang hidup lolos. Ciri: `#! TODO: add aud: {"aud": ["https://api/admin/graphql"]}` di `dev/config/ory/oathkeeper_rules.yaml`. | `admin-backend` DAN `galoy-backend` sama-sama membawa TODO itu → cek semua rule, bukan cuma satu. |
| **L3 — backend** | Service istimewa membaca izin **dari string di token** (mutator `id_token` menyalin `{{ print .Extra.scope }}`) alih-alih memeriksa subjek/peran di DB. | `mutators: id_token, claims: '{"sub": "{{ print .Subject }}", "scope": "{{ print .Extra.scope }}", …}'` → upstream menerima scope hasil copy apa adanya. |

Aturan: **fix di satu rule/lapis tidak memperbaiki sibling-nya.** Setelah primari ditambal,
`grep -n "TODO: add aud\|oauth2_introspection\|authorizer"` di rules Oathkeeper dan uji tiap API istimewa
satu per satu dengan token ber-scope rendah.

## Recipe — uji L1 (scope tampering) setelah punya sesi

Butuh: akun sendiri + satu OAuth client target yang **tidak** `skip_consent` (client_id terlihat di URL
flow / bundle).

1. Mulai flow sendiri untuk `login_challenge` (JANGAN ikuti redirect):
   `GET https://oauth.<t>/oauth2/auth?client_id=<id>&response_type=code&scope=read&redirect_uri=<url client>&state=<random 8+>`
   → baca `Location` → `login_challenge=…`.
2. Selesaikan login → halaman consent memuat `consent_challenge=…` di `/consent`.
3. **Uji L1 via CDP** (browser sendiri, sesi sudah login):
   - buka `/consent?consent_challenge=<fresh>`; kalau client `skip_consent`, app langsung accept dengan
     `requested_scope` → bukan jalur uji L1; ganti client.
   - `Runtime.evaluate`: ubah/tambah checkbox `grant_scope` agar form mengirim scope yang **tidak pernah
     diminta** (`admin`, `write`, `receive`).
   - submit → baca respons Hydra:
     - **FIXED** → `invalid_scope` / consent ditolak / token hanya berisi irisan scope.
     - **VULN** → Hydra menerima, token/`id_token` memuat scope ekstra → rangkai ke impact (panggil
       endpoint yang butuh scope itu; kalau endpoint primari VPN-only, pindah ke sibling).
   - Bukti minimal: 2 request tersimpan (baseline vs tampered) + respons berbeda — bukan "field-nya ada".
4. **Uji L2** dengan token langkah 3 ke API istimewa lain (`api/admin`, `api-keys`, service internal):
   diotorisasi atau tidak? Kalau primari di balik VPN, catat sebagai kontrol dan uji sibling publik.
5. **Uji L3** dengan token ber-`scope` lebar tapi subjek BUKAN admin; hubungi endpoint yang menyimpulkan
   izin dari token (biasanya GraphQL dengan `scope` di context).

## Pemeriksaan sampingan murah (hari yang sama)

- `/oauth2/auth` scope tak dikenal → `error=invalid_scope`; scope valid + `audience` salah → ditolak.
- `redirect_uri` strict: sibling domain, traversal, `localhost`, `evil.com` → `invalid_request`.
- **DCR** (`POST /oauth2/register`) hidup = daftarkan client sendiri (jalur uji terbaik).
- **Introspection endpoint publik** (`/admin/oauth2/introspect`, `/oauth2/introspect`) reachable tanpa auth
  = temuan tersendiri (kebocoran metadata token).
- `client_credentials` tanpa secret → `invalid_client`; client publik + PKCE → cek `code_verifier`
  benar-benar divalidasi.
- Consent page `Cache-Control: private, no-store` (anti cache-poisoning jalur consent).
- `client.skip_consent` diset untuk client pihak ketiga = hilangnya layar izin (privilege).

## Pitfalls

- **Challenge kedaluwarsa.** `login_challenge` / `consent_challenge` berumur pendek — generate ulang tepat
  sebelum dipakai; challenge basi tampil sebagai error dan mudah disalahartikan "target broken".
- **Simpan `state`** kalau callback client memvalidasinya; tanpa itu flow terlihat gagal padahal server sehat.
- **Jangan simpulkan L1 aman dari halaman statis.** Verdict hanya dari beda respons server saat `grant_scope`
  ditamper.
- **Batasi jumlah tamper.** Satu request + baca respons cukup untuk verdict; catat sebagai authorization
  test, bukan fuzzing.
- Cookie consent (Hydra) ≠ cookie sesi aplikasi — uji dari browser yang sama tempat login terjadi.
- Client `skip_consent` melewati halaman consent → untuk menguji L1 kamu butuh client yang benar-benar
  menampilkan layar izin.
