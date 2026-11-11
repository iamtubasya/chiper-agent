#!/usr/bin/env python3
"""Generic attack-surface change monitor (watchdog contract).

Prints a report ONLY when the surface changed; prints NOTHING otherwise.
Run once by hand to establish the baseline, then hand this file to the cron
tool BY BARE FILENAME (copy it to ~/.chiper/skills/bounty-pack/ first).

Edit the CONFIG block for the target. Two supported feed shapes:
  * ct_domain      : crt.sh certificate-transparency sweep for a wildcard domain
  * json_feeds     : any JSON endpoint; keep either its sorted "paths" keys
                     (OpenAPI) or its sorted top-level keys.
  * text_feeds     : any text/JSON list endpoint kept as a sorted unique line set.

NOTE (Dynamic path): STATE_PATH resolves dynamically via CHIPER_PATH/CHIPER_HOME/HOME, not
/c/Users/... — Python's open() cannot resolve MSYS paths. Also, at runtime the
CWD of the cron job is not guaranteed, so STATE_PATH must stay absolute.
"""
import json
import os
import ssl
import sys
import urllib.error
import urllib.request

# --------------------------------------------------------------------------
# CONFIG — edit per target
# --------------------------------------------------------------------------
CONFIG = {
    "name": "example-target",
    "state_path": "~/.chiper/skills/bounty-pack/surface_monitor_state.json",
    # crt.sh CT sweep for '%.<domain>'; set to None to skip
    "ct_domain": "example.com",
    # JSON endpoints. extract: "paths" -> OpenAPI path table, "top_keys" -> dict keys
    "json_feeds": [
        # {"name": "api_openapi", "url": "https://api.example.com/documentation/json", "extract": "paths"},
    ],
    # text/list endpoints kept as sorted unique non-empty lines
    "text_feeds": [
        # {"name": "docs_index", "url": "https://docs.example.com/llms.txt"},
    ],
    "timeout": 30,
}
# --------------------------------------------------------------------------

UA = {"User-Agent": "Mozilla/5.0 (compatible; SurfaceMonitor/1.0)"}
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _get(url, timeout):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - keep the run alive, surface the error
        return "__ERR__" + type(e).__name__ + ":" + str(e)[:120]


def _get_json(url, timeout):
    t = _get(url, timeout)
    if t.startswith("__ERR__"):
        return {"__err__": t}
    try:
        return json.loads(t)
    except Exception:  # noqa: BLE001
        return {"__err__": "parse-error"}


def snapshot(cfg):
    snap = {}
    to = cfg["timeout"]

    if cfg.get("ct_domain"):
        names = set()
        raw = _get(
            "https://crt.sh/?q=%25." + cfg["ct_domain"] + "&output=json", max(to, 40)
        )
        if not raw.startswith("__ERR__"):
            try:
                for entry in json.loads(raw):
                    for n in entry.get("name_value", "").split("\n"):
                        n = n.strip().lower()
                        if n:
                            names.add(n)
            except Exception:  # noqa: BLE001
                pass
        snap["ct_subdomains"] = sorted(names)

    for feed in cfg.get("json_feeds", []):
        d = _get_json(feed["url"], to)
        if "__err__" in d:
            snap[feed["name"]] = {"__err__": d["__err__"]}
        elif feed.get("extract") == "paths":
            snap[feed["name"]] = sorted((d.get("paths") or {}).keys())
        else:
            snap[feed["name"]] = sorted(d.keys()) if isinstance(d, dict) else []
        if feed.get("nested_json_path"):
            # keep a dotted sub-object too (e.g. per-chain vmType+depository)
            node = d
            for part in feed["nested_json_path"].split("."):
                node = node.get(part, {}) if isinstance(node, dict) else {}
            snap[feed["name"] + "__" + feed["nested_json_path"]] = node

    for feed in cfg.get("text_feeds", []):
        raw = _get(feed["url"], to)
        if raw.startswith("__ERR__"):
            snap[feed["name"]] = {"__err__": raw}
        else:
            snap[feed["name"]] = sorted({ln.strip() for ln in raw.splitlines() if ln.strip()})

    return snap


def diff(old, new, path=""):
    out = []
    if isinstance(old, dict) and isinstance(new, dict):
        for k in sorted(set(old) | set(new)):
            if k not in old:
                out.append("  + %s%s = %s" % (path, k, json.dumps(new[k])[:160]))
            elif k not in new:
                out.append("  - %s%s" % (path, k))
            else:
                out += diff(old[k], new[k], path + k + ".")
    elif isinstance(old, list) and isinstance(new, list):
        so, sn = {str(x) for x in old}, {str(x) for x in new}
        for x in sorted(sn - so):
            out.append("  + %s%s" % (path, x))
        for x in sorted(so - sn):
            out.append("  - %s%s" % (path, x))
    else:
        if old != new:
            out.append("  ~ %s%s -> %s" % (path, old, new))
    return out


def main():
    cfg = CONFIG
    _base = os.environ.get("CHIPER_PATH") or os.environ.get("CHIPER_HOME")
    _raw_state = cfg["state_path"]
    if _base and _raw_state.startswith("~/.chiper/"):
        state = os.path.join(_base, _raw_state[len("~/.chiper/"):])
    else:
        state = os.path.expanduser(_raw_state)
    new = snapshot(cfg)

    # Guard: an all-empty snapshot means the fetch layer failed, not "no surface".
    populated = [k for k, v in new.items() if v and not (isinstance(v, dict) and "__err__" in v)]
    if not populated:
        print("[SurfaceMonitor] WARNING: every feed empty/errored — refusing to "
              "overwrite baseline. Feeds: %s" % json.dumps(new)[:400])
        return

    old = {}
    if os.path.exists(state):
        try:
            with open(state, encoding="utf-8") as fh:
                old = json.load(fh)
        except Exception:  # noqa: BLE001
            old = {}

    if not old:
        with open(state, "w", encoding="utf-8") as fh:
            json.dump(new, fh, indent=1)
        # Print counts so the operator can VERIFY the baseline is not empty.
        detail = ", ".join("%s=%d" % (k, len(v)) for k, v in new.items() if isinstance(v, list))
        print("[SurfaceMonitor] baseline established for %s (%s)" % (cfg["name"], detail))
        return

    changed, report = False, []
    for k in new:
        if k not in old:
            report.append("NEW TRACK: %s" % k)
            changed = True
            continue
        d = diff(old[k], new[k], k + ".")
        if d:
            changed = True
            report.append("### %s changed (%d diffs)" % (k, len(d)))
            report += d[:60]

    if changed:
        print("[SurfaceMonitor] ATTACK-SURFACE CHANGE DETECTED @ %s" % cfg["name"])
        print("\n".join(report))
        with open(state, "w", encoding="utf-8") as fh:
            json.dump(new, fh, indent=1)
    # silent when nothing changed — that is the contract


if __name__ == "__main__":
    sys.exit(main())
