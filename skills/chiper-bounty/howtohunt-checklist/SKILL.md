---
name: howtohunt-checklist
version: 1.0.0
author: RESEARCHER_NAME
description: Per-vuln-class hunting checklist — read before each hunt.
metadata:
  hermes:
    tags: [bug-bounty, methodology, checklist, hunt]
---

# HowToHunt — per-class hunting checklist

Checklist ringkas per kelas vuln. Dipakai sebagai **pra-jual sebelum buka skill
khusus**: pastikan surface-nya ada dulu, baru pilih skill yang tepat.

**Provenance:** disusun dari struktur HowToHunt + AllAboutBugBounty (kategori sama),
diisi dari teknik yang sudah ada di vault lokal (`pat-techniques/`, `cbh-hunt-skills/`,
`articles-*-playbook.md`). Bukan salinan repo — ini checklist operasional.

## Aturan pakai

0. **Petakan dulu ke `attack-surface-index`** — fitur yang ditemukan recon → probe
   pertama per kelas. Satu baris cocok = probe wajib, kelas itu belum boleh N/A.
1. **Cek surface dulu** — kalau kelas gak ada di target, catat N/A + alasan (jangan skip diam-diam).
2. **Baru buka skill khusus** — checklist ini cuma penyaring, skill `hunt-*` yang punya teknik lengkap.
3. **Differential wajib** — tiap item yang dicentang harus punya 2-state evidence (lihat `audit-runbook`).

## Checklist per kelas

### 1. IDOR / Broken Access Control
- [ ] Endpoint terautentikasi dengan parameter objek (`id`, `uid`, `order_id`, `file_id`)
- [ ] Ganti nilai param dengan objek milik user B → bandingkan response (200 + data = temuan)
- [ ] Coba variasi nama param (`userId`/`user_id`/`account`) + HPP (`?id=own&id=victim`)
- [ ] UUID? cari sumber bocor (API lain, email, referer, JS bundle)
- [ ] Method tampering: GET→POST→PUT→DELETE pada endpoint yang sama
- [ ] Level vertikal: user biasa → endpoint admin
- **Skill:** `hunt-idor` · ref: `pat-techniques/idor.md`

### 2. Auth bypass / OAuth
- [ ] Login tanpa kredensial (default creds, error-based enum, forced browsing)
- [ ] Reset password: token entropy, token reuse, host-header poisoning
- [ ] OAuth: `redirect_uri` bypass, scope escalation, `state` absen/fixation, PKCE downgrade
- [ ] JWT: `alg:none`, key-confusion, `kid` injection
- **Skill:** `hunt-auth-bypass` · `hunt-oauth` · `hunt-jwt-crypto` · ref: `pat-techniques/oauth.md`

### 3. ATO (Account Takeover)
- [ ] Reset-token theft (referer, email interception, host header)
- [ ] Session fixation / cookie tanpa rotate pasca-login
- [ ] CSRF pada endpoint sensitif (ganti email/password tanpa token)
- [ ] OAuth/SAML token theft → ATO lintas sistem
- **Skill:** `hunt-ato` · ref: `pat-techniques/account-takeover.md`

### 4. Race condition
- [ ] Endpoint dengan efek finansial/kuota (transfer, redeem, withdraw, claim)
- [ ] Single-packet attack (Turbo Intruder / `curl --next` / HTTP/2 coalescing)
- [ ] Limit overrun (voucher sekali-pakai dipakai N×)
- [ ] Double-spend pada balance/credit
- **Skill:** `hunt-race-condition` · ref: `pat-techniques/race-condition.md`

### 5. Business logic
- [ ] Price/quantity/currency tamper (negatif, nol, desimal, overflow)
- [ ] Step-skip via direct URL nav (checkout tanpa bayar)
- [ ] Coupon/referral stacking, proration
- [ ] Workflow reversal (refund setelah cancel)
- **Skill:** `hunt-business-logic` · ref: `pat-techniques/business-logic.md`

