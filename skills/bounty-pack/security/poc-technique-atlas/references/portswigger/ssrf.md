# PortSwigger WSA — SSRF
Source: https://portswigger.net/web-security/ssrf

## Technique headings
- Server-side request forgery (SSRF)
- What is SSRF?
- Labs
- What is the impact of SSRF attacks?
- Common SSRF attacks
- SSRF attacks against the server
- SSRF attacks against other back-end systems
- Circumventing common SSRF defenses
- SSRF with blacklist-based input filters
- SSRF with whitelist-based input filters
- Read more
- Bypassing SSRF filters via open redirection
- Blind SSRF vulnerabilities
- Finding hidden attack surface for SSRF vulnerabilities
- Partial URLs in requests
- URLs within data formats
- SSRF via the Referer header
- Find SSRF vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/ssrf/blind
- https://portswigger.net/web-security/ssrf/url-validation-bypass-cheat-sheet


## Labs (2026-10-18 — per-lab scenarios & solutions), 5 lab)

- **Basic SSRF against another back-end system** (`lab-basic-ssrf-against-backend-system`)
  - Visit a product, click Check stock , intercept the request in Burp Suite, and send it to Burp Intruder. Change the stockApi parameter to http://192.168.0.1:8080/admin then highlight the final octet of the IP address (the number 1 ) and click Add § . In the Payloads side panel, change the payload type to Numbers , and enter 1, 255, and 1 in the From and To and Step boxes respectively. Click Start attack . Click on the
- **Basic SSRF against the local server** (`lab-basic-ssrf-against-localhost`)
  - Browse to /admin and observe that you can't directly access the admin page. Visit a product, click "Check stock", intercept the request in Burp Suite, and send it to Burp Repeater. Change the URL in the stockApi parameter to http://localhost/admin . This should display the administration interface. Read the HTML to identify the URL to delete the target user, which is: http://localhost/admin/delete?username=carlos Sub
- **SSRF with filter bypass via open redirection vulnerability** (`lab-ssrf-filter-bypass-via-open-redirection`)
  - Visit a product, click "Check stock", intercept the request in Burp Suite, and send it to Burp Repeater. Try tampering with the stockApi parameter and observe that it isn't possible to make the server issue the request directly to a different host. Click "next product" and observe that the path parameter is placed into the Location header of a redirection response, resulting in an open redirection. Create a URL that 
- **SSRF with blacklist-based input filter** (`lab-ssrf-with-blacklist-filter`)
  - Visit a product, click "Check stock", intercept the request in Burp Suite, and send it to Burp Repeater. Change the URL in the stockApi parameter to http://127.0.0.1/ and observe that the request is blocked. Bypass the block by changing the URL to: http://127.1/ Change the URL to http://127.1/admin and observe that the URL is blocked again. Obfuscate the "a" by double-URL encoding it to %2561 to access the admin inte
- **SSRF with whitelist-based input filter** (`lab-ssrf-with-whitelist-filter`)
  - Visit a product, click "Check stock", intercept the request in Burp Suite, and send it to Burp Repeater. Change the URL in the stockApi parameter to http://127.0.0.1/ and observe that the application is parsing the URL, extracting the hostname, and validating it against a whitelist. Change the URL to http://username@stock.weliketoshop.net/ and observe that this is accepted, indicating that the URL parser supports emb
