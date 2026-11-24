#!/usr/bin/env python3
"""Render an evidence-backed report from collected artefacts.

Documented usage (chiper-ai-agent-security, Phase 6):
    python3 report/generate.py \
      --recon recon/ --mcp-probes mcp_probe_results/ --chains chain_evidence/ \
      --template report/agent-redteam.md.j2 \
      --output deliverables/agent-redteam-report.md

The renderer is dependency-free: it supports plain text, simple
{{ variable }} substitution and {% for item in list %} loops so the
templates work even where Jinja2 is not installed.
"""
import argparse, re, sys
from datetime import date
from pathlib import Path

def gather(root: str):
    """Collect evidence files under a directory into a list of dicts."""
    base = Path(root)
    if not base.exists():
        return []
    out = []
    for p in sorted(base.rglob("*")):
        if p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            out.append({"path": str(p), "name": p.name, "lines": len(text.splitlines()),
                        "preview": text.strip().splitlines()[0][:160] if text.strip() else ""})
    return out

def render(template: str, ctx: dict) -> str:
    """Substitute {{ vars }} and expand {% for item in list %} ... {% endfor %}."""

    def expand(match):
        item_name, list_name, body = match.group(1), match.group(2), match.group(3)
        sequence = ctx.get(list_name, [])
        if not isinstance(sequence, list):
            return ""
        rows = []
        for entry in sequence:
            row = body
            if isinstance(entry, dict):
                for key, value in entry.items():
                    # dukung {{ key }} dan {{ item.key }} (pemakaian di template pack)
                    row = re.sub(r"{{\s*" + re.escape(str(key)) + r"\s*}}", str(value), row)
                    row = re.sub(
                        r"{{\s*" + re.escape(item_name) + r"\.\s*" +
                        re.escape(str(key)) + r"\s*}}", str(value), row)
            else:
                row = re.sub(r"{{\s*" + re.escape(item_name) + r"\s*}}", str(entry), row)
            rows.append(row)
        return "".join(rows)

    out = re.sub(r"{%\s*for\s+(\w+)\s+in\s+(\w+)\s*%}(.*?){%\s*endfor\s*%}",
                 expand, template, flags=re.S)
    for key, value in ctx.items():
        out = re.sub(r"{{\s*" + re.escape(str(key)) + r"\s*}}", str(value), out)
    out = re.sub(r"{{[^{}]*}}", "", out)     # placeholder kosong -> bersih
    out = re.sub(r"{%[^{}]*%}", "", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Render the evidence-backed report.")
    ap.add_argument("--recon", default="recon/", help="directory of recon artefacts")
    ap.add_argument("--mcp-probes", default="mcp_probe_results/")
    ap.add_argument("--chains", default="chain_evidence/")
    ap.add_argument("--template", required=True, help="template file to render")
    ap.add_argument("--output", required=True, help="report file to write")
    args = ap.parse_args()

    tpl_path = Path(args.template)
    if not tpl_path.exists():
        print(f"error: template {tpl_path} not found", file=sys.stderr)
        return 2

    ctx = {
        "date": date.today().isoformat(),
        "recon": gather(args.recon),
        "mcp_probes": gather(args.mcp_probes),
        "chains": gather(args.chains),
        "recon_count": len(gather(args.recon)),
        "probe_count": len(gather(args.mcp_probes)),
        "chain_count": len(gather(args.chains)),
    }
    try:
        template = tpl_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    text = render(template, ctx)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text.splitlines())} lines, "
          f"recon={ctx['recon_count']} probes={ctx['probe_count']} chains={ctx['chain_count']})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
