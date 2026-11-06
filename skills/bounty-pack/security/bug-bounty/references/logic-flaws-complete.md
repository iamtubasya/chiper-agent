# Business Logic Vulnerabilities & Race Conditions — Complete Reference

> Based on PortSwigger Web Security Academy, PortSwigger Research (Black Hat USA 2023), OWASP, Strobes, CHS (2026-08)
> Standalone deep-dive — separate from other skill files

---

## 1. What Are Business Logic Vulnerabilities?

Flaws in the **design and implementation** of an application that allow an attacker to elicit **unintended behavior** by manipulating legitimate functionality.

Key distinction: **No scanner will find these bugs.** There's no malformed payload or injection signature — every request is well-formed, authenticated, and authorized. The code does what the developer told it to do, but what the developer told it to do doesn't match what the business actually needs.

> *"The bug isn't in any single function. It's in the gap between what the developer assumed and what a user can actually do."* — OWASP

---

## 2. Why They're Different from Technical Vulns

| Technical Vuln (SQLi, XSS) | Business Logic Flaw |
|---|---|
| Malformed input triggers it | Perfectly valid input triggers it |
| Scanner can detect signature | No signature to match |
| Input validation helps | Input is syntactically perfect |
| Code-level fix | Process/design-level fix |
| Exploits technical gap | Exploits behavioral assumption |

---

## 3. Types of Business Logic Flaws

### 3.1 Excessive Trust in Client-Side Controls

**Pattern:** The application relies on client-side validation (JavaScript, hidden fields, cookies) instead of re-validating on the server.

**Attack vectors:**
- Modifying hidden form fields (price, quantity, user ID, role)
- Tampering with cookies or localStorage values
- Intercepting and modifying requests via Burp Proxy
- Disabling client-side JavaScript validation
- Manipulating API request body directly (bypassing UI entirely)

**Examples:**
- Changing `price=99999` to `price=1` in checkout POST
- Modifying `discount=0` to `discount=50` in coupon application
- Changing `user_role=user` to `user_role=admin` in profile update
- Setting `verified=true` in registration response

**Server-side fix:** Always re-derive security-relevant values from trusted data:
```
Client sends:     Product ID + Quantity
Server computes:  Price from database, line total, tax, shipping
```

### 3.2 Failing to Handle Unconventional Input

**Pattern:** The application only handles expected input and crashes or misbehaves on edge cases.

**Attack vectors:**
- Extremely large quantities (integer overflow)
- Negative quantities (returns money instead of ordering)
- Zero quantities
- Special characters in names/addresses
- Unicode/emoji in form fields
- NULL/empty string in required fields
- Maximum integer values (2147483647)

**Examples:**
- `quantity=-1` → store credits you the item price
- `quantity=999999999999` → integer overflow gives negative balance
- Empty coupon code → applies default discount
- `price=0.00000001` → rounding error exploit

### 3.3 Flawed Assumptions About User Behavior

**Pattern:** Developers assume users will follow the UI's prescribed workflow. Attackers don't.

**Common assumptions that fail:**
1. "Users will complete steps in order" → Step skipping
2. "Users won't revisit completed steps" → Replay attacks
3. "Users won't submit the same request twice" → Duplicate processing
4. "Users won't access endpoints they're not supposed to" → Direct endpoint access
5. "The UI is the only way to interact" → API manipulation
6. "Rate limiting on auth is enough" → Feature-specific abuse

### 3.4 Domain-Specific Flaws

Logic flaws unique to the business domain:
- E-commerce: price manipulation, coupon abuse, refund exploits
- Banking: transfer amount manipulation, balance check race conditions
- SaaS: plan downgrade/upgrade exploits, feature gate bypass
- Gaming: item duplication, currency exploits
- Social: self-referral, multi-accounting, content moderation bypass

### 3.5 Providing an Encryption Oracle

**Pattern:** The application encrypts user-controlled input and returns it, allowing an attacker to:
- Understand the encryption scheme
- Craft encrypted values for arbitrary inputs
- Exploit format-oracle attacks

### 3.6 Email Address Parser Discrepancies

**Pattern:** Different parts of the application parse email addresses differently, allowing:
- Duplicate account creation via email variations
- Verification bypass via address spoofing
- Invitation hijacking via email mangling

---

## 4. Race Conditions — The Hidden Multi-Step Monster

> *"With race conditions, everything is multi-step."* — James Kettle, PortSwigger Research

### 4.1 What Are Race Conditions?

Race conditions occur when websites process requests **concurrently without adequate safeguards**. Multiple threads interact with the same data simultaneously, causing unintended behavior.

