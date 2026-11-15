# PortSwigger WSA — SQL Injection
Source: https://portswigger.net/web-security/sql-injection

## Technique headings
- SQL injection
- Labs
- What is SQL injection (SQLi)?
- What is the impact of a successful SQL injection attack?
- How to detect SQL injection vulnerabilities
- SQL injection in different parts of the query
- SQL injection examples
- Retrieving hidden data
- Warning
- Subverting application logic
- Retrieving data from other database tables
- Read more
- Blind SQL injection vulnerabilities
- Second-order SQL injection
- Examining the database
- SQL injection in different contexts
- How to prevent SQL injection
- Find SQL injection vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/sql-injection/blind
- https://portswigger.net/web-security/sql-injection/cheat-sheet
- https://portswigger.net/web-security/sql-injection/examining-the-database
- https://portswigger.net/web-security/sql-injection/union-attacks


## Labs (2026-10-18 — per-lab scenarios & solutions), 2 lab)

- **SQL injection vulnerability allowing login bypass** (`lab-login-bypass`)
  - Use Burp Suite to intercept and modify the login request. Modify the username parameter, giving it the value: administrator'--
- **SQL injection vulnerability in WHERE clause allowing retrieval of hidden data** (`lab-retrieve-hidden-data`)
  - Use Burp Suite to intercept and modify the request that sets the product category filter. Modify the category parameter, giving it the value '+OR+1=1-- Submit the request, and verify that the response now contains one or more unreleased products.
- **SQL injection with filter bypass via XML encoding** (`lab-sql-injection-with-filter-bypass-via-xml-encoding`)
  - Hint A web application firewall (WAF) will block requests that contain obvious signs of a SQL injection attack. You'll need to find a way to obfuscate your malicious query to bypass this filter. We recommend using the Hackvertor extension to do this. .
