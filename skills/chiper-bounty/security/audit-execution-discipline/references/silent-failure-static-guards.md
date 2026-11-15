# Static guards for the "failure that pretends to be a result" family

Measured on 2026-10-10 while hardening the audit pipeline. Three separate bugs in code I had
just written produced **silent wrong results** — no crash, no red text, just plausible-looking
output. `ast.parse()` passed every time. These guards live in
`%LOCALAPPDATA%\hermes\scripts\hermes-health-audit.py` and run on every audit.

Why this matters more than a normal bug: a loud failure gets fixed. A silent one gets **reported
as a finding, or as "0 findings"**. The guards below exist because three of them shipped into a
pipeline that then produced a report.

---

## 1. `import_fail` — runtime NameError that syntax checking cannot see

```python
ast.parse(src)          # PASSES
importlib exec the module  # NameError: name 're' is not defined
```

Real case: a patch rewrote `log()` to call `re.match(...)`, but the module never imported `re`.
`ast.parse` is happy — the name only resolves at call time. The orchestrator died **8 seconds
into a run**, after the "run started" log line, which reads like a hang rather than a crash.

**Guard:** import each pipeline script in a subprocess and report a non-zero exit.

```python
code = ("import importlib.util as u, sys\n"
        f"spec = u.spec_from_file_location('m', r'{fp}')\n"
        "m = u.module_from_spec(spec)\n"
        "try:\n    spec.loader.exec_module(m)\nexcept SystemExit:\n    pass\n")
subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=90)
```

---

## 2. `unbound_name_fail` — a name used but bound in no enclosing scope

This one bit **three times in one session** (`nl`, `_nl`, `_re`) every time I injected a helper
into a method whose definition lived in my *patch script*, not the module. Inside a `try/except`
the NameError is swallowed and the caller reports "tool ran with an error" — or worse, writes an
**empty evidence file** and the linter one layer away complains the evidence is "fabricated".

### The trap: a naive check is worse than none

First implementation flagged **37 false positives** — every closure, every `self`, every
`__file__`. A noisy guard gets ignored, which is strictly worse than no guard.

**Scope analysis must walk the ENCLOSING chain, not just the function:**

```python
def own_bindings(node):
    """names bound directly by this scope"""
    b = set()
    for n in ast.walk(node):
        if n is not node and isinstance(n, (FunctionDef, AsyncFunctionDef, ClassDef)):
            b.add(n.name)                      # bound here; its body is its own scope
        elif isinstance(n, Name) and isinstance(n.ctx, Store):
            b.add(n.id)                        # assignment / for / with / comprehension target
        elif isinstance(n, arg):
            b.add(n.arg)                       # parameters (incl. self)
        elif isinstance(n, (Import, ImportFrom)):
            for al in n.names:
                b.add((al.asname or al.name).split(".")[0])
        elif isinstance(n, ExceptHandler) and n.name:
            b.add(n.name)
    return b


def visit(fn, chain):
    scope = own_bindings(fn)
    visible = scope | set().union(*chain) if chain else scope
    visible |= module_bound | set(dir(builtins)) | {"__file__", "__name__", "__doc__"}
    for n in ast.walk(fn):
        if isinstance(n, Name) and isinstance(n.ctx, Load) and n.id not in visible:
            ...
    for sub in fn.body:
        for inner in ast.walk(sub):
            if isinstance(inner, (FunctionDef, AsyncFunctionDef)):
                visit(inner, chain + [scope])   # nested functions inherit the chain
```

`chain` is the list of enclosing scopes. Closures then resolve correctly, `self` comes from the
method's own `args`, and `__file__` is a module-level builtin.

**Narrow the REPORTED set to the names you actually inject.** Reporting every unbound name is
technically correct and practically useless. Restrict to the helper-name class:

```python
if n.id in ("nl", "_nl", "_re", "_json", "_sh", "_dt", "_u2", "_sp",
            "_usage_path", "_log_path", "_ev_file"):
```

That keeps false positives at zero while catching 100% of this bug class.

---

## 3. `budget_arith_fail` — `0` is a valid but FATAL value

Neutralising a wall-clock budget (`_BUDGET = 900` → `None`) is half the change. Every **consumer**
must be updated too, and the two failure modes are different:

| consumer | with `budget = None` / `0` |
|---|---|
| `deadline = time.monotonic() + budget` | **`TypeError: float + NoneType`** → whole layer dies |
| `deadline = time.monotonic() + (budget or 0)` | `0` is falsy but **arithmetically valid** → `deadline = now` → every clue silently marked `SKIPPED_BUDGET`. **No crash. Zero coverage. Worse than the crash.** |

Correct form for both:

```python
deadline = (time.monotonic() + budget) if budget else float("inf")
```

**Guard — match only the two shapes that actually break:**

```python
DANGER = [
    (re.compile(r"time\.monotonic\(\)\s*\+\s*budget"),
     "deadline = monotonic() + budget  -> TypeError when budget is None"),
    (re.compile(r"budget\s*=\s*[^\r\n=]*\bor\s+0\b(?![^\r\n]*#)"),
     "`budget or 0` -> deadline = now -> ALL work silently SKIPPED_BUDGET"),
]
```

**Exclude the safe form and the docs**, or you get noise:

```python
guarded = ("if budget" in line) or ("float(" in line) or ("if not budget" in line)
if pat.search(line) and not guarded:
    bad.append(...)
```

Strip fenced code blocks and the module docstring before scanning:
`text.split('"""', 2)[2]` skips the module docstring; a ``` fence toggle skips examples.

An earlier version also flagged `elif sys.argv[i] == "--budget" and i + 1 < len(sys.argv):` —
arg parsing contains `+` and the word `budget` on the same line. Anchor on `monotonic()`.

---

## 4. Companion guard: `budget or 0` vs the ledger's "produced EMPTY"

Related, and the reason the ledger kept blocking: an artefact that is legitimately empty must be
distinguished from one that was never produced.

```python
if not p.exists():          setu(key, "NOT_RUN", ...)   # never produced -> FAIL
elif p.stat().st_size > 2:  setu(key, "USED", ...)
else:                       setu(key, "N/A", "produced EMPTY (valid artefact, no rows)")  # record, don't fail
```

`exists()` is the fact that matters. Recording the emptiness **explicitly** stops a silent empty
from hiding, without turning "0 candidates → 0 chains" into a gate failure.

---

## 5. The pattern, stated plainly

Every case above is the same shape: **a failure that produces output indistinguishable from
success.** Symptoms and their one-line discriminators:

| symptom | discriminator |
|---|---|
| "tool ran with an error" for everything | suspect YOUR code before the tool — check for swallowed exceptions |
| evidence file "missing" but `ls` shows it | `open(p, "rb").read()` — see `unreadable-evidence-and-av-quarantine.md` |
| gate says "no reason recorded" | `print(list(json.load(open(f))[0].keys()))` — you are reading the wrong field name |
| count looks plausible but disagrees with a sibling number | `isinstance(d, dict)` → `len(d)` counts KEYS, not rows |
| a fix "had no effect" | did you patch the live script or a synced copy? see `toolkit-copy-drift-and-bundle-sync.md` |

**Practice that caught all three this session:** run the new code **once against a real target
dir** — not `ast.parse`, not `import`. Two of the three bugs sat inside `try/except` and were
invisible until the code actually executed with real inputs.
