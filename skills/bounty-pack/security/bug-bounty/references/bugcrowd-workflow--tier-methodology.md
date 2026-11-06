# Tier-Based Audit Methodology

## Overview
Progressive testing approach: mulai dari yang sederhana ke kompleks.
Setiap tier harus selesai sebelum lanjut ke tier berikutnya.

## Tier Structure

### Tier 1: Recon Dasar (Sederhana)
**Target**: Mapping attack surface
**Waktu**: 1-2 hari
**Resiko**: Rendah

**Activities**:
1. Subdomain enumeration (subfinder)
2. Live host detection (httpx)
3. Technology fingerprinting
4. JavaScript analysis
5. Wayback/archives lookup

**Output**:
- Complete asset inventory
- Prioritized test candidates
- Tech stack profile

---

### Tier 2: API Testing (Medium)
**Target**: API endpoints
**Waktu**: 3-5 hari
**Resiko**: Medium

**Activities**:
1. API recon (Swagger/OpenAPI docs)
2. Authentication testing (JWT, API keys)
3. IDOR/BOLA testing
4. Business logic testing
5. Input validation testing

**Output**:
- API endpoint map
- Authentication flow analysis
- Potential vulnerabilities list

---

### Tier 3: Advanced Features (High)
**Target**: Specific features (SAML, OAuth, etc.)
**Waktu**: 5-7 hari
**Resiko**: High

**Activities**:
1. Feature-specific attack vectors
2. Protocol-level testing
3. Configuration analysis
4. Integration testing

**Output**:
- Feature-specific vulnerabilities
- Protocol-level findings

---

### Tier 4: Business Logic (Critical)
**Target**: Core business flows
**Waktu**: 7-10 hari
**Resiko**: High
**Impact**: Fund loss, data breach

**Activities**:
1. Race condition testing
2. Business logic flaws
3. Price/quantity manipulation
4. Multi-step flow bypass
5. Authorization escalation

**Output**:
- Business logic vulnerabilities
- Financial impact proof

---

### Tier 5: Chain Attacks (Maximum)
**Target**: Multiple vulnerabilities digabung
**Waktu**: 10+ hari
**Resiko**: Very High
**Impact**: Full compromise

**Activities**:
1. Vulnerability chaining
2. Escalation paths
3. Impact amplification
4. Full exploit development

**Output**:
- Complete attack chain
- Maximum impact demonstration

## Decision Matrix

| Factor | Tier 1 | Tier 2 | Tier 3 | Tier 4 | Tier 5 |
|--------|--------|--------|--------|--------|--------|
| Time | 1-2d | 3-5d | 5-7d | 7-10d | 10d+ |
| Skill | Beginner | Intermediate | Advanced | Expert | Expert |
| Impact | Low | Medium | High | Critical | Critical |
| Reward | $ | $$ | $$$ | $$$$ | $$$$$ |

## When to Skip Tiers
- Skip Tier 1 if target is well-known (use existing recon data)
- Skip Tier 2 if no API endpoints found
- Skip Tier 3 if target doesn't use advanced auth
- Skip Tier 4 if business logic is simple
- Never skip Tier 5 if you have multiple findings

## When to Stop
- 2-strike rule: if 2 approaches fail, move on
- Time-box: if no progress in allocated time, pivot
- Impact bar: if can't demonstrate real exploitation, drop
