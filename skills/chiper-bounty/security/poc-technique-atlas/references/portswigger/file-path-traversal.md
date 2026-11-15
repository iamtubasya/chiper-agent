# PortSwigger WSA — Path Traversal
Source: https://portswigger.net/web-security/file-path-traversal

## Technique headings
- Path traversal
- Labs
- What is path traversal?
- Reading arbitrary files via path traversal
- Common obstacles to exploiting path traversal vulnerabilities
- How to prevent a path traversal attack
- Read more
- Find path traversal vulnerabilities using Burp Suite


## Labs (2026-10-18 — per-lab scenarios & solutions), 6 lab)

- **File path traversal, traversal sequences blocked with absolute path bypass** (`lab-absolute-path-bypass`)
  - Use Burp Suite to intercept and modify a request that fetches a product image. Modify the filename parameter, giving it the value /etc/passwd . Observe that the response contains the contents of the /etc/passwd file.
- **File path traversal, traversal sequences stripped non-recursively** (`lab-sequences-stripped-non-recursively`)
  - Use Burp Suite to intercept and modify a request that fetches a product image. Modify the filename parameter, giving it the value: ....//....//....//etc/passwd Observe that the response contains the contents of the /etc/passwd file.
- **File path traversal, simple case** (`lab-simple`)
  - Use Burp Suite to intercept and modify a request that fetches a product image. Modify the filename parameter, giving it the value: ../../../etc/passwd Observe that the response contains the contents of the /etc/passwd file.
- **File path traversal, traversal sequences stripped with superfluous URL-decode** (`lab-superfluous-url-decode`)
  - Use Burp Suite to intercept and modify a request that fetches a product image. Modify the filename parameter, giving it the value: ..%252f..%252f..%252fetc/passwd Observe that the response contains the contents of the /etc/passwd file.
- **File path traversal, validation of file extension with null byte bypass** (`lab-validate-file-extension-null-byte-bypass`)
  - Use Burp Suite to intercept and modify a request that fetches a product image. Modify the filename parameter, giving it the value: ../../../etc/passwd%00.png Observe that the response contains the contents of the /etc/passwd file.
- **File path traversal, validation of start of path** (`lab-validate-start-of-path`)
  - Use Burp Suite to intercept and modify a request that fetches a product image. Modify the filename parameter, giving it the value: /var/www/images/../../../etc/passwd Observe that the response contains the contents of the /etc/passwd file.
