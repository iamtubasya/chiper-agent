# VRT Analysis Workflow

Reusable workflow for mapping findings to Bugcrowd VRT categories and assigning severity.

## Why This Exists

Session 2026-09 (Fireblocks): Agent downloaded VRT JSON from GitHub, parsed it with Python, and mapped smart contract findings to VRT categories programmatically. This prevented hours of manual category hunting and enabled accurate severity assignment.

## Step 1: Get VRT JSON

```bash
# Download latest VRT JSON from Bugcrowd GitHub
curl -sL "https://raw.githubusercontent.com/bugcrowd/vulnerability-rating-taxonomy/master/vulnerability-rating-taxonomy.json" -o /tmp/vrt.json

# Verify file downloaded
wc -l /tmp/vrt.json
```

## Step 2: Parse and Search

```python
import json

with open('/tmp/vrt.json') as f:
    vrt = json.load(f)

# Search for matching categories by keyword
def search_vrt(data, keyword, path=""):
    results = []
    if isinstance(data, dict):
        for key, value in data.items():
            if keyword.lower() in key.lower():
                results.append({"path": f"{path}.{key}", "data": value})
            results.extend(search_vrt(value, keyword, f"{path}.{key}"))
    elif isinstance(data, list):
        for i, item in enumerate(data):
            results.extend(search_vrt(item, keyword, f"{path}[{i}]"))
    return results

# Example: Find smart contract categories
matches = search_vrt(vrt, "smart contract")
for m in matches:
    print(f"Path: {m['path']}")
    print(f"Data: {json.dumps(m['data'], indent=2)[:500]}")
```

## Step 3: Map Finding to Category

### Mapping Decision Tree

```
1. What is the VULNERABILITY CLASS?
   ├── Smart Contract → Category 25 (Smart Contract Misconfiguration)
   ├── API/Backend → Category 3, 4, 23, 24 (BAC, Auth, Server, Injection)
   ├── Frontend → Category 7, 6 (XSS, CSRF)
   └── Infrastructure → Category 23 (Server Security Misconfiguration)

2. What is the SPECIFIC VARIANT?
   ├── Reentrancy → P1 (Category 25)
   ├── Owner Takeover → P1 (Category 25)
   ├── Improper Use of Modifier → P4 (Category 25)
   └── No exact match → Check parent category

3. Is there a VARIANT entry?
   ├── YES → Use variant priority
   ├── NO → Use parent priority (if exists)
   └── Parent is N/A → Argue with concrete impact scenario
```

### Smart Contract VRT Quick Reference

| Finding Pattern | VRT Category | Priority |
|----------------|--------------|----------|
| Reentrancy | Smart Contract Misconfiguration > Reentrancy Attack | P1 |
| Owner key compromise | Smart Contract Misconfiguration > Owner Takeover | P1 |
| Unauthorized transfer | Smart Contract Misconfiguration > Unauthorized Transfer | P1 |
| Uninitialized proxy | Smart Contract Misconfiguration > Uninitialized Variables | P1 |
| Integer overflow | Smart Contract Misconfiguration > Integer Overflow | P2 |
| Missing access control on critical function | Smart Contract Misconfiguration > Owner Takeover | P1-P2 |
| Missing modifier on upgrade function | Smart Contract Misconfiguration > Improper Use of Modifier | P4 |
| Missing modifier on non-critical function | Smart Contract Misconfiguration > Improper Use of Modifier | P4 |
| Function DoS (gas limit) | Smart Contract Misconfiguration > Function-level DoS | P3 |
| Fee logic error | Smart Contract Misconfiguration > Improper Fee Implementation | P3 |
| Decimals mismatch | Smart Contract Misconfiguration > Improper Decimals | P4 |
| Upgradeable with no pause on auth | Smart Contract Misconfiguration > Improper Use of Modifier | P4 |
| ERC-2771 forwarder spoofing | Smart Contract Misconfiguration > Unauthorized Transfer | P1-P2 |
| No deployment access control | Smart Contract Misconfiguration > Owner Takeover | P1 |

