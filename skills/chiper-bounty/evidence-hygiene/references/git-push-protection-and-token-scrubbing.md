# Git Push Protection & Secret Sanitization in Bug Bounty Repositories

When archiving, committing, or pushing bug bounty research bundles, writeups, and disclosed report archives (`h1-reports`, `cbh-hunt-skills`, test payloads):

## 1. Root Cause
Disclosed report dumps (from HackerOne, Bugcrowd, or research blogs) often contain sample or real access tokens:
- npm auth tokens (`//registry.npmjs.org/:_authToken=...` or `npm_...`)
- Salesforce session IDs (`sid=00D...`)
- Facebook Graph API tokens (`EAA...`)
- GitHub Personal Access Tokens (`ghp_...`, `github_pat_...`)
- Slack bot/user tokens (`xoxb-...`, `xoxp-...`)

When pushing to GitHub, **GitHub Push Protection (Rule Violation GH013)** blocks the push at the server-side pre-receive hook.

## 2. Common Pitfall
Simply editing the offending file and making a new commit on top **does NOT work**. 
Git history retains the previous commit containing the secret. GitHub checks all commits being pushed on the ref branch, so `git push` continues to be rejected with:
`! [remote rejected] main -> main (push declined due to repository rule violations)`

## 3. Standard Recovery & Remediation Protocol

### Step 1: Undo the Offending Commit
Undo the commit while keeping file modifications staged/unstaged in the working tree:
```bash
git reset HEAD~1
```

### Step 2: Automated Regex Sanitization Script
Run a Python one-liner or script to sanitize all common token patterns across markdown, json, yaml, and text files:

```python
import os, re

patterns = [
    (re.compile(r'npm_[a-zA-Z0-9]{30,}'), 'npm_[REDACTED_NPM_TOKEN]'),
    (re.compile(r'_authToken=[a-f0-9\-]{30,}'), '_authToken=[REDACTED_NPM_TOKEN]'),
    (re.compile(r'00D[0-9a-zA-Z]{12,15}![0-9a-zA-Z._\-]{10,}'), '[REDACTED_SALESFORCE_TOKEN]'),
    (re.compile(r'sid=00D[^;\s]+'), 'sid=[REDACTED_SALESFORCE_TOKEN]'),
    (re.compile(r'EAA[a-zA-Z0-9]{30,}'), '[REDACTED_FACEBOOK_TOKEN]'),
    (re.compile(r'ghp_[a-zA-Z0-9]{30,}'), 'ghp_[REDACTED_GITHUB_TOKEN]'),
    (re.compile(r'github_pat_[a-zA-Z0-9_]{30,}'), 'github_pat_[REDACTED_GITHUB_TOKEN]'),
    (re.compile(r'glpat-[a-zA-Z0-9\-]{20,}'), 'glpat-[REDACTED_GITLAB_TOKEN]'),
    (re.compile(r'xox[baprs]-[0-9a-zA-Z]{20,}'), 'xoxb-[REDACTED_SLACK_TOKEN]'),
]

for root, _, files in os.walk('.'):
    for f in files:
        if f.endswith(('.md', '.txt', '.json', '.yaml', '.yml', '.py', '.sh')):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                modified = False
                for pat, repl in patterns:
                    if pat.search(content):
                        content = pat.sub(repl, content)
                        modified = True
                if modified:
                    with open(path, 'w', encoding='utf-8') as fp:
                        fp.write(content)
            except Exception:
                pass
```

### Step 3: Re-Stage & Clean Push
```bash
git add .
git commit -m "feat: Add research assets (sanitized against GitHub Push Protection)"
git push origin <branch>
```
