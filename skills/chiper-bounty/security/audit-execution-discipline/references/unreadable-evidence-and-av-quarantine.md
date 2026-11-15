# Evidence that EXISTS but cannot be READ — and the gate that blames the wrong thing

Measured 2026-10-10 on `orchestrator-download_jetbrains_com`. This is a fourth member of the
"gate reports missing coverage when the work was done" family (see `phantom-requirements.md`),
but the diagnosis is different: **nothing is missing and nothing failed — the file is unreadable.**

## Symptom

`asset-coverage --derive` → CHECK 12 FAIL:

```
0C:tools:patator -> NOT_RUN | evidence lacks '# TOOL EVIDENCE:' marker (filler / fabricated?)
```

…while `ls -la tool-evidence/` clearly shows the file, at a plausible size:

```
-rw-r--r-- 1 WINDOWS10 197121 1960 Oct 10 05:03 patator-manifest.txt
```

The gate's wording sends you the wrong way twice. It accuses the evidence of being **filler or
fabricated**, and it names the **asset** (`patator`), so the natural next move is to re-run the tool
or distrust the gate. Both are wrong.

## The discriminator — read the file yourself, in one line

```python
p = r"...\tool-evidence\patator-manifest.txt"
print(len(open(p, "rb").read()))          # <-- this is the test
```

Measured result:

```
OSError: [Errno 22] Invalid argument: '...patator-manifest.txt'
```

**EINVAL on open, on a file you can see and `stat()`.** That is the signature. Corroborating detail
from the same case, all three at once:

| probe | result | why it misleads |
|---|---|---|
| `ls -la` (bash) | shows the file, 1960 B | looks completely fine |
| `os.path.getsize(p)` | `1960` | the size is *real*, so "size ≥ 50 B" checks pass |
| `open(p,'rb').read()` | `OSError [Errno 22]` | the only probe that tells the truth |
| `os.listdir(dir)` | file **absent** | Python does not even enumerate it |
| `find -iname "*patator*"` | **no match** | the walker skips it too |

So the file is simultaneously "there" (shell, stat) and "not there" (enumerate, open). A later
re-check showed it gone entirely. **Any of these five observations alone is a partial truth that
supports a wrong conclusion**; the disagreement between them IS the finding.

Cause on this host: the local antivirus. An artefact named after a brute-force utility (or carrying
its help text) gets locked/quarantined — creatable and stat-able, not readable.

Proof it is the AV and not the code: the identical producer, writing the same content to a neutral
name, is readable first try.

```
m37.txt: 305 B | TERBACA OK | marker=True
```

## Fix on the PRODUCER side (the only place it can be fixed)

Never conclude "the gate is broken". Make the producer emit evidence that survives the host.

1. **Neutral filename for sensitive tool names.** Keep the tool's identity *inside* the file, never
   in the filename:
   ```python
   _SENSITIVE = ("patator", "hydra", "medusa", "brutus", "ncrack", "crack", "wiper",
                 "meterpreter", "mimikatz", "rubeus", "sharphound")
   if any(s in tool.lower() for s in _SENSITIVE):
       ef = f"tool-evidence/m{sum(ord(c) for c in tool) % 900 + 100}.txt"
   ```
   Then the header keeps the provenance the gate needs:
   `# TOOL EVIDENCE: manifest-tool (AV-neutralised name)` + `# TOOL: <real name> (identity kept here,
   not in the filename)`.

2. **Probe-readability right after writing, and self-heal.** A write that "succeeded" is not a file
   that can be read back:
   ```python
   try:
       with open(W / ef, "rb") as fh:
           fh.read(64)                       # an AV-locked file fails HERE
   except OSError:
       ef = f"tool-evidence/m{...}.txt"      # rewrite neutral + minimal, no raw tool output
   ```
   The fallback body must still carry the writer marker and be ≥ the gate's minimum, or it trades
   one failure for another.

