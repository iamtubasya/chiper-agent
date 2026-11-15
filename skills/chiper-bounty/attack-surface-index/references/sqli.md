# Reverse Index — SQL Injection

**Cara pakai:** cocokkan fitur yang ditemukan recon dengan kolom kiri.
Satu baris cocok = probe WAJIB sebelum kelas ini boleh ditandai N/A.

| Fitur di target | Probe pertama | Lab PortSwigger |
|---|---|---|
| search / filter / sort / autocomplete | kirim ' dan bandingkan error + waktu (boolean & time-based) | SQL injection vulnerability allowing login bypass · SQL injection vu |
| login form | administrator'-- di username, bandingkan response sukses | SQL injection vulnerability allowing login bypass · SQL injection vu |
| parameter id numerik di URL | ' OR 1=1-- dan ' AND 1=2--, bandingkan jumlah baris | SQL injection vulnerability allowing login bypass · SQL injection vu |
| endpoint yang makan XML/JSON | SQLi dengan filter bypass via XML encoding | SQL injection vulnerability allowing login bypass · SQL injection vu |
| API dengan parameter order/group | UNION SELECT lewat ORDER BY injection | SQL injection vulnerability allowing login bypass · SQL injection vu |

## PoC corpus terkait (19 repo)

- `0x3f3c_CVE-2024-32640-SQLI-MuraCMS`
- `0xYumeko_CVE-2024-32640-SQLI-MuraCMS`
- `19melek19_TheMisfits-CVE-2024-8465-SQLi`
- `874anthony_CVE-2024-42327_Zabbix_SQLi`
- `AbdullahMaqbool22_CVE-2026-60137-WordPress-Core-SQL-Injection-PoC`
- `BiiTts_CVE-2026-52887-NocoBase-SQLi-RCE`
- `BiiTts_CVE-2026-54350-Budibase-NoSQL-Injection`
- `BridgerAlderson_Zabbix-CVE-2024-42327-SQL-Injection-RCE`
- `BurakSevben_Daily_Habit_Tracker_App_SQL_Injection`
- `BurakSevben_School-Task-Manager-SQL-Injection-2`
- `BurakSevben_School-Task-Manager-System-SQLi-1`
- `CerberusMrXi_CVE-2026-44680-MikroORM-SQL-Injection-Exploit-Framework`
- `CerberusMrXi_CVE-2026-57588-Nessus-XML-Import-SQL-Injection-PoC`
- `ChrisSub08_CVE-2026-25746_SqlInjectionVulnerabilityOpenEMR7.0.4`
- `ChrisSub08_CVE-2026-32127_SqlInjectionVulnerabilityOpenEMR8.0.0`
- … +4 lagi di `D:/data hermes/poc-compact/`

## Lab PortSwigger: sql-injection (3 lab)

- SQL injection vulnerability allowing login bypass (`lab-login-bypass`)
- SQL injection vulnerability in WHERE clause allowing retrieval of hidden data (`lab-retrieve-hidden-data`)
- SQL injection with filter bypass via XML encoding (`lab-sql-injection-with-filter-bypass-via-xml-encoding`)
