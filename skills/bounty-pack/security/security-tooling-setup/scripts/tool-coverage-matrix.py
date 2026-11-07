#!/usr/bin/env python3
"""tool-coverage-matrix — which of a skill's REQUIRED tools are actually present.

Operator rule this enforces: when a vuln class has a skill but no working tool, COMPLETE the
tooling. Do not narrow the skill. This script tells you exactly which tools are missing, grouped
BY SKILL, so the gap can be closed instead of the class being dropped.

Usage:
    python tool-coverage-matrix.py                 # web2 map (default)
    python tool-coverage-matrix.py --json          # machine-readable
    python tool-coverage-matrix.py --probe         # ALSO run each present tool with -h

Presence is checked far beyond PATH (see RULE 0 in SKILL.md): user dirs, Go bins, npm global,
pip user site, D:/data hermes/tools/*, and library-only tools via importability.
A presence hit is NOT proof of function — use --probe, or the probe snippet in SKILL.md.
"""
from __future__ import annotations
import argparse, importlib.util, json, pathlib, shutil, subprocess, sys
from collections import OrderedDict

HOME = pathlib.Path.home()

SEARCH = [
    HOME / "go" / "bin",
    HOME / "/usr/local/bin",
    HOME / ".cargo" / "bin",
    HOME / "/usr/local/bin",
    HOME / ".local" / "bin",
    Path("/usr/local/bin"),
    HOME / "~/.chiper/skills/bounty-pack/tools",
    HOME / "~/.chiper/skills/bounty-pack/hermes-agent/venv/Scripts",
    HOME / "/usr/local/bin",
    pathlib.Path("C:/tools"),
    pathlib.Path("D:/data hermes/tools"),
    pathlib.Path("D:/data hermes/tools/web2"),
    pathlib.Path("C:/Program Files/Java"),
    # Ruby toolchain (RubyInstaller installs gem executables into its own bin) and the
    # per-user gem bin. Without these the matrix reports false MISSING for wpscan/whatweb.
    pathlib.Path("D:/Ruby40/bin"),
    HOME / ".gem" / "ruby",
]

# library-only tools have no console script -> test importability instead
PYMOD_ALIASES = {
    "pyjwt": "jwt", "pycryptodomex": "Cryptodome", "pytesseract": "pytesseract",
    "semgrep": "semgrep", "requests_futures": "requests_futures", "impacket": "impacket",
}

# skill -> tools it requires.  Extend per engagement; keep it grouped by skill (that is the point).
WEB2_MAP = OrderedDict([
    ("security-recon / web2-recon", ["subfinder", "amass", "puredns", "dnsx", "httpx", "naabu",
                                     "katana", "gau", "waymore", "gospider", "hakrawler",
                                     "findomain", "assetfinder"]),
    ("hunt-spa-api / hunt-source-leak", ["jsluice", "linkfinder", "secretfinder", "sourcemapper",
                                         "js-beautify"]),
    ("hunt-secrets", ["trufflehog", "gitleaks", "secretfinder"]),
    ("hunt-sqli", ["sqlmap", "ghauri"]),
    ("hunt-nosqli", ["nosqlmap"]),
    ("hunt-xss", ["dalfox", "xsstrike", "kxss"]),
    ("hunt-ssrf", ["ssrfmap", "interactsh-client", "gopherus"]),
    ("hunt-ssti", ["sstimap", "tplmap"]),
    ("hunt-jwt-crypto", ["jwt_tool", "pyjwt"]),
    ("hunt-deserialization", ["ysoserial", "phpggc", "marshalsec"]),
    ("hunt-http-smuggling", ["smuggler", "h2csmuggler"]),
    ("hunt-race-condition", ["race-checker"]),
    ("hunt-cors", ["corscanner"]),
    ("hunt-brute-force", ["ffuf", "patator", "hydra"]),
    ("hunt-mfa-bypass / captcha", ["pytesseract"]),
    ("hunt-tls-network", ["testssl", "sslscan"]),
    ("hunt-graphql", ["graphqlmap", "graphw00f", "clairvoyance"]),
    ("hunt-grpc", ["grpcurl", "grpcui"]),
    ("hunt-websocket", ["websocat", "wscat"]),
    ("hunt-saml", ["xmlsec1"]),
    ("hunt-lfi", ["liffy"]),
    ("hunt-k8s", ["kube-hunter", "kubectl"]),
    ("hunt-cloud-misconfig", ["aws", "az", "gcloud", "s3scanner", "cloud_enum", "pacu", "scout"]),
    ("hunt-subdomain", ["subfinder", "subjack", "dnsreaper"]),
    ("hunt-cicd", ["act", "gitleaks"]),
    ("hunt-api-misconfig / shadow-api", ["kiterunner", "ffuf", "clairvoyance"]),
    ("cms-security-testing", ["wpscan", "joomscan", "droopescan"]),
    ("security-scanners", ["nuclei", "nikto", "whatweb", "wafw00f"]),
    ("codebase-bounty-review", ["semgrep"]),
    ("hunt-ntlm-info", ["impacket"]),
])


def pymod(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def have(tool: str) -> bool:
    if tool in PYMOD_ALIASES and pymod(PYMOD_ALIASES[tool]):
        return True
    for cand in (tool, tool + ".exe", tool + ".bat", tool + ".py", tool + ".cmd"):
        if shutil.which(cand):
            return True
    for d in SEARCH:
        try:
            for pat in (tool, tool + ".exe", tool + ".bat", tool + ".py"):
                if (d / pat).exists():
                    return True
        except Exception:
            pass
    if pymod(tool):
        return True
    return False


def probe(tool: str) -> str:
    """Presence is not function. Returns JALAN / GAGAL / SKIP."""
    for launcher in (tool,):
        try:
            r = subprocess.run(f"{launcher} -h", shell=True, capture_output=True,
                               text=True, timeout=60)
        except Exception:
            return "SKIP"
        txt = (r.stdout or r.stderr or "")
        if "Traceback" in txt or "syntax is incorrect" in txt or not txt.strip():
            return "GAGAL"
        return "JALAN"
    return "SKIP"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--probe", action="store_true", help="also run each present tool with -h")
    a = ap.parse_args()

    present, missing = 0, []
    report = OrderedDict()
    for skill, tools in WEB2_MAP.items():
        rows = []
        for t in tools:
            ok = have(t)
            status = "OK" if ok else "MISS"
            if ok and a.probe:
                status = probe(t)
                ok = status == "JALAN"
            rows.append({"tool": t, "status": status})
            if ok:
                present += 1
            else:
                missing.append((skill, t))
        report[skill] = rows

    if a.json:
        print(json.dumps({"present": present, "missing": len(missing),
                          "by_skill": report}, indent=2))
        return 0

    for skill, rows in report.items():
        print(f"{skill:<38} " + "  ".join(
            ("✓" if r["status"] in ("OK", "JALAN") else "✗") + r["tool"] for r in rows))

    gaps = OrderedDict()
    for s, t in missing:
        gaps.setdefault(s, []).append(t)
    print(f"\nTOTAL: {present} present / {len(missing)} missing")
    if gaps:
        print("\n=== GAPS BY SKILL (complete the tooling; do NOT drop the class) ===")
        for s, ts in gaps.items():
            print(f"  {s:<38} -> {', '.join(ts)}")
    uniq = list(dict.fromkeys(t for _, t in missing))
    print(f"\nUNIQUE MISSING ({len(uniq)}): " + ", ".join(uniq))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
