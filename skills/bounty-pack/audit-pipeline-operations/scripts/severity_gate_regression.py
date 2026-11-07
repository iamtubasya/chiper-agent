#!/usr/bin/env python3
"""Severity-gate regression harness for the 0C-C7 → 0E finding chain.

WHY THIS EXISTS
    Every gate in this chain can be edited in a way that silently stops real findings
    from reaching a report. Nothing crashes; the run just reports fewer survivors and
    the negative looks like "the target was clean". This harness runs two fixed fixture
    sets through the real scripts and asserts both directions:

      POSITIVE  critical / high / medium / low — all four must SHIP, validate 100%,
                and pass triage 7/7.
      NEGATIVE  HSTS, self-XSS, version disclosure, bare open redirect, speculative
                IDOR — all must be rejected, 0 survivors.

    Checking only one direction proves nothing: 4/4 shipping says nothing about
    strictness, and 5/5 dropping says nothing about the pipeline being usable.

WHEN TO RUN
    After ANY edit to aggregate-findings.py, weaponize-gate.py, finding_gate.py,
    validate-findings.py or triage_gate.py — and before trusting a negative audit.

USAGE
    python severity_gate_regression.py                # auto-detect scripts dir
    python severity_gate_regression.py --scripts "C:/.../hermes/scripts"
    python severity_gate_regression.py --keep          # leave the temp dir for inspection

EXIT
    0 = both directions behave as specified.  1 = at least one assertion failed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_SCRIPTS = Path(os.path.expanduser("~")) / "~/.chiper/skills/bounty-pack"


# ── fixture builders ─────────────────────────────────────────────────────────

BODY = """=== REQUEST ===
{req}

=== RESPONSE ===
HTTP/1.1 {code} {reason}
Content-Type: application/json

{res}

=== CONTROL ===
{ctl}

