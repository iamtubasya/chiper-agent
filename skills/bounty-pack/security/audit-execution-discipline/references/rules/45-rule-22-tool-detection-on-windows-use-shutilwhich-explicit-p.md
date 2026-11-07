## ⛔ RULE 22: Tool Detection on Windows — Use shutil.which + Explicit Paths

**Live discovery (2026-09-24):** `force-full-execution.py` hardcoded Linux bin paths (`/home/windows10/go/bin/`) → tools like `sqlmap`, `dalfox`, `nuclei` showed `NOT_FOUND` even though they were installed under `C:/go/bin` and `/home/agentuser/go/bin`. The gate checked 5 static paths that didn't include Windows locations.

**The FIX:** First call `shutil.which(tool)` for standard PATH lookup; if that fails, check explicit Windows dirs:
- `Path.home() / "go/bin"`
- `"C:/go/bin"`
- `Path.home() / "/usr/local/bin"`
- `Path.home() / "~/.chiper/skills/bounty-pack/bin"`

Try extensions `.exe` explicitly too (native Python doesn't add it in PATH search). This pattern ensures tools fire reliably across both Unix and Windows environments.

> **Reference:** `references/tool-detection-windows.md` — full list of tool paths and verification commands for each.

