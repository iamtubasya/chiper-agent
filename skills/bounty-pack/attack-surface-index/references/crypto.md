# Reverse Index — Crypto / JWT

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| JWT session | alg:none, key confusion, kid/jku/jwk injection | JWT authentication bypass via unverified signature · JWT authenticat |
| password hashing lemah (MD5/SHA1) | crack + credential stuffing | JWT authentication bypass via unverified signature · JWT authenticat |
| padding oracle (CBC) | padding oracle attack → decrypt | JWT authentication bypass via unverified signature · JWT authenticat |
| nonce/IV reuse | known-plaintext recovery | JWT authentication bypass via unverified signature · JWT authenticat |

## PoC corpus terkait (7 repo)

- `AmberWolfCyber_DEFCON34-ThinClientThinCrypto`
- `ByteMe1001_DJI-Enhanced-WiFi-Weak-Cryptography`
- `Crypto-Cat_wp2shell`
- `CryptoMachio_CVE-2025-5548`
- `D3CRYPTORDE_GuentherJB`
- `George0Papasotiriou_CVE-2026-11119-Padding-Oracle-Attack-on-CBC-Mode-Encryption`
- `George0Papasotiriou_CVE-2026-21003-JWT-none-Algorithm-Bypass-via-kid-Header-Omission`

## Lab PortSwigger: jwt (6 lab)

- JWT authentication bypass via unverified signature (`lab-jwt-authentication-bypass-via-unverified-signature`)
- JWT authentication bypass via flawed signature verification (`lab-jwt-authentication-bypass-via-flawed-signature-verification`)
- JWT authentication bypass via weak signing key (`lab-jwt-authentication-bypass-via-weak-signing-key`)
- JWT authentication bypass via jwk header injection (`lab-jwt-authentication-bypass-via-jwk-header-injection`)
- JWT authentication bypass via jku header injection (`lab-jwt-authentication-bypass-via-jku-header-injection`)
- JWT authentication bypass via kid header path traversal (`lab-jwt-authentication-bypass-via-kid-header-path-traversal`)
