#!/usr/bin/env python3
"""final-deliverable.py — the reportability gate + PDF builder this skill's own
SKILL.md describes (§ "Enforced by scripts/final-deliverable.py") but that was
missing from the kit export. Reconstructed here from that spec — see the
provenance note at the bottom of this docstring.

A finding is REPORTABLE only if ALL of:
    1. it is present in <target_dir>/passed-findings.json
       (it cleared the impact gate + the 7-question triage gate upstream)
    2. it carries a demonstrated-impact record: "probe" (the exact action taken)
       AND "observed" (raw, unedited output, >= 40 chars) — a claim without its
       raw result is theory, not a finding
    3. it was re-verified CONFIRMED at least 3 times (a "reverify" list/count
       in the record — this script does not re-run the probe itself; pair it
       with your own reverify step/script if you want that automated)
    4. it has an "impact" string that states what the observed output PROVES,
       not a hedge ("impact: potential ..." does not pass)

Input format (<target_dir>/passed-findings.json — a JSON list of objects):
    [
      {
        "id": "F1",
        "title": "...",
        "severity": "HIGH",
        "probe": "curl -i https://target/api/internal/users/1",
        "observed": "<raw response, >= 40 chars>",
        "reverify": {"count": 3, "status": "CONFIRMED"},
        "impact": "Proves an unauthenticated attacker can read any user's PII.",
        ... (any other fields are carried through into the PDF/report untouched)
      },
      ...
    ]

Usage:
    python final-deliverable.py check <target_dir>                  # reportability only, writes nothing
    python final-deliverable.py build <target_dir> --to <vendor> --from <me>

`check` prints a PASS/FAIL table per finding and exits non-zero if anything fails.
`build` runs the same gate, then for every PASSing finding emits:
    <target_dir>/poc-pdfs/<slug>.pdf

PDF generation reuses the same reportlab patterns as this skill's
templates/multi-finding-pdf-gen.py so output is visually consistent with the
rest of this skill's deliverables. Requires: reportlab.

---
Provenance: this script did not exist anywhere in the originally exported kit —
SKILL.md referenced it, but the file itself was missing. It's been written here
from that spec rather than left as a dead reference, per the kit's own
"COMPLETE the tooling, don't narrow the skill" operating rule (see
bounty-kit/skills/security-tooling-setup/SKILL.md). Treat the 4-gate logic below
as a reasonable, literal implementation of the documented contract — adjust the
JSON schema above to match whatever upstream step in your own pipeline actually
produces passed-findings.json.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

MIN_OBSERVED_LEN = 40
MIN_REVERIFY_COUNT = 3
HEDGE_WORDS = ("potential", "might", "could possibly", "may allow", "theoretically")


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\-]+", "-", text).strip("-")
    return s or "finding"


def check_finding(f: dict) -> tuple[bool, list[str]]:
    """Returns (passes, list_of_reasons_if_failed)."""
    reasons = []

    probe = f.get("probe")
    observed = f.get("observed")
    if not probe:
        reasons.append("missing 'probe' (the exact action taken)")
    if not observed or len(str(observed)) < MIN_OBSERVED_LEN:
        reasons.append(f"'observed' missing or under {MIN_OBSERVED_LEN} chars (raw output required)")

    reverify = f.get("reverify") or {}
    rv_count = reverify.get("count", 0) if isinstance(reverify, dict) else 0
    rv_status = reverify.get("status", "") if isinstance(reverify, dict) else ""
    if rv_count < MIN_REVERIFY_COUNT or rv_status != "CONFIRMED":
        reasons.append(
            f"not re-verified CONFIRMED {MIN_REVERIFY_COUNT}x "
            f"(got count={rv_count}, status={rv_status!r})"
        )

    impact = (f.get("impact") or "").strip()
    if not impact:
        reasons.append("missing 'impact' statement")
    elif any(h in impact.lower() for h in HEDGE_WORDS):
        reasons.append(f"'impact' reads as a hedge, not a proof: {impact!r}")

    return (len(reasons) == 0, reasons)


def load_findings(target_dir: Path) -> list[dict]:
    path = target_dir / "passed-findings.json"
    if not path.exists():
        print(f"ERROR: {path} not found. Nothing is in scope for this gate.", file=sys.stderr)
        sys.exit(1)
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        print(f"ERROR: {path} must be a JSON list of finding objects.", file=sys.stderr)
        sys.exit(1)
    return data


def cmd_check(target_dir: Path) -> int:
    findings = load_findings(target_dir)
    if not findings:
        print("No findings in passed-findings.json.")
        return 0

    all_pass = True
    for f in findings:
        fid = f.get("id", "?")
        ok, reasons = check_finding(f)
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {fid}: {f.get('title', '(untitled)')}")
        for r in reasons:
            print(f"         - {r}")
        all_pass = all_pass and ok

    n_pass = sum(1 for f in findings if check_finding(f)[0])
    print(f"\n{n_pass}/{len(findings)} findings are reportable.")
    return 0 if all_pass else 1


def _build_pdf(f: dict, out_path: Path, to_vendor: str, from_name: str) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

    SEV_COLORS = {
        "CRITICAL": HexColor("#dc3545"), "HIGH": HexColor("#fd7e14"),
        "MEDIUM": HexColor("#ffc107"), "LOW": HexColor("#28a745"), "INFO": HexColor("#17a2b8"),
    }
    styles = getSampleStyleSheet()
    mono = ParagraphStyle("mono", parent=styles["Code"], fontSize=8, leading=10)
    h1 = styles["Heading1"]
    h2 = styles["Heading2"]
    body = styles["BodyText"]

    sev = str(f.get("severity", "INFO")).upper()
    story = [
        Paragraph(f.get("title", "(untitled finding)"), h1),
        Paragraph(f"To: {to_vendor}  |  From: {from_name}  |  Severity: {sev}", body),
        Spacer(1, 0.2 * inch),

        Paragraph("Summary", h2),
        Paragraph(f.get("summary", f.get("impact", "")), body),
        Spacer(1, 0.15 * inch),

        Paragraph("PROOF OF CONCEPT \u2014 DEMONSTRATED IMPACT", h2),
        Paragraph("Probe (exact action taken):", body),
        Paragraph(str(f.get("probe", "")).replace("\n", "<br/>"), mono),
        Spacer(1, 0.1 * inch),
        Paragraph("Observed (raw, unedited):", body),
        Paragraph(str(f.get("observed", "")).replace("\n", "<br/>"), mono),
        Spacer(1, 0.1 * inch),
        Paragraph("What this proves:", body),
        Paragraph(f.get("impact", ""), body),
        Spacer(1, 0.15 * inch),
    ]

    reverify = f.get("reverify") or {}
    story += [
        Paragraph("Verification", h2),
        Paragraph(
            f"Re-verified: {reverify.get('count', 0)}x \u2014 status: {reverify.get('status', 'n/a')}",
            body,
        ),
        Spacer(1, 0.15 * inch),
    ]

    if f.get("remediation"):
        story += [Paragraph("Suggested remediation", h2), Paragraph(f["remediation"], body)]

    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                             topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    doc.build(story)


def cmd_build(target_dir: Path, to_vendor: str, from_name: str) -> int:
    findings = load_findings(target_dir)
    out_dir = target_dir / "poc-pdfs"
    out_dir.mkdir(exist_ok=True)

    built, skipped = 0, 0
    for f in findings:
        ok, reasons = check_finding(f)
        fid = f.get("id", "?")
        if not ok:
            print(f"[SKIP] {fid}: not reportable ({'; '.join(reasons)})")
            skipped += 1
            continue
        slug = _slug(f"{fid}-{f.get('title', 'finding')}")
        out_path = out_dir / f"{slug}.pdf"
        try:
            _build_pdf(f, out_path, to_vendor, from_name)
            print(f"[BUILT] {fid}: {out_path}")
            built += 1
        except ImportError:
            print("ERROR: reportlab is required for `build`. Install with: "
                  "pip install --user reportlab", file=sys.stderr)
            return 1

    print(f"\n{built} PDF(s) built, {skipped} finding(s) skipped (not reportable).")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="reportability only, writes nothing")
    p_check.add_argument("target_dir", type=Path)

    p_build = sub.add_parser("build", help="build PDFs for every reportable finding")
    p_build.add_argument("target_dir", type=Path)
    p_build.add_argument("--to", dest="to_vendor", default="Vendor Security Team")
    p_build.add_argument("--from", dest="from_name", default="Researcher")

    args = ap.parse_args()
    if not args.target_dir.exists():
        print(f"ERROR: {args.target_dir} does not exist.", file=sys.stderr)
        sys.exit(1)

    if args.cmd == "check":
        sys.exit(cmd_check(args.target_dir))
    elif args.cmd == "build":
        sys.exit(cmd_build(args.target_dir, args.to_vendor, args.from_name))


if __name__ == "__main__":
    main()
