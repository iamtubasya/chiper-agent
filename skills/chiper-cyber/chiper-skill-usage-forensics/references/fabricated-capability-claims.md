# Fabricated Capability Claims — When a Pack's Inventory Is 100% False

A skill pack's `TOOLS.md`, `MEMORY.md`, and `SKILL.md` are *prose*, not measurements. A pack
authored on one machine and shipped to another routinely carries an inventory that is
confidently, totally wrong. The agent reads it as fact and then writes commands for binaries
that do not exist.

This is upstream of skill loading: **a poisoned inventory makes the agent act wrongly even when
it loads the right skill.**

## The failure shape

Measured live on a `chiper-cyber` pack installed on Ubuntu 24.04 x86_64 (2026-11-08):

| Claim in the pack | Reality on the host |
|---|---|
| `OS: Kali Linux 2025-2` | `Ubuntu 24.04.4 LTS` |
| `Kernel: 6.18.12+kali-arm64` | `6.8.0-101-generic` |
| `Architecture: aarch64 (ARM64)` | `x86_64` |
| `All 518 Kali tools mastered` | **11 of 50 core tools present (22%)** |
| `MEMORY.md: Tools Mastered 518/518 (100%)` | 39 core tools absent entirely |

Absent but claimed mastered: `burpsuite, msfconsole, radare2, amass, katana, naabu,
feroxbuster, gau, waybackurls, jwt_tool, trufflehog, commix, nikto, masscan, tshark,
aircrack-ng, hashcat, john, impacket, netexec, responder, bettercap, wireshark, binwalk,
ghidra, frida, apktool, jadx, mobsf, proxychains, chisel, ligolo` — plus 28 more.

## Why it poisons behaviour (not just cosmetics)

1. The agent plans a task from the inventory, writes `msfconsole` / `burpsuite`, and gets
   `command not found`.
2. It does not backtrack to "this claim is false" — it retries with re-rolled parameters
   (classic tunnel vision), which is exactly the error-rate and two-strike-breaker dynamics
   described in `skill-loading-doctrine.md`.
3. Because the file also declares a wrong OS and architecture, every architecture-sensitive
   recipe in the pack (ARM64 offsets, Kali paths) is silently misfiring too.

## Verification sweep — replace the claim with a measurement

Never accept an inventory you have not measured. Regenerate it:

```python
from chiper_tools import terminal

tools = ["nmap","dig","whois","whatweb","wpscan","gobuster","theHarvester","sublist3r",
         "assetfinder","dirb","sqlmap","burpsuite","hydra","msfconsole","radare2","ffuf",
         "nuclei","subfinder","httpx","katana","amass","naabu","feroxbuster","gau",
         "waybackurls","jwt_tool","trufflehog","commix","nikto","masscan","tshark",
         "aircrack-ng","hashcat","john","impacket","crackmapexec","netexec","responder",
         "bettercap","wireshark","binwalk","ghidra","frida","objection","apktool","jadx",
         "mobsf","proxychains","chisel","ligolo"]

found, missing = [], []
for t in tools:
    r = terminal(f"command -v {t} >/dev/null 2>&1 && echo OK || echo NO")
    (found if "OK" in r["output"] else missing).append(t)

print(f"{len(found)}/{len(tools)} = {len(found)/len(tools)*100:.0f}%")
print("MISSING:", ", ".join(missing))
```

Also capture the environment truth at the same moment and put it *in* the replacement file:

```bash
uname -srm                       # Linux 6.8.0-101-generic x86_64
grep PRETTY_NAME /etc/os-release # PRETTY_NAME="Ubuntu 24.04.4 LTS"
```

## Propagation check — the false number lives in more than one file

A single lie gets copied. Before fixing, grep every claim site:

```bash
grep -rn "518\|aarch64\|Kali 2025" <pack>/*.md
```

Observed spread in one pack: `TOOLS.md`, `MEMORY.md`, `SKILL.md`, `README.md`, `CLAUDE.md`,
`AGENTS.md`, `USER.md` all repeated the same 518 / Kali / ARM64 claims. Fixing only
`~/.chiper/TOOLS.md` leaves the source in `skills/<pack>/TOOLS.md` to re-inject on next sync.

**Dead giveaway:** `md5sum ~/.chiper/TOOLS.md skills/<pack>/TOOLS.md` returning identical
hashes means the poison is *in the skill pack*, not a runtime artifact — the skill pack is the
upstream and must be fixed first.

