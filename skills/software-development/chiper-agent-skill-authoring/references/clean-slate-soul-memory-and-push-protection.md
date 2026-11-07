# Clean-Slate Soul Memory, Persona Separation & Secret Sanitization

Architecture notes for Multi-Soul configuration, clean installation isolation, and Git repository protection.

---

## 1. Clean-Slate Soul Memory Isolation

When designing isolated memory architectures (`~/.chiper/memories/souls/<soul_id>.md`) for multi-persona agents:

### The Pitfall
Developers frequently hardcode their own current operational notes into `DEFAULT_SOUL_MEMORIES`:
- Specific test emails and credentials
- VPN / Tailscale IP addresses
- Active target engagements and API endpoints

When a new user clones and installs the agent on a new server, those personal notes are copied directly into the new environment, causing:
1. Leaks of sensitive developer metadata.
2. Contamination of the agent's reasoning context with outdated or irrelevant facts.
3. Confusion about the actual target and operating environment.

### The Standard
In repository source code (`agent/soul_manager.py`), default initial memory for all souls must be empty:
```python
DEFAULT_SOUL_MEMORIES: Dict[str, str] = {
    "chiper-cyber": "",
    "chiper-hunt": "",
    "chiper-dev": "",
    "chiper-web3": "",
}
```

### Self-Preservation on Existing Hosts
When initializing memories (`ensure_default_soul_memories()`):
- Check `if not mem_path.exists():` before writing.
- On an existing host, existing populated memory files are never overwritten.
- On a clean host, empty `.md` files are initialized, allowing each soul to dynamically learn and save facts via `memory(action='add', target='memory')`.

---

## 2. Soul Separation vs Skill Collision

When integrating large specialized skill packs alongside general offensive suites:

### The Problem
- Suite A: `chiper-web-ssrf`, `chiper-web-access-control`, `chiper-web-sqli` (15 KB each, formal ISO/defense-oriented).
- Suite B: `hunt-ssrf`, `hunt-idor`, `hunt-sqli` (45 KB each, payout-oriented, HackerOne report citations, WAF bypasses).

If both are dumped into the same persona:
- Calling both wastes ~16,000 context tokens on a single vulnerability class.
- The model hesitates or arbitrarily alternates between auditor-style and bounty-hunter-style responses.

### The Solution: Purpose-Built Soul Personas
Separate the operational mindsets into distinct souls:
- **`🛡️ Chiper-Cyber`**: Enterprise auditor, internal infrastructure, Active Directory, hardware, radio/telecom, defense matrix & Sigma rules.
- **`🎯 Chiper-Hunt`**: Commercial bug bounty hunter, web & API specialist, minimal PoC, OOB verification, K/A/B/X exploit chain composition, triager-ready reports.

---

## 3. GitHub Push Protection & Secret Sanitization Protocol

Disclosed vulnerability reports (HackerOne, Bugcrowd) often contain real-world sample tokens that trigger GitHub's pre-receive secret scanning hook (`GH013`).

### The Recovery Workflow
1. **Unstage and Undo Rejected Commit:**
   ```bash
   git reset HEAD~1
   ```
2. **Execute Automated Regex Sanitization:**
   ```python
   import os, re

   patterns = [
       (re.compile(r'npm_[a-zA-Z0-9]{30,}'), 'npm_[REDACTED_NPM_TOKEN]'),
       (re.compile(r'_authToken=[a-f0-9\-]{30,}'), '_authToken=[REDACTED_NPM_TOKEN]'),
       (re.compile(r'00D[0-9a-zA-Z]{12,15}![0-9a-zA-Z._\-]{10,}'), '[REDACTED_SALESFORCE_TOKEN]'),
       (re.compile(r'sid=00D[^;\s]+'), 'sid=[REDACTED_SALESFORCE_TOKEN]'),
       (re.compile(r'EAA[a-zA-Z0-9]{30,}'), '[REDACTED_FACEBOOK_TOKEN]'),
       (re.compile(r'ghp_[a-zA-Z0-9]{30,}'), 'ghp_[REDACTED_GITHUB_TOKEN]'),
   ]

   for root, _, files in os.walk('.'):
       for f in files:
           if f.endswith(('.md', '.json', '.txt', '.yaml', '.py', '.sh')):
               p = os.path.join(root, f)
               try:
                   with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                       content = fp.read()
                   modified = False
                   for pat, repl in patterns:
                       if pat.search(content):
                           content = pat.sub(repl, content)
                           modified = True
                   if modified:
                       with open(p, 'w', encoding='utf-8') as fp:
                           fp.write(content)
               except Exception:
                   pass
   ```
3. **Re-stage and Push Cleanly:**
   ```bash
   git add .
   git commit -m "feat: Add assets (sanitized against GitHub Push Protection)"
   git push origin <branch>
   ```
