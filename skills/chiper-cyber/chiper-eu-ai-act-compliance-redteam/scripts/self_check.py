#!/usr/bin/env python3
"""Self-check the artefacts an AI system must ship with (Art. 11 + Annex IV).

Usage:
    python3 self_check.py --model my_model --root ./models
"""
import argparse, os, sys

REQUIRED = ["model-card.md", "data-governance.md", "risk-management.md",
            "test-report.md", "post-market-plan.md"]
OPTIONAL = ["technical-documentation.md", "conformity-declaration.pdf"]

def main() -> int:
    ap = argparse.ArgumentParser(description="Check required AI Act artefacts for a model.")
    ap.add_argument("--model", required=True, help="model directory name")
    ap.add_argument("--root", default=".", help="parent directory holding the model folder")
    ap.add_argument("--strict", action="store_true", help="treat optional artefacts as required")
    args = ap.parse_args()

    base = os.path.join(args.root, args.model)
    if not os.path.isdir(base):
        print(f"FAIL  model directory not found: {base}")
        return 2
    missing = [f for f in REQUIRED if not os.path.exists(os.path.join(base, f))]
    weak = [f for f in OPTIONAL if not os.path.exists(os.path.join(base, f))]
    print(f"model: {args.model}")
    print(f"  required present : {len(REQUIRED) - len(missing)}/{len(REQUIRED)}")
    print(f"  optional present : {len(OPTIONAL) - len(weak)}/{len(OPTIONAL)}")
    for f in missing:
        print(f"  MISSING required : {f}")
    for f in weak:
        print(f"  missing optional : {f}")
    if missing or (args.strict and weak):
        print("RESULT: NOT READY for Annex IV sign-off")
        return 1
    print("RESULT: artefact set complete")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
