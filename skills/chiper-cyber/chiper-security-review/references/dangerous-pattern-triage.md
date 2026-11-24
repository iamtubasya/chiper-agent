# Dangerous-Pattern Triage: Whole-Tree Greps vs Production Source

Companion to `chiper-security-review`. Use when the task is **"classify every
dangerous-pattern hit as real risk or benign, with file:line evidence"** on a
Python codebase (especially an agent framework with `skills/`, `plugins/`,
`node_modules`-equivalents, and a checked-in `.venv/`).

---

## 0. The headline pitfall: hit counts almost never reconcile

A dispatch brief or prior scan will often quote counts like
"53 `shell=True`, 127 `eval(`, 61 `pickle.loads`". Those numbers usually come
from a whole-tree grep that swept `.venv/`, `skills/`, `optional-skills/`,
`website/`, `tests/`, and vendored deps — while the actual auditable surface is
production source only.

**Lesson:** never argue with the count, and never repeat it unqualified.
Re-derive it yourself and report **both numbers side by side**:

| pattern | raw tree grep | production source | delta explanation |
|---|---|---|---|
| `pickle.loads` | 61 | 0 | 59 in `.venv/` + skill docs; 2 are the scanner's own rule strings |

Then classify only the production hits. The reconciliation table is itself
reviewer-credible evidence — it proves you didn't skim.

```bash
# Production scope, explicitly enumerated (never grep the repo root)
S="agent gateway tools chiper_cli providers cron plugins tui_gateway web \
   run_agent.py model_tools.py cli.py acp_adapter batch_runner.py \
   mcp_serve.py utils.py"

for p in "shell=True" "os.system(" "pickle.loads" "yaml.load(" \
         "verify=False" "check_hostname"; do
  echo "=== $p: $(grep -rnF "$p" --include=*.py $S 2>/dev/null | wc -l)"
done
echo "=== eval( $(grep -rnE '(^|[^a-zA-Z_.])eval\(' --include=*.py $S | wc -l)"
echo "=== exec( $(grep -rnE '(^|[^a-zA-Z_.])exec\(' --include=*.py $S | wc -l)"

# And always show the excluded-location breakdown for the discrepancy
grep -rn -F "pickle.loads" --include=*.py . | grep -c "\.venv/"
```

**`eval(`/`exec(` need the negative-lookbehind** `(^|[^a-zA-Z_.])` or you drown
in `.eval(`, `model.exec(`, `drivers.exec(` and every prose mention.

---

## 1. Benign classes — say so explicitly, with the reason

Most hits in a mature codebase fall into four "looks dangerous, isn't" buckets.
Naming the bucket is the value of the audit; a bare "benign" is not evidence.

| Bucket | What it looks like | Why it's benign | Anchor the claim |
|---|---|---|---|
| **The scanner auditing itself** | `skills_guard.py:318` `"eval() with string argument"`, `patterns.py:129` reminder text | rule/pattern strings, not call sites | cite the file as the scanner, not the vuln |
| **Prompt/guidance docs** | `patterns.py:165-175` showing `subprocess.run(f"ls {u}", shell=True)` as a *bad example* | content is a string literal never executed | quote the surrounding `reminder`/docstring |
| **Docstrings & comments** | `main.py:7792` "across ``exec()``, so pip…" | comment prose | line must be `#`/docstring |
| **Constant-time-safe loaders** | `yaml.load(v, Loader=CSafeLoader)`, `ruamel.YAML(typ="rt")` | safe constructor; `typ="rt"` cannot build `!!python/object` | cite the Loader/typ line, not just the `load` line |

**Pitfall:** `yaml.load(x)` is not automatically a finding — read the `Loader=`
argument. `SafeLoader`/`CSafeLoader` and ruamel's `typ="rt"`/`typ="safe"` are
safe. Bare `yaml.load(x)` (PyYAML default) is the real one.

---

## 2. Real-risk classes for agent frameworks

Agent frameworks differ from web apps: the *model* is a semi-trusted input
channel, and the *user* is privileged. Classify by **who controls the string**,
not by which sink it reaches.

Ask, in this order, for every `shell=True` / `exec` / `dynamic-import` sink:

1. **Literal?** → benign (note it, e.g. `os.system("cls" if nt else "clear")`).
2. **Env var / user config?** → real but *local-user-only* — rate LOW/MEDIUM,
   never HIGH, and say so. The user owns their own `config.yaml`.