The **race window** is the period during which a collision is possible — often just ~1ms.

### 4.2 Limit Overrun (Classic TOCTOU)

**Pattern:** Check-then-act where the check and act aren't atomic.

**Classic example — Discount code reuse:**
1. Request A: Check if code `TOP10` used → No → Apply discount
2. Request B: Check if code `TOP10` used → No (DB not yet updated) → Apply discount
3. Both apply the same discount code

**Common limit-overrun scenarios:**
- Redeeming a gift card multiple times
- Applying a single discount code repeatedly
- Rating a product multiple times
- Withdrawing/transferring cash in excess of balance
- Reusing a single CAPTCHA solution
- Bypassing brute-force rate limits
- Creating multiple accounts for one-per-account bonuses

### 4.3 Object Masking (New Class — Black Hat 2023)

**Pattern:** Two concurrent operations on the same object create a hidden state where the object appears to be in one state while actually being in another.

**GitLab example:**
- Send 6 identical invitation requests simultaneously
- Result: 1 success response, but 2 emails sent
- The invitation list only shows ONE invitation per email
- Create dummy low-privilege invitation → race → gets replaced by admin invitation
- Impact: Privilege escalation via invitation hijacking

**Detection:** Send multiple identical requests and check if response count ≠ side-effect count (email sent, DB state, etc.)

### 4.4 Multi-Endpoint Collisions

**Pattern:** Two different endpoints operate on the same resource, and their concurrent execution creates an exploitable state.

**E-commerce example:**
1. Start purchase flow, pay for order
2. Simultaneously add extra item to basket
3. Order confirmation loads — extra item included for free

**GitLab email verification example:**
1. Request A: Change email to `attacker@evil.com`
2. Request B: Confirm email at `victim@target.com`
3. Race window: confirmation token arrives at attacker's email for victim's address
4. Attacker verifies victim's email address

**Key insight:** The two endpoints need **different processing times** to line up the race window. Use delay (e.g., 90ms) if needed, or abuse server rate-limits to create server-side delays.

### 4.5 Single-Endpoint Collisions

**Pattern:** A single complex endpoint has enough internal complexity to create exploitable sub-states.

**Devise/Rails email change vulnerability:**
1. `send_devise_notification` sends email to `unconfirmed_email` (from variable)
2. Email body is generated from database (separate thread reads DB)
3. Race window: Another thread can update `unconfirmed_email` in DB between step 1 and 2
4. Email sent to address A, but body contains token for address B

**Impact:** Verify arbitrary email addresses, hijack invitations, SSO takeover

### 4.6 Deferred Collisions

**Pattern:** The collision doesn't happen immediately — the application processes data in batches asynchronously.

**Detection:**
- Send two conflicting requests with 20-minute delay
- Monitor for anomalous behavior hours later
- Check for inconsistent emails/states that appear non-deterministically
- **Spotting anomalies is THE single most important skill for finding race conditions**

### 4.7 Partial Construction Attacks

**Pattern:** An object is created in multiple steps, creating an insecure middle state.

**Example — Registration:**
1. Step 1: Create user in DB (password is NULL)
2. Step 2: Set password hash
3. Race window: Account exists with NULL password

**Exploit:** Submit login with a value that produces the same hash as NULL (null JSON, empty array in PHP)

### 4.8 The Single-Packet Attack

**Problem:** Network jitter makes it hard to get requests to arrive close together.

**Solution:** Use HTTP/2 to send 20-30 requests in a single TCP packet:
1. Pre-send headers and most body data (withhold final byte)
2. Wait 100ms for frames to be sent
3. Send withheld final frames — TCP batches them into one packet
4. All 20-30 requests arrive at server within ~1ms

**Benchmark:**
| Technique | Median Spread | Std Deviation |
|---|---|---|
| Last-byte sync | 4ms | 3ms |
| Single-packet attack | 1ms | 0.3ms |

**Tools:** Burp Suite Turbo Intruder (`single-packet-attack.py` template), Burp Repeater "Send group in parallel"

---

## 5. Payment Tampering

### 5.1 Price Manipulation

**Attack patterns:**
- Modify `price` field in checkout request
- Change `subtotal` or `total` in POST body
- Modify shipping cost to negative
- Change quantity after price calculation
- Tamper with `discount_amount` field
- Modify currency code (cheaper in different currency)

### 5.2 Negative Quantity Exploit

```
Normal: quantity=1, price=$50 → total=$50
Attack: quantity=-1, price=$50 → total=-$50 (store credits you $50)
```

### 5.3 Coupon Stacking

