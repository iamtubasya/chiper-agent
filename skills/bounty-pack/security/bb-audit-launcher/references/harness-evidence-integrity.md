# Harness evidence integrity — how a scanner sweep fabricates coverage

Source: Vinted engagement (Bugcrowd `vinted-uab-mbb`), 2026-10-01. A sweep harness was written to
close a real coverage gap. It reported **40/40 tools EXECUTED** and produced **zero useful evidence**.
Every failure below looked like a result; none of them were. Read this before writing any harness
that fans tools out over a host list.

## 0. The user challenge that started it

> "yakin kamu udh pakai all tools dan varian attack dengan phase lengkap dr 0a k 0f?"

The honest answer was **no**, and the mechanical proof took two commands:

```bash
# 1. what the pipeline is supposed to have produced
find <workspace> -name tools-usage.json -o -name variant-usage.json \
     -o -name business-logic-usage.json -o -name poc-execution.json \
     -o -name poc-variant-usage.json -o -name findings.json \
     -o -name validated-findings.json -o -name review-candidates.json
# -> ALL MISSING

# 2. did the orchestrator ever run for this target
ls -d ~/.chiper/skills/bounty-pack/poc-plans/orchestrator-*<target>*      # -> does not exist
```

Real state: 0A + 0B done properly, 0C manual/partial, **C2/C3/C4/C5 + 0D + 0E + 0F never executed**.
The manual negatives were genuine; the *completeness* claim was not. Separate the two sentences
forever: "every surface I could reach was tested manually and is clean" ≠ "all tools, all variants,
0A-0F complete".

## 1. Answer "did you use ALL tools?" by diffing two lists — never from memory

```bash
# universe that exists on this box
for t in subfinder httpx naabu katana gau waybackurls ffuf gobuster dirsearch nuclei dalfox \
         sqlmap arjun kxss interactsh-client CORScanner commix graphqlmap SSRFmap race-checker \
         nmap whatweb wpscan nikto testssl sslscan jwt_tool tplmap sstimap xsstrike feroxbuster smuggler; do
  printf "%-18s " "$t"; command -v $t >/dev/null 2>&1 && echo INSTALLED || echo not-installed
done

# what actually fired (evidence on disk, not the status field)
ls -la <workspace>/tool-evidence/ <workspace>/*usage.json
```

Three honest classes, and only the middle one is embarrassing:

| Class | Meaning |
|---|---|
| NOT-INSTALLED | honest N-A on this host; name it as a coverage gap |
| **INSTALLED but never fired** | the real gap — check this before answering |
| RAN but evidenced only by an error banner | covered by RULE 2c body-read in the parent skill |

## 2. Bug: the shell-quoted command header breaks the shell, so nothing runs

Written naively, the "prove which command ran" header **became** the command:

```bash
echo "=== CMD: nuclei -u "https://host" -t "D:/tmpl" ..." > out.txt ; ( nuclei ... ) >> out.txt
#           ^^^^^^^^^^^^ nested double quotes -> shell parse ends here
```

Symptom: **every tool finishes in 0.1-0.2 s** and the evidence file contains only a quoted copy of the
command string. A 0.1 s scanner run is physically impossible — that is the tell.

**Fix: never interpolate the command into the shell. Write the header from Python, hand the tool a
file handle.**

```python
with open(evidence, "w", encoding="utf-8") as fh:
    fh.write(f"=== TOOL   : {tool}\n=== TARGET : {target}\n=== CMD    : {cmd}\n"
             f"=== START  : {datetime.now().isoformat()}\n\n")
    fh.flush()
    try:
        p = subprocess.run(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT, timeout=timeout)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        rc = "TIMEOUT"
    fh.write(f"\n=== END    : {datetime.now().isoformat()}  rc={rc} ===\n")
```

## 3. Bug: `capture_output=True` + `shell=True` defeats your own timeout

A grandchild (nuclei/gobuster) inherits the stdout **pipe**. `subprocess.run(timeout=)` kills only the
`cmd.exe` shell; the grandchild keeps the pipe open and the read never returns. Observed: a `timeout=420`
call still running at 8 minutes with the wrapper blocked, long past 420 s — the same leak shape as the
interactsh zombie-process pitfall in the parent skill.

Fixes, either is sufficient:
- **`stdout=fh` (a real file object)** — no pipe exists, so the timeout fires cleanly. Preferred.
- On timeout, tree-kill the tool: `taskkill /F /T /PID <pid>` (Windows) and re-check the process list.

Always verify afterwards, because a "stopped" scan can still be hitting the target:

```bash
tasklist | grep -iE "nuclei|gobuster|dalfox|sqlmap|CORScanner"   # count survivors
```

## 4. Bug: status derived from "the command returned" — false EXECUTED

A first cut marked `EXECUTED` whenever the process exited 0 and the end-marker was present. That is
true for a tool that printed a **usage banner** and exited 0. All 40 entries were fiction.

Derive the status from **the tool's own banner plus the exit sentinel**:

| Signal in the evidence body | Status |
|---|---|
| `Usage:` / `flag provided but not defined` / `unknown command` / `unrecognized arguments` / `required: -r` | `FAILED_USAGE` — never scanned, blocks the report |
| `Access Denied` / `Just a moment` / `You have been blocked` / `RBAC: access denied` / `captcha-delivery` **and the tool banner absent** | `BLOCKED_EDGE` |
| tool's banner absent (e.g. `Gobuster v`, `Dalfox`, `CORScanner` ASCII art) | `FAILED` |
| banner present, rc == 0, no findings | `EXECUTED` (or `NO_OUTPUT`) — the usable negative |
| banner present, rc != 0 | `RAN_WITH_ERROR` |
| `=== END` line never written | `TIMEOUT` |

Two consequences worth engineering in on purpose:

- **Keep the banner** — do not pass `-q`/`-silent` to a tool whose banner you need as proof-of-run.
  `gobuster` without `-q` prints `Gobuster v3.8.2`; that line *is* the evidence.
- **Print the end sentinel from Python**, so "the file has a header but no END" unambiguously means
  "still running / killed", which is exactly the case RULE 2c-bis warns about.

## 5. Bug: the sweep used the wrong wordlist and the scanner's default UA

- Picking a wordlist with `os.listdir(dir)[0]` grabbed `security-headers.txt` instead of
  `sensitive-files-wordlist.txt`. **Name the file explicitly; never index a directory listing.**
- `gobuster` prints `User-Agent: gobuster/3.8.2` by default. Scanner default UAs are the single most
  common cause of an all-403 result set (see `bot-protected-target-testing` §3a). Pass a browser UA:
  `-a "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ... Chrome/128.0.0.0 Safari/537.36"`.

## 6. Bug: output buffering hid the whole run

Backgrounding with `python sweep.py > log 2>&1` block-buffers stdout, so a killed run loses every line
it "printed". Run `PYTHONUNBUFFERED=1 python -u sweep.py` and keep `flush=True` on progress prints —
otherwise you cannot tell "still on host 1" from "finished long ago".

## 7. What a correct sweep costs, and what it is actually worth

Budget honestly: ~10 in-scope hosts × 4 tools, with nuclei needing ~330 s per host on a 13.7k-template
mirror, is **60-90 minutes** of background time. Say that up front rather than discovering it mid-run.

And set expectations correctly: on a bot-managed primary host nearly every scanner will land on
`BLOCKED_EDGE`, and most programs declare scanner output non-reportable. The sweep's value is
**evidence + a 0D gate that is genuinely earned** — not new findings. State that instead of letting the
reader expect a finding from it.
