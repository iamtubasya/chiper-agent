# 01 — Dual graph (dualgraph.py)

Two graphs, one bridge. Storage: SQLite at `<target_dir>/_graph/graph.db` (WAL mode).

- **Asset graph** (`assets`) — the *things*, globally reusable across targets.
  Columns: type, value, company, task, ip, port, root_domain, url, tech(json), status_code, title,
  extra, first_seen, last_seen. `UNIQUE(type,value)` makes re-adding idempotent (upsert).
  Types: root_domain | ip | subdomain | app | service | endpoint
- **Exploration graph** (`nodes` + `edges`) — the *thinking*, per target.
  Node kinds + their legal states:
    goal    : open | met | abandoned
    intent  : open | running | paused | done | blocked | exhausted | stopped
    fact    : confirmed | dismissed | origin
    finding : confirmed | dismissed
    hint    : active | consumed
  Edge rels: spawns | derived_from | yields | proves | covers  (no self-edges)
- **Bridge** (`anchors(node_id, asset_id)`) — the ONLY link. From an asset you can ask which intents
  touched it and what facts resulted; from an intent you can ask which assets it targets.

## Commands

```bash
python "$S/dualgraph.py" "$T" init
python "$S/dualgraph.py" "$T" asset add --type endpoint --value "https://h/x" \
      [--company C --task T --ip 1.2.3.4 --port 443 --url U --tech "a,b" --status 200 --title ".."]
python "$S/dualgraph.py" "$T" node add --kind fact --title "one-line conclusion" \
      [--state confirmed] [--detail ".."] [--evidence "cmd + 1-2 proof lines"] \
      [--confidence observed|inferred] [--owner w1] [--asset 3 --asset 7]
python "$S/dualgraph.py" "$T" edge add --src 5 --dst 9 --rel yields
python "$S/dualgraph.py" "$T" anchor --node 5 --asset 3
python "$S/dualgraph.py" "$T" query coverage|lineage|open|orphans|assets|nodes|stats [--node ID] [--table]
python "$S/dualgraph.py" "$T" render [--out graph.md]
python "$S/dualgraph.py" "$T" verify
```

`node add --asset` anchors in the same call — prefer that over a separate `anchor`.

## What the queries answer

- `coverage` — per asset: how many nodes anchored it, split by intents/facts/findings + `untested_assets`.
- `orphans` — assets with ZERO anchored node = genuinely not yet touched.
- `lineage --node N` — ancestors (derived_from/spawns) + descendants (yields/proves/covers). This is
  the report's "how did I get here" chain.
- `open` — nodes in non-terminal states = live threads.
- `render` — a markdown digest; safe to paste into a phase log.

## Discipline

- Write to the ASSET graph when you learn a *thing* exists (subdomain, endpoint, param, credential).
- Write to the EXPLORATION graph when you reach a *conclusion* (`fact`) or reproduce a bug (`finding`).
- `--confidence observed` = you saw it; `inferred` = you reasoned it. Never dress an inference as observed.
- Keep the state machine honest: a completed intent is `done`; budget-exhausted is `exhausted`;
  external failure is `blocked`. The gate (chainplan) reads these.