**Pattern:** Multiple promotions meant to be used alone get combined:
- Percentage discount + fixed discount + free shipping
- First-time buyer + referral + seasonal promo
- Each coupon is valid alone, but stacking pushes price below cost

### 5.4 Gift Card / Promo Code Race

**Pattern:** Apply the same code multiple times before the balance updates:
1. Send 50 concurrent "apply gift card" requests
2. Code is checked and approved in each request
3. Balance is only deducted once (or not at all if batched)
4. Gift card applied 50 times

### 5.5 Free Trial Reset

**Pattern:** Cancel and re-sign up to stay on free tier forever:
- Track trial by email → create new emails
- Track by IP → use VPN/proxy
- Track by payment method → use virtual cards
- Track by device fingerprint → clear cookies/browser

---

## 6. Workflow Bypass Techniques

### 6.1 Step Skipping

**Normal flow:** Register → Verify Email → Choose Plan → Payment → Access
**Attack flow:** Register → [Direct URL to /access] → Full platform access

**How to detect:**
- Map the complete workflow (all steps)
- Access each step's endpoint directly
- Check if server enforces step ordering
- Try accessing final steps without completing prerequisites

### 6.2 Step Replay

**Pattern:** Re-submit completed steps to trigger side-effects again:
- Apply signup bonus multiple times
- Re-trigger welcome email (spam)
- Re-apply referral credit
- Re-submit verification to get new codes

### 6.3 Step Manipulation

**Pattern:** Modify data in already-completed steps:
- Complete checkout → go back → change quantity → resubmit
- Complete registration → go back → change role → resubmit
- Complete payment → replay request with modified amount

### 6.4 Direct Endpoint Access

**Pattern:** Skip the UI entirely and hit API endpoints directly:
- UI hides the "admin" button, but `/api/admin/endpoint` exists
- UI validates form fields, but API accepts raw JSON
- UI enforces workflow, but API endpoints are independent

---

## 7. OWASP Defense Patterns (What to Look For When Bypassing)

### 7.1 Server-Side Re-derivation (Client Trust)

**Secure pattern:**
```
Server computes: price, tax, shipping, total, discount amount
Server validates: coupon code exists and is valid
Server rejects: any client-supplied price/discount/total
```

**Vulnerable pattern:**
```
Server trusts: price from request body
Server trusts: discount_amount from request body
Server trusts: total from request body
```

### 7.2 State Machine Enforcement

**Secure pattern:**
```
Step 1: Create record with state "awaiting_email_verification"
Step 2: Verify email → state becomes "awaiting_payment"
Step 3: Payment → state becomes "active"
Each step checks current state before proceeding
```

**Vulnerable pattern:**
```
No server-side state tracking
Steps are independent endpoints
UI guides the flow, but nothing enforces it
```

### 7.3 Race Condition Prevention

**Secure patterns:**
- `SELECT ... FOR UPDATE` (row-level locking)
- `UPDATE ... WHERE balance >= amount` (conditional update)
- SERIALIZABLE transaction isolation
- Idempotency keys for non-idempotent operations
- Unique constraints: `UNIQUE(user_id, bonus_type)`

**Vulnerable patterns:**
- Check balance → separate debit (non-atomic)
- Read-modify-write without locks
- No idempotency keys on payment endpoints
- Batch updates without proper locking

### 7.4 Abuse-Friendly Feature Controls

**Features that need extra protection:**
- Referral bonuses (self-referral, multi-accounting)
- Promo codes (stacking, reuse)
- Signup credits (trial reset, multi-accounting)
- Password reset (enumeration, abuse)
- Free trials (reset, multi-accounting)
- Coupon systems (stacking, race conditions)

---

## 8. Bug Bounty Hunting Methodology

### 8.1 Identify Business Logic Entry Points

```
1. Map all features that handle value:
   - Payment flows
   - Account creation/management
   - Coupon/discount systems
   - Referral programs
   - File upload/download
   - Admin panels
   - API endpoints

2. Identify security-relevant parameters:
   - Price, quantity, discount
   - User ID, role, permissions
   - Order status, payment status
   - Verification status
   - Account balance/credits

3. Map multi-step workflows:
   - Registration flow
   - Checkout flow
   - Password reset flow
   - Email verification flow
   - KYC/identity verification
```

### 8.2 Test for Client-Side Trust

```python
# Intercept and modify:
1. Price/total in checkout request
2. Quantity in order request
3. Discount amount in coupon application
4. User role in profile update
5. Verification status in any request
6. Any hidden field value
7. Any value computed by JavaScript
```

### 8.3 Test for Workflow Bypass