## Step 4: Verify Viability

Before assigning final severity, check:

```
□ Is the finding REPRODUCIBLE by external researcher?
□ Does it require SPECIAL CONDITIONS (owner key, specific state)?
□ Is it BY DESIGN (documented behavior, expected functionality)?
□ Does it have REAL IMPACT (financial, data, availability)?
□ Does it match a FOCUS AREA of the program?
```

## Cloud Security / API Infrastructure VRT Quick Reference

| Finding Pattern | VRT Category | Priority |
|----------------|--------------|----------|
| Health endpoint returns full infra dump | Cloud Security > Insecure API Endpoints | P3-P4 |
| AWS Account ID disclosed externally | Cloud Security > IAM Misconfigurations | P3-P4 |
| SNS/SQS ARNs exposed | Cloud Security > Misconfigured Services | P3 |
| S3 bucket name disclosed | Cloud Security > Storage > Publicly Accessible | P2-P3 |
| Auth0 client_id in client config | Sensitive Data > Known Public Information | P5 (NOT REPORTABLE) |
| Client-side analytics IDs (Datadog RUM, Pendo, LD) | Sensitive Data > Known Public Information | P5 (NOT REPORTABLE) |
| Server version banner | Server Security > Fingerprinting | P5 |
| CORS wildcard on sensitive data | Server Security > Misconfiguration > CORS | P3-P4 |
| Debug/error endpoints accessible | Server Security > Exposed Portal | P3-P4 |
| Cloud metadata endpoint accessible | Cloud Security > Misconfigured Services > Metadata | P2 |
| Full stack trace on error | Server Security > Sensitive Data Hardcoded | P2-P3 |

### Severity Adjustment Rules

1. **VRT says P1 but requires owner key compromise** → May downgrade to P3-P4 (defense-in-depth gap, not authorization bypass)
2. **VRT says P4 but chains to P1** → Argue P2-P3 with concrete exploitation chain
3. **VRT says N/A (no priority)** → Argue with impact scenario; submit as informational if impact is real
4. **Program-specific override** → If program lists finding type as P1 in focus areas, use program's severity even if VRT says lower

## Step 5: Document the Mapping

Include in your finding notes:

```
## VRT Analysis

**VRT Category:** Smart Contract Misconfiguration
**VRT Subcategory:** Improper Use of Modifier
**VRT Priority (baseline):** P4 (Low)

**Adjustment reasoning:**
- Finding requires owner key to exploit (not authorization bypass)
- Is a defense-in-depth gap (missing `whenNotPaused` check)
- Does not directly lead to fund loss without additional compromise
- Mapped to P4 per VRT baseline

**Program context:**
- Program focus areas: [extracted from program page]
- Finding aligns with: [specific focus area]
- Reward range: $X-$Y for P4
```

## Case Study: Fireblocks Smart Contract Findings (2026-09)

**Finding:** `_authorizeUpgrade` missing `whenNotPaused` check

**VRT Analysis:**
- Category: Smart Contract Misconfiguration (25)
- Subcategory: Improper Use of Modifier
- Priority: P4 (Low)

**Why P4 (not P1-P2):**
- Requires owner key to call `upgradeToAndCall`
- Is a defense-in-depth gap (not authorization bypass)
- Does not directly lead to fund loss
- Chain: Owner compromised → can upgrade while paused → potential for malicious upgrade

**Program context:**
- Fireblocks MBB on Bugcrowd
- Scope ambiguity: Smart contract code vs API endpoints
- Decision: Pending scope clarification from program

**Lesson learned:** Always verify the ACCESS REQUIREMENTS before finalizing severity. A "missing modifier" on an admin-only function is fundamentally different from a "missing modifier" on a public function.
