"""Build one PDF per finding from a single parametrised builder.

Why this exists: the canonical `report_style_structured.py` helpers (`P`, `BUL`,
`NUMB`) each accept a **string**. Feeding any of them a list raises

    AttributeError: 'list' object has no attribute 'split'

from inside reportlab's paragraph cleaner, which is a confusing trace for a
typing mistake. When you spec a finding as a dict, half the fields naturally
want to be lists ("impact" is 3 bullets), so normalise *inside* one `blocks()`
helper and never call `P()` directly on a container.

Second reason: vendor programmes score per case, so one finding per report is
the default. This builds N small reports from one list of dicts instead of
copy-pasting a 200-line story per bug.

Layout: 2 pages per finding is the sweet spot for a single Medium. If a report
runs past 3 pages for one bug, it is usually carrying a second bug.

Usage:
    python build_per_finding_reports.py            # uses FINDINGS below
    python build_per_finding_reports.py --outdir ./reports

Gate afterwards (from the parent skill):
    python ../../scripts/qa_pdf_layout.py reports/*.pdf --margin-mm 19.05
"""
import argparse
import importlib.util
import os
import sys

CONDUCT = (
    "Testing was performed only against accounts and wallets created by the researcher. "
    "No other user's data was accessed, no withdrawal was attempted, and no deposit was "
    "completed. Request rates were kept low and 429 responses were respected."
)

SIGN = "Researcher name - date"


def load_style(template_path):
    """Import report_style_structured.py, which is not a package module."""
    spec = importlib.util.spec_from_file_location("report_style", template_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["report_style"] = mod
    spec.loader.exec_module(mod)
    return mod


def build(rs, n, total, f, outdir):
    """Render one finding dict to a PDF. `f` keys:

    slug, title, severity, component, summary, steps[], expected,
    code (str|None), actual[str|list], impact[str|list],
    notlist[str|list], remediation[str|list], evidence[str|list]|None
    """
    B, N, P = rs.BUL, rs.NUMB, rs.P
    H2, KVB, CODE = rs.H2P, rs.kv, rs.CODE_BLOCK

    def blocks(items, sink):
        # THE FIX: accept a bare string or a list, never hand a list to P().
        if isinstance(items, str):
            items = [items]
        for x in items:
            sink(x if isinstance(x, str) else str(x))

    st = [
        P(f["title"], rs.H1),
        P(f["summary"], rs.SUB),
        KVB(
            [
                ("Target", f.get("target", "target.com / api.target.com")),
                ("Component", f["component"]),
                ("Severity", f["severity"]),
                ("Date", f.get("date", "date")),
                ("Researcher", f.get("researcher", "researcher")),
            ],
            widths=(105, 382),
        ),
        H2("Severity rationale"),
        P(f["severity"]),
        H2("Steps to reproduce"),
    ]
    for i, step in enumerate(f["steps"], 1):
        st.append(N(i, step))

    st.append(H2("Expected result"))
    st.append(P(f["expected"]))

    st.append(H2("Actual result"))
    blocks(f["actual"], lambda x: st.append(P(x)))
    if f.get("code"):
        st.append(CODE(f["code"]))

    st.append(H2("Impact"))
    blocks(f["impact"], lambda x: st.append(B(x)))

    st.append(H2("What this is NOT"))
    blocks(f["notlist"], lambda x: st.append(B(x)))

    if f.get("evidence"):
        st.append(H2("Evidence"))
        blocks(f["evidence"], lambda x: st.append(B(x)))

    st.append(H2("Recommended remediation"))
    blocks(f["remediation"], lambda x: st.append(B(x)))

    st.append(H2("Scope and conduct"))
    st.append(P(CONDUCT, rs.SMALL))
    st.append(rs.SP(10))
    st.append(P(f.get("sign", SIGN), rs.SMALL))

    out = os.path.join(outdir, f["slug"])
    rs.make_docs(out, f["title"], "bug bounty - finding %d of %d" % (n, total), st, two_pass=True)
    return out


def verify(paths):
    """Cheap structural assertion: every report has the honesty furniture."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("pypdf not installed, skipping structural check")
        return
    need = ["Steps to reproduce", "Expected result", "Actual result", "Impact",
            "What this is NOT", "Recommended remediation", "Scope and conduct"]
    for p in paths:
        text = "\n".join(pg.extract_text() for pg in PdfReader(p).pages)
        flat = " ".join(text.split())
        missing = [s for s in need if s not in flat]
        pages = len(PdfReader(p).pages)
        flag = "OK " if not missing else "MISSING " + ",".join(missing)
        print("%-52s %2d pages  %6d bytes  %s" % (os.path.basename(p), pages, os.path.getsize(p), flag))


FINDINGS = [
    {
        "slug": "F1_example.pdf",
        "title": "Target - Finding 1: <actor> can <effect>",
        "severity": "Medium. One sentence on who can do what, plus the one condition that would raise it.",
        "component": "GET /path on the API host",
        "summary": "Two to four short sentences. What happens, why it is wrong, what you observed.",
        "steps": [
            "Send an unauthenticated GET to <url>. No cookies, no token.",
            "Observe HTTP 200 and <body shape>.",
            "Repeat to confirm it is stable rather than cached.",
        ],
        "expected": "What correct behaviour looks like, citing the product's own strings where possible.",
        "code": "curl -s <url> | head\n# HTTP/1.1 200 OK\n# <the decisive lines only>",
        "actual": ["Facts only. What the server actually did."],
        "impact": ["Who loses what.", "The chain it enables.", "Volume or durability of the weakness."],
        "notlist": [
            "What you did NOT prove (stops the triager reading more into it than you showed).",
            "Any control that is actually working - say so.",
        ],
        "remediation": ["Cheap fix.", "Structural fix."],
        "evidence": ["Artefact filenames on disk; raw capture offered on request."],
    },
]


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--style", default=os.path.join(here, "..", "templates", "report_style_structured.py"))
    ap.add_argument("--outdir", default="./reports")
    a = ap.parse_args()

    os.makedirs(a.outdir, exist_ok=True)
    rs = load_style(os.path.abspath(a.style))
    total = len(FINDINGS)
    paths = [build(rs, i, total, f, a.outdir) for i, f in enumerate(FINDINGS, 1)]
    for p in paths:
        print("built", p)
    verify(paths)


if __name__ == "__main__":
    main()
