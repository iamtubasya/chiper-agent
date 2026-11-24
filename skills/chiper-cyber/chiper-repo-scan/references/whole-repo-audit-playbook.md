# Whole-Repository Audit — Orchestration Playbook

How to run a full audit ("audit keseluruhan", "full security review", "review
this whole repo") of a large codebase without drowning in its own grep noise,
and without reporting self-reported subagent claims as verified fact.

Derived from a 2026 full audit of a ~470K-LOC Python agent framework
(933K LOC incl. tests, 10k `.py` files, 1.5 GB with `.venv`).

---

## Phase 0 — Baseline before any opinion

Get the shape first. Five commands, all cheap:

```bash
git log --oneline -3                       # what am I actually looking at
ls                                          # layout
find . -name "*.py" -not -path "./.git/*" -not -path "*/node_modules/*" | wc -l
du -sh --exclude=.git .
find . -name "*.py" -not -path "./.venv/*" -not -path "./tests/*" | xargs wc -l | sort -rn | head -25
```

Then read whatever design doc the repo ships (`AGENTS.md`, `CONTRIBUTING.md`,
`ARCHITECTURE.md`). In repos with a written contribution rubric, that rubric
**is** the quality standard — audit against it, quote it, don't invent your own.

**Always scope out `.venv/`, `node_modules/`, `site-packages/`.** A raw
`grep -r` over the repo root counts the entire dependency tree. Observed
mismatch: `shell=True` raw count 53 vs production count **6**; `eval(` 127 vs
**0**; `pickle.loads` 61 vs **0**; `verify=False` 52 vs **0**. Reporting the
raw number as a finding is a credibility-killing first paragraph. Report both
numbers and say which is real.

---

## Phase 1 — Parallelize, then verify

A full audit is 4-6 independent workstreams. Delegate them, but **every
subagent summary is a self-report, not a fact**. Independently re-read the
top findings yourself before they enter the report.

| Workstream | Prompt shape | What to demand back |
|---|---|---|
| Static security | Classify *every* dangerous-pattern hit as real or benign, with `file:line` | Per-hit verdict + a "benign/high-volume" section |
| Architecture + quality | Module map, god files with largest-function LOC, dead code, duplication | Quantified tables + `file:line` |
| Dependencies | Lockfile-wide CVE audit, version consistency, CI inventory | Per-package advisories + fix version |
| Docs vs reality | Fetch published docs, diff against live CLI/registry | Claim-vs-reality table, both sides cited |

Give each subagent: absolute repo path, the exclusion list, the `AGENTS.md`
location, the output format, an explicit "do NOT modify files", and a word cap.
Ask for **English output** if the report will be translated, so the summary
doesn't arrive half-localized.

**Verification pattern that worked:** after subagents return, pick the 6-8
highest-severity claims and read the actual lines. In the 2026 audit all 8
critical findings held up, but two subagent summaries carried wrong numbers
(hit counts from the wrong scope) and one carried a wrong file count for a
security-relevant package registry. Verification cost ~8 reads and prevented
four bad lines in the report.

**Verify against the live artifact where possible.** For claim-vs-reality
("docs say N tools, code has M"), don't count by grepping — import the actual
registry and print `len()`. And check whether the *published* site/package
exists at all before diffing its content:

```bash
curl -sI https://<org>.github.io/<repo>/docs | head -1     # 404?
curl -s https://api.github.com/repos/<org>/<repo> | grep has_pages
curl -sI https://pypi.org/pypi/<package>/json | head -1    # 404?
```

A 404 there is a *headline finding*: every README install command is dead.

---

## Phase 2 — Findings that only appear in a whole-repo read

These categories are invisible to per-file scanners and only surface when you
hold the design doc, the git history, and the code together.

**Cache / invariant violations.** In agent frameworks (and any long-running
conversational service) the expensive asset is a cached prompt prefix. Grep
for mid-conversation mutation of the system prompt, tool list, or model
reference. Look for `_cached_system_prompt =`, in-place `agent.tools` edits,
and runtime toolset swaps outside the compression path. Report the *cost
model* (every subsequent turn pays full prefix), not just "inconsistent
state" — that's what makes it a P1 in a fix queue.

**Parallel code paths that should be one.** Multiple implementations of the
same operation mean fixes miss siblings. Concrete instance: a gateway had three
agent-run paths (`_run_agent`, `_run_agent_via_proxy`, an embedded one) so a
fix applied to one silently missed platform users on the others. One-line
symptom to look for: two or three functions with near-identical names and
near-identical bodies.

**Duplicated canonical helpers.** `get_<app>_home()`, `_load_config()`,
`_truncate()`, `_parse_iso_timestamp()` reimplemented 3-12×. Each copy is a
divergence waiting to happen. AST body-hashing finds these fast — or grep the
function name and count definitions.

**Env-var / path portability bypass.** If the repo has a canonical home-dir
resolver, grep for `Path.home()` and direct `.config/<app>` construction that
bypasses it. Every bypass is a path that breaks under a non-standard install
root, container, or multi-profile setup — and it silently passes tests because
the test harness sets the canonical var.

**Security guard with a permissive condition.** The highest-value SSRF/priv-esc
findings are guards that are correct *except* for one `and not X` clause:
`if not _is_local_backend() and _is_blocked(url)`. Enumerate every guard's
boolean condition and ask which branch is unchecked. A guard whose comment
explains exactly the attack it wants to stop, wrapped in a condition that lets
that attack through, is the most reportable class of finding there is.

**Guard-consistency gaps across sibling adapters.** If a webhook platform
verifies HMAC with `compare_digest` in 5 adapters and plain `!=` in the 6th,
the 6th is the finding. Diff the security idiom across adapters, not just
against theory.

**Test-suite shape.** Ratio test-LOC : source-LOC (0.6-1.2 : 1 is healthy).
Then check *what* is tested: contract assertions vs change-detector snapshots
(`assert len(registry) == 71`, hardcoded model-name lists). Then check for
over-mocking — a test file with 130 `patch(` and 5 asserts is asserting the
mocks, not the behavior. Report the hermeticity harness (does `conftest.py`
build a temp app-home?) because that determines whether the suite catches
environment regressions.

---

## Phase 3 — Report shape

One file. Lead with a scored table so the reader knows the shape in five
seconds, then severity-ordered findings, then a phased action list.

```markdown
## 0. RINGKASAN EKSEKUTIF
| Aspek | Skor | Verdict |

## 1. TEMUAN SECURITY
### CRITICAL / HIGH / MEDIUM / LOW-INFO
each: ID · title · Lokasi (file:line) · Bukti · Dampak · Fix

## 1b. YANG SUDAH BAIK (jangan diutak-atik)
## 2. DEPENDENCY AUDIT (table: package | pin | fix | gap)
## 3. CODE QUALITY (god files, duplication, dead code, invariants)
## 4. CI/CD (present vs missing, one line per missing gate)
## 5. GAP: DOCS vs REALITA
## 6. PRIORITAS AKSI  (P0 this week / P1 sprint / P2 month / P3 publish)
## 7. LAMPIRAN — METODE & BATAS (tools, coverage, honest limits)
```

Rules that make it land:

- **Every finding carries `file:line`.** A finding without a line number gets
  triaged as noise.
- **Section "what's already good" is not padding.** It tells the reader which
  subsystems to leave alone and proves you read the code rather than only
  grepping it. It also prevents the report from being read as "the project is
  broken."
- **P0 = 5-7 items max, each one concrete edit.** "Bump X to Y", "wrap in
  `hmac.compare_digest`". If P0 has 20 items it is a backlog, not a priority.
- **State limits honestly in an appendix.** Which URLs failed to fetch, which
  findings are `NEEDS-VERIFY`, what the CVE snapshot date is. CVE counts move
  daily; date-stamp them.
- **Report the missing gate, not just the symptom.** "318 advisories" is a
  triage marathon. "Nothing in your CI could ever have surfaced these" is the
  fixable root cause. Pair each class of finding with the one workflow/gate
  that would have caught it.
- **Confirm the repo is untouched at the end**: `git status --short` empty.
  Say so explicitly.

---

## Pitfalls

**Don't trust the subagent's file count for a security-relevant artifact.**
One subagent correctly noted docs claimed a tool that "absent from registry",
but the import path used to check excluded plugin registration — the tool was
present. Re-run the registry check yourself with the plugin-enabled import
before reporting absence.

**Don't let a subagent's "everything is fine" end the workstream.** A strong
verdict on the authz layer is a finding too — record *why* it's strong
(default-deny, fail-closed on missing secret, `compare_digest` at every site)
so a future regression is measured against a named baseline.

**Don't audit the installed environment and call it a dependency audit.**
See `chiper-supply-chain-security/references/lockfile-audit-vs-venv.md`.

**Don't open the report with a raw grep count.** `grep -r "shell=True" | wc -l`
across the repo root counts `.venv/`. Lead with the production-scope number and
footnote the raw one.

**Don't call a pattern a vulnerability before reading the guard.**
`tarfile.extractall` flagged HIGH by bandit had a manual `..`/absolute-path
member check two lines above — real remaining risk was symlink members only.
Read the surrounding 15 lines before assigning severity. Bandit's own output
triage for a 300K-LOC Python repo: 23 HIGH, of which 19 were non-security
`hashlib` use, 5 were the genuine `shell=True` set, 1 was guarded `tarfile`,
1 was a false-positive bidirectional-char "trojansource" hit on an emoji
comment.