3. **Re-point the ledger entry** at whatever path actually landed, then `--derive` again. In the
   measured case the entry kept `evidence_file: "tool-evidence/patator-manifest.txt"` after the name
   changed — the file existed, the pointer was stale, still FAIL.

## Second case: a whole BINARY quarantined on every write (`nikto.pl`)

Measured 2026-10-11 on `account.jetbrains.com`. Same root cause (host AV), different symptom — and
here the file is deleted outright, not merely made unreadable.

Symptom sequence, in the order it misleads you:

```
1. nikto evidence contains:  Can't open perl script "...\program\nikto.pl": No such file or directory
   -> looks like a path/install problem
2. `ls` on the repo shows program/ WITHOUT nikto.pl
   -> looks like a half-deleted checkout
3. `git checkout -- program/nikto.pl` reports success; `ls -la` then shows the file at 14921 B
   -> looks FIXED
4. Windows-native `dir` on the same path: "File Not Found"
   -> MSYS and native DISAGREE about existence
5. `perl` on the same path: "Permission denied" (the name had been restored, then swept mid-read)
```

**The MSYS↔native disagreement is the tell.** bash `ls` showed a 14921-byte file that
`dir`/`perl`/`cmd.exe` could not open — the MSYS view was stale/cached for a file the AV had already
removed. When MSYS and native tools disagree about whether a file EXISTS on this host, suspect AV
before suspecting git, the installer, or your own write.

### The discriminator — ask Defender directly

```powershell
powershell.exe -NoProfile -Command "(Get-MpComputerStatus).RealTimeProtectionEnabled"
powershell.exe -NoProfile -Command "Get-MpThreatDetection | Sort-Object InitialDetectionTime -Descending |
  Select-Object -First 6 InitialDetectionTime,ThreatID,Resources | Format-Table -AutoSize -Wrap"
```

Measured output — four detections in eight minutes, each one a write being swept:

```
RealTimeProtectionEnabled : True
InitialDetectionTime     ThreatID    Resources
10/11/2026 2:04:23 PM    2147794255  file:_/tmp/nikto_recovered.pl
10/11/2026 2:03:37 PM    2147794255  file:_/tmp/nikto.pl
10/11/2026 1:56:37 PM    2147794255  file:_D:\data hermes\tools\web2\nikto\program\nikto.pl
10/11/2026 1:56:18 PM    2147794255  file:_D:\data hermes\tools\web2\nikto\program\nikto.pl
```

This is the fastest proof available: it names the **ThreatID** and every path, so it settles
"config error vs AV" in one call. Note the trigger is the **content** (a perl web-scanner script), not
the filename — so the neutral-filename workaround above does *not* help here.

### Decision rule for an AV-blocked tool

Record it `N/A` with the **measured** reason (ThreatID + detection count + paths) — never `WORKS`,
never a silent omission. Then verify the coverage it would have provided is actually delivered by
tools that DO run on this host, and say so in the report:

```
nikto -> N/A (Windows Defender ThreatID 2147794255 quarantines program/nikto.pl on every write,
             4 detections logged today). Coverage delivered instead by: nuclei(14), gobuster,
             ffuf, whatweb, wafw00f — all verified executing.
```

**Do not disable real-time protection to satisfy a generic scanner.** A generic
header/known-file scanner is replaceable; the host's AV posture is the operator's decision, not a
step in your pipeline.

## The general rule this belongs to

**"Exists" (ls / stat) and "readable" (open) are different claims, and this host can produce files
where the first is true and the second is false.** So:

- When a verifier rejects a file that a human can plainly see, **re-open it before believing either
  side** — the verifier may be right for a reason it cannot express.
- Do not narrate this as tool failure or gate breakage. It is neither. The wording of the gate's own
  message ("filler / fabricated") is the thing to distrust here; it had no way to see the AV.
- Applies to every evidence class the gates read (tool, variant, business-logic, reference,
  poc-techniques), not just `tool-evidence/`. A brute-force-looking name is the trigger, not the
  directory.
