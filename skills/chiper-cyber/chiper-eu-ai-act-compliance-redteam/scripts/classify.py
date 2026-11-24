#!/usr/bin/env python3
"""Decision-tree classifier for EU AI Act scope (Annex III / Article 51).

Documented usage (chiper-eu-ai-act-compliance-redteam SKILL.md, Phase 1):

    python3 scripts/classify.py \
      --system-description "LLM screening resumes for senior engineer role" \
      --output scope.json

Emits {"annex_iii_clause", "high_risk", "obligations"} plus reasoning.
"""
import argparse
import json
import sys

# clause -> human description of the Annex III / Article 51 trigger
CLAUSES = {
    "IV(a)": ("employment", ("recruit", "screen", "shortlist", "cv", "resume",
                             "promotion", "termination", "worker")),
    "IV(b)": ("credit", ("credit", "loan eligibility", "creditworthiness")),
    "IV(c)": ("education", ("admission", "exam", "proctor", "student assessment",
                            "education provider")),
    "IV(d)": ("essential-services", ("benefit eligibility", "public services",
                                     "emergency dispatch", "triage")),
    "IV(e)": ("law-enforcement", ("recidivism", "polygraph", "risk assessment",
                                  "law enforcement")),
    "IV(f)": ("migration", ("asylum", "border", "visa", "migration")),
    "IV(g)": ("justice", ("judicial", "court", "democratic process", "election")),
    "51": ("gpai-systemic-risk", ("general-purpose model", "systemic risk",
                                  "frontier model")),
}
OBLIGATIONS = ["Art.9", "Art.10", "Art.13", "Art.14", "Art.15"]
GPAI = ["Art.53", "Art.55"]
PROHIBITED = ("social scoring", "manipulation of behaviour",
              "real-time remote biometric identification")


def classify(text: str) -> dict:
    low = text.lower()
    if any(p in low for p in PROHIBITED):
        return {"annex_iii_clause": "Art.5", "high_risk": False, "prohibited": True,
                "obligations": ["Art.5 (prohibited practice)"],
                "reason": "practice listed in Article 5"}
    for clause, (name, keys) in CLAUSES.items():
        if any(k in low for k in keys):
            if clause == "51":
                return {"annex_iii_clause": clause, "high_risk": False,
                        "obligations": GPAI, "matched_domain": name,
                        "reason": "GPAI with systemic risk (Article 51)"}
            return {"annex_iii_clause": clause, "high_risk": True,
                    "obligations": OBLIGATIONS, "matched_domain": name,
                    "reason": f"Annex III({name}) use case"}
    return {"annex_iii_clause": None, "high_risk": False, "obligations": [],
            "reason": "no Annex III use case matched; transparency duties only"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify an AI system under the EU AI Act.")
    ap.add_argument("--system-description", "--description", dest="description",
                    required=True, help="intended purpose of the system")
    ap.add_argument("--output", help="write JSON here instead of stdout")
    args = ap.parse_args()
    if not args.description.strip():
        print("error: --system-description is empty", file=sys.stderr)
        return 2

    verdict = classify(args.description)
    verdict["input"] = args.description
    payload = json.dumps(verdict, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(payload + "\n")
        except OSError as exc:
            print(f"error: cannot write {args.output}: {exc}", file=sys.stderr)
            return 2
        print(f"wrote {args.output} (high_risk={verdict['high_risk']})")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
