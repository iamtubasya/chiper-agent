#!/usr/bin/env python3
"""Lockfile-wide dependency CVE audit via the OSV API.

Why this exists: SCA tools run against an *installed environment* miss the
lockfile. A repo can have a clean venv and a vulnerable pin in pyproject.toml
at the same time (real case: python-multipart pinned 0.0.20 in pyproject while
the venv had 0.0.33). Audit the LOCKFILE, which is what new installs get.

Usage:
    python osv-lockfile-audit.py uv.lock
    python osv-lockfile-audit.py uv.lock --ecosystem PyPI --json out.json
    python osv-lockfile-audit.py package-lock.json --ecosystem npm
    python osv-lockfile-audit.py requirements.txt --ecosystem PyPI

Output: per-package advisory counts, CRITICAL/HIGH ids, and the minimum
version that fixes each. Exit code 1 when CRITICAL or HIGH is present, so it
can gate CI.

No auth required. OSV is Google's aggregator (GHSA + PYSEC + NVD + RustSec).
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_QUERY = "https://api.osv.dev/v1/query"
CHUNK = 100  # OSV caps querybatch at 1000; 100 keeps request bodies sane


def _post(url: str, payload: dict, timeout: int = 90) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def _read_toml(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def parse_uv_lock(path: str) -> list[tuple[str, str]]:
    """Extract (name, version) from uv.lock. TOML but no external dep needed
    for this narrow shape: [[package]] blocks with name/version lines."""
    out: list[tuple[str, str]] = []
    name = None
    for raw in _read_toml(path).splitlines():
        line = raw.strip()
        if line == "[[package]]":
            name = None
            continue
        if line.startswith("name = "):
            name = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("version = ") and name:
            ver = line.split("=", 1)[1].strip().strip('"')
            out.append((name, ver))
            name = None
    return out


def parse_requirements(path: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for raw in _read_toml(path).splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or "==" not in line:
            continue
        spec = line.split(";", 1)[0].strip()
        parts = spec.split("==", 1)
        name = parts[0].split("[", 1)[0].strip()
        ver = parts[1].strip()
        if name and ver:
            out.append((name, ver))
    return out


def parse_package_lock(path: str) -> list[tuple[str, str]]:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    out: list[tuple[str, str]] = []
    packages = data.get("packages") or {}
    for meta in packages.values():
        name = meta.get("name")
        ver = meta.get("version")
        if name and ver:
            out.append((name, ver))
    for name, ver in (data.get("dependencies") or {}).items():
        if isinstance(ver, dict) and ver.get("version"):
            out.append((name, ver["version"]))
    return out


PARSERS = {
    "uv.lock": parse_uv_lock,
    "requirements.txt": parse_requirements,
    "package-lock.json": parse_package_lock,
}


def pick_parser(path: str):
    for suffix, fn in PARSERS.items():
        if path.endswith(suffix):
            return fn
    raise SystemExit(f"unknown lockfile type: {path}")


def batch_query(deps: list[tuple[str, str]], ecosystem: str) -> dict:
    """Query OSV in chunks. Returns {(name, version): [vuln_id, ...]}."""
    hits: dict[tuple[str, str], list[str]] = {d: [] for d in deps}
    for i in range(0, len(deps), CHUNK):
        chunk = deps[i : i + CHUNK]
        payload = {
            "queries": [
                {"package": {"name": n, "ecosystem": ecosystem}, "version": v}
                for n, v in chunk
            ]
        }
        results = _post(OSV_BATCH, payload).get("results", [])
        for dep, res in zip(chunk, results):
            hits[dep] = [x["id"] for x in (res.get("vulns") or [])]
    return hits


def detail_severity(vuln_id: str) -> tuple[str, str]:
    """Return (severity, fixed_version_hint). One extra call per advisory —
    needed because querybatch omits severity and affected ranges."""
    try:
        with urllib.request.urlopen(
            f"https://api.osv.dev/v1/vulns/{vuln_id}", timeout=45
        ) as resp:
            v = json.load(resp)
    except Exception:
        return ("UNKNOWN", "")

    sev = (v.get("database_specific") or {}).get("severity") or ""
    if not sev:
        for s in v.get("severity") or []:
            score = s.get("score", "")
            if "CVSS" in s.get("type", "") and score:
                sev = f"CVSS:{score}"
                break
    fixed = ""
    for aff in v.get("affected") or []:
        for rng in aff.get("ranges") or []:
            for ev in rng.get("events") or []:
                if ev.get("fixed"):
                    fixed = ev["fixed"]
    return (sev.upper() or "UNKNOWN", fixed)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("lockfile")
    ap.add_argument(
        "--ecosystem",
        default=None,
        help="PyPI | npm | crates.io | Go ... (auto from filename if omitted)",
    )
    ap.add_argument("--json", dest="json_out")
    ap.add_argument(
        "--no-severity",
        action="store_true",
        help="skip per-advisory detail fetch (much faster, counts only)",
    )
    args = ap.parse_args()

    eco = args.ecosystem
    if not eco:
        eco = "npm" if args.lockfile.endswith(".json") else "PyPI"

    deps = sorted(set(pick_parser(args.lockfile)(args.lockfile)))
    print(f"[*] {args.lockfile}: {len(deps)} packages, ecosystem={eco}")

    hits = batch_query(deps, eco)
    vulned = {d: ids for d, ids in hits.items() if ids}
    print(
        f"[*] {sum(len(v) for v in hits.values())} advisories "
        f"across {len(vulned)}/{len(deps)} packages\n"
    )

    report = []
    crit = high = 0
    for (name, ver), ids in sorted(vulned.items(), key=lambda kv: -len(kv[1])):
        sev_map: list[tuple[str, str, str]] = []
        if not args.no_severity:
            for vid in ids:
                sev, fixed = detail_severity(vid)
                sev_map.append((vid, sev, fixed))
            crit += sum(1 for _, s, _ in sev_map if "CRITICAL" in s)
            high += sum(1 for _, s, _ in sev_map if "HIGH" in s)

        worst = sorted(
            {s for _, s, _ in sev_map}, key=lambda s: ("CRITICAL" not in s, s)
        )
        fixes = sorted({f for _, _, f in sev_map if f})
        print(
            f"{name:28} {ver:14} adv={len(ids):3}  "
            f"sev={','.join(worst[:2]) or '-'}  fix>={fixes[-1] if fixes else '?'}"
        )
        report.append(
            {
                "package": name,
                "version": ver,
                "advisories": ids,
                "severity": sev_map,
                "fix_min": fixes[-1] if fixes else None,
            }
        )

    print(f"\n=== CRITICAL={crit} HIGH={high} total_advisory={len(report) and sum(len(r['advisories']) for r in report)} ===")
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2)
        print(f"[*] wrote {args.json_out}")

    return 1 if (crit or high) else 0


if __name__ == "__main__":
    sys.exit(main())
