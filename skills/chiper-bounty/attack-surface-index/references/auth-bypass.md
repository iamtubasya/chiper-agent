# Reverse Index — Auth Bypass

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| login form | default creds, error-based enum, forced browsing | Insecure direct object references · Method-based access control can  |
| endpoint admin tanpa cek role | akses langsung + method tampering | Insecure direct object references · Method-based access control can  |
| session/cookie trust | forge cookie, cek signature | JWT authentication bypass via unverified signature · JWT authenticat |
| API tanpa auth middleware | akses endpoint internal tanpa token | Exploiting an API endpoint using documentation · Finding and exploit |

## PoC corpus terkait (8 repo)

- `00lucasm_CVE-2025-58434-Flowiseai-Auth-Bypass-PoC`
- `0xDTC_CrushFTP-auth-bypass-CVE-2025-31161`
- `Bangkah_apache-auth-bypass-poc`
- `BiiTts_CVE-2026-49230-APISIX-jwe-decrypt-Auth-Bypass`
- `BiiTts_CVE-2026-49468-LiteLLM-Auth-Bypass`
- `BiiTts_CVE-2026-56782-Gorse-Auth-Bypass`
- `CerberusMrXi_cPanel-WHM-CVE-2026-41940-auth-bypass-exploit`
- `Danimlzg_chia-rpc-auth-bypass.git`

## Lab PortSwigger: access-control (13 lab)

- Insecure direct object references (`lab-insecure-direct-object-references`)
- Method-based access control can be circumvented (`lab-method-based-access-control-can-be-circumvented`)
- Multi-step process with no access control on one step (`lab-multi-step-process-with-no-access-control-on-one-step`)
- Referer-based access control (`lab-referer-based-access-control`)
- Unprotected admin functionality (`lab-unprotected-admin-functionality`)
- Unprotected admin functionality with unpredictable URL (`lab-unprotected-admin-functionality-with-unpredictable-url`)
- URL-based access control can be circumvented (`lab-url-based-access-control-can-be-circumvented`)
- User ID controlled by request parameter (`lab-user-id-controlled-by-request-parameter`)
- User ID controlled by request parameter with data leakage in redirect (`lab-user-id-controlled-by-request-parameter-with-data-leakage-in-redirect`)
- User ID controlled by request parameter with password disclosure (`lab-user-id-controlled-by-request-parameter-with-password-disclosure`)
- User ID controlled by request parameter, with unpredictable user IDs (`lab-user-id-controlled-by-request-parameter-with-unpredictable-user-ids`)
- User role can be modified in user profile (`lab-user-role-can-be-modified-in-user-profile`)
- User role controlled by request parameter (`lab-user-role-controlled-by-request-parameter`)
