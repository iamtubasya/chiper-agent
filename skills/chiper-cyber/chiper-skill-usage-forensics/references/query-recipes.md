# Query Recipes

All recipes are read-only Python stdlib. Run under `execute_code` or plain `python3`.
Nothing here writes to `~/.chiper`.

## Timeline with session + file + follow-up classification

```python
import sqlite3, json, datetime, collections

DB = "/home/agentuser/.chiper/state.db"
c = sqlite3.connect(DB)
c.row_factory = sqlite3.Row

rows = list(c.execute(
    "SELECT id, session_id, role, tool_calls, timestamp FROM messages "
    "WHERE role='assistant' AND tool_calls LIKE '%\"skill_view\"%' "
    "ORDER BY timestamp"
))

events, all_calls = [], []
for r in rows:
    try:
        tcs = json.loads(r["tool_calls"])
    except Exception:
        continue
    if not isinstance(tcs, list):
        continue
    for tc in tcs:
        fn = (tc or {}).get("function") or {}
        nm = fn.get("name")
        if not nm:
            continue
        try:
            a = json.loads(fn.get("arguments") or "{}")
        except Exception:
            a = {}
        rec = {"ts": r["timestamp"], "session": r["session_id"], "tool": nm, "args": a}
        all_calls.append(rec)
        if nm == "skill_view":
            events.append(rec)

def follow_ups(sv, window=300):
    return [x for x in all_calls
            if x["session"] == sv["session"]
            and x["ts"] > sv["ts"]
            and x["ts"] - sv["ts"] <= window
            and x["tool"] != "skill_view"]

for e in events:
    f = follow_ups(e)
    status = "USED" if f else "VIEW-ONLY"
    tools = ",".join(dict.fromkeys(x["tool"] for x in f))[:40]
    print(f'{datetime.datetime.fromtimestamp(e["ts"]):%Y-%m-%d %H:%M} '
          f'{status:<10} {str(e["args"].get("name")):<45} follow={len(f)} {tools}')
```

Note: this only sees `skill_view`. To attribute *other* tool calls you must widen the
initial query to all assistant rows — the narrow `LIKE` filter above is deliberate
when you only need the skill timeline.

## Token cost from the executor log

```python
import re, glob, collections

LINE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ (\w+) \[([^\]]*)\] (.*)$')
OK   = re.compile(r'tool (\w+) completed \(([\d.]+)s, (\d+) chars\)')
FAIL = re.compile(r'Tool (\w+) returned error \(([\d.]+)s\): (.*)')

calls, failures = [], []
for path in glob.glob("/home/agentuser/.chiper/logs/agent.log*"):
    for line in open(path, encoding="utf-8", errors="replace"):
        m = LINE.match(line.strip())
        if not m:
            continue
        ts, lvl, sess, msg = m.groups()
        if "skill" not in msg.lower():
            continue
        m2 = OK.search(msg)
        if m2:
            calls.append({"ts": ts, "sess": sess, "tool": m2.group(1),
                          "dur": float(m2.group(2)), "chars": int(m2.group(3))})
            continue
        m3 = FAIL.search(msg)
        if m3:
            failures.append({"ts": ts, "sess": sess, "tool": m3.group(1),
                             "dur": float(m3.group(2)), "err": m3.group(3)[:120]})

calls.sort(key=lambda x: x["ts"])          # filename order is NOT chronological
views = [c for c in calls if c["tool"] == "skill_view"]
total_chars = sum(c["chars"] for c in views)
print("skill_view calls:", len(views))
print("avg payload:", round(total_chars / max(len(views), 1)), "chars")
print("total payload:", total_chars, "chars  ~", round(total_chars / 4), "tokens")
print("failures:", len(failures), "/", len(calls))
for c in sorted(views, key=lambda x: -x["chars"])[:10]:
    print(f'{c["ts"]}  {c["chars"]:>7,} chars  {c["dur"]:>5.2f}s  [{c["sess"]}]')
```

## Lifetime aggregate with forked-key normalisation

```python
import json, collections
d = json.load(open("/home/agentuser/.chiper/skills/.usage.json"))

agg = collections.Counter()
last = {}
for k, r in d.items():
    base = k.split(":")[-1]            # collapse plugin:skill -> skill
    agg[base] += r.get("view_count", 0)
    ts = r.get("last_used_at")
    if ts and ts > last.get(base, ""):
        last[base] = ts

for name, n in agg.most_common():
    print(f"{n:>4}x  {name:<45} last={last.get(name)}")
print("records:", len(d), "distinct after normalise:", len(agg))
```

## Dead-skill detector

```python
import json, pathlib, collections

d = json.load(open("/home/agentuser/.chiper/skills/.usage.json"))
used = {k.split(":")[-1] for k, r in d.items() if r.get("view_count", 0) > 0}

root = pathlib.Path("/home/agentuser/.chiper/skills")
installed = {p.parent.name for p in root.rglob("SKILL.md")}
never = sorted(installed - used)

print(f"installed={len(installed)}  ever-used={len(used & installed)}  never={len(never)}")
print(f"coverage={len(used & installed)/max(len(installed),1):.1%}")
for n in never[:40]:
    print("  ", n)
```

## Success / failure tally by tool (log only)

```python
import collections, re, glob
# reuse LINE / OK / FAIL from the token-cost recipe
tally = collections.Counter()
for path in glob.glob("/home/agentuser/.chiper/logs/agent.log*"):
    for line in open(path, encoding="utf-8", errors="replace"):
        m = LINE.match(line.strip())
        if not m or "skill" not in m.group(4).lower():
            continue
        if (m2 := OK.search(m.group(4))):
            tally[(m2.group(1), "ok")] += 1
        elif (m3 := FAIL.search(m.group(4))):
            tally[(m3.group(1), "fail")] += 1
for (tool, kind), n in tally.most_common():
    print(f"{n:>4}x  {tool:<16} {kind}")
```

## Notes on accuracy

- Duplicate events appear if the same tool call is logged in more than one rotated file
  boundary; de-duplicate on `(ts, sess, tool, chars)` if exact totals matter.
- `.usage.json` is written under an flock; a concurrent curator run can make a read
  briefly stale. Re-read rather than caching across minutes.
- Never write to `.usage.json` during an audit — the counter bumps are best-effort and
  a half-written file breaks the curator's staleness maths.
