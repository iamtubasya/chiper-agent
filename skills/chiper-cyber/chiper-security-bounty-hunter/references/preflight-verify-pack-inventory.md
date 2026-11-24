# Preflight: Verify the Pack's Own Inventory Before Acting On It

A skill pack shipped from another host carries an inventory (`TOOLS.md`, `MEMORY.md`,
`SKILL.md`) that is prose, not measurement. It can be confidently and completely wrong — wrong
OS, wrong architecture, and a tool list where most binaries do not exist. The agent then plans
from that map and writes commands that fail.

**Run this preflight before following any pack's declared environment or tool inventory.**

## 1. Environment truth (30 seconds)

```bash
uname -srm                        # kernel + arch
grep -E 'PRETTY_NAME|VERSION_ID' /etc/os-release
echo "$HOME"; whoami
```

Compare against what the pack claims. Any mismatch (e.g. pack says `Kali 2025-2 aarch64`,
host is `Ubuntu 24.04 x86_64`) invalidates every architecture-specific and path-specific
recipe in the pack.

## 2. Tool inventory truth

```python
from chiper_tools import terminal

claimed = ["nmap","dig","whois","whatweb","wpscan","gobuster","theHarvester","sublist3r",
           "assetfinder","dirb","sqlmap","burpsuite","hydra","msfconsole","radare2","ffuf",
           "nuclei","subfinder","httpx","katana","amass","naabu","feroxbuster","gau",
           "waybackurls","jwt_tool","trufflehog","commix","nikto","masscan","tshark",
           "aircrack-ng","hashcat","john","impacket","netexec","responder","bettercap",
           "wireshark","binwalk","ghidra","frida","apktool","jadx","mobsf","proxychains",
           "chisel","ligolo"]

missing = [t for t in claimed
          if "OK" not in terminal(f"command -v {t} >/dev/null 2>&1 && echo OK")["output"]]
print(f"{len(claimed)-len(missing)}/{len(claimed)} present")
print("MISSING:", ", ".join(missing))
```

A large `missing` list means: do **not** plan around those tools. Use only what `command -v`
confirmed, or install first via `chiper-bootstrap`.

## 3. Directory-layout truth

Packs often declare `memory/`, `chronicle/`, `bak/`, `tools/` in their architecture diagram
while shipping none of them. Startup sequences that read those paths half-fail silently.

```bash
cd <pack> && for d in memory chronicle bak validation skills docs tools references; do
  [ -d "$d" ] && echo "OK     $d ($(ls -1 "$d" | wc -l))" || echo "ABSENT $d"
done
```

## 4. Claim-propagation check

The same false number is usually copy-pasted across the pack. Before "fixing" one file, find
every site:

```bash
grep -rn "518\|aarch64\|Kali 2025" <pack>/*.md
```

If `md5sum ~/.chiper/TOOLS.md <pack>/TOOLS.md` returns identical hashes, the false inventory
originates in the **skill pack**, not in the runtime — fix the pack first or the next sync
re-injects it.

## 5. Then, and only then, decide on doctrine

Once the inventory is measured:

- **Coverage ratio** from `.usage.json` (distinct skills used ÷ installed) tells you if the pack
  is mostly dead weight → prune, don't add prompt text.
- **Domain-hit rate** tells you if routing fails for domains that do exist → this is when
  `references/skill-loading-doctrine.md` applies.

Full detail, worked numbers and the field-by-field failure table:
`references/fabricated-capability-claims.md` in `chiper-skill-usage-forensics`.