3. **Model-generated / tool-argument?** → this is the real class. Then check
   whether an approval gate or denylist sits in front of it, and **cite the
   gate lines**. A `shell=True` behind `detect_dangerous_command()` +
   `detect_hardline_command()` is MEDIUM-with-mitigation, not CRITICAL.
4. **Third-party data (catalog entry, remote installer URL)?** → supply-chain
   RCE-by-design. Note whether a confirmation prompt shows the command.

Common agent-framework hits and their usual verdicts:

- `subprocess.run(cmd, shell=True)` for a *user-configured command template*
  (STT, TTS, quick commands) — args often `shlex.quote`d but the template body
  still reaches a shell. MEDIUM, local-user-only.
- `curl … | bash` installer as a **literal string** — not injectable, but
  unauthenticated RCE by design. Flag as supply-chain; recommend pinned tag +
  checksum.
- Catalog/plugin `bootstrap` command arrays run with `shell=True` — shipped
  data, so trust = trust in the catalog.
- RPC handlers (`command.dispatch`, `shell.exec`) — the *transport auth* is
  half the finding; trace bind address and token checking before rating.

---

## 3. Don't stop at the sink — verify the adjacent control

Pattern greps find sink syntax. The severity lives in the *guard*, and the
guard is never at the sink line. For each hit class, read the neighbour:

| Sink found | Also read | What makes it benign |
|---|---|---|
| `subprocess` / bake-a-command | approval module | denylist call *immediately above* the run |
| any HTTP client / URL fetch | SSRF module | `is_safe_url` before fetch **and re-check after redirect** |
| any file write with a user path | path helpers | `resolve()` + `relative_to()` (symlink-safe), not just `".." in path` |
| any `!=`/`==` on a signature or token | compare helper | `hmac.compare_digest` — plain `!=` on an HMAC is a LOW/MED timing finding |
| any `verify=` kwarg | verify resolver | resolves to `True`/CA bundle by default; `False` only via explicit user opt-in |
| any webhook handler | secret check ordering | HMAC validated **before** JSON parse; **missing secret → 403, not skip** |

Two high-yield checks that greps miss entirely:

- **Fail-open on missing config.** Grep the webhook/auth handlers for
  `if not secret:` and confirm the branch *returns an error* rather than
  falling through. "No secret configured" selling ciphertext is the classic bug.
- **Post-redirect SSRF.** `is_safe_url(url)` before the request is only half a
  control; look for a second check on `final_url`/`redirect_url` after the
  response lands. Absent that check is the finding.
- **Local-backend exemptions.** A `not _is_local_backend()` prefix on an
  always-blocked-IP check (cloud metadata) is a real hole on a cloud VM, even
  though the comment says "local browser by design."

---

## 4. Write-up format that survived review

Per finding, one tight block — severity, exact `file.py:line`, what controls
the string, exploitability sentence, then a concrete fix:

```
**MEDIUM | tui_gateway/server.py:10655-10656** | `shell.exec` RPC →
`subprocess.run(cmd, shell=True)`. Guarded at 10640-10651 by
`detect_hardline_command` + `detect_dangerous_command` (4005 "use the agent").
| Exploitability: any command not matched by the regex denylist still runs
shell-expanded; transport auth is the other half. | Fix: keep, but document
denylist is heuristic; `shlex.split`+argv for non-pipeline commands.
```

Plus a closing **BENIGN / HIGH-VOLUME PATTERNS** section that maps every big
number to its delta, so the reader can see 127 `eval(` became 0 real calls
without re-running anything.

**Always end with an explicit "issues encountered" line** if you ran out of
budget or could not trace something. Writing `NEEDS-VERIFY` on the Slack /
transport path was better than asserting a vulnerability I hadn't confirmed —
and better than silently dropping the area.

---

## 5. Budget discipline

- Scan *all* patterns in one batched command first (single terminal call, loop
  over patterns) before reading a single file. Confirm the scope dirs exist
  first — a wrong working directory silently produces 0 hits that look like
  "clean."
- If a first grep returns 194 hits across 100 files, that is the signal you
  grepped too wide — re-scope before reading.
- Read files in parallel batches (one turn, 3–4 `read_file` calls) since each
  hit needs ±20 lines of context.
- Do not spend turns on the saturation patterns (`pickle`, `verify=False`) once
  you've established the delta is `.venv/`-only; report the deltas in one
  table and move budget to auth, SSRF, and path containment, where findings
  actually live.
