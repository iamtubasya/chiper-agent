# PortSwigger WSA — Access Control
Source: https://portswigger.net/web-security/access-control

## Technique headings
- Access control
- Labs
- What is access control?
- Read more
- Vertical access controls
- Horizontal access controls
- Context-dependent access controls
- Examples of broken access controls
- Vertical privilege escalation
- Unprotected functionality
- Parameter-based access control methods
- Broken access control resulting from platform misconfiguration
- Broken access control resulting from URL-matching discrepancies
- Horizontal privilege escalation
- Note
- Horizontal to vertical privilege escalation
- Insecure direct object references
- Access control vulnerabilities in multi-step processes
- Referer-based access control
- Location-based access control
- How to prevent access control vulnerabilities
- Find access control vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/access-control/idor
- https://portswigger.net/web-security/access-control/security-models


## Labs (2026-10-18 — per-lab scenarios & solutions), 13 lab)

- **Insecure direct object references** (`lab-insecure-direct-object-references`)
  - Select the Live chat tab. Send a message and then select View transcript . Review the URL and observe that the transcripts are text files assigned a filename containing an incrementing number. Change the filename to 1.txt and review the text. Notice a password within the chat transcript. Return to the main lab page and log in using the stolen credentials.
- **Method-based access control can be circumvented** (`lab-method-based-access-control-can-be-circumvented`)
  - Log in using the admin credentials. Browse to the admin panel, promote carlos , and send the HTTP request to Burp Repeater. Open a private/incognito browser window, and log in with the non-admin credentials. Attempt to re-promote carlos with the non-admin user by copying that user's session cookie into the existing Burp Repeater request, and observe that the response says "Unauthorized". Change the method from POST t
- **Multi-step process with no access control on one step** (`lab-multi-step-process-with-no-access-control-on-one-step`)
  - Log in using the admin credentials. Browse to the admin panel, promote carlos , and send the confirmation HTTP request to Burp Repeater. Open a private/incognito browser window, and log in with the non-admin credentials. Copy the non-admin user's session cookie into the existing Repeater request, change the username to yours, and replay it.
- **Referer-based access control** (`lab-referer-based-access-control`)
  - Log in using the admin credentials. Browse to the admin panel, promote carlos , and send the HTTP request to Burp Repeater. Open a private/incognito browser window, and log in with the non-admin credentials. Browse to /admin-roles?username=carlos&action=upgrade and observe that the request is treated as unauthorized due to the absent Referer header. Copy the non-admin user's session cookie into the existing Burp Repe
- **Unprotected admin functionality** (`lab-unprotected-admin-functionality`)
  - Go to the lab and view robots.txt by appending /robots.txt to the lab URL. Notice that the Disallow line discloses the path to the admin panel. In the URL bar, replace /robots.txt with /administrator-panel to load the admin panel. Delete carlos .
- **Unprotected admin functionality with unpredictable URL** (`lab-unprotected-admin-functionality-with-unpredictable-url`)
  - Review the lab home page's source using Burp Suite or your web browser's developer tools. Observe that it contains some JavaScript that discloses the URL of the admin panel. Load the admin panel and delete carlos .
- **URL-based access control can be circumvented** (`lab-url-based-access-control-can-be-circumvented`)
  - Try to load /admin and observe that you get blocked. Notice that the response is very plain, suggesting it may originate from a front-end system. Send the request to Burp Repeater. Change the URL in the request line to / and add the HTTP header X-Original-URL: /invalid . Observe that the application returns a "not found" response. This indicates that the back-end system is processing the URL from the X-Original-URL h
- **User ID controlled by request parameter** (`lab-user-id-controlled-by-request-parameter`)
  - Log in using the supplied credentials and go to your account page. Note that the URL contains your username in the "id" parameter. Send the request to Burp Repeater. Change the "id" parameter to carlos . Retrieve and submit the API key for carlos .
- **User ID controlled by request parameter with data leakage in redirect** (`lab-user-id-controlled-by-request-parameter-with-data-leakage-in-redirect`)
  - Log in using the supplied credentials and access your account page. Send the request to Burp Repeater. Change the "id" parameter to carlos . Observe that although the response is now redirecting you to the home page, it has a body containing the API key belonging to carlos . Submit the API key.
- **User ID controlled by request parameter with password disclosure** (`lab-user-id-controlled-by-request-parameter-with-password-disclosure`)
  - Log in using the supplied credentials and access the user account page. Change the "id" parameter in the URL to administrator . View the response in Burp and observe that it contains the administrator's password. Log in to the administrator account and delete carlos .
- **User ID controlled by request parameter, with unpredictable user IDs** (`lab-user-id-controlled-by-request-parameter-with-unpredictable-user-ids`)
  - Find a blog post by carlos . Click on carlos and observe that the URL contains his user ID. Make a note of this ID. Log in using the supplied credentials and access your account page. Change the "id" parameter to the saved user ID. Retrieve and submit the API key.
- **User role can be modified in user profile** (`lab-user-role-can-be-modified-in-user-profile`)
  - Log in using the supplied credentials and access your account page. Use the provided feature to update the email address associated with your account. Observe that the response contains your role ID. Send the email submission request to Burp Repeater, add "roleid":2 into the JSON in the request body, and resend it. Observe that the response shows your roleid has changed to 2. Browse to /admin and delete carlos .
- **User role controlled by request parameter** (`lab-user-role-controlled-by-request-parameter`)
  - Browse to /admin and observe that you can't access the admin panel. Browse to the login page. In Burp Proxy, turn interception on and enable response interception. Complete and submit the login page, and forward the resulting request in Burp. Observe that the response sets the cookie Admin=false . Change it to Admin=true . Load the admin panel and delete carlos .