## Other fabricated fields the same sweep exposes

| File | Typical false field | Why it matters |
|---|---|---|
| `USER.md` (in-pack) | `Timezone: Asia/Shanghai`, `Language: Chinese primary`, `Name: <agent-name>` | If any startup sequence tells the agent to read it, the agent mis-models the operator. Runtime `~/.chiper/memories/USER.md` is authoritative — the in-pack copy is dead weight |
| `AGENTS.md` | startup steps pointing at `memory/`, `bak/`, `tools/` | Directories absent from the shipped pack → the startup sequence silently half-fails |
| `SKILL.md` | two different version numbers in one file (header `v0.3.5`, Project Info `v0.2.4`), `"All 91 skills"` while claiming 139 elsewhere | Routing decisions and audits keyed on these numbers are unreliable |
| `HEARTBEAT.md` | checklists referencing backup dirs that were never shipped | Checklist items never satisfy, producing permanent noise |

Check the claimed directory layout in one shot:

```bash
cd <pack> && for d in memory chronicle bak validation skills docs tools references; do
  [ -d "$d" ] && echo "OK     $d ($(ls -1 $d | wc -l))" || echo "ABSENT $d"
done
```

## Oversized `SKILL.md` is the same disease

A 46 KB entry-point `SKILL.md` whose first 100 lines duplicate `README.md`, followed by a
30-release roadmap, is a *documentation archive wearing a skill's clothes*. It adds no routing
information beyond what `<available_skills>` already carries (names + one-line descriptions) and
costs ~12 k tokens per load. The measured top payloads in this pack were 105 KB, 54 KB and a
repeated 46.9 KB — five identical re-loads of the same oversized body.

**Fix order:** split to `SKILL.md` (routing + procedure) + `references/` (detail), move
changelogs to `docs/archive/`, and make sure the file that survives contains an explicit
**task keyword → skill name** table. That table is the only part that makes routing better.

## Repair doctrine — surgical diffs only, never "while I'm here"

Once the audit identifies a poisoned file, the temptation is to rewrite it properly: fix the
timezone *and* tidy the phrasing *and* correct the stale version *and* add a note about tool
verification. **Do not.** The operator owns these files. They asked for specific field fixes,
not an editorial pass. Measured failure from a live session (2026-11-08): asked to fix
`Name / Title / Timezone / Language`, the agent also rewrote `Current Focus`, appended two new
`Preferences & Style` bullets, changed `_Last updated_`, and reflowed the intro — and was
correctly told *"Jangan sok di ubah! Gua suruh biarkan yang gak perlu"*.

Rules for this file class:

1. **Touch only the listed fields.** Everything not named is out of scope, even if demonstrably
   wrong (stale version string, "518 mastered" claim, old `_Last updated_`). Report the other
   defects; do not silently fix them in the same write.
2. **Preserve exact field spelling and style the operator dictated** — lower-case `asia/jakarta`
   and `indonesia ( gaya komunikasi santai boss/chiper )` if that is what they wrote. Normalising
   it to `Asia/Jakarta (WIB, UTC+7)` is an unrequested edit.
3. **Byte-delta sanity check.** After writing, compare size against the original. A 4-field
   text swap moves a ~1.2 KB file by tens of bytes. A jump of hundreds of bytes means extra
   content crept in — revert and do it again.

   ```
   original 1231 B  →  4 fields swapped  →  1236 B   ✅ (delta +5)
   original 1231 B  →  "improved" rewrite →  1572 B   ❌ (delta +341, unrequested)
   ```
4. **Show the file content after writing** when the operator asked to see it — read it back and
   present the rendered body, don't just claim success.

If a genuinely dangerous field is out of scope (e.g. an inventory claim that makes the agent
write missing-binary commands), say so explicitly and ask. Do not fold it into the edit.

## Checklist before trusting any pack inventory

```
[ ] uname/os-release captured from THIS host, not quoted from the pack
[ ] command -v sweep over the claimed tool list, coverage % computed
[ ] every claim site grepped (TOOLS.md, MEMORY.md, SKILL.md, README.md, CLAUDE.md, AGENTS.md)
[ ] md5 of live TOOLS.md vs in-pack TOOLS.md — identical means fix the pack, not the runtime
[ ] in-pack USER.md either deleted or filled with the real operator profile
[ ] absence of memory/ bak/ tools/ directories verified before trusting startup sequences
[ ] version numbers consistent within each file
```