```
1. Complete workflow normally, note all URLs
2. Access final step URL directly without prerequisites
3. Access intermediate steps out of order
4. Re-submit completed steps
5. Modify data in completed steps and re-submit
6. Check if state is enforced server-side
```

### 8.4 Test for Race Conditions

```
1. Identify check-then-act patterns:
   - Check balance → debit
   - Check coupon validity → apply
   - Check item availability → add to cart
   - Check email uniqueness → register

2. Send concurrent requests:
   - Burp Intruder: set concurrency to 10-20
   - Turbo Intruder: single-packet attack
   - Burp Repeater: "Send group in parallel"
   - curl + GNU parallel

3. Look for:
   - Duplicate side effects (2 emails, 2 deductions)
   - Inconsistent state (different values in different views)
   - Error messages revealing race window
   - Response timing anomalies

4. Advanced:
   - Test with different sessions (PHP locks on sessionid)
   - Test with delayed requests (deferred collisions)
   - Test single endpoints with multiple parameters
   - Test object masking with duplicate requests
```

### 8.5 Test for Negative Values

```
1. quantity=-1 → credit instead of debit
2. quantity=0 → skip item but process order
3. discount=100 → free everything
4. price=-100 → store pays you
5. balance_check_result=false → bypass
6. timestamp in the past → replay old data
```

### 8.6 Test for Integer Overflow

```
1. quantity=2147483647 (max int32)
2. quantity=9999999999999
3. price=0.00000001 (precision exploit)
4. discount_percentage=999
```

---

## 9. Real-World Case Studies

### Case 1: GitLab Email Verification Race (CVE-2022-4037)

**Vulnerability:** Single-endpoint race condition in Devise email confirmation
**Impact:** Verify arbitrary email addresses, hijack project invitations, SSO takeover
**Root cause:** Email sent to variable, body generated from DB (different threads)
**Exploit:** Change email to victim's address simultaneously with confirmation request
**Severity:** High (despite GitLab classifying as Medium)
**Fix:** Devise patched to read both token and email from same source atomically

### Case 2: E-Commerce Free Item

**Vulnerability:** Multi-endpoint race — add item after payment, before confirmation
**Impact:** Get extra items for free
**Root cause:** Order total calculated before basket is finalized
**Exploit:** Pay → add item → load confirmation page

### Case 3: Gift Card Double-Spend

**Vulnerability:** Limit-overrun race on gift card redemption
**Impact:** Use gift card unlimited times
**Root cause:** Balance check and deduction not atomic
**Exploit:** Send 50 concurrent redemption requests

### Case 4: Session Handler Vulnerability

**Vulnerability:** Custom session handler with no concurrency defense
**Impact:** Account takeover, 2FA bypass, privilege escalation
**Root cause:** Session variables updated individually without locking
**Exploit:** Simultaneous login to two accounts from same session → session swap

### Case 5: Referral Self-Abuse

**Vulnerability:** Self-referral via multi-accounting
**Impact:** Unlimited referral bonuses
**Root cause:** No identity verification beyond email
**Exploit:** Create N accounts, refer yourself each time

---

## 10. Detection Checklist

### Client-Side Trust
- [ ] Modify price/total in checkout request
- [ ] Modify quantity (positive, negative, zero, overflow)
- [ ] Modify discount/coupon values
- [ ] Modify user role/permissions
- [ ] Modify hidden form fields
- [ ] Modify localStorage/sessionStorage
- [ ] Modify cookies
- [ ] Access API endpoints directly (bypass UI)

### Workflow Bypass
- [ ] Map all workflow steps
- [ ] Access final step directly
- [ ] Skip intermediate steps
- [ ] Replay completed steps
- [ ] Modify completed step data
- [ ] Check if state is enforced server-side
- [ ] Test with different sessions/users

### Race Conditions
- [ ] Identify all check-then-act patterns
- [ ] Send concurrent requests (10-20)
- [ ] Check for duplicate side effects
- [ ] Check for inconsistent state
- [ ] Test with different sessions (PHP)
- [ ] Test deferred collisions (delayed requests)
- [ ] Test single-endpoint complexity
- [ ] Test object masking (duplicate requests)

### Negative/Edge Cases
- [ ] Test negative quantities
- [ ] Test zero quantities
- [ ] Test integer overflow
- [ ] Test decimal precision
- [ ] Test maximum values
- [ ] Test empty/null values
- [ ] Test Unicode/emoji input
- [ ] Test extremely large inputs

