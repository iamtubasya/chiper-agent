# PortSwigger WSA — JWT Attacks
Source: https://portswigger.net/web-security/jwt

## Technique headings
- JWT attacks
- Labs
- What are JWTs?
- JWT format
- JWT signature
- JWT vs JWS vs JWE
- Note
- What are JWT attacks?
- What is the impact of JWT attacks?
- How do vulnerabilities to JWT attacks arise?
- How to work with JWTs in Burp Suite
- Read more
- Exploiting flawed JWT signature verification
- Accepting arbitrary signatures
- Accepting tokens with no signature
- Brute-forcing secret keys
- Brute-forcing secret keys using hashcat
- JWT header parameter injections
- Injecting self-signed JWTs via the jwk parameter
- Public and private keys
- Injecting self-signed JWTs via the jku parameter
- JWK Set
- Injecting self-signed JWTs via the kid parameter
- Other interesting JWT header parameters
- JWT algorithm confusion
- How to prevent JWT attacks
- Additional best practice for JWT handling
- Find JWT vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/jwt/algorithm-confusion


## Labs (2026-10-18 — per-lab scenarios & solutions), 1 lab)

- **JWT authentication bypass via unverified signature** (`lab-jwt-authentication-bypass-via-unverified-signature`)
  - In the lab, log in to your own account. In Burp, go to the Proxy > HTTP history tab and look at the post-login GET /my-account request. Observe that your session cookie is a JWT. Double-click the payload part of the token to view its decoded JSON form in the Inspector panel. Notice that the sub claim contains your username. Send this request to Burp Repeater. In Burp Repeater, change the path to /admin and send the r
- **JWT authentication bypass via flawed signature verification** (`lab-jwt-authentication-bypass-via-flawed-signature-verification`)
  - Solution • In the lab, log in to your own account. . • In Burp, go to the Proxy > HTTP history tab and look at the post-login GET /my-account request. Observe that your session cookie is a JWT. . • Double-click the payload part of the token to view its decoded JSON form in the Inspector panel. Notice that the sub claim contains your username. Send this request to Burp Repeater. . • In Burp Repeater, change the path to /admin and send the request. Observe that the admin panel is only accessible when logged in as the administrator user. . • Select the payload of the JWT again. In the Inspector p
- **JWT authentication bypass via weak signing key** (`lab-jwt-authentication-bypass-via-weak-signing-key`)
  - Solution Part 1 - Brute-force the secret key • In Burp, load the JWT Editor extension from the BApp store. . • In the lab, log in to your own account and send the post-login GET /my-account request to Burp Repeater. . • In Burp Repeater, change the path to /admin and send the request. Observe that the admin panel is only accessible when logged in as the administrator user. . • Copy the JWT and brute-force the secret. You can do this using hashcat as follows: . hashcat -a 0 -m 16500 <YOUR-JWT> /path/to/jwt.secrets.list If you're using hashcat, this outputs the JWT, followed by the secret. If ev
- **JWT authentication bypass via jwk header injection** (`lab-jwt-authentication-bypass-via-jwk-header-injection`)
  - Solution • In Burp, load the JWT Editor extension from the BApp store. . • In the lab, log in to your own account and send the post-login GET /my-account request to Burp Repeater. . • In Burp Repeater, change the path to /admin and send the request. Observe that the admin panel is only accessible when logged in as the administrator user. . • Go to the JWT Editor Keys tab in Burp's main tab bar. . • Click New RSA Key . . • In the dialog, click Generate to automatically generate a new key pair, then click OK to save the key. Note that you don't need to select a key size as this will automaticall
- **JWT authentication bypass via jku header injection** (`lab-jwt-authentication-bypass-via-jku-header-injection`)
  - Solution Part 1 - Upload a malicious JWK Set • In Burp, load the JWT Editor extension from the BApp store. . • In the lab, log in to your own account and send the post-login GET /my-account request to Burp Repeater. . • In Burp Repeater, change the path to /admin and send the request. Observe that the admin panel is only accessible when logged in as the administrator user. . • Go to the JWT Editor Keys tab in Burp's main tab bar. . • Click New RSA Key . . • In the dialog, click Generate to automatically generate a new key pair, then click OK to save the key. Note that you don't need to select 
- **JWT authentication bypass via kid header path traversal** (`lab-jwt-authentication-bypass-via-kid-header-path-traversal`)
  - Solution Note In this solution, we'll point the kid parameter to the standard file /dev/null . In practice, you can point the kid parameter to any file with predictable contents. . . Generate a suitable signing key • In Burp, load the JWT Editor extension from the BApp store. . • In the lab, log in to your own account and send the post-login GET /my-account request to Burp Repeater. . • In Burp Repeater, change the path to /admin and send the request. Observe that the admin panel is only accessible when logged in as the administrator user. . • Go to the JWT Editor Keys tab in Burp's main tab b
