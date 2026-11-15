# PortSwigger WSA — Web Cache Deception
Source: https://portswigger.net/web-security/web-cache-deception

## Technique headings
- Web cache deception
- Note
- PortSwigger research
- Web caches
- Cache keys
- Cache rules
- Constructing a web cache deception attack
- Using a cache buster
- Detecting cached responses
- Exploiting static extension cache rules
- Path mapping discrepancies
- Exploiting path mapping discrepancies
- Delimiter discrepancies
- Exploiting delimiter discrepancies
- Delimiter decoding discrepancies
- Exploiting delimiter decoding discrepancies
- Exploiting static directory cache rules
- Normalization discrepancies
- Detecting normalization by the origin server
- Detecting normalization by the cache server
- Exploiting normalization by the origin server
- Exploiting normalization by the cache server
- Exploiting file name cache rules
- Detecting normalization discrepancies
- Exploiting normalization discrepancies
- Preventing web cache deception vulnerabilities
- Find web cache deception vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/web-cache-deception/wcd-lab-delimiter-list


## Labs (2026-10-18 — per-lab scenarios & solutions), 5 lab)

- **Exploiting path mapping for web cache deception** (`lab-wcd-exploiting-path-mapping`)
  - Solution Identify a target endpoint • In Burp's browser, log in to the application using the credentials wiener:peter .. • Notice that the response contains your API key.. Identify a path mapping discrepancy • In Proxy > HTTP history , right-click the GET /my-account request and select Send to Repeater .. • Go to the Repeater tab. Add an arbitrary segment to the base path, for example change the path to /my-account/abc .. • Send the request. Notice that you still receive a response containing your API key. This indicates that the origin server abstracts the URL path to /my-account .. • Add a s
- **Exploiting path delimiters for web cache deception** (`lab-wcd-exploiting-path-delimiters`)
  - Solution Identify a target endpoint • In Burp's browser, log in to the application using the credentials wiener:peter .. • Notice that the response contains your API key.. Identify path delimiters used by the origin server • In Proxy > HTTP history , right-click the GET /my-account request and select Send to Repeater .. • Go to the Repeater tab. Add an arbitrary segment to the path. For example, change the path to /my-account/abc .. • Send the request. Notice the 404 Not Found response with no evidence of caching. This indicates that the origin server doesn't abstract the path to /my-account .
- **Exploiting origin server normalization for web cache deception** (`lab-wcd-exploiting-origin-server-normalization`)
  - Solution Identify a target endpoint • In Burp's browser, log in to the application using the credentials wiener:peter .. • Notice that the response contains your API key.. Investigate path delimiter discrepancies • In Proxy > HTTP history , right-click the GET /my-account request and select Send to Repeater .. • Go to the Repeater tab. Change the path to /my-account/abc , then send the request. Notice the 404 Not Found response. This indicates that the origin server doesn't abstract the path to /my-account .. • Change the path to /my-accountabc , then send the request. Notice that this returns
- **Exploiting cache server normalization for web cache deception** (`lab-wcd-exploiting-cache-server-normalization`)
  - Solution Identify a target endpoint • In Burp's browser, log in to the application using the credentials wiener:peter .. • Notice that the response contains your API key.. Investigate path delimiters used by the origin server • In Proxy > HTTP history , right-click the GET /my-account request and select Send to Repeater .. • Change the URL path to /my-account/abc , then send the request. Notice the 404 Not Found response. This indicates that the origin server doesn't abstract the path to /my-account .. • Change the path to /my-accountabc , then send the request. Notice that this returns a 404 
- **Exploiting exact-match cache rules for web cache deception** (`lab-wcd-exploiting-exact-match-cache-rules`)
  - Solution Identify a target endpoint • In Burp's browser, log in to the application using the credentials wiener:peter , then change your email address.. • In Proxy > HTTP history , notice that the email change submission form in the /my-account response contains a CSRF token as a hidden parameter.. Investigate path delimiter discrepancies • Right-click the GET /my-account request and select Send to Repeater .. • In Repeater , change the URL path to /my-account/abc , then send the request. Notice the 404 Not Found response. This indicates that the origin server doesn't abstract the path to /my-
