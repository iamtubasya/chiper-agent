<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/jwt.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Attack Vectors

Notable Techniques and Attack Vectors
JWT vulnerabilities exploit weaknesses in implementation, cryptographic choices, and trust assumptions. The most prevalent attack vectors target signature verification and algorithm handling.

1. Signature Verification Failures
This is arguably the most common and impactful category of JWT vulnerabilities. It occurs when the server fails to properly validate the signature on an incoming token.

• Using decode() instead of verify(): Many JWT libraries offer distinct functions for merely decoding the token's contents and for verifying the signature before decoding. Developers may mistakenly use a decoding-only function, completely bypassing signature validation. 

• The "None" Algorithm (alg: "none"): The JWT standard permits an algorithm value of "none", indicating an unsigned token. Vulnerable implementations that don't explicitly reject this algorithm, or have case-insensitive checks that can be bypassed (e.g., None, NONE), will accept tokens with no signature. Attackers can simply remove the signature part and set the algorithm to "none" to forge tokens. 

• Null Signature/Signature Stripping: Similar to the "none" algorithm, some implementations might accept tokens with an empty signature, even if the alg header is not explicitly set to "none". This can happen if the verification logic doesn't correctly handle a missing or empty signature as an error. 

# Example of crafting a 'none' algorithm token (manually or with a tool) # Original token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.signature_here # Modified token: eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFkbWluIn0. 

2. Algorithm Confusion Attacks
These attacks exploit the server's trust in the alg parameter specified in the JWT header. Instead of enforcing a specific, expected algorithm server-side, the vulnerable server uses the algorithm provided in the token header to select the verification method.

• RS256 to HS256 Confusion: This is the most common algorithm confusion attack. An attacker crafts a token with the alg header set to HS256 (symmetric HMAC) instead of RS256 (asymmetric RSA). The attacker then signs this token using the server's public RSA key as the HMAC secret. Since the public key is often publicly accessible (e.g., via a JWKS endpoint), the attacker can generate a valid signature that the server, trusting the HS256 header, will verify using the public key as an HMAC secret. 

• ECDSA to HS256 Confusion: Similar to the RS256 to HS256 attack, but applicable when the server uses ECDSA for signing. The attacker sets the alg to HS256 and uses the server's public ECDSA key as the HMAC secret. 

• Unknown Algorithm Bypass: Some JWT libraries might not properly validate the alg value. If an attacker provides an unrecognized algorithm string (e.g., "zzz", "banana"), the library might default to a bypass or an insecure verification mechanism, such as returning an empty signature or treating it as unsigned. 

# Example of crafting an HS256 token signed with an RSA public key # (Requires attacker to obtain the server's public key and use a tool like jwt_tool or custom script) # Original header: {"alg": "RS256", "typ": "JWT", "kid": "some-key-id"} # Modified header: {"alg": "HS256", "typ": "JWT", "kid": "some-key-id"} # Payload: {"sub": "attacker", "admin": true} # Signature: Generated using HMAC-SHA256 with the server's public key as the secret. 

3. Weak Secrets and Key Management
For symmetric algorithms like HS256, HS384, and HS512, the security relies entirely on the secrecy and strength of the shared secret key. Weak or compromised keys are a direct path to token forgery.

• Guessable Secrets: Developers often use predictable secrets like "secret", "password123", "changeme", or application-specific names. These are easily brute-forced or dictionary-attacked offline. 

• Hardcoded Secrets: Secrets embedded directly in client-side code (e.g., JavaScript) or committed to version control systems are highly vulnerable. 

• Key Rotation Neglect: Failure to regularly rotate signing keys leaves tokens vulnerable for extended periods if a key is compromised. 

• Insufficient Entropy: Using keys that are too short or lack sufficient randomness drastically weakens cryptographic strength. 

# Example using jwt_tool to crack an HS256 token with a weak secret # python3 jwt_tool.py <JWT_TOKEN> -C -d /path/to/wordlist.txt 

4. Header Parameter Injection and Manipulation
Certain JWT header parameters, if not properly validated by the server, can be manipulated to achieve various attacks.

• kid (Key ID) Injection: The kid parameter specifies which key to use for signature verification. If the server uses this value to construct file paths or database queries without sanitization, it can lead to path traversal or SQL injection vulnerabilities. Attackers can point kid to sensitive files (e.g., /dev/null, system configuration files) and use their contents as a signing key, or even achieve command injection. 

• jku (JWK Set URL) and x5u (X.509 URL) Injection: These parameters specify URLs from which to fetch the public key or certificate for verification. If not strictly validated against an allowlist, an attacker can host their own JWKS file at a controlled URL, containing their own public key. The server then fetches this malicious key and verifies a token signed by the attacker's private key. 

• jwk (JSON Web Key) Injection: This parameter allows embedding the public key directly within the JWT header. Vulnerable implementations might trust this embedded key for verification, allowing an attacker to embed their own key and sign a forged token. 

# Example of kid path traversal to /dev/null # Original header: {"alg": "HS256", "typ": "JWT", "kid": "some_actual_key_id"} # Modified header: {"alg": "HS256", "typ": "JWT", "kid": "../../../../../../../proc/self/getPrototypeOf"} 

5. Claim Tampering and Validation Issues
Even if the signature is valid, the claims within the payload must be correctly validated by the server.

• Missing or Incorrect Claim Validation: Critical registered claims like exp (expiration), nbf (not before), iss (issuer), and aud (audience) must be validated.

• Expiration Bypass: If exp is not checked, a valid token can be used indefinitely. 

• Issuer (iss) Validation Failure: If the iss claim is not validated against a trusted issuer, tokens from other, potentially malicious, issuers might be accepted. 

• Audience (aud) Validation Failure: If the aud claim is not validated, tokens intended for one service might be replayed against another, potentially granting unintended access. 

• Partial Claim Matching: Vulnerabilities in validation logic might allow partial string matches for claims like iss or aud, enabling spoofing. 

• Sensitive Data in Payload: Storing sensitive information (passwords, PII, credit card numbers) directly in the JWT payload is a critical security flaw, as JWTs are typically only encoded, not encrypted. Anyone intercepting or obtaining the token can read this data. 

• Token Replay: Without proper mechanisms like short expiration times, jti (JWT ID) claims, or checking nbf, attackers can reuse captured tokens. 

6. Client-Side Storage Vulnerabilities
How JWTs are stored on the client-side significantly impacts security, particularly against Cross-Site Scripting (XSS) attacks.

• Storing JWTs in localStorage/sessionStorage: These browser storage mechanisms are accessible via JavaScript, making them vulnerable to XSS attacks. If an XSS vulnerability exists, attackers can steal tokens stored here. 

• Cookie Storage without HttpOnly and Secure flags: While cookies are generally preferred, if not properly configured with HttpOnly (to prevent JavaScript access) and Secure (to ensure transmission over HTTPS), they can still be vulnerable. 

7. Other Vulnerabilities

• Key Injection via kid: Beyond path traversal, if the kid value is used in database queries, it can be vulnerable to SQL injection. 

• JWE Processing Issues: When JWTs are encrypted (JWE), vulnerabilities can arise if the inner signature is not validated after decryption, allowing unsigned inner JWTs to be accepted. 

• Weak Encryption/Key Lengths: For algorithms that involve encryption, using keys that are too short or lack sufficient entropy can lead to cryptographic breaks. 

• Token Limit Exploitation (e.g., CSS-based exfiltration): In scenarios where tokens are excessively large and passed in contexts like CSS selectors, sophisticated techniques might be employed to exfiltrate them in smaller pieces. 