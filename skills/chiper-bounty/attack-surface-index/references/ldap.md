# Reverse Index — LDAP Injection

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| login LDAP | wildcard di username → bypass filter | — |
| pencarian direktori (user/group) | LDAP injection via filter metacharacters | — |
| SSO berbasis LDAP | bypass hanya bila LdapAuthModule aktif | — |

## PoC corpus terkait (0 repo)

