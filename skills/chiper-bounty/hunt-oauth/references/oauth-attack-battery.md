# OAuth / OIDC Attack Battery — ordered, run top-to-bottom

Katalog eksekusi cepat untuk `hunt-oauth`. Detail payload & bypass lengkap tetap di SKILL.md;
di sini urutan kerja berjenjang + kill-signal + fingerprint. Additive-only. Setiap langkah
wajib OOB/artefak-verifiabel, jangan substring-match `access_token` (decode error body JSON —
mis. `AADSTS50076` claim-challenge membawa `access_token` substring yang BUKAN token usable).

---

## Tier 0 — Discovery & fingerprint (sebelum serang, petakan dulu 1 menit)

| # | Cek | Signal | Kill-signal |
|---|---|---|---|
| 0a | `/.well-known/openid-configuration` | issuer/authorization/token/jwks/registration_endpoint | config ada → lanjut 0b |
| 0b | `registration_endpoint` terbuka (DCR) | bisa daftar client tanpa auth | **DCR terbuka = pintu utama**, lanjut Tier 3 |
| 0c | `jwks_uri` + `token_endpoint_auth_method` | `none`/`client_secret_post`/`private_key_jwt` | auth method lemah → Tier 5 |
| 0d | `response_types_supported` berisi `token` (implicit) | implicit flow masih on | fragment leak surface |
| 0e | `prompt=none` + `response_type=code` tanpa interaksi | silent token | cek session fixation |

Cross-ref: `web2-recon` `.well-known` battery + `hunt-subdomain` untuk SSO host.

---

## Tier 1 — redirect_uri validation bypass (path paling sering bayar)

Urutan cheapest-first (dari SKILL.md browser-parse vs server-parse):

1. **Exact-match dulu** (kontrol negatif): whitelist exact → coba semua shape di bawah.
2. **Host confusion**: `https://target.com@attacker.com`, `https://attacker.com/target.com`,
   `https://target.com.attacker.com`, backslash `https://target.com\@attacker.com`.
3. **Prefix / string-match**: `https://target.com.attacker.com/cb`, `https://attacker.com#target.com`.
4. **Path traversal**: `https://target.com/../attacker/cb`, `%2f%2e%2e`, `..;/`.
5. **Param pollution**: `redirect_uri=A&redirect_uri=attacker`, `?redirect_uri=A&redirect_uri=B`.
6. **Encoded slash/char**: `%2f`, `%3a`, `%40`, double-encode `%252f`.
7. **Open-redirect chain**: cari open redirect di domain legit → `redirect_uri=https://legit/open-redirect?url=attacker`.
8. **Browser-parse vs server-parse**: parser beda interpretasi (browser normalized vs server raw).

**Kill-signal:** `Location: https://attacker.com/...?code=` atau `access_token=` nyata → auth-code/authorization-code theft = **Critical**, stop.

**Proof bar:** code/token B yang melewati redirect_uri host penyerang, lalu ditukar jadi token B. Bukan sekadar reflected.

---

## Tier 2 — state CSRF (login/link CSRF) & token confusion

| # | Attack | Probe | Proof bar |
|---|---|---|---|
| 2a | State nil/static | drop `state` → callback tetap jalan | akun B ke-link ke attacker account |
| 2b | Account-link CSRF | initiate flow A, replay ke sesi B tanpa state | akun B terikat ke identitas A |
| 2c | Cross-client token confusion | mint token client A → replay ke API client B | API B terima token A (audience tak divalidasi) |
| 2d | Nonce via Referer | callback page load third-party → `Referer` bawa token | token terlihat di log/Collaborator |

**Kill-signal:** akun B berubah/kebind ke sesi penyerang tanpa state valid = ATO (chain ke `hunt-ato`).

---

## Tier 3 — OIDC Dynamic Client Registration (DCR) abuse

```bash
curl -X POST https://<TARGET>/.well-known/openid-registration -H 'Content-Type: application/json' \
  -d '{"redirect_uris":["https://attacker.com/cb"],"client_name":"x","grant_types":["authorization_code"]}'
```

- `registration_endpoint` terbuka → daftar client dengan `redirect_uri` penyerang → mint code untuk victim.
- `POST_logout_redirect_uris` / `initiate_login_uri` kadang lolos validasi (bukan bagian dari check redirect_uri ketat).
- ⚠️ **Depending on flow**: kalau DCR butuh token (protected), cari `registration_access_token` di bundle/broadcast.

**Kill-signal:** client terdaftar dengan redirect_uri penyerang + code victim mendarat → **Critical**.

Lihat ref `dcr-arbitrary-redirect-uri.md`.

---

## Tier 4 — Consent / scope confusion (add role di form) → `oauth-consent-scope-confusion.md`

```
scope=openid email admin.write ... (tambah scope privileged)
prompt=none  (silent re-auth)
```

- Consent screen yang cuma merender scope tapi tak enforce → attacker inject scope admin.
- Client config dengan `scope` trust penuh dari request.

**Kill-signal:** token B keluar dengan scope admin yang tak diminta consent → priv-esc/ATO.

---

## Tier 5 — Token endpoint auth bypass & key confusion

| # | Probe | Signal |
|---|---|---|
| 5a | Token exchange tanpa verifikasi client | `POST /token` tanpa `client_secret` tetap keluar token |
| 5b | Unverified account untuk token | akun belum-verifikasi → token tetap valid |
| 5c | `token_endpoint_auth_method: none` | public client → bisa mint token atas nama korban |
| 5d | PKCE downgrade / absent | client tanpa PKCE → authorization code interception |

Crypto detail (`alg:none`, key confusion, kid) → `hunt-jwt-crypto` matrix.

---

## Tier 6 — Implicit / hybrid flow & mobile deep link (fragment leak)

- `response_type=token` (implicit) → token di fragment URL, bocor via Referer/history/log.
- Mobile custom-scheme `://callback` deeplink hijack (Android `push_notification_webview`).

**Kill-signal:** access_token B tertangkap di host/Referer penyerang.

---

## Tier 7 — Intra-IdP / SAML-to-OIDC trust confusion (lanjutan)

- `hydra-oathkeeper-permission-confusion.md` + `cloudflare-access-mcp-oauth.md` + `relying-party-oidc-client.md` — permission mapping antar IdP/SP yang salah jadi cross-tenant akses.

## Quick refusal-pattern (jangan lapor buta)

- `redirect_uri` cuma *reflected* tapi exchange di-pin server → TIDAK exploit (OOB wajib).
- `access_token` substring dalam error body (AADSTS claim-challenge) → BUKAN token usable.
- Token mint `alg:none` tanpa tindakan privileged di bawah identitas B → bukan temuan.