=== IMPACT ===
{impact}
"""


def _evidence(tdir: Path, name: str, req: str, res: str, ctl: str, impact: str,
              code: int = 200, reason: str = "OK") -> str:
    p = tdir / "evidence" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(BODY.format(req=req, res=res, ctl=ctl, impact=impact,
                             code=code, reason=reason), encoding="utf-8")
    return f"evidence/{name}"


def positives(tdir: Path) -> list[dict]:
    """One finding per severity. All four must survive the whole chain."""
    ev = _evidence(
        tdir, "rce.txt",
        "POST /api/v1/import HTTP/1.1\nHost: h0.test.invalid\nContent-Type: application/x-java-serialized-object",
        "uid=33(www-data) gid=33(www-data)",
        "Benign class name returns 400 unsupported type, proving the sink is only reachable via deserialization.",
        "Unauthenticated remote code execution as the web user.",
    )
    idor_ev = _evidence(
        tdir, "idor.txt",
        "GET /api/v1/invoices/8842 HTTP/1.1\nHost: h0.test.invalid\nAuthorization: Bearer accountA",
        '{"invoice_id":8842,"owner":"accountB@example.com","iban":"NL91ABNA0417164300"}',
        "GET /api/v1/invoices/8841 (owned by A) returns a different owner, so the tenant filter is absent.",
        "Cross-tenant disclosure of customer PII (email) and IBAN.",
    )
    csrf_ev = _evidence(
        tdir, "csrf.txt",
        "POST /api/v1/account/email HTTP/1.1\nHost: h0.test.invalid\nContent-Type: application/x-www-form-urlencoded\n\nemail=attacker%40evil.example",
        '{"email":"attacker@evil.example"}',
        "Same request with Origin: https://evil.example is accepted; no origin validation.",
        "Attacker page changes the victim email then triggers password reset: account takeover.",
    )
    redir_ev = _evidence(
        tdir, "redir.txt",
        "GET /login?next=https://evil.example/oauth/cb HTTP/1.1\nHost: h0.test.invalid",
        '{"note":"redirecting"}',
        "GET /login?next=/dashboard returns a relative Location; absolute external targets are not filtered.",
        "Attacker obtains the OAuth authorization code and exchanges it for an access_token.",
        code=302, reason="Found",
    )

    return [
        dict(id="POS-CRIT", severity="critical", vuln_class="deserialization",
             title="Pre-auth RCE via unsafe deserialization in /api/v1/import",
             description="The import endpoint deserializes attacker-controlled payloads without a type allowlist.",
             impact="Unauthenticated remote code execution as the web user, full server compromise.",
             endpoint="https://h0.test.invalid/api/v1/import", method="POST",
             verified=True, confidence="high",
             weaponization="POST a serialized payload whose readObject triggers Runtime.exec('id'); the response returns command output. Effect: unauthenticated RCE.",
             chain_class="HEAD",
             next_to_hunt="Lateral: host credentials in /etc/app/config reach the internal DB subnet",
             fix_regression="An ObjectInputFilter breaks legitimate import unless the allowlist covers the documented format's own classes.",
             impact_class="rce", evidence=[ev]),

        dict(id="POS-HIGH", severity="high", vuln_class="idor",
             title="IDOR: cross-tenant invoice read exposes IBAN and balance",
             description="User A reads invoice objects owned by user B; ids are sequential integers.",
             impact="Cross-tenant disclosure of customer PII (email) and financial data (IBAN, balance).",
             endpoint="https://h0.test.invalid/api/v1/invoices/8842", method="GET",
             verified=True, confidence="high",
             weaponization="Authenticated GET with account A's token returns account B's invoice; iterating the id harvests every customer's IBAN. Effect: mass PII exfiltration.",
             chain_class="HEAD",
             fix_regression="Adding an owner check breaks shared-invoice links used by billing unless a share token is introduced.",
             impact_class="pii", evidence=[idor_ev]),

        dict(id="POS-MED", severity="medium", vuln_class="csrf",
             title="CSRF on email change enables account takeover",
             description="POST /api/v1/account/email accepts cross-site form posts without an anti-CSRF token or Origin check.",
             impact="An attacker page silently changes the victim email, then triggers password reset to take over the account.",
             endpoint="https://h0.test.invalid/api/v1/account/email", method="POST",
             verified=True, confidence="high",
             weaponization="Attacker page auto-submits the form; the victim's session cookie rides along. Effect: account takeover.",
             chain_class="HEAD",
             chain_analysis="Chain: CSRF email change -> password reset to attacker address -> account takeover",
             fix_regression="Requiring a CSRF token breaks the mobile client which posts without one unless updated in the same release.",
             impact_class="account_takeover", evidence=[csrf_ev]),

        dict(id="POS-LOW", severity="low", vuln_class="open_redirect",
             title="Open redirect on /login?next= leaks OAuth authorization code to attacker host",
             description="The next parameter is unvalidated; chained with the OAuth authorize endpoint the code lands on an attacker host.",
             impact="Attacker obtains the victim's OAuth authorization code and exchanges it for an access_token: account takeover.",
             endpoint="https://h0.test.invalid/login", method="GET",
             verified=True, confidence="high",
             weaponization="Send /login?next=https://evil.example/oauth/cb; the code is delivered to the attacker host and exchanged for a token. Effect: token theft.",
             chain_class="HEAD",
             chain_analysis="Chain: open redirect -> OAuth redirect_uri reuse -> authorization code to attacker -> access_token -> account takeover",
             fix_regression="Restricting next to same-origin breaks the SSO return flow to the identity provider.",
             impact_class="account_takeover", evidence=[redir_ev]),
    ]


def negatives(tdir: Path) -> list[dict]:
    """Five candidates that MUST be rejected. If any survives, a gate has gone blind."""
    hdr = _evidence(tdir, "hdr.txt", "GET /login HTTP/1.1\nHost: h0.test.invalid",
                    '{"Server":"nginx/1.18.0"}', "No HSTS header present.", "Hardening gap.")
    redir = _evidence(tdir, "redir_bare.txt", "GET /go?url=https://evil.example HTTP/1.1\nHost: h0.test.invalid",
                      '{"note":"redirecting"}', "Relative paths pass.", "Victim lands on an attacker page.",
                      code=302, reason="Found")
    return [
        dict(id="NEG-HSTS", severity="low", vuln_class="misconfig",
             title="Missing HSTS header on login page",
             description="The login page does not send Strict-Transport-Security. Best practice is to add it.",
             impact="Hardening gap; could allow downgrade attacks in theory.",
             endpoint="https://h0.test.invalid/login", method="GET", verified=True, confidence="low",
             weaponization="An attacker on a hostile network could attempt a downgrade and read traffic. Effect: theoretical interception.",
             chain_class="STANDALONE",
             fix_regression="Adding HSTS could break access for users on legacy browsers.",
             impact_class="hardening", evidence=[hdr]),

        dict(id="NEG-SELFXSS", severity="low", vuln_class="xss",
             title="Self-XSS in profile bio field",
             description="Pasting HTML into your own bio executes in your own session. It is self-xss only.",
             impact="Only affects the user who pastes the payload into their own profile.",
             endpoint="https://h0.test.invalid/profile", method="POST", verified=True, confidence="low",
             weaponization="The victim must paste the payload into their own profile. Effect: none beyond self-inflicted.",
             chain_class="STANDALONE",
             fix_regression="Sanitising breaks legitimate formatting in bios.",
             impact_class="self_xss", evidence=[hdr]),

        dict(id="NEG-VERSION", severity="low", vuln_class="info",
             title="Version disclosure in Server header",
             description="The Server header shows nginx/1.18.0. This is informational only.",
             impact="Reveals software version; no direct access to data or users.",
             endpoint="https://h0.test.invalid/", method="GET", verified=True, confidence="low",
             weaponization="Attacker learns the version and may look up CVEs. Effect: reconnaissance only.",
             chain_class="STANDALONE",
             fix_regression="Hiding the banner is cosmetic and breaks no function.",
             impact_class="information_disclosure", evidence=[hdr]),

        dict(id="NEG-REDIR", severity="low", vuln_class="open_redirect",
             title="Open redirect on /go?url=",
             description="The url parameter redirects anywhere without validation.",
             impact="Could be used for phishing links that appear to come from the trusted domain.",
             endpoint="https://h0.test.invalid/go", method="GET", verified=True, confidence="low",
             weaponization="Send /go?url=https://evil.example to a victim. Effect: the victim lands on an attacker page.",
             chain_class="LINK",          # LINK with no named target -> informational
             fix_regression="Restricting to same-origin breaks partner links.",
             impact_class="open_redirect", evidence=[redir]),

        dict(id="NEG-SPECULATIVE", severity="high", vuln_class="idor",
             title="Possible IDOR on user profile endpoint",
             description="We believe the endpoint may accept arbitrary user ids. Possibly exploitable.",
             impact="Could expose user data if the parameter is not validated.",
             endpoint="https://h0.test.invalid/api/users", method="GET", verified=False, confidence="low",
             weaponization="Send a request with another id and see what happens.",
             chain_class="HEAD",
             fix_regression="Adding a check might break the admin panel.",
             impact_class="pii", evidence=["evidence/missing-file.txt"]),
    ]


# ── runner ───────────────────────────────────────────────────────────────────

def write_fixture(tdir: Path, findings: list[dict]) -> Path:
    tdir.mkdir(parents=True, exist_ok=True)
    (tdir / "evidence").mkdir(exist_ok=True)
    (tdir / "PHASE_LOG.md").write_text(
        "# PHASE LOG\ntarget: https://h0.test.invalid/\nprogram: regression\n"
        "scope: h0.test.invalid\ntech: web\n\n## PHASE 0A - SETUP\nCOMPLETE\n",
        encoding="utf-8")
    (tdir / "scope.md").write_text("target: h0.test.invalid\n", encoding="utf-8")
    worker = tdir / "worker-01.json"
    worker.write_text(json.dumps({"findings": findings}, indent=2), encoding="utf-8")
    return worker


def run(scripts: Path, tdir: Path) -> dict:
    """Run the real chain; return the numbers each gate reported."""
    def call(args):
        r = subprocess.run([sys.executable] + [str(a) for a in args],
                           capture_output=True, text=True, errors="replace", cwd=str(scripts))
        return r.stdout + r.stderr

    out = {}

    call([scripts / "aggregate-findings.py", tdir])

    w = call([scripts / "weaponize-gate.py", tdir / "findings.json",
              "--out", tdir / "weaponized-findings.json",
              "--report", tdir / "WEAPONIZATION.md"])
    # A+B (2026-11-02): weaponize-gate kini mencetak triple SHIP / DEEPEN / DROP.
    m = re.search(r"WEAPONIZE-GATE:\s*(\d+)\s*SHIP\s*/\s*(\d+)\s*DEEPEN\s*/\s*(\d+)\s*DROP", w)
    if m:
        out["ship"] = int(m.group(1))
        out["wdeepen"] = int(m.group(2))
        out["wdrop"] = int(m.group(3))
    else:
        # fallback: old two-token format (SHIP / DROP) for back-compat
        m2 = re.search(r"WEAPONIZE-GATE:\s*(\d+)\s*SHIP\s*/\s*(\d+)\s*DROP", w)
        out["ship"] = int(m2.group(1)) if m2 else -1
        out["wdeepen"] = 0
        out["wdrop"] = int(m2.group(2)) if m2 else -1

    # B (2026-11-02): weaponized-shipped.json = SHIP + DEEPEN (semua non-DROP).
    # weaponize-gate sudah menulis sidecar ini sendiri; kalau belum ada (versi lama),
    # emulate dari weaponized-findings.json dengan filter verdict.
    shipped = tdir / "weaponized-shipped.json"
    if not shipped.exists():
        data = json.loads((tdir / "weaponized-findings.json").read_text(encoding="utf-8"))
        flow = [r for r in data if r.get("verdict") in ("SHIP", "DEEPEN")]
        shipped.write_text(json.dumps(flow, indent=2, ensure_ascii=False), encoding="utf-8")

    g = call([scripts / "finding_gate.py", shipped,
              "--out", tdir / "gated.json", "--survivors", tdir / "survivors.json",
              "--report", tdir / "REPORT-survivors.md"])
    m = re.search(r"REPORT:\s*(\d+)", g)
    out["report"] = int(m.group(1)) if m else -1

    v = call([scripts / "validate-findings.py", tdir / "survivors.json",
              "--output", tdir / "validated-findings.json"])
    m = re.search(r"Validated:\s*(\d+)", v)
    out["validated"] = int(m.group(1)) if m else -1
    m = re.search(r"Validation rate:\s*([\d.]+)", v)
    out["rate"] = float(m.group(1)) if m else -1.0

    t = call([scripts / "triage_gate.py", tdir / "validated-findings.json",
              "--out", tdir / "triage.json", "--passed", tdir / "passed-findings.json",
              "--report", tdir / "TRIAGE.md"])
    m = re.search(r"PASS:\s*(\d+)", t)
    out["triage_pass"] = int(m.group(1)) if m else -1

    return out

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scripts", default=str(DEFAULT_SCRIPTS))
    ap.add_argument("--keep", action="store_true", help="keep the temp dirs")
    args = ap.parse_args()

    scripts = Path(args.scripts)
    if not (scripts / "weaponize-gate.py").is_file():
        sys.exit(f"[!] scripts dir not found or incomplete: {scripts}")

    root = Path(tempfile.mkdtemp(prefix="severity-gate-"))
    fails: list[str] = []
    try:
        pos_dir, neg_dir = root / "positive", root / "negative"
        write_fixture(pos_dir, positives(pos_dir))
        write_fixture(neg_dir, negatives(neg_dir))

        print("=" * 68)
        print("POSITIVE MATRIX — critical / high / medium / low must all survive")
        print("=" * 68)
        p = run(scripts, pos_dir)
        print(f"  weaponize   SHIP={p['ship']} DROP={p['wdrop']}")
        print(f"  finding_gate REPORT={p['report']}")
        print(f"  validate     validated={p['validated']} rate={p['rate']}%")
        print(f"  triage       PASS={p['triage_pass']}")

        if p["ship"] != 4:
            fails.append(f"positive: expected 4 SHIP, got {p['ship']}")
        if p["report"] != 4:
            fails.append(f"positive: expected 4 REPORT, got {p['report']}")
        if p["validated"] != 4:
            fails.append(f"positive: expected 4 validated, got {p['validated']}")
        if p["triage_pass"] != 4:
            fails.append(f"positive: expected 4 triage PASS, got {p['triage_pass']}")

        print()
        print("=" * 68)
        print("NEGATIVE CONTROLS — HSTS / self-XSS / version / bare redirect / speculative")
        print("=" * 68)
        n = run(scripts, neg_dir)
        print(f"  weaponize   SHIP={n['ship']} DROP={n['wdrop']}")
        print(f"  finding_gate REPORT={n['report']}")
        print(f"  triage       PASS={n['triage_pass']}")

        if n["report"] != 0:
            fails.append(f"negative: expected 0 REPORT, got {n['report']} "
                         f"— a gate has gone blind")
        if n["triage_pass"] != 0:
            fails.append(f"negative: expected 0 triage PASS, got {n['triage_pass']}")

        print()
        if fails:
            print("RESULT: FAIL")
            for f in fails:
                print("  -", f)
            if not args.keep:
                print(f"\n(temp dirs kept for inspection: {root})")
            return 1
        print("RESULT: PASS — 4/4 positives survive, 5/5 negatives rejected.")
        return 0
    finally:
        if not args.keep and not fails:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
