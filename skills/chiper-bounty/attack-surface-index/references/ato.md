# Reverse Index — Account Takeover

**Cara pakai:** saat recon menemukan *fitur* di kolom kiri, jalankan probe di
kolom tengah SEBELUM menandai kelas ini N/A. Lab & PoC di kolom kanan adalah
contoh nyata yang bisa dibaca/dijalankan.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| password reset / forgot password | Host-header poisoning + token entropy + reuse + cross-account | — |
| OAuth / SSO login | redirect_uri bypass, state fixation, implicit flow, PKCE downgrade | Authentication bypass via OAuth implicit flow · Forced OAuth profile l |
| email change / profile update | change without re-auth -> silent victim swap | — |
| OTP / 2FA / MFA | OTP re-routing, code brute, backup-code reuse | — |
| JWT session | alg:none, key confusion, kid injection, jwk/jku header | JWT authentication bypass via unverified signature · JWT authenticatio |
| SAML enterprise login | XSW signature wrapping, audience restriction removal | — |
| invite / referral / magic link | token reuse, cross-tenant replay, missing expiry | — |
| session cookie | fixation, no rotation post-login, cross-subdomain scope | — |

## PoC corpus terkait (36 repo)

- `00lucasm_CVE-2025-58434-Flowiseai-Auth-Bypass-PoC`
- `0xDTC_CrushFTP-auth-bypass-CVE-2025-31161`
- `0xROOTPLS_GiveMeKernel`
- `0xkickit_iCUE_DllHijack_LPE-CVE-2024-22002`
- `ATonysan_CVE-2024-20931_weblogic`
- `AdityaBhatt3010_CVE-2025-54794-Hijacking-Claude-AI-with-a-Prompt-Injection-The-Jailbreak-That-Talked-Back`
- `AlissonFaoli_Apache-OFBiz-Exploit`
- `AntonieSoga_Erlang-OTP-PoC_CVE-2025-32433`
- `Arian91_CVE-2025-23369_SAML_bypass`
- `Ash1996x_CVE-2025-50154-Aggressor-Script`
- `AtoposX-J_CVE-2026-34197-Apache-ActiveMQ-RCE`
- `Bangkah_apache-auth-bypass-poc`
- `BigSweetPotatoStudio_HyperChat`
- `BiiTts_CVE-2026-46490-samlify-SAML-Attribute-Injection`
- `BiiTts_CVE-2026-49230-APISIX-jwe-decrypt-Auth-Bypass`
- `BiiTts_CVE-2026-49468-LiteLLM-Auth-Bypass`
- `BiiTts_CVE-2026-56782-Gorse-Auth-Bypass`
- `BirdsAreFlyingCameras_CVE-2025-53770_Raw-HTTP-Request-Generator`
- `BrowserOperator_browser-operator-core`
- `Bubka_2FAuth`
- … +16 repo lagi di `D:/data hermes/poc-compact/`