### Payment Tampering
- [ ] Modify price field
- [ ] Modify subtotal/total
- [ ] Modify shipping cost
- [ ] Modify currency
- [ ] Modify discount amount
- [ ] Apply same coupon multiple times
- [ ] Stack multiple coupons
- [ ] Use expired coupons
- [ ] Modify gift card balance check

### Information Disclosure
- [ ] Check error messages for logic details
- [ ] Check response timing for race windows
- [ ] Check if hidden fields reveal internal state
- [ ] Check if API responses reveal more than UI

---

## 11. Report Templates

### Template 1: Price Manipulation
```
Title: [App] Price Manipulation via Client-Side Trust

Severity: High (CVSS 8.6 — Financial Impact)

Description:
The application trusts client-supplied price/total values in the checkout flow.
An attacker can modify the price parameter in the HTTP request to pay an
arbitrary amount for any product.

Reproduction Steps:
1. Add any item to cart
2. Proceed to checkout
3. Intercept the checkout POST request with Burp Suite
4. Modify the [price/total/discount] parameter from [original] to [modified]
5. Forward the request
6. Observe: Order confirmed at manipulated price

Impact:
- Complete bypass of pricing controls
- Attacker can purchase any item for any price
- Direct financial loss to the business

Remediation:
- Never accept price/total values from the client
- Re-derive all financial values server-side from product ID + quantity
```

### Template 2: Race Condition
```
Title: [App] Race Condition Allows [Limit Overrun/Duplicate Processing]

Severity: [High/Medium] (CVSS [score])

Description:
The application has a race condition in [feature] where [check] and [action]
are not performed atomically. An attacker can [exploit] by sending [N]
concurrent requests.

Reproduction Steps:
1. [Setup]
2. Send [N] concurrent requests to [endpoint] using [tool]
3. Observe: [duplicate side effect / inconsistent state]

Impact:
- [financial loss / privilege escalation / data corruption]

Remediation:
- Use database transactions with proper isolation level
- Implement row-level locking (SELECT ... FOR UPDATE)
- Use conditional updates (UPDATE ... WHERE condition)
- Add idempotency keys for non-idempotent operations
```

### Template 3: Workflow Bypass
```
Title: [App] Workflow Bypass Allows [Skipping Step]

Severity: [Medium/High] (CVSS [score])

Description:
The application does not enforce workflow ordering server-side. An attacker
can skip [step] by directly accessing [endpoint].

Reproduction Steps:
1. [Expected workflow]
2. Instead, directly access [final step URL]
3. Observe: [bypass achieved]

Impact:
- [unauthorized access / bypass verification / etc.]

Remediation:
- Implement server-side state machine
- Check current state before each step
- Reject requests that don't match expected state
```

---

## 12. Advanced Techniques

### 12.1 Rate Limit Abuse for Race

**Pattern:** Use server rate-limiting to create server-side delays for multi-endpoint races.

**Technique:**
1. Send many dummy requests to trigger rate-limit
2. Rate-limit creates server-side delay
3. During delay, send the actual race attack requests
4. Single-packet attack works even when different timing is needed

### 12.2 Deferred Collision Detection

**Pattern:** Test with large delays between requests:
1. Send Request A: Change email to `attacker@evil.com`
2. Wait 20 minutes
3. Send Request B: Confirm email at `victim@target.com`
4. Monitor for anomalies hours later

**Key:** Anomaly detection > immediate response analysis

### 12.3 Session Handler Exploitation

**Pattern:** Test custom session handlers for concurrency issues:
1. Login as User A
2. Simultaneously login as User B in same session
3. Check if session contains mixed state (A's user_id + B's token)

**Exploitable session code:**
```python
# VULNERABLE: Reset password flow
session['reset_username'] = username
session['reset_code'] = randomCode()
# Exploit: Simultaneous reset for $your-username and $victim-username

# VULNERABLE: 2FA bypass
session['user'] = username
if 2fa_enabled:
    session['require2fa'] = true
# Exploit: Simultaneous login and sensitive page fetch

# VULNERABLE: Session swap
session['user'] = username
set_auth_cookies_for(session['user'])
# Exploit: Force anon session cookie on victim, then log in simultaneously
```

### 12.4 ORM-Level Race Conditions

**Pattern:** ORM batching can hide race conditions:
- ORM reads entire record into memory
- Modifications happen in-memory
- ORM writes entire record back to DB at end of request
- Two concurrent requests → one overwrites the other's changes

**Impact:** Data loss, inconsistent state, limit-overrun on database-stored values

---

*Last updated: 2026-08-09 | Sources: PortSwigger Academy, PortSwigger Research (Black Hat 2023), OWASP, Strobes, CHS*
