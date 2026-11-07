# Floor Guard — the five non-negotiables

> Reference implementation of the *floor* (the checks that sit below the
> scored dimensions). Diff-scoped, exit `0`/`1`/`2`, patterns adaptable per
> ecosystem. Adapt this file rather than writing a fresh checker each run —
> that is the whole point: one mechanism, same across runs and stacks.

## Why a floor at all

The numbered quality dimensions each name a de-facto tool (tsc, eslint, semgrep,
axe, gitleaks). The floor is different: it has no single tool, and an agent asked
to "enforce the floor" tends to invent a checker from scratch. Two agents →
two different checkers → the bar drifts. This file pins it.

## The five floor checks

| # | Check | Why it is floor-level | Default pattern |
|---|-------|----------------------|-----------------|
| 1 | **No suppressed diagnostics** | Silencing a linter/compiler to get green is the canonical fake pass | `# noqa`, `// eslint-disable`, `@ts-ignore`, `# type: ignore` |
| 2 | **No skipped / focused tests** | `.skip`/`.only` silently removes coverage from CI | `it.skip`, `test.only`, `@pytest.mark.skip`, `xit(` |
| 3 | **No debug artifacts** | Leftover prints leak data and signal an unfinished change | `console.log`, `print(`, `debugger`, `fmt.Println` |
| 4 | **No hardcoded secrets** | A credential in the diff is an incident, not a nit | AKIA…, `sk-live_`, PEM headers, long high-entropy strings |
| 5 | **No disabled security checks** | Turning off TLS verification / CSRF / auth is a real regression | `verify=False`, `InsecureSkipVerify`, `csrf_exempt`, `--insecure` |

## Exit-code contract

```
0   clean — nothing on the floor was tripped by the diff
1   violation found — report it, do NOT auto-fix silently
2   checker could not run (bad args, not a git repo) — never a silent pass
```

Exit `2` is loud on purpose: a floor check that *cannot run* must not look like
a floor check that *passed*.

## Diff-scoping

Only the changed lines are checked. A pre-existing `// eslint-disable` on line 4
of an untouched file is not this change's problem; the same text on an added line
is. Scope with `git diff --unified=0 <base>...HEAD` and match on `+` lines.

## Adapting per ecosystem

The patterns above are language-agnostic defaults. Tighten or swap them:

- **Python** — add `# pylint: disable`, `pytest.mark.xfail`; keep `# noqa`.
- **Go** — `//nolint`, `t.Skip(`, `log.Print`.
- **Rust** — `#[allow(`, `#[ignore]`, `dbg!`, `unwrap()` on fallible I/O.
- **TS/JS** — `@ts-expect-error`, `jest.skip`, `eslint-disable-next-line`.

## Non-goals

- This is **not** the scored quality gate (that is `scripts/quality-gate.mjs`).
  The floor is binary: tripped or not. No percentages, no scoring.
- Do not auto-remediate. A floor violation is a conversation — the diff author
  decided to suppress something and may have a reason worth hearing.
