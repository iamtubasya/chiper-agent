# PoC Data Integrity — sweep + recovery recipe

Location: `D:/data hermes/poc-compact/` — manifest.json + 2,223 repo dirs + nuclei-index.json (16,261 templates).

## Full sweep (all 61,135 manifest files, ~6s)

```python
from pathlib import Path
import json
D = Path("D:/data hermes")
repos = json.loads((D / "poc-compact/manifest.json").read_text())["repos"]
missing = []
for name, files in repos.items():
    if not files:
        continue
    repo_dir = D / "poc-compact" / name
    for f in files:
        candidates = [repo_dir / f,
                      repo_dir / f.replace("\\", "/"),
                      repo_dir / f.replace("/", "\\")]
        if not any(c.exists() for c in candidates):
            missing.append((name, f))
```

Manifest paths use BACKSLASH separators; on Windows `Path` accepts both, but check all
variants before declaring missing. 304 repos have ZERO files in manifest — that is a
legit empty entry, not data loss.

## Recovery (verified working, 2026-09-24: 40/40 recovered)

Repo dir name format: `Owner_RepoName` — split on the FIRST underscore.
Prefer raw file fetch over full clone (fast, no junk):

```python
import urllib.request
def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        return urllib.request.urlopen(req, timeout=15).read()
    except Exception:
        return None

for name, f in missing:
    owner, _, repo = name.partition("_")
    rel = f.replace("\\", "/")
    for branch in ("main", "master"):
        blob = fetch(f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{rel}")
        if blob:
            target = D / "poc-compact" / name / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
            break
```

Fallback when raw fetch 404s (repo renamed/private): `git clone --depth 1
https://github.com/{owner}/{repo}` into a temp dir, copy only the missing files in.

## MSYS/Windows path gotchas (recurring in this env)

- MSYS `/tmp` is `C:\Users\<user>\AppData\Local\Temp`, but native Python does NOT resolve
  `/tmp/...` — `python "C:\tmp\x.py"` fails with "can't open file". Copy scripts to
  `$LOCALAPPDATA/Temp` and use `C:/Users/...` style paths.
- `wslpath -w /msys/path` converts to native when needed.
- `execute_code` kernel: file writes may not persist to host disk — verify via `terminal`
  or use the write_file tool.