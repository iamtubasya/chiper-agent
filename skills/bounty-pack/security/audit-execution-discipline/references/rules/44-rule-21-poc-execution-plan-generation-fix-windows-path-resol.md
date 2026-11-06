## ⛔ RULE 21: POC Execution Plan Generation Fix (Windows path resolution)

**Live discovery (2026-09-24):** `track-poc-execution.py`'s `generate_plan()` always returned `None` because it tried to parse `poc-pipeline.py full`'s stdout as JSON — but the script writes a human-readable banner to stdout AND saves machine-readable JSON to `~/AppData/Local/hermes/poc-plans/<target>.json`. Reading stdout failed → `NO_POC_MATCHED` → 0 PoCs executed → Gate C8 (`poc-variant-usage.json empty`) failed repeatedly.

**The FIX:** Change `generate_plan()` to **read the saved plan file first**, only fall back to stdout parsing if the file is missing.

```python
def generate_plan(target, tech_list):
    """Run poc-pipeline.py full; read the JSON plan it saves to disk.

    Note: poc-pipeline 'full' prints a human-readable banner to stdout and
    writes the machine-readable plan to OUTPUT_DIR/<target>.json — it does NOT
    print JSON to stdout. So read the saved file (fall back to stdout parse).
    """
    cmd = f'python "{SCRIPTS_DIR}/poc-pipeline.py" full "{target}" --tech "{tech_list}"'
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        log(f"⚠️  poc-pipeline.py exit {r.returncode}: {r.stderr[:300]}")
        return None

    # Primary: read the JSON plan poc-pipeline saves (OUTPUT_DIR/<target>.json)
    out_dir = Path(os.path.expanduser("~/AppData/Local/hermes/poc-plans"))
    safe = target.replace("https://", "").replace("http://", "").replace("/", "_")
    plan_file = out_dir / f"{safe}.json"
    if plan_file.exists():
        try:
            plan = json.loads(plan_file.read_text())
            if isinstance(plan, dict) and "plan" in plan:
                return plan
        except Exception as e:
            log(f"⚠️  Could not read plan file {plan_file.name}: {e}")

    # Fallback: parse JSON from stdout (older poc-pipeline printed JSON)
    try:
        start = r.stdout.index("{")
        plan = json.loads(r.stdout[start:])
        return plan
    except (ValueError, json.JSONDecodeError):
        log("⚠️  Could not parse plan from poc-pipeline output")
        return None
```

Also ensure `--tech` is passed properly (orchestrator used positional arg without flag earlier). Add `import os` at top for `os.path.expanduser()`.

> **Debugging transcript:** `references/session-lessons/orchestrator-poc-plan-fix-2026-09-24.md` — full conversation transcript showing the triple-rework loop until the fix landed.

