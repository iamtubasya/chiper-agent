#!/usr/bin/env python3
"""
Regression fixture for the chain-composition classifier (chain_builder.py).

WHY THIS EXISTS
---------------
A regex/classifier that over-matches silently DELETES a valid finding. The run exits 0,
the report is quietly short one Critical, and nothing looks wrong. Three such bugs were
found in one session (2026-10-30) by running the classifier against a fixture whose
correct answer was already known:

  1. `dead` regex matched the bare word "unverified"  -> the ATO primitive
     "unverified email change" was flagged DEAD and dropped from every chain.
  2. `GOALS` had no pattern for the ATO sink, so chains that should end in
     `account_takeover` ended nowhere (or in `pii`).
  3. The signal cap ignored K/A/B/X parts, dropping auth findings that carry only a
     part label.

USAGE
-----
    python scripts/check_chain_builder_fixture.py [path/to/chain_builder.py]

Exit 0 = classifier behaves. Exit 1 = at least one assertion failed (read the diff).

The fixture is deliberately small and self-contained: it writes a temp findings.json,
runs the real classifier as a subprocess, and asserts on four axes per finding:
present/absent, goal, part, dead. A check that only asserts "did it run" catches nothing.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TARGET = Path(__file__).resolve().parents[3] / "scripts" / "chain_builder.py"

# Each row: what the finding IS, and what the classifier MUST say about it.
# `expect_absent` = the finding is noise and must NOT appear as a chainable signal.
FIXTURE = [
    {
        "id": "F1",
        "title": "User enumeration via differential login error",
        "severity": "low",
        "description": (
            "Existing user returns 'incorrect password', unknown user returns "
            "'invalid request'. Error text differential leaks account state."
        ),
        "expect_part": "K",
        "expect_absent": False,
    },
    {
        "id": "F2",
        "title": "No rate limit on /api/v1/auth/login",
        "severity": "low",
        "description": (
            "Endpoint mints an ephemeral requestId per call with no authentication and "
            "no throttle. 30 concurrent requests all returned 200, no 429."
        ),
        "expect_part": "B",
        "expect_absent": False,
    },
    {
        "id": "F3",
        "title": "Unverified email change",
        "severity": "medium",
        "description": (
            "POST /api/account/email changes the address without verification token; "
            "attacker can set arbitrary email."
        ),
        # THE critical assertion. "unverified" here describes the ADDRESS, not the
        # finding. If this row ever comes back DEAD/absent, the dead-regex regressed.
        "expect_goal": "account_takeover",
        "expect_part": "A",
        "expect_dead": False,
        "expect_absent": False,
    },
    {
        "id": "F4",
        "title": "IDOR on /api/users/{id}/export",
        "severity": "medium",
        "description": (
            "Export endpoint ignores tenant filter; cross-tenant identifier acceptance "
            "returns other tenant records."
        ),
        "expect_goal": "pii",
        "expect_part": "X",
        "expect_absent": False,
    },
    {
        "id": "F5",
        "title": "Missing X-Frame-Options header",
        "severity": "info",
        "description": "Header absent on login page.",
        # Noise: no K/A/B/X part. Must not be presented as a chainable signal.
        "expect_absent": True,
    },
    {
        "id": "F6",
        "title": "Theoretical SSRF",
        "severity": "low",
        "description": "Could not confirm; precondition not met. Theoretical only.",
        "expect_dead": True,
        "expect_absent": False,
    },
]


def build_findings() -> list[dict]:
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "severity": r["severity"],
            "description": r["description"],
        }
        for r in FIXTURE
    ]


def run_classifier(script: Path, findings_path: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(script), str(findings_path)],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main() -> int:
    target = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_TARGET
    if not target.is_file():
        print(f"[!] classifier not found: {target}")
        print("    pass the path explicitly: check_chain_builder_fixture.py <chain_builder.py>")
        return 2

    with tempfile.TemporaryDirectory() as td:
        fp = Path(td) / "findings.json"
        fp.write_text(json.dumps(build_findings(), indent=1), encoding="utf-8")
        rc, out = run_classifier(target, fp)

    failures: list[str] = []

    # --- global: the run must succeed and must not silently drop everything -------
    if rc != 0:
        failures.append(f"classifier exited {rc} (expected 0)")

    # Count how many fixture findings the classifier actually reported.
    # The header line is: "# CHAIN BUILDER — N finding(s)"
    reported = 0
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("# CHAIN BUILDER"):
            try:
                reported = int(s.split("—")[1].strip().split()[0])
            except (IndexError, ValueError):
                failures.append(f"could not parse finding count from: {s!r}")

    if reported == 0:
        failures.append("classifier reported 0 findings — either it crashed or the cap is wrong")

    # --- per-finding assertions -------------------------------------------------
    for row in FIXTURE:
        rid, title = row["id"], row["title"]
        # Findings are printed as " N. <title truncated to 66 chars>"
        present = any(
            line.strip().startswith(tuple("0123456789")) and title[:40] in line
            for line in out.splitlines()
        )

        if row.get("expect_absent") and present:
            failures.append(
                f"{rid} ({title}): expected ABSENT (noise, no part label) but it was reported"
            )
        if not row.get("expect_absent") and not present:
            failures.append(
                f"{rid} ({title}): expected PRESENT but it was dropped — "
                "check the dead-regex / signal-cap / goal patterns"
            )

        if not present:
            continue

        # Locate this finding's flag block (the indented line(s) after its title).
        block = ""
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if title[:40] in line:
                block = lines[i + 1] if i + 1 < len(lines) else ""
                break

        if row.get("expect_dead") and "DEAD" not in block:
            failures.append(f"{rid}: expected DEAD flag, got: {block.strip()!r}")
        if row.get("expect_dead") is False and "DEAD" in block:
            failures.append(
                f"{rid}: UNEXPECTED DEAD flag — a real primitive was killed by the dead-regex. "
                f"Block: {block.strip()!r}"
            )
        if row.get("expect_goal") and row["expect_goal"] not in block:
            failures.append(
                f"{rid}: expected GOAL:{row['expect_goal']}, got: {block.strip()!r}"
            )
        if row.get("expect_part") and f"part:{row['expect_part']}" not in block:
            failures.append(
                f"{rid}: expected part:{row['expect_part']}, got: {block.strip()!r}"
            )

    # --- report -----------------------------------------------------------------
    if failures:
        print("FAIL — classifier regression detected:\n")
        for f in failures:
            print(f"  - {f}")
        print("\n--- raw classifier output ---")
        print(out)
        print("\nFix the CLASSIFIER, not the finding. A known-good primitive that vanishes")
        print("from the output is a script bug, never a reason to re-hunt the bug.")
        return 1

    print("PASS — classifier handles all 6 fixture rows correctly.")
    print("  F1 part:K   F2 part:B   F3 GOAL:account_takeover+part:A (alive)")
    print("  F4 GOAL:pii+part:X      F5 absent (noise)              F6 DEAD")
    print("\nRe-run this after ANY edit to the classifier's regex/goal/cap logic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
