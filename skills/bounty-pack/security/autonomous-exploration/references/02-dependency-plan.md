# 02 — Dependency plan (chainplan.py)

A real chain is ordered: find injection -> get creds -> lateral -> privesc. Parallelising it tangles it.
`chainplan.py` keeps ONE plan per target and releases only the next step whose prerequisites are met.

Storage: `<target_dir>/_plan/chain.json` (NOT `plan.json`, which belongs to poc-pipeline).

## Commands

```bash
python "$S/chainplan.py" "$T" init --target <name>
python "$S/chainplan.py" "$T" add --id s1 --desc "confirm injection point" --phase 0C [--prereq s0] [--requires-fact 12]
python "$S/chainplan.py" "$T" next        # the ONLY step you may dispatch now (gate)
python "$S/chainplan.py" "$T" done  --id s1 [--fact 15] [--note ".."]
python "$S/chainplan.py" "$T" fail  --id s1 --why "WAF filtered"
python "$S/chainplan.py" "$T" block --id s1 --why "awaiting creds"
python "$S/chainplan.py" "$T" status
python "$S/chainplan.py" "$T" render [--out chain.md]
python "$S/chainplan.py" "$T" verify
```

## How the gate decides

`next` returns the first `pending` step whose:
1. every `--prereq <step id>` is `done`, AND
2. if `--requires-fact <node_id>` is set, that node EXISTS in `_graph/graph.db` and is a
   confirmed/origin `fact`.

That second clause is the real cross-tool link: a step cannot start before the fact it depends on
actually exists in the dual graph. (Proven: step blocked on a missing fact -> create the fact ->
`next` flips the step to ready.)

If no step is dispatchable it says so and why ("waiting on prereq [...]" / "waiting on fact #N").
`done` echoes the newly-dispatchable step, so completion and next-step line up.

## Rules

- Do not run step N+1 "because it will probably work". Ask `next`.
- `blocked` = awaiting an external thing (creds, approval). `failed` = tried and it did not work.
  `blocked` keeps the chain alive; `failed` means re-plan that step.
- Keep steps coarse ("get creds"), not micro ("run curl"). The plan is the spine, the graph is the tissue.
