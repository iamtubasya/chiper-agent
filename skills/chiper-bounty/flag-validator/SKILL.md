---
name: flag-validator
author: RESEARCHER_NAME
description: "CTF flag validation with anti-hallucination: reject placeholders, extract from output."
category: security
version: 1.0.0
metadata:
  hermes:
    tags: [flag-validator]
---

# Flag Validator

## Triggers
- flag check, validate flag, flag format, anti-hallucination, flag extract

## Quick Usage
```python
from flag_validator import validate, extract_all

# Validate a single flag
validate("flag{abc_123}")                          # True
validate("flag{...}")                              # False (placeholder)

# Extract all flags from exploit output
output = "...the answer is flag{sup3r_s3cr3t} here..."
extract_all(output)                                # ["flag{sup3r_s3cr3t}"]
```

## Full Source

```python
import re

COMMON_FORMATS = [
    r"flag\{[^}]+\}",
    r"CTF\{[^}]+\}",
    r"[A-Za-z0-9_]+\{[^}]+\}",
    r"picoCTF\{[^}]+\}",
    r"HTB\{[^}]+\}",
]

PLACEHOLDER_BLOCKLIST = {
    "flag{...}", "flag{your_flag_here}", "flag{example}",
    "flag{redacted}", "ctf{example}", "flag{}", "flag{flag}",
}

def validate(candidate, fmt_regex=None):
    if not candidate: return False
    cand = candidate.strip()
    if cand.lower() in PLACEHOLDER_BLOCKLIST: return False
    patterns = [fmt_regex] if fmt_regex else COMMON_FORMATS
    for pat in patterns:
        try:
            if re.fullmatch(pat, cand): return True
        except re.error: continue
    return False

def extract_all(blob, fmt_regex=None):
    patterns = [fmt_regex] if fmt_regex else COMMON_FORMATS
    found = []
    for pat in patterns:
        try:
            found.extend(m.group(0) for m in re.finditer(pat, blob))
        except re.error: continue
    seen, out = set(), []
    for f in found:
        if f not in seen and f.lower() not in PLACEHOLDER_BLOCKLIST:
            seen.add(f); out.append(f)
    return out
```

## Pitfalls
- `re.fullmatch` — entire string must be a flag, partial matches rejected
- Placeholder blocklist catches model hallucinations
- Extract uses `re.finditer` — flags buried in output text are found
- Case-sensitive by default (flag{...} ≠ FLAG{...})
