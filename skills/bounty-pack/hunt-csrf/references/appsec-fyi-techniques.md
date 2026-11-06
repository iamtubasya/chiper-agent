<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/csrf.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Attack Vectors

Notable Techniques and Attack Vectors
CSRF exploits manifest in various forms, often differing based on the HTTP method used and the application's specific defenses (or lack thereof).

GET-Based CSRF
This is often the simplest to execute, as an attacker can embed a malicious URL directly within an ` tag, 
• , ` tag, or simply send it as a clickable link. When the victim's browser attempts to load the resource or follow the link, it issues a GET request, which, if state-changing and unprotected, will be processed by the server .

For example, a vulnerability allowing password changes via a GET request:

<img src="http://vulnerable-website.com/change-password?newPassword=attacker_password">
RFC 2616 explicitly discourages using GET for state-changing operations due to its idempotent nature, but it remains a common vector when not strictly enforced .

POST-Based CSRF
POST requests are more commonly used for state-changing operations. While not as trivially embeddable as GET requests in simple HTML tags, attackers can still forge them. This typically involves creating an HTML form on a malicious site that automatically submits a POST request to the target application. This can be triggered by JavaScript or a user interaction disguised as something else .

<body onload="document.forms.submit()">
<form action="https://target.com/transfer" method="POST"> <input type="hidden" name="toAccount" value="attacker_account" /> <input type="hidden" name="amount" value="10000" /> </form> </body>

JSON-Based CSRF
Modern applications frequently use JSON for data exchange, often via AJAX or fetch requests. Exploiting JSON endpoints can be more complex due to the Same-Origin Policy (SOP) and Cross-Origin Resource Sharing (CORS) restrictions. However, attackers can bypass these by:

• Manipulating Content-Type: If the application accepts text/plain or application/x-www-form-urlencoded with a JSON body, or if it parses text/plain as JSON, a malicious form can be used .

• Exploiting CORS Misconfigurations: Overly permissive CORS policies, especially those allowing credentials (Access-Control-Allow-Credentials: true) and dynamically setting Access-Control-Allow-Origin, can enable cross-origin fetch or XMLHttpRequest calls to JSON endpoints .

An example of exploiting text/plain with a JSON structure:

<form action="https://target.com/api/update" method="POST" enctype="text/plain">
<input name='{"user_id":123, "action":"delete_account"}' value="" /> </form> <script>document.forms.submit();</script>

Referrer Header Bypass
Some applications use the Referer header to validate the origin of a request. However, this is often an unreliable defense because the Referer header can be absent, spoofed, or its validation logic might be weak (e.g., subdomain checks) .

A particularly interesting bypass leverages the strict-origin-when-cross-origin referrer policy. If an attacker can host a resource (like a CSS file) on the target domain, and that resource makes a request back to the target domain, the Referer header will be the target domain's origin, satisfying a referrer check even though the initial request came from the attacker's site .

Method Override Bypass
Some frameworks or applications allow HTTP methods to be overridden (e.g., using _method=PUT in a POST request). If CSRF protection is only applied to the primary method (e.g., POST) and not the overridden method, an attacker can potentially bypass it. This can be combined with SameSite=Lax bypasses, as a GET request with a method override might trigger state changes .

SameSite Cookie Bypass
Modern browsers' SameSite cookie attribute (Strict, Lax, None) significantly mitigates CSRF. However, bypasses exist:

• SameSite=Lax Exploitation: Lax allows cookies to be sent with top-level GET requests. Attackers can exploit this if a state-changing action can be triggered via GET, or if the application allows method overriding where a GET can become a POST .

• SameSite=None and Secure: If cookies are set with SameSite=None; Secure, they are sent with all cross-site requests. This is often seen in OAuth flows or scenarios requiring cross-origin resource access .

• Cookie Refresh/Replay: Some implementations might allow re-authentication flows or cookie refreshes that can be exploited to bypass SameSite=Lax limitations, especially if combined with browser popup behaviors .

CSRF Token Validation Bypass
Even with CSRF tokens, vulnerabilities can arise:

• Missing Validation: The application might fail to validate tokens for certain requests or methods .

• Predictable Tokens: If tokens are not truly random or are tied to predictable values, attackers might guess them .

• Token Reuse: If tokens are not properly regenerated per session or request, or if they are tied to a global pool rather than a specific user session, they can be reused .

• Token Omission: In some cases, simply removing the token parameter from a request, rather than just its value, bypasses validation if the server only checks for parameter presence .