### 6. Injection
- [ ] SQLi: boolean + time-based differential (true vs false)
- [ ] NoSQLi: operator injection (`$where`, `$ne`)
- [ ] SSTI: `{{7*7}}` vs `${7*7}` — beda engine, beda payload
- [ ] Command injection: `;`, `|`, `` ` ``, `$()`
- [ ] XXE / SSRF: OOB callback vs no-callback
- **Skill:** `hunt-sqli` · `hunt-nosqli` · `hunt-ssti` · `hunt-rce` · `hunt-xxe` · `hunt-ssrf`

### 7. XSS
- [ ] Reflected: marker unik 8+ char (bukan `test`) → cek baseline dulu
- [ ] Stored: canary payload vs plain-text rendering
- [ ] DOM: source→sink di JS bundle
- **Skill:** `hunt-xss` · `hunt-dom`

### 8. SSRF
- [ ] Parameter URL/webhook/avatar/fetch
- [ ] Cloud metadata (169.254.169.254) — kalau tembus, eskalasi
- [ ] Internal port scan via timing/response diff
- **Skill:** `hunt-ssrf`

### 9. API misconfig / GraphQL
- [ ] Introspection on → dump schema
- [ ] Persisted-query vs ad-hoc
- [ ] Swagger/OpenAPI exposed
- [ ] Mass assignment (`role`, `verified`, `tenantId`)
- **Skill:** `hunt-api-misconfig` · `graphql-audit`

### 10. Secrets / exposed files
- **Skill:** `hunt-source-leak` · `security-arsenal`

---

## Checklist per kelas — WEB3 (pakai kalau target on-chain)

Aturan sama: kelas yang tidak ada di target → catat `N/A: <alasan>` di LEDGER, bukan skip
diam-diam. Untuk target DeFi, kelas 1-10 di atas tetap berlaku untuk lapisan web/API-nya;
kelas 11-19 di bawah khusus on-chain.

### 11. Smart account / modular authz (ERC-7579 / 4337 / 7702)
- **Skill:** `hunt-aa-modular`
- **Cek surface ada:** `installModule`/`setValidator`/`setExecutor` di ABI, atau chain dengan
  EIP-7702 aktif, atau SDK yang sebut "modular/plugins/session key".
- **N/A kalau:** target hanya ERC-20/721 polos tanpa account abstraction.

### 12. Signed approval / permit replay (Permit2 / ERC-3009 / EIP-712)
- **Skill:** `hunt-permit2-signature`
- **Cek surface ada:** import `permit2`, `permit(`, `transferWithAuthorization(`, relayer,
  "gasless approval".
- **N/A kalau:** tidak ada jalur approval berbasis signature.

### 13. AMM hooks / pool manipulation (v4 / Balancer v3 / singleton)
- **Skill:** `hunt-amm-hooks`
- **Cek surface ada:** `PoolManager`/`swap(`/`modifyLiquidity(`, hook callbacks, "singleton",
  "flash accounting".
- **N/A kalau:** target tidak punya pool/DEX sendiri.

### 14. Restaking / LRT accounting
- **Skill:** `hunt-restaking-lrt`
- **Cek surface ada:** operator registry, AVS, withdrawal queue, LRT/receipt token.
- **N/A kalau:** tidak ada lapisan restaking.

### 15. Intent / solver / attestor trust
- **Skill:** `hunt-intent-settlement`
- **Cek surface ada:** `solve(`/`fill(`/`settle(`, solver registry, attestor off-chain, bridge
  dengan signature release.
- **N/A kalau:** settlement murni on-chain tanpa aktor off-chain.

### 16. Oracle / sequencer uptime (L2)
- **Skill:** `hunt-oracle-l2`
- **Cek surface ada:** target di L2, atau baca `latestRoundData`/`getPrice`/`sequencerUptimeFeed`.
- **N/A kalau:** target tidak membaca harga eksternal untuk aksi bernilai.

### 17. Vault inflation / share-price (ERC-4626)
- **Skill:** `hunt-vault-inflation`
- **Cek surface ada:** vault, staking receipt, LRT, `convertToShares`/`convertToAssets`.
- **N/A kalau:** tidak ada vault yang mint share terhadap aset.

### 18. Upgradeability / diamond / proxy
- **Skill:** `hunt-diamond-proxy`
- **Cek surface ada:** `diamondCut`/facet, `upgradeTo`, implementation slot, `initialize(`.
- **N/A kalau:** kontrak immutable, tidak ada proxy.

### 19. On-chain forensics / chain recon
- **Skill:** `evm-chain-recon` · `onchain-source-recovery` · `defi-exploit-forensics`
- **Cek surface ada:** RPC publik chain tidak dikenal, exploit tx hash untuk dipelajari,
  deployed bytecode yang perlu dipulihkan.
- **N/A kalau:** semuanya sudah verified source + explorer lengkap.
- [ ] `.git/config`, `.env`, `.svn`, backup `.zip/.bak/.sql`
- [ ] API key di JS bundle (regex high-entropy + verifikasi key hidup)
- [ ] `security.txt` → contact + policy
- **Skill:** `hunt-source-leak` · `security-arsenal`

## Sumber di lokal
- `security/bug-bounty/references/pat-techniques/` — payload shelf (5 file)
- `security/bug-bounty/references/cbh-hunt-skills/` — 58 hunt skill komunitas (cadangan)
- `security/bug-bounty/references/articles-*-playbook.md` — playbook per-topik
- `security/bug-bounty/references/cbh-disclosed-reports/` — studi kasus severity nyata
