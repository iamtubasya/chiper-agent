# Browserbase vs User's Chrome — Automation Pitfall

## Problem
`browser_navigate`/`browser_click` (Browserbase) and `computer_use` (user's Chrome) are **completely separate browsers**. Sessions, cookies, logins are NOT shared.

## Scenario: User needs to login to target
1. `browser_navigate(target.com/login)` → reCAPTCHA blocks automated browser
2. User cannot share Browserbase session — it's a different browser
3. Solution: user logs in manually in their Chrome, then `computer_use` drives it

## Pattern (Klaviyo Example)
```
1. browser_navigate(klaviyo.com/sign-up) → {is_robot: true}
2. Tell user: "Signup manually, then paste your API key"
3. User creates account in their Chrome
4. computer_use(action='capture', app='Chrome') → see Klaviyo dashboard
5. computer_use(action='click', element=49) → navigate to Customer Agent
```

## computer_use Chrome Quirks
- **Background mode** clicks work but modal buttons at (0,0) bounds may not land
- **Keystrokes** (key/type) require `delivery_mode='foreground'` on Chrome
- After `raise_window`, always re-capture to verify state
- Background clicks return `unverifiable` when modal is overlaying — that's normal, try pressing Escape first

## When to Use Which
| Situation | Tool | Why |
|-----------|------|-----|
| Testing unauthenticated endpoints | `browser_navigate` (Browserbase) | Fast, no user involvement |
| Need user's login session | `computer_use` (Chrome) | Shares user's cookies/auth |
| Quick API testing | `curl` / `execute_code` | No browser needed |
| Checking dashboard rendering | `computer_use` (Chrome) | See what user sees |
