# pySigma / sigma-cli — modern syntax & the validation loop (verified 2026-11-24)

Everything below was verified against a live `sigma-cli` install while generating
`sigma/rules/auth/brute_force.yml` for `chiper-web-auth-bypass`. Each "wrong" line is an error the
validator actually returned — not theory.

## Toolchain

```bash
python3 -m venv /tmp/sigmaenv && /tmp/sigmaenv/bin/pip install sigma-cli
/tmp/sigmaenv/bin/sigma version            # note: NOT --version
/tmp/sigmaenv/bin/sigma --help             # commands: analyze check convert list plugin pysigma version
                                            # there is NO `parse` subcommand anymore
/tmp/sigmaenv/bin/sigma list targets       # "No backends installed" on a fresh install
/tmp/sigmaenv/bin/sigma plugin install splunk   # backend plugins are separate
/tmp/sigmaenv/bin/sigma list pipelines splunk   # splunk_windows / splunk_sysmon_acceleration / splunk_cim
```

- Backend PyPI names are traps: `pip install pysigma-splunk` → *no versions*. Use `sigma plugin install <name>`.
- `sigma-cli convert` **requires a pipeline** unless told otherwise:
  `Processing pipeline required by backend!` → add `-p splunk_cim` (or any id from `sigma list
  pipelines splunk`), or `--without-pipeline` for a raw translation.

## Validation loop (run all three, in this order)

```bash
sigma check  rules/                       # schema + best practice lint -> want 0 errors / 0 issues
sigma convert -t splunk --without-pipeline rules/   # real translation
sigma convert -t splunk -p splunk_cim rules/       # or with a pipeline (needs a mapped logsource)
```

`sigma check` reports `Found 0 errors … 0 issues` yet can still miss a **semantic** bug — always read
the generated query, not just the exit status (see the `group-by` trap below).

## The four syntax errors this session hit (each caught by the validator)

| # | Error returned | Cause | Fix |
|---|---|---|---|
| 1 | *The pipe syntax in Sigma conditions has been deprecated and replaced by Sigma correlations. pySigma doesn't supports this syntax.* | `condition: selection \| count() > 10` (old spec) | split into base rule + **correlation rule** |
| 2 | `InvalidATTACKTagIssue … tag=attack.credential_access` | ATT&CK v14+ tags use **hyphens** | `attack.credential-access` |
| 3 | `SigmaLogsourceError` + `SigmaDetectionError` on the correlation file | classifier keys on `if "correlation" in rule` — the mapping must be **nested** | `correlation:` block, not top-level `type:`/`rules:` |
| 4 | `group_by` parsed as `None` → SPL counted **globally** | `from_dict` reads `correlation_rule.get("group-by")` | key is **`group-by`** (hyphen) |

Error 4 is the dangerous one: no lint error, rule still "works", but it fires on 10 *different*
users failing once each in 5 minutes instead of 10 failures from one source.

## Correlation rule shape (thresholds: ">N in T")

Two files — the correlation references the base rule by its `id`:

```yaml
# rules/auth/brute_failures.yml   (base: the events)
title: Failed Authentication Attempts
id: 6f1c2f5e-3b7a-4d21-9c8e-0a1f5b7d2e44
status: experimental
tags: [attack.credential-access, attack.t1110.001]
logsource: { category: authentication, product: any }
detection:
  selection: { event.outcome: failure }
  condition: selection
level: medium
```

```yaml
# rules/auth/brute_force.yml      (the threshold — the file skills actually reference)
title: Brute Force Authentication Failures
id: b7e4a91d-5c62-4f88-a3d1-9e0f2c6b8a55
correlation:
  type: event_count          # event_count | value_count | temporal | temporal_ordered
  rules: [6f1c2f5e-3b7a-4d21-9c8e-0a1f5b7d2e44]
  timespan: 5m
  group-by: [source.ip]      # HYPHEN; omit and you count globally
  condition: { gte: 10 }     # mapping: exactly one of lt/lte/gt/gte/eq/neq
```

Accepted keys come from the installed source — read it instead of guessing:
`grep -n "correlation_rule.get" <venv>/lib/python*/site-packages/sigma/correlations.py`
(lines ~581–646: `type`, `rules`, `generate`, `group-by`, …) and the document classifier at
`<venv>/lib/python*/site-packages/sigma/collection.py` (`if "correlation" in rule:`).

Generated SPL for the pair above:

```
event.outcome="failure"
| bin _time span=5m
| stats count as event_count by _time source.ip
| search event_count >= 10
```

If the `by … source.ip` clause is missing from that output, `group-by` did not parse — fix the key,
do not ship it.

## Correlation without a pipeline

Generic logsources (`category: authentication`, `product: any`) are unmapped, so pipeline-based
conversion fails with *Rule type not yet supported by the … pipeline*. Use `--without-pipeline`
for generic logsources, or give the rule a logsource a pipeline knows (`windows`/`sysmon`).
