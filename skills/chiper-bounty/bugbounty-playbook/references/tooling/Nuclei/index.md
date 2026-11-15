# Nuclei

> tags: tooling, nuclei

> related: Tooling/Burp-Suite/, Tooling/Automation/, Tooling/ffuf/

Nuclei
Nuclei's default template run is table stakes. The real value is writing your own templates for target-specific logic and chaining it into a pipeline. If you're just running nuclei -u target.com and calling it a day, you're leaving findings on the table.
Installation and Setup
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
nuclei -update-templates
Keep templates updated weekly. New CVE templates drop fast. Check ~/.local/nuclei-templates/ for what you have.
Beyond Default Runs
Stop running everything. It's noisy and slow. Build target-appropriate template sets.
# Only high/critical severity
nuclei -l targets.txt -s high,critical -o results.txt
 
# Specific tags for web app testing
nuclei -l targets.txt -tags xss,sqli,ssrf,idor -o results.txt
 
# Exclude noise-heavy template categories
nuclei -l targets.txt -etags ssl,dns,info -o results.txt
 
# New templates only (great for continuous monitoring)
nuclei -l targets.txt -nt -o new-findings.txt
Custom Template Writing
This is where you differentiate. A template that catches target-specific logic beats 500 generic ones.
Template anatomy:
id: custom-admin-panel-disclosure
 
info:
  name: Admin Panel Accessible Without Auth
  author: yourhandle
  severity: high
  tags: misconfig,auth-bypass
 
http:
  - method: GET
    path:
      - "{{BaseURL}}/admin"
      - "{{BaseURL}}/admin/dashboard"
      - "{{BaseURL}}/internal/admin"
 
    matchers-condition: and
    matchers:
      - type: status
        status:
          - 200
      - type: word
        words:
          - "Admin Dashboard"
          - "Welcome, Administrator"
        condition: or
      - type: word
        words:
          - "login"
          - "sign in"
        negative: true
Extractors - pull values from responses for chaining:
    extractors:
      - type: regex
        name: api_key
        regex:
          - 'apiKey["\s:=]+([A-Za-z0-9_\-]{32,})'
        group: 1
 
      - type: xpath
        name: csrf_token
        xpath:
          - '//input[@name="csrf_token"]/@value'
DSL matchers for complex logic:
    matchers:
      - type: dsl
        dsl:
          - "status_code == 200 && contains(body, 'secret') && !contains(body, 'login')"
          - "response_time > 5000"  # for timing-based detection
        condition: or
Workflow Chaining
Extract values in one template, pass them to the next. The flow field enables this.
id: find-and-test-api-keys
 
http:
  - method: GET
    path:
      - "{{BaseURL}}/config.js"
    extractors:
      - type: regex
        name: keys
        internal: true
        regex:
          - 'key["\s:=]+([A-Za-z0-9]{40})'
 
  - method: GET
    path:
      - "api.service.com/validate{{keys}}"
    matchers:
      - type: word
        words:
          - '"valid":true'
httpx Pipeline Integration
httpx feeds Nuclei. This is my standard recon-to-scan flow.
# Subdomain enum -> probe live hosts -> scan with Nuclei
subfinder -d target.com -silent | \
  httpx -silent -mc 200,301,302,403 -o live-hosts.txt && \
  nuclei -l live-hosts.txt -tags exposed-panels,misconfig,takeover -o nuclei-out.txt
 
# Fingerprint first, then template-match
httpx -l hosts.txt -tech-detect -json -o tech.json
# Parse tech.json, run tech-specific nuclei templates
cat tech.json | jq -r 'select(.technologies[] | test("WordPress")) | .url' > wp-targets.txt
nuclei -l wp-targets.txt -tags wordpress -o wp-results.txt
Target-Specific Template Patterns
When I start an engagement, I write templates for anything the app does that's unique:

Custom session token format? Write a regex extractor + validator template.
API versioning pattern? Template to check if v1 endpoints exist behind a v2 app.
Known internal tool stack (Grafana, Jenkins, etc.)? Pull the relevant community templates and tune them.

Store custom templates in ~/nuclei-templates/custom/. Run with:
nuclei -l targets.txt -t ~/nuclei-templates/custom/ -t ~/.local/nuclei-templates/
Rate Limiting and Stealth
# Respectful rate limit for smaller programs
nuclei -l targets.txt -rl 10 -c 5
 
# Header injection for tracking your traffic
nuclei -l targets.txt -H "X-Bug-Bounty: yourhandle@platform"
 
# Proxy through Burp for manual review
nuclei -l targets.txt -proxy http://127.0.0.1:8080
Output and Triage
# JSON output for scripted triage
nuclei -l targets.txt -json -o results.jsonl
 
# Parse critical findings immediately
cat results.jsonl | jq 'select(.info.severity == "critical")'
Linked Notes

Burp Suite - validate Nuclei findings manually
Automation - pipeline orchestration
ffuf - content discovery to feed Nuclei target lists
