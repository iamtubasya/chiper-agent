# 04 — Traffic recorder (trafficrec.py)

On-demand MITM recorder: captures request/response so a PoC transcript is automatic instead of hand-copied.
It is a **mitmproxy addon + a query CLI in one file**.

Storage: `<target_dir>/_traffic/traffic.db` (+ `blobs/`). Bodies over 64 KiB spill to a blob ref.

## Two modes

ADDON (runs under mitmdump's own python 3.11):
```bash
~/.local/bin/mitmdump -s "$S/trafficrec.py" -p 8081 \
   --set traf_db="<target>/_traffic/traffic.db" --set confdir="<target>/_traffic/mitmconf"
# point the client at http://127.0.0.1:8081 ; https needs the mitm CA trusted (mitm.it)
```
CLI (system python 3.14):
```bash
python "$S/trafficrec.py" "<target or .db>" search --host h --contains "token" [--status 200] [--limit 20]
python "$S/trafficrec.py" "<target or .db>" get --id 3
python "$S/trafficrec.py" "<target or .db>" stats
python "$S/trafficrec.py" "<target or .db>" verify
```

The CLI accepts EITHER a target dir (-> `<dir>/_traffic/traffic.db`) OR an explicit `.db` path.

## Rules / pitfalls

- **Start on demand, stop after.** An always-on recorder wastes RAM on this 6GB host.
- **Use a FREE port (e.g. 8081).** `:8080`/`:6666` are MiniTool ShadowMaker on this host — never bind them.
- **Same db path.** SQLite WAL keeps rows in `traffic.db-wal` until checkpoint; querying a different
  path shows an empty db. Use the identical path/convention for record and query.
- The mitmproxy import is **guarded** so the CLI still works on 3.14. Do not "fix" it.
- httpx/curl/ffuf all accept `-x http://127.0.0.1:8081` (or `--proxy`), so most tool traffic can be captured.
