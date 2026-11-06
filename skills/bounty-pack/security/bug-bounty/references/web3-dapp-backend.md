# Reference: Web3 dApp Backend / Off-Chain Attack Surface (BBflow §4.3)

> Sering payout lebih tinggi daripada contract bugs. Kontrak diaudit bersih,
> backend-nya nggak. Modern DeFi = hybrid: backend API + smart contracts + off-chain services.

## Kelas Bug Utama

### Missing Auth di Backend API (CWE-306)
- Internal endpoints diekspos lewat frontend proxy (mis. `/api/backend/*`) tanpa auth.
- Contoh real: Sweepr Critical = unauthenticated paymaster proxy di backend, bukan contract bug.
- **Cara nemu:** cari Swagger/OpenAPI doc, baca flag `security: []` per route.

### Paymaster / Relayer / Bundler Abuse
- Unauth proxy ke gas-sponsoring paymaster (`pm_getPaymasterData`, `pm_sponsorUserOperation`, `eth_sendUserOperation`).
- Siapa aja bisa drain paymaster deposit.
- Base gas murah, tapi deposit tetap shared pool — per-op kecil ≠ aman.

### Gas Sponsorship Abuse
- Free gas untuk operasi arbitrary = fund loss, walau cost per-op kecil.

### Fee-Authorization Signature Bypass
- Fees di-sign off-chain (feeSigner) → test replay, missing deadline, weak validation, signer leaked/reachable.

### IDOR di Wallet Data
- `GET /history/{wallet}` return balance/history wallet siapa aja tanpa auth.

### Off-Chain Partner Accounting
- V1-style off-chain fee/accounting logic unverifiable on-chain → test parameter injection & missing auth.

## Metode

1. Temukan backend API lewat: JS bundle, Swagger, network tab, proxy paths.
2. Baca OpenAPI doc → daftar semua route `security: []`.
3. Hit tiap route tanpa header → 200 dengan data real = missing auth.
4. Untuk paymaster: uji `eth_sendUserOperation` dengan relayer palsu.
5. Dokumentasi: request/response + dampak finansial konkret.