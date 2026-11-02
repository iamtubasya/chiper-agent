# Supabase Cookie Injection — Bluejay Auth Bypass

## When to Use
When normal login fails (wrong password, account registered via Google, or session expired mid-session) and Boss provides raw cookie values.

## Cookie Structure
Bluejay uses Supabase auth split across two cookies:
```
sb-auth-auth-token.0=base64-<first_chunk>
sb-auth-auth-token.1=<second_chunk>
```
Plus optional:
```
pw_rotation_cache=<json_blob>
```

Token expiry is in the JWT payload: `expires_at` (Unix timestamp). Check before injecting — expired tokens cause Internal Server Error, not login redirect.

## Injection Pattern

**Critical:** Must be on the `app.getbluejay.ai` domain when injecting — NOT on an auth redirect page that returns a SecurityError. The auth/login page at `/auth/login` can throw `SecurityError: Failed to set the 'cookie' property` when the page is in a security-restricted state (blank page, 500 error, or mid-redirect). If that happens, navigate to a static asset or the root domain first.

Navigate to `https://app.getbluejay.ai/auth/login` first (need the domain context), then:

```javascript
document.cookie = "sb-auth-auth-token.0=<value>; path=/; domain=app.getbluejay.ai";
document.cookie = "sb-auth-auth-token.1=<value>; path=/; domain=app.getbluejay.ai";
document.cookie = "pw_rotation_cache=<value>; path=/; domain=app.getbluejay.ai";
```

Then navigate to `/simulations` or `/chat`. If redirected back to login, token is expired.

## Verify Token Freshness (MANDATORY — do this BEFORE injecting)
Decode the base64 portion of `sb-auth-auth-token.0` (strip the `base64-` prefix), parse as JSON, check `expires_at`:
```javascript
const raw = cookieValue.replace('base64-', '');
const decoded = JSON.parse(atob(raw));
console.log('expires_at:', decoded.expires_at, 'now:', Math.floor(Date.now()/1000));
// expires_at must be > now
```

## Pitfalls
- Injecting via `document.cookie` without `domain=` flag may not work across subdomains
- If page returns "Internal Server Error" after inject → token expired, need fresh cookie
- Token valid for 3600s from issue time — Boss needs to export cookie within 1 hour of login
- Account registered via Google OAuth may not have an email/password — use cookie injection instead of trying to reset password
- If `document.cookie` throws `SecurityError: Access is denied for this document` → page is in restricted state (empty page, mid-redirect, or 500); navigate to a real page on the domain first
- If browser shows blank page (`(empty page)`) after navigate — server may be returning 500; verify with `document.body.innerHTML` before diagnosing as a cookie/auth problem
- **Do NOT try to reset password** when login fails — diagnose the actual error first (invalid creds vs. wrong auth method vs. expired token vs. server 500)
- When Bluejay server returns 500 on ALL pages — this is platform downtime, not a client-side issue; wait and retry
- **Cookie freshness is relative to `last_sign_in_at`, NOT when Boss copied it.** If Boss copied cookies 2+ hours ago but just sent them now, they are already expired. Always check `expires_at > current_epoch` before injecting. If expired, Boss must login again and copy fresh cookies immediately.
