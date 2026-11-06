# PortSwigger WSA — CORS
Source: https://portswigger.net/web-security/cors

## Technique headings
- Cross-origin resource sharing (CORS)
- What is CORS (cross-origin resource sharing)?
- Labs
- Same-origin policy
- Read more
- Relaxation of the same-origin policy
- Vulnerabilities arising from CORS configuration issues
- Server-generated ACAO header from client-specified Origin header
- Errors parsing Origin headers
- Whitelisted null origin value
- Exploiting XSS via CORS trust relationships
- Breaking TLS with poorly configured CORS
- Intranets and CORS without credentials
- How to prevent CORS-based attacks
- Proper configuration of cross-origin requests
- Only allow trusted sites
- Avoid whitelisting null
- Avoid wildcards in internal networks
- CORS is not a substitute for server-side security policies
- Find CORS vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/cors/access-control-allow-origin
- https://portswigger.net/web-security/cors/same-origin-policy


## Labs (2026-10-18 — per-lab scenarios & solutions), 3 lab)

- **CORS vulnerability with basic origin reflection** (`lab-basic-origin-reflection-attack`)
  - Solution • Check intercept is off, then use the browser to log in and access your account page. • Review the history and observe that your key is retrieved via an AJAX request to /accountDetails , and the response contains the Access-Control-Allow-Credentials header suggesting that it may support CORS. • Send the request to Burp Repeater, and resubmit it with the added header: . Origin: https://example.com • Observe that the origin is reflected in the Access-Control-Allow-Origin header. • In the browser, go to the exploit server and enter the following HTML, replacing YOUR-LAB-ID with your uni
- **CORS vulnerability with trusted null origin** (`lab-null-origin-whitelisted-attack`)
  - Solution • Check intercept is off, then use Burp's browser to log in to your account. Click "My account". • Review the history and observe that your key is retrieved via an AJAX request to /accountDetails , and the response contains the Access-Control-Allow-Credentials header suggesting that it may support CORS. • Send the request to Burp Repeater, and resubmit it with the added header Origin: null. • Observe that the "null" origin is reflected in the Access-Control-Allow-Origin header. • In the browser, go to the exploit server and enter the following HTML, replacing YOUR-LAB-ID with the URL 
- **CORS vulnerability with trusted insecure protocols** (`lab-breaking-https-attack`)
  - Hint If you could man-in-the-middle attack (MITM) the victim, you could use a MITM attack to hijack a connection to an insecure subdomain, and inject malicious JavaScript to exploit the CORS configuration. Unfortunately in the lab environment, you can't MITM the victim, so you'll need to find an alternative way of injecting JavaScript into the subdomain. .
