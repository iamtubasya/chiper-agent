# 03 — Trace exchange (tracestore.py)

Observations appear *during* execution (an error, a response fragment, a hidden param) and often never
become a finding. This keeps them so a LATER step (or another subagent) can reuse them instead of redoing
the work — the ARTEX `search_all_worker_traces` idea.

Storage: `<target_dir>/_traces/traces.jsonl` (append-only) + `_traces/blobs/<sha1>` for big outputs.

## Commands

```bash
python "$S/tracestore.py" "$T" add --step s1 --tool ffuf --cmd "ffuf -u ..." \
      [--output-file out.txt | --output "inline text"] [--error] [--tag idor,vuln] [--worker w1]
python "$S/tracestore.py" "$T" search --q "keyword" [--exclude-step s1] [--limit 10] [--full]
python "$S/tracestore.py" "$T" show --id 3
python "$S/tracestore.py" "$T" list [--step s1] [--limit 20]
python "$S/tracestore.py" "$T" stats
python "$S/tracestore.py" "$T" verify
```

## Notes

- `--exclude-step sN` reproduces ARTEX's "self excluded" rule: search everything EXCEPT your own step,
  so you reuse others' work and do not get fooled by your own earlier output.
- Outputs over ~4k chars spill to a blob automatically (`@blob <sha1>`); `show` re-materialises them.
- `add` auto-flags `is_error` when the body parses as JSON containing `is_error`/`exit_code`.
- For subagents: have each delegated task append its trace under its own step id; the parent then
  searches across all of them. This is the recovery path for delegation that produced no structured output.
