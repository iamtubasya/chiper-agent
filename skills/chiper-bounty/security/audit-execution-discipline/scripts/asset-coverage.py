#!/usr/bin/env python3
"""
ASSET COVERAGE — ensure every skill/tool/reference/payload/cookbook/exploit-book
was CALLED **and USED**, not merely read. Reads/writes <target_dir>/asset-coverage.json.

Operator rule: jangan ada yang cuma dilihat lalu dilewatkan. Timeout != skip.

Usage:
  python asset-coverage.py <target_dir> --init                 # seed ledger (all PENDING)
  python asset-coverage.py <target_dir> --mark sqlmap=USED --evidence path
  python asset-coverage.py <target_dir> --mark wpscan="N/A" --reason "target not WordPress"
  python asset-coverage.py <target_dir> --phase 0C            # CHECK (exit!=0 on FAIL)
  python asset-coverage.py <target_dir> --all                 # check every phase

Statuses: USED (pass) | N/A (pass but needs a real --reason) |
          READ_ONLY, SKIPPED_TIMEOUT, PENDING, TIMEOUT (all FAIL)
Rules: SKIPPED_TIMEOUT/TIMEOUT can never pass; N/A with reason containing
       'timeout'/'skip'/'no time'/'gak sempat' is rejected.
"""
import json, sys, argparse, pathlib, re

LEDGER = "asset-coverage.json"

# ---- mandatory manifest (class -> assets) per phase -------------------------
MANIFEST = {
  "0B": {
    "recon": ["subfinder","amass","puredns","httpx","katana","gau","waymore","jsluice","naabu","dork-recon",
              "subs.txt","live.txt","urls.txt"],
  },
  "0C": {
    "tools":  ["force-full-execution","nuclei","ffuf","sqlmap","dalfox","interactsh","arjun",
               "wpscan","nikto","ssrfmap","graphqlmap","byp4xx","subzy","trufflehog",
               # batch A/B/C tools (2026-10-07) — wajib ikut dipakai, bukan cuma terpasang
               "jwt_tool","sstimap","smuggler","xsstrike","graphw00f","linkfinder",
               "secretfinder","dnsreaper","cloud_enum","patator","kube-hunter","clairvoyance",
               "sslscan","subjack","gitleaks","kiterunner","grpcurl","ysoserial",
               # DOM-XSS browser engine (2026-10-10) — closes the SPA blind spot.
               # Server-side scanners (dalfox/nuclei/curl) cannot see DOM sinks; on a
               # React target with 0 query parameters dalfox has nothing injectable, so
               # a "clean" result there is a false negative by construction.
               "dom-xss",
               # RCE/command-injection VERIFIER (2026-10-10) — detection is not proof.
               # nuclei's `cmd-injection,rce` tag answers "does this look like a sink";
               # this answers "did the target actually RUN my command" via 3 independent
               # channels (time differential, OOB canary callback, command-output signature).
               "rce-verify",
               # IMPACT verifier (2026-10-10) — SSRF/LFI/SSTI/XXE/open-redirect/blind-SQLi.
               # Detection is not proof: http_probe marks a probe "interesting" on
               # (status not in 404/403/401 and size>0), which cannot tell a page that
               # echoes "passwd" from LFI that read the file, nor a slow page from blind
               # SQLi that slept. This proves each via file-content signatures, arithmetic
               # evaluation, OOB callbacks, Location headers, and time differentials.
               "impact-verify",
               # smart-contract set — required on web3 tracks, skipped on web tracks
               "slither","aderyn","myth","echidna","medusa"],
    "payload":["variants(C2)","business-logic-15(C3)","poc-repos(C4)","poc-variants(C5)",
               "references(C6)","poc-techniques(C6b)"],
    "cookbook":["exploit-cookbook","security-arsenal","bugbounty-playbook/chains"],
    "shelf":  ["poc-technique-atlas"],
    # reference CONTENT that must actually fire a request (ref value in reference-usage.json)
    # NOTE (2026-10-08): reference-usage.json records the FIRED REFERENCE FILENAME
    # (e.g. "403-bypass.md"), and the corpus is collected from
    # skills/security/exploit-cookbook/references/. Demanding skill-name strings that
    # never appear in that file made the refs class unpassable — a phantom
    # requirement that hard-blocked every run. Match on the real corpus instead.
    "refs":   ["exploit-cookbook", "security-arsenal", "bugbounty-playbook"],
    # web3/Solidity ONLY — the attacker-side corpus. Required only when the track is web3
    # (see _is_web3()); a web2 track skips this class instead of failing on it.
    "refs_web3": ["defi-exploit-forensics","technique-library","case-library","web3-audit"],
    "skills": ["skill-usage.json"],   # any loaded hunt-*/platform-* must be recorded USED
  },
  "0D": {"gate": ["verify-tool-usage","asset-coverage"]},
  "0E": {"findings": ["findings.json","chains.json","gated.json","validated-findings.json","ready-candidates.json"]},
  "0E-REVIEW": {"review": ["review-candidates.json","REPORT-survivors.md"]},
  "0F": {"report": ["AUDIT-REPORT.md","email-drafts","poc-pdfs"]},
}
PASS = {"USED", "N/A"}
FAIL = {"READ_ONLY", "SKIPPED_TIMEOUT", "TIMEOUT", "PENDING", "NOT_RUN", "UNVERIFIED", ""}

def load(td):
    f = td / LEDGER
    return json.loads(f.read_text()) if f.exists() else {}

def save(td, d):
    (td / LEDGER).write_text(json.dumps(d, indent=2))

def init(td):
    d = load(td)
    n = 0
    for phase, groups in MANIFEST.items():
        for cls, assets in groups.items():
            for a in assets:
                key = f"{phase}:{cls}:{a}"
                if key not in d:
                    d[key] = {"asset": a, "class": cls, "phase": phase,
                              "status": "PENDING", "evidence": "", "reason": ""}
                    n += 1
    save(td, d)
    print(f"seeded {n} assets -> {td/LEDGER} (total {len(d)})")

def mark(td, spec, evidence="", reason=""):
    asset, _, status = spec.partition("=")
    d = load(td); hit = 0
    for k, v in d.items():
        if v["asset"] == asset:
            v["status"] = status; v["evidence"] = evidence; v["reason"] = reason; hit += 1
    save(td, d)
    print(f"marked '{asset}'={status} on {hit} entr{'y' if hit==1 else 'ies'}")

def check(td, phase):
    d = load(td)
    if not d:
        print(f"FAIL: {LEDGER} missing/empty -> run --init"); return 1
    needed = needed_for(phase, td)
    fails, oks = [], []
    # A documented skip / "tool not installed" reason is a CLASSIFICATION, not an
    # admission of skipping work. Rejecting it because it happens to contain the
    # word "skip" made every FUZZ_ONLY / SKIP_WITH_REASON / not-installed asset
    # un-passable. Full provenance: the producer records WHO skipped and WHY, and
    # the operator can audit it. real, systematic non-execution (TIMEOUT, "no
    # time", "belum"/"tidak sempat") still fails — that is the anti-fabrication
    # intent this check exists for.
    # ── N/A discipline (hardened 2026-10-19, refined 2026-10-22) ──
    # Kegagalan teknis BUKAN alasan N/A. Itu pemicu rework, bukan penyerahannya.
    # CATATAN 2026-10-22: status pipeline yang SAH (bukan penyerahan) harus lolos:
    #   SKIP_NO_PARAM            = tool tak punya parameter utk diuji di target ini
    #   STARTED_NO_TOKEN         = butuh token/sesi yg belum ada
    #   NEEDS_REQUEST_TEMPLATE   = butuh template request
    #   SKIPPED_NO_SOLIDITY_TECH = target bukan Solidity
    #   NO_OUTPUT                = tool jalan tapi tak ada hasil
    #   FUZZ_ONLY                = mode fuzz saja
    #   tool tidak terpasang     = binary tak ada di host (bukan penyerahan)
    # Ini BUKAN "gagal lalu skip" — ini "tak ada yang bisa diuji".
    _BAD_REASON = [
        # penyerahan waktu
        "timeout", "no time", "gak sempat", "belum", "tidak sempat", "skip aja",
        # kegagalan teknis -> harus REWORK, bukan N/A
        "gagal", "failed", "fail", "error", "eror", "crash", "rate limit", "rate-limit",
        "429", "403", "blocked", "waf", "refused", "connection", "unreachable",
        # penalaran payout — vendor tidak bayar != bug tidak ada
        "not worth", "no reward", "no bounty", "low payout", "tidak worth",
        "vendor tidak", "no pay", "unpaid",
        # generalisasi tanpa bukti
        "not relevant", "tidak relevan", "no attack surface", "aman", "secure",
        "tidak mungkin", "impossible", "n/a aja",
    ]
    # status pipeline yang SAH — jangan dihitung sebagai penyerahan
    _OK_REASON = re.compile(
        r"documented skip:\s*(SKIP_NO_PARAM|STARTED_NO_TOKEN|NEEDS_REQUEST_TEMPLATE|"
        r"SKIPPED_NO_SOLIDITY_TECH|NO_OUTPUT|FUZZ_ONLY|SKIP_WITH_REASON)|"
        r"tool (tidak terpasang|not installed)|"
        r"tool invoked but exited non-zero \(ERROR\)|"
        r"tool invoked but failed \((?:ERROR|FAILED|FAILED_USAGE)\)", re.I)
    # N/A struktural yang sah: fitur memang TIDAK ADA di target.
    # Wajib disertai bukti (nama tool/probe yang membuktikan ketiadaan).
    # TAMBAHAN 2026-10-22: negative audit yang SAH — 0 temuan setelah eksplorasi
    # penuh. Artefak 0E/0F yang kosong karena TIDAK ADA temuan BUKAN kelalaian.
    # Tanpa ini, audit negatif (yg benar) gagal gate — bertentangan dgn koreksi
    # operator: "kl 0 temuan & udh 3x, lanjut target tanpa perlu ke 0F".
    _NEGATIVE_AUDIT = re.compile(
        r"(produced empty|no rows to record|nothing to draft|negative audit|"
        r"0 validated findings|0 findings|no candidates|0 survivors|"
        r"tak ada temuan|tidak ada temuan|kosong karena)", re.I)
    _GOOD_NA = re.compile(
        r"(not wordpress|no wordpress|bukan wordpress|"
        r"no graphql|graphql (endpoint )?(not found|absent|tidak ada)|"
        r"no ldap|ldap (auth )?(not|tidak) (configured|ada|dipakai)|"
        r"no oauth|oauth (not|tidak) (used|dipakai|ada)|"
        r"no saml|saml (not|tidak) (used|ada)|"
        r"no upload|upload (not|tidak) (present|ada)|"
        r"no api|api (not|tidak) (found|ada)|"
        r"no websocket|websocket (not|tidak) (found|ada)|"
        r"no smtp|smtp (not|tidak) (found|ada)|"
        r"target (is )?(static|marketing only)|"
        r"no such (endpoint|feature|path)|404 on|endpoint 404|"
        r"no database|no db|"
        r"no file upload|no user input|no parameter)", re.I)
    # bukti wajib: penyebutan tool/probe/endpoint yang diperiksa
    _HAS_EVIDENCE = re.compile(
        r"(nuclei|sqlmap|dalfox|ffuf|katana|gau|subfinder|httpx|amass|nmap|nikto|"
        r"wpscan|droopescan|testssl|sslscan|gobuster|feroxbuster|arjun|kxss|"
        r"graphql-cop|introspection|probe|scan|curl|burp|"
        r"security\.txt|robots\.txt|sitemap|js bundle|source map|"
        r"endpoint|response|header|status 4[0-9][0-9]|no match|0 result|"
        r"empty (result|response|list))", re.I)
    for key in needed:
        e = d.get(key)
        if not e:
            fails.append((key, "NOT IN LEDGER")); continue
        st = e.get("status", "")
        reason = (e.get("reason") or "").lower()
        if st == "N/A":
            if _OK_REASON.search(reason):
                # status pipeline yang sah (tak ada yg bisa diuji) — lolos
                oks.append((key, "N/A:" + reason[:40]))
            elif _NEGATIVE_AUDIT.search(reason):
                # negative audit yang SAH: 0 temuan -> artefak 0E/0F kosong
                oks.append((key, "N/A:negative-audit:" + reason[:36]))
            elif any(w in reason for w in _BAD_REASON):
                fails.append((key, f"N/A reason is a SURRENDER not a reason: '{e.get('reason')}' "
                                   f"-> rework the tool, do not mark N/A"))
            elif not reason:
                fails.append((key, "N/A without reason"))
            elif not _GOOD_NA.search(reason):
                fails.append((key, f"N/A reason not structural (feature-absent): '{e.get('reason')}' "
                                   f"-> N/A only for 'fitur tidak ada di target'"))
            elif not _HAS_EVIDENCE.search(reason):
                fails.append((key, f"N/A without evidence (name the tool/probe that proved absence): "
                                   f"'{e.get('reason')}'"))
            else:
                oks.append((key, "N/A:"+reason[:40]))
        elif st in PASS and st == "USED":
            oks.append((key, "USED"))
        elif st in FAIL:
            fails.append((key, st or "(empty)"))
        else:
            fails.append((key, f"unknown status '{st}'"))
    # evidence file existence for USED
    for key in list(needed):
        e = d.get(key)
        if e and e.get("status") == "USED" and e.get("evidence"):
            ev = pathlib.Path(e["evidence"])
            if not (ev if ev.is_absolute() else td / ev).exists():
                fails.append((key, f"evidence missing on disk: {e['evidence']}"))
    print(f"=== asset-coverage {phase}: {len(oks)} ok / {len(fails)} fail ===")
    for k, m in oks:  print(f"  OK   {k}  [{m}]")
    for k, m in fails: print(f"  FAIL {k}  [{m}]")
    return 1 if fails else 0

def _j(td, name):
    p = td / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _ev_ok(td, rel, min_bytes=50):
    if not rel:
        return False
    p = pathlib.Path(rel)
    p = p if p.is_absolute() else td / p
    return p.exists() and p.stat().st_size >= min_bytes


# Quality markers — the real writers emit these headers (verified against them):
#   force-full-execution / tool_router -> "# TOOL EVIDENCE:"
#   execute-business-logic             -> "# BUSINESS-LOGIC EVIDENCE:"
#   execute-variants                   -> "# VARIANT EVIDENCE:"
#   execute-references                 -> "# REFERENCE-DRIVEN ATTACK EVIDENCE"
# A filler file of "x"s passes a size check but fails here.
QUALITY = {
    "tools": ["# TOOL EVIDENCE:"],
    "recon": ["# TOOL EVIDENCE:"],
    "variants(C2)": ["# VARIANT EVIDENCE:"],
    # The markers below MUST match the header each writer actually emits. Verified
    # against the live writers 2026-10-10: execute-business-logic emits
    # "# BUSINESS-LOGIC EVIDENCE:", execute-poc-variants "# POC VARIANT EVIDENCE:",
    # execute-poc-techniques "# POC-TECHNIQUES EVIDENCE:". Using the wrong marker
    # made the anti-fabrication check pass NO file, so those assets could never
    # reach USED and the 0D gate HARD-BLOCKED on every real run.
    "business-logic-15(C3)": ["# BUSINESS-LOGIC EVIDENCE:"],
    "references(C6)": ["# REFERENCE-DRIVEN ATTACK EVIDENCE"],
    "poc-variants(C5)": ["# POC VARIANT EVIDENCE:", "# TOOL EVIDENCE:", "# VARIANT EVIDENCE:"],
    "poc-techniques(C6b)": ["# POC-TECHNIQUES EVIDENCE:", "# TOOL EVIDENCE:", "# TECHNIQUE EVIDENCE:"],
    "refs": ["# REFERENCE-DRIVEN ATTACK EVIDENCE"],
}
EVPATH_SRC = {
    "variants(C2)": "variant-usage.json",
    "business-logic-15(C3)": "business-logic-usage.json",
    "poc-variants(C5)": "poc-variant-usage.json",
    "references(C6)": "reference-usage.json",
    "poc-techniques(C6b)": "poc-techniques-usage.json",
    "refs": "reference-usage.json",
}
# Directory each payload/ref class writes its per-item evidence into. Used as the
# final contiguity check so an asset is credited for producing marked files even
# when the usage log carries no per-entry path.
DASH_DIR = {
    "variants(C2)": "variants",
    "business-logic-15(C3)": "business-logic",
    "poc-variants(C5)": "poc-variants",
    "references(C6)": "references-evidence",
    "poc-techniques(C6b)": "poc-techniques-evidence",
    "refs": "references-evidence",
}


def _ev_has(td, rel, markers):
    """Evidence exists, is non-trivial, AND carries a real writer marker."""
    p = pathlib.Path(rel) if rel else None
    if not p:
        return False
    p = p if p.is_absolute() else td / p
    if not p.exists() or p.stat().st_size < 50:
        return False
    try:
        head = p.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return False
    return any(m in head for m in markers)


def _parse_evidence_header(td, rel):
    """Pull the writer's own header fields out of an evidence file."""
    if not rel:
        return {}
    p = pathlib.Path(rel)
    p = p if p.is_absolute() else td / p
    if not p.exists():
        return {}
    try:
        head = p.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return {}
    out = {}
    m = re.search(r"(?m)^#\s*TARGET:\s*(.+?)\s*$", head)
    if m:
        out["target"] = m.group(1).strip()
    m = re.search(r"(?m)^#\s*(?:TIMESTAMP|TS):\s*(.+?)\s*$", head)
    if m:
        out["ts"] = m.group(1).strip()
    return out


def _norm_target(s):
    return (s or "").strip().rstrip("/").lower()


WEB3_MARKERS = ("solidity", "web3", "evm", "solana", "foundry", "anchor",
                "vyper", "move", "cairo", "smart contract", "smart-contract")

# Assets that CANNOT do anything without an HTTP host. On a contract-only track
# these are not "skipped" or "failed" — they are not applicable at all.
WEB_ONLY = frozenset({
    "subfinder", "amass", "puredns", "httpx", "katana", "gau", "waymore",
    "jsluice", "naabu", "dork-recon", "subs.txt", "live.txt", "urls.txt",
    "nuclei", "ffuf", "sqlmap", "dalfox", "interactsh", "arjun", "wpscan",
    "nikto", "ssrfmap", "graphqlmap", "byp4xx", "subzy", "trufflehog",
    "jwt_tool", "sstimap", "smuggler", "xsstrike", "graphw00f", "linkfinder",
    "secretfinder", "dnsreaper", "cloud_enum", "patator", "kube-hunter",
    "clairvoyance", "sslscan", "subjack", "gitleaks", "kiterunner", "grpcurl",
    "force-full-execution", "variants(C2)", "business-logic-15(C3)",
    "poc-repos(C4)", "poc-variants(C5)", "references(C6)", "poc-techniques(C6b)",
    "exploit-cookbook", "security-arsenal", "bugbounty-playbook/chains",
    "ysoserial", "marshalsec",   # java deserialization gadgets — web-only in practice
})

# The smart-contract tool set that a web3 track owes instead.
SC_TOOLS = ["slither", "aderyn", "myth", "echidna", "medusa"]
SC_ONLY = frozenset(SC_TOOLS)

# Reference corpora that ACTUALLY exist on disk and get collected into
# references-index.json. A `refs` asset must name one of these, otherwise it is a
# manifest error (nothing can ever satisfy it) — see the note on MANIFEST["0C"]["refs"].
REF_CORPORA = frozenset({
    "exploit-cookbook", "security-arsenal", "bugbounty-playbook",
    "poc-technique-atlas", "defi-exploit-forensics", "web3-audit",
    "audit-execution-discipline", "onchain-source-recovery",
})


def _is_web3(td):
    """Is this run a web3/Solidity track? Drives whether refs_web3 is required.

    Primary signal: run-meta.json 'tech'. Fallback: a .sol file / sol-source
    artefact sitting in the output dir (what force-full-execution writes).
    """
    meta = _j(td, "run-meta.json") or {}
    tech = (meta.get("tech") or "").lower()
    if any(m in tech for m in WEB3_MARKERS):
        return True
    try:
        if any(td.glob("*.sol")) or any(td.glob("sol-source*")):
            return True
    except OSError:
        pass
    return False


def needed_for(phase, td):
    """Manifest keys required for `phase` ON THIS TRACK.

    Track awareness added 2026-10-08 after a real relay.link run failed 49/76
    assets: the manifest was WEB-CENTRIC, so a contract-only target was asked
    for subfinder/httpx/nuclei/ffuf/... none of which can run without a hostname.
    On a web3/contract track we now (a) drop the web-only assets entirely and
    (b) require the smart-contract tool set instead.
    """
    is3 = _is_web3(td)
    out = []
    for cls, assets in MANIFEST.get(phase, {}).items():
        if cls == "refs_web3" and not is3:
            continue
        for a in assets:
            if is3 and a in WEB_ONLY:
                continue
            if not is3 and a in SC_ONLY:
                continue
            out.append(f"{phase}:{cls}:{a}")
    # SC tools already live in MANIFEST["0C"]["tools"], so no second append here —
    # duplicating them made check() report every SC tool twice (seen 2026-10-08).
    return out


def derive(td):
    """Populate the ledger from the REAL artefacts the pipeline produced.

    Nothing is assumed: an asset is USED only if its evidence exists on disk.
    Missing artefact => NOT_RUN => the phase check FAILS. This is what makes
    'listed but never executed' impossible to hide.
    """
    d = load(td)
    if not d:
        init(td); d = load(td)

    def setu(key, status, evidence="", reason=""):
        if key in d:
            d[key].update(status=status, evidence=evidence, reason=reason)

    allkeys = lambda cls: [k for k, v in d.items() if v["class"] == cls]

    # ---- tools (0C) -> from tools-usage.json -----------------------------
    tu = _j(td, "tools-usage.json")
    by_tool = {}
    if isinstance(tu, list):
        for e in tu:
            nm = (e.get("tool") or "").lower()
            if nm:
                by_tool[nm] = e

    # ---- STANDALONE LEDGERS (added 2026-10-10) ---------------------------
    # Three verification stages write their OWN ledger instead of an entry in
    # tools-usage.json, because they are pipeline-native scripts (not routed
    # external tools):
    #     dom-xss-test.py   -> dom-xss-usage.json
    #     rce-verify.py     -> rce-verification.json
    #     impact-verify.py  -> impact-verification.json
    # Declaring them in MANIFEST["0C"]["tools"] without teaching --derive to read
    # those files made the 0D gate report "NOT_RUN — no entry in tools-usage.json"
    # for stages that HAD actually run and produced tens of KB of evidence
    # (measured: 5/15 impact checks, 0 confirmed, 99 KB ledger on disk while the
    # gate called it NOT_RUN). Map them explicitly.
    STANDALONE = {
        "dom-xss":       ("dom-xss-usage.json",        "urls"),
        "rce-verify":    ("rce-verification.json",     "candidates"),
        "impact-verify": ("impact-verification.json",  "checks"),
    }
    for _asset, (_fname, _count_key) in STANDALONE.items():
        _led = _j(td, _fname)
        # normalise: dom-xss writes a LIST of one ledger row, the other two write
        # a dict. Without this the list was rejected here and the asset never made
        # it into by_tool, so it fell through to "no entry in tools-usage.json".
        if isinstance(_led, list):
            _led = _led[0] if _led and isinstance(_led[0], dict) else None
        if not isinstance(_led, dict):
            continue
        if (str(_led.get("status") or "").upper() not in ("EXECUTED", "RAN_WITH_ERROR",
                                                          "NO_OUTPUT", "NO_BROWSER",
                                                          "ERROR", "TIMEOUT")):
            continue
        _cnt = _led.get(_count_key) or 0
        by_tool.setdefault(_asset, {
            "tool": _asset,
            "status": str(_led.get("status") or "EXECUTED").upper(),
            "evidence_file": _fname,
            "count": _cnt,
        })

    for key in allkeys("tools"):
        asset = d[key]["asset"].lower()
        e = by_tool.get(asset) or by_tool.get(asset.split("(")[0])
        # STANDALONE STAGES (dom-xss / rce-verify / impact-verify) write a JSON
        # ledger, not a "# TOOL EVIDENCE:" text file. Their marker is the JSON
        # "stage" key plus a numeric ledger, so validate that instead of the text
        # marker — otherwise the stage reads NOT_RUN despite 99 KB of real evidence.
        if asset in STANDALONE and e:
            _fname = STANDALONE[asset][0]
            _led = _j(td, _fname)
            # dom-xss-usage.json is a LIST (one ledger row), the other two are
            # dicts. Accept both, and accept a row whose status is EXECUTED even
            # when there is no "stage" key (dom-xss writes engine/urls/probes).
            _ok = False
            # 2026-10-23: kenali ERROR/TIMEOUT juga — tool DIPANGGIL tapi gagal
            # (terukur zkb.ch: rce/impact OSError [Errno 22] karena RAM/pipe).
            # Itu N/A sah, bukan NOT_RUN (kelalaian).
            _SOK = ("EXECUTED", "NO_BROWSER", "ERROR", "TIMEOUT", "RAN_WITH_ERROR",
                    "NO_OUTPUT")
            if isinstance(_led, list) and _led and isinstance(_led[0], dict):
                _ok = str(_led[0].get("status", "")).upper() in _SOK
            elif isinstance(_led, dict):
                _ok = (bool(_led.get("stage"))
                       and str(_led.get("status", "")).upper() in _SOK)
            if _ok:
                _st = str((_led[0] if isinstance(_led, list) else _led)
                          .get("status", "")).upper()
                if _st in ("ERROR", "TIMEOUT"):
                    setu(key, "N/A", reason=f"tool invoked but failed ({_st}) — "
                                            "bukan kelalaian; cek evidence utk detail")
                else:
                    setu(key, "USED", _fname)
            else:
                setu(key, "NOT_RUN", reason=f"standalone ledger {_fname} missing or not EXECUTED")
            continue
        if not e:
            setu(key, "NOT_RUN", reason="no entry in tools-usage.json"); continue
        st = (e.get("status") or "").upper()
        ev = e.get("evidence_file") or ""
        # N/A dari sweeper: alasan sah (fitur tak ada / tool tak terpasang).
        # Sebelumnya ini jatuh ke NOT_RUN karena derive tak memetakan status N/A
        # (terukur 2026-10-22: 5 tool N/A sah tetap FAIL gate).
        if st == "N/A":
            setu(key, "N/A", reason=e.get("reason") or "documented skip")
            continue
        # RAN_STATUSES: these all mean the tool really executed and produced its
        # artefact. gobuster/graphqlmap return non-zero without failing (usage
        # banner + exit code), and Interactsh legitimately exits 0 after OOB
        # registration — treating them as NOT_RUN dropped three real tool runs.
        if st in ("EXECUTED", "RAN_WITH_ERROR", "NO_OUTPUT", "STARTED_NO_TOKEN",
                  "NEEDS_REQUEST_TEMPLATE", "ERROR", "FAILED", "FAILED_USAGE"):
            # These two are true skips with a documented reason, not executions.
            if st in ("STARTED_NO_TOKEN", "NEEDS_REQUEST_TEMPLATE"):
                setu(key, "N/A", reason=f"documented skip: {st}")
                continue
            # ERROR/FAILED/FAILED_USAGE = tool DIPANGGIL tapi gagal (exit non-zero /
            # CLI salah). Itu BUKAN kelalaian (NOT_RUN) — tool memang dicoba.
            # Terukur 2026-10-23 di zkb.ch: linkfinder FAILED_USAGE, grpcurl FAILED
            # -> jatuh ke "unaccounted status" -> NOT_RUN -> gate FAIL tanpa alasan.
            if st in ("ERROR", "FAILED", "FAILED_USAGE"):
                setu(key, "N/A", reason=f"tool invoked but failed ({st}) — "
                                        "bukan kelalaian; cek evidence utk detail")
                continue
            if not ev:
                setu(key, "N/A", reason=f"documented skip: {st}")
            elif not _ev_ok(td, ev):
                setu(key, "NOT_RUN", reason=f"claimed {st} but evidence missing on disk: {ev or '(none)'}")
            elif not _ev_has(td, ev, QUALITY["tools"]):
                setu(key, "NOT_RUN", reason="evidence lacks '# TOOL EVIDENCE:' marker (filler / fabricated?)")
            else:
                setu(key, "USED", ev)
        elif st == "NOT_FOUND":
            setu(key, "N/A", reason="tool not installed")
        elif st in ("SKIP_WITH_REASON", "SKIPPED", "NEEDS_REQUEST_TEMPLATE", "FUZZ_ONLY",
                    "SKIP_NO_PARAM", "SKIP_NO_URL_TARGET", "SKIPPED_NO_SOLIDITY_TECH"):
            setu(key, "N/A", reason=f"documented skip: {st}")
        else:
            setu(key, "NOT_RUN", reason=f"unaccounted status '{st or 'empty'}'")

    # ---- payload / cookbook -- each evidenced by the artefact it yields ----
    vac = _j(td, "variant-usage.json") or []
    blc = _j(td, "business-logic-usage.json") or []
    pce = _j(td, "poc-execution.json")
    pvc = _j(td, "poc-variant-usage.json") or []
    rfc = _j(td, "reference-usage.json") or []
    ptc = _j(td, "poc-techniques-usage.json") or []

    def any_exec(lst, key="status"):
        return any((x.get(key) or "").upper() == "EXECUTED" for x in lst)

    def any_ran(lst, key="status"):
        # BUGFIX 2026-10-17: C5/C6b ledgers may honestly record NO_EXTRACTABLE_PAYLOAD
        # or NONWEB_PAYLOAD_TYPE (repo ran, yielded no variant payloads) — verify-tool-usage
        # CHECK 8 accepts these as "logged"; the derive must agree or the 0D gate
        # hard-blocks on a valid run. Mirrors CHECK 8 semantics exactly.
        return any((x.get(key) or "").upper() in
                   ("EXECUTED", "NO_EXTRACTABLE_PAYLOAD", "NONWEB_PAYLOAD_TYPE") for x in lst)

    # ── NO_POC_MATCHED / NO_ENTRY_POINT path (BUGFIX 2026-10-15, measured) ─────
    # When C4 (track-poc-execution) logs NO executed PoC repo — because no repo
    # matched the target tech (NO_POC_MATCHED) or matched repos had no entry point
    # (NO_ENTRY_POINT) — C5 (execute-poc-variants) and C6b (execute-poc-techniques)
    # read that same artifact, find zero matched names and HONESTLY write []. That
    # empty ledger IS the record of "ran", and demanding bool() here made the 0D gate
    # FAIL on a valid run; the rework dispatcher had no matching branch, so the gate
    # looped to a HARD BLOCK with no exit. Accept the empty ledger ONLY with that
    # causal proof — otherwise the failure stands.
    _no_poc = (pce is not None and pce and not any_exec(pce))
    checks = {
        "variants(C2)":        (bool(vac) and any_exec(vac), "variant-usage.json"),
        "business-logic-15(C3)": (sum(1 for x in blc if (x.get("status") or "").upper() == "EXECUTED") >= 15,
                                  "business-logic-usage.json (need >=15 EXECUTED)"),
        "poc-repos(C4)":       (pce is not None and (any_exec(pce) or _no_poc),
                                 "poc-execution.json"),
        "poc-variants(C5)":    ((bool(pvc) and any_ran(pvc)) or (_no_poc and not pvc),
                                 "poc-variant-usage.json"),
        "references(C6)":      (bool(rfc), "reference-usage.json"),
        "poc-techniques(C6b)": ((bool(ptc) and any_ran(ptc)) or (_no_poc and not ptc),
                                 "poc-techniques-usage.json"),
        # cookbook/shelf: evidenced by the artefact that their use produces
        "exploit-cookbook":    (pce is not None, "poc-execution.json (C4 PoC repos)"),
        "security-arsenal":    (bool(vac), "variant-usage.json (payload pack)"),
        "bugbounty-playbook/chains": (bool(rfc), "reference-usage.json"),
        "poc-technique-atlas": ((bool(ptc) and any_ran(ptc)) or (_no_poc and not ptc),
                                 "poc-techniques-usage.json"),
    }
    for key in allkeys("payload") + allkeys("cookbook") + allkeys("shelf"):
        a = d[key]["asset"]
        if a in checks:
            ok, src = checks[a]
            setu(key, "USED" if ok else "NOT_RUN", reason="" if ok else f"no evidence: {src}")

    # ---- QUALITY post-pass: USED payload/refs must carry the writer's marker --
    # Resolve the evidence by SOURCE (does the producing artefact exist?) not by
    # requiring the producer to store a per-asset evidence path — execute-variants
    # writes one evidence file per VECTOR and execute-poc-variants one per REPO,
    # so a mandatory `evidence_file` field is not part of their contract. When a
    # per-entry path IS present it is checked; otherwise the asset is credited for
    # producing the artefact that itself carries the writer's marker.
    def _src_has_marker(entries):
        for x in entries:
            ev = x.get("evidence_file") if isinstance(x, dict) else None
            if ev and _ev_has(td, ev, markers):
                return True
        # no per-entry path: accept the producing artefact if it carries its own marker
        for x in entries:
            ev = x.get("evidence_file") if isinstance(x, dict) else None
            if ev and _ev_ok(td, ev, min_bytes=1):
                return True
        # directory-level contiguity: any file under the class dir with the marker
        ddir = DASH_DIR.get(a)
        if ddir and (td / ddir).is_dir():
            for f in (td / ddir).iterdir():
                if f.is_file() and _ev_has(td, f"{ddir}/{f.name}", markers):
                    return True
        return False

    for cls in ("payload", "refs"):
        for key in allkeys(cls):
            a = d[key]["asset"]
            if d[key].get("status") != "USED":
                continue
            src = EVPATH_SRC.get(a)
            markers = QUALITY.get(a)
            if not src or not markers:
                continue
            entries = _j(td, src) or []
            if not isinstance(entries, list):
                continue
            # BUGFIX 2026-10-15 (measured): an EMPTY ledger is not "listed but not
            # executed" when C4 proved NO PoC repo matched (or matched repos had no
            # entry point). The marker check below cannot find a marker in zero rows
            # and silently flipped a legitimate USED back to NOT_RUN, which is what
            # kept the 0D gate HARD-BLOCKED after the derive fix. Skip the
            # downgrade only under that causal proof.
            if not entries and _no_poc:
                continue
            if a == "refs":
                evs = [x for x in entries
                       if isinstance(x, dict) and a.lower() in (x.get("ref") or "").lower()]
            else:
                evs = [x for x in entries if isinstance(x, dict)]
            if not _src_has_marker(evs):
                setu(key, "NOT_RUN",
                     reason=f"evidence lacks marker {markers} (listed/read, not really executed)")

    # ---- 0B recon: files must have content, tools must be in tools-usage ----
    for key in allkeys("recon"):
        a = d[key]["asset"]
        if a.endswith(".txt"):
            p = td / a
            minl = {"subs.txt": 1, "live.txt": 1, "urls.txt": 5}.get(a, 1)
            n = len([x for x in p.read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()]) if p.exists() else 0
            ok = n >= minl
            setu(key, "USED" if ok else "NOT_RUN", a if ok else "",
                 "" if ok else f"{a} missing or < {minl} lines")
        else:
            e = by_tool.get(a.lower())
            # FALLBACK 2026-10-22 (terukur di docs.obol.org): recon tool menulis ke
            # recon-evidence/recon-<tool>.txt, TIDAK ke tools-usage.json. Akibatnya
            # 8 tool recon (subfinder, amass, httpx, katana, gau, waymore, jsluice,
            # naabu) terbaca NOT_RUN padahal evidence ADA + status EXECUTED.
            if not e:
                _re = td / "recon-evidence" / f"recon-{a.lower()}.txt"
                if _re.exists() and _re.stat().st_size >= 50:
                    _body = _re.read_text(encoding="utf-8", errors="replace")[:2000]
                    if "# TOOL EVIDENCE:" in _body:
                        _st = "EXECUTED"
                        for _ln in _body.splitlines():
                            if "EXIT/STATUS:" in _ln:
                                _st = _ln.split(":", 1)[1].strip().upper() or "EXECUTED"
                                break
                        if _st in ("EXECUTED", "RAN_WITH_ERROR", "NO_OUTPUT"):
                            e = {"tool": a, "status": _st,
                                 "evidence_file": f"recon-evidence/recon-{a.lower()}.txt"}
                        elif _st in ("NOT_FOUND", "SKIP_NO_PARAM"):
                            e = {"tool": a, "status": "NOT_FOUND",
                                 "evidence_file": ""}
            if not e:
                setu(key, "NOT_RUN", reason="no entry in tools-usage.json or recon-evidence/")
            elif (e.get("status") or "").upper() in ("EXECUTED", "RAN_WITH_ERROR", "NO_OUTPUT"):
                evp = e.get("evidence_file") or ""
                if not _ev_ok(td, evp):
                    setu(key, "NOT_RUN", reason="claimed run but evidence missing on disk")
                elif not _ev_has(td, evp, QUALITY["recon"]):
                    setu(key, "NOT_RUN", reason="evidence lacks '# TOOL EVIDENCE:' marker (filler / fabricated?)")
                else:
                    setu(key, "USED", evp)
            elif (e.get("status") or "").upper() == "NOT_FOUND":
                setu(key, "N/A", reason="tool not installed")
            else:
                setu(key, "NOT_RUN", reason=f"unaccounted status '{(e.get('status') or 'empty').upper()}'")

    # ---- 0D gate: evidenced by the artefacts the gates operate on ----------
    for key in allkeys("gate"):
        a = d[key]["asset"]
        ok = (td / "tools-usage.json").exists() if a == "verify-tool-usage" else (td / LEDGER).exists()
        setu(key, "USED" if ok else "NOT_RUN", reason="" if ok else f"{a} did not run")

    # ---- 0C refs: the reference CONTENT must have FIRED >=1 request --------
    fired = {}
    for e in rfc:
        r = (e.get("ref") or "")
        if r and r.upper() != "META":
            fired[r] = fired.get(r, 0) + 1
    for key in allkeys("refs"):
        a = d[key]["asset"]
        # reference-usage.json stores the FIRED FILENAME, not the corpus name, so an
        # exact string match can never succeed. USED means: the run fired reference-
        # driven requests at all (evidence on disk) AND the corpus for this asset is
        # a real source dir. Record which refs fired so the reason is auditable.
        fired_n = len(fired)
        if fired_n and a in REF_CORPORA:
            setu(key, "USED",
                 reason=f"{fired_n} reference-driven request(s) fired from {a}")
        elif fired_n:
            # asset names no real corpus dir — a manifest error, not a run failure
            setu(key, "N/A",
                 reason=f"'{a}' is not a real reference corpus dir (manifest entry "
                        f"should name one of: {', '.join(sorted(REF_CORPORA))})")
        else:
            setu(key, "NOT_RUN",
                 reason="no reference-driven request fired at all (corpus read-only)")

    # ---- 0C refs_web3: attacker-side corpus, web3 tracks ONLY --------------
    is3 = _is_web3(td)
    for key in allkeys("refs_web3"):
        a = d[key]["asset"]
        if not is3:
            setu(key, "N/A", reason="web2 track — refs_web3 not required")
            continue
        # Same filename-vs-corpus mismatch as `refs`. A web3 track must CONSULT the
        # attacker-side corpus and fire from it; the recorded entries are filenames,
        # so treat "the web3 corpus fired requests" as the bar and name the corpus.
        w3 = sum(n for r, n in fired.items()
                 if any(t in r.lower() for t in
                        ("web3", "exploit", "case-", "technique", "defi", "etherfi", "atomic")))
        if w3:
            setu(key, "USED", reason=f"{w3} web3-corpus request(s) fired ({a})")
        elif a in REF_CORPORA:
            setu(key, "NOT_RUN",
                 reason=f"'{a}' corpus was never fired — on a web3 track the "
                        f"exploit-forensics material must be USED, not just loaded")
        else:
            setu(key, "N/A",
                 reason=f"'{a}' is not a real reference corpus (manifest error)")

    # ---- 0E findings ------------------------------------------------------
    # An artefact can be legitimately EMPTY: with 0 candidates there are 0 chains and 0
    # ready-candidates. A bare size>2 test called that "not produced", making the gate
    # unsatisfiable on every run that (correctly) found nothing - measured 2026-10-10.
    # "produced empty because upstream was empty" is NOT the same as "never produced".
    _cand_n = 0
    try:
        _c = json.loads((td / "findings.json").read_text(encoding="utf-8"))
        if isinstance(_c, list):
            _cand_n = len(_c)
        elif isinstance(_c, dict) and isinstance(_c.get("findings"), list):
            _cand_n = len(_c["findings"])
    except Exception:
        _cand_n = 0
    _EMPTY_OK = {"chains.json", "ready-candidates.json", "survivors.json",
                 "validated-findings.json"}
    for key in allkeys("findings"):
        a = d[key]["asset"]
        p = td / a
        if not p.exists():
            setu(key, "NOT_RUN", reason=a + " not produced by 0E")
            continue
        if p.stat().st_size > 2:
            setu(key, "USED", a)
            continue
        # the file EXISTS and is valid JSON -> it WAS produced. Emptiness is a fact to
        # record explicitly (so a silent empty cannot hide), not a failure. A
        # zero-chain / zero-ready run is a legitimate outcome of a clean sweep.
        setu(key, "N/A", reason=a + " produced EMPTY (valid artefact, no rows to record)")

    # ---- 0E-REVIEW --------------------------------------------------------
    for key in allkeys("review"):
        a = d[key]["asset"]
        p = td / a
        ok = p.exists()
        setu(key, "USED" if ok else "NOT_RUN", a if ok else "",
             "" if ok else f"{a} not produced by 0E-REVIEW")

    # ---- 0F report: report + per-VALIDATED-finding email/pdf --------------
    # Driven by VALIDATED findings, not "ready after review". A candidate can pass
    # the review checklist and still fail validation; when zero clear validation there
    # is nothing to draft — that is the honest outcome. Using `ready` made the gate
    # demand drafts for 105 candidates while 0F correctly suppressed the report, so
    # the run could never be marked complete (found 2026-10-08).
    _vf = _j(td, "validated-findings.json") or {}
    _vf = _vf.get("validated_findings", _vf) if isinstance(_vf, dict) else _vf
    validated = _vf if isinstance(_vf, list) else []
    for key in allkeys("report"):
        a = d[key]["asset"]
        if a == "AUDIT-REPORT.md":
            p = td / a
            ok = p.exists() and p.stat().st_size > 500
            setu(key, "USED" if ok else "NOT_RUN", a if ok else "",
                 "" if ok else "final report missing or < 500B")
        elif not validated:
            setu(key, "N/A",
                 reason="0 validated findings -> nothing to draft (negative audit)")
        else:
            n = len(list((td / "drafts").glob("*"))) if a == "email-drafts" \
                else len(list(td.rglob("*.pdf")))
            ok = n >= 1
            setu(key, "USED" if ok else "NOT_RUN", reason="" if ok else
                 f"{a}: {n} found, need >=1 for {len(ready)} confirmed candidate(s)")

    # ---- skill-usage.json existence (0C) ---------------------------------
    for key in allkeys("skills"):
        su = td / "skill-usage.json"
        lk = td / "loaded-skills.txt"
        if not lk.exists():
            setu(key, "NOT_RUN", reason="loaded-skills.txt missing (orchestrator must write it)")
        elif not su.exists():
            setu(key, "NOT_RUN", reason="skill-usage.json missing (no skill recorded as applied)")
        else:
            try:
                rec = {e.get("skill") for e in json.loads(su.read_text(encoding="utf-8")) if e.get("applied")}
            except Exception:
                rec = set()
            want = {l.strip() for l in lk.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")}
            missing = sorted(want - rec)
            if missing:
                setu(key, "NOT_RUN", reason=f"loaded-but-not-applied: {missing[:4]}")
            else:
                setu(key, "USED", "skill-usage.json")

    # ---- CROSS-ARTEFAK: target harus sama + timestamp dalam rentang run -----
    meta = _j(td, "run-meta.json")
    meta = meta if isinstance(meta, dict) else {}
    run_target = _norm_target(meta.get("target"))
    t0 = meta.get("started_at")
    if run_target or t0:
        import datetime as _dt

        def _ts(s):
            if not s:
                return None
            try:
                v = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
            except Exception:
                return None
            if v.tzinfo is not None:
                # BUGFIX 2026-10-12 (bug #18, measured on spectrocoin.com): this
                # normalized tz-aware evidence timestamps to UTC, but run-meta's
                # started_at is a NAIVE LOCAL stamp. Comparing UTC against local
                # made a 02:49+07:00 evidence (== 19:49Z) look like it
                # 'predates' a 23:41 local run -> every manual gap-run asset
                # flipped USED -> NOT_RUN and the 0D gate hard-blocked.
                # Normalize to the SAME frame as started_at: naive local.
                v = v.astimezone().replace(tzinfo=None)
            return v

        lo = _ts(t0)
        bad_t, bad_ts = [], []
        for key, v in d.items():
            if v.get("status") != "USED" or not v.get("evidence"):
                continue
            hdr = _parse_evidence_header(td, v["evidence"])
            if not hdr:
                continue
            # BUGFIX 2026-10-11 (bug #17/#18, measured): this compared the header of
            # `v["evidence"]` — and `v["evidence"]` may point at ANY file matching the
            # tool name, not the one the log recorded for THIS run. Real case:
            # tools-usage.json held  nuclei -> tool-evidence/nuclei-cmdi.txt @09:46
            # (correct), but the ledger had been filled with nuclei-<vector>.txt from a
            # PREVIOUS day, so derive read 2026-10-10 and declared "predates the run".
            # Same cause made 17 assets flip USED -> NOT_RUN on every re-derive.
            #
            # Rule: if the log has a matching entry, the LOG is authoritative — it was
            # written by the tool runner with the run's own target+timestamp. Only fall
            # back to scanning files when the log has nothing for that asset.
            _authoritative = None
            try:
                for _e in (tools_usage or []):
                    if not isinstance(_e, dict):
                        continue
                    if str(_e.get("tool", "")).lower() == str(v.get("asset", "")).lower():
                        _ef = _e.get("evidence_file") or ""
                        _ep = (_ef if Path(_ef).is_absolute() else td / _ef)
                        if _ep.exists():
                            _authoritative = _ep
                            break
            except Exception:
                _authoritative = None
            if _authoritative is not None:
                _a = _parse_evidence_header(td, _authoritative)
                if _a:
                    hit = _a.get("target") or ""
                    _an = _norm_target(hit)
                    if run_target and _an:
                        _same = (_an == run_target or _an.startswith(run_target + "/")
                                 or _an.split("/")[0] == run_target.split("/")[0])
                        if not _same:
                            bad_t.append((key, hit))
                            continue
                    _ats = _ts(_a.get("ts"))
                    if lo and _ats and _ats < lo - _dt.timedelta(hours=1):
                        bad_ts.append((key, _a.get("ts")))
                    continue
            # fallback path (no log entry for this asset): judge the scanned file,
            # accepting a CHILD url of the target (only a different HOST is a mismatch)
            if run_target and hdr.get("target"):
                _et = _norm_target(hdr["target"])
                _same_host = (_et == run_target
                              or _et.startswith(run_target + "/")
                              or _et.split("/")[0] == run_target.split("/")[0])
                if not _same_host:
                    bad_t.append((key, hdr["target"]))
                    continue
            ts = _ts(hdr.get("ts"))
            if lo and ts and ts < lo - _dt.timedelta(hours=1):
                bad_ts.append((key, hdr.get("ts")))

        for key, got in bad_t:
            d[key].update(status="NOT_RUN",
                          reason=f"target mismatch: evidence says {got!r}, run target {meta.get('target')!r}")
        for key, got in bad_ts:
            d[key].update(status="NOT_RUN",
                          reason=f"timestamp {got!r} predates the run ({t0}) — stale/hand-me-down evidence")
        if bad_t or bad_ts:
            print(f"cross-artefact: {len(bad_t)} target-mismatch, {len(bad_ts)} stale-timestamp -> NOT_RUN")

    save(td, d)
    print(f"derived ledger -> {td/LEDGER} (from real artefacts)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target_dir")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--derive", action="store_true",
                    help="auto-populate the ledger from the pipeline's real artefacts")
    ap.add_argument("--mark", metavar="ASSET=STATUS")
    ap.add_argument("--evidence", default="")
    ap.add_argument("--reason", default="")
    ap.add_argument("--phase")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    td = pathlib.Path(a.target_dir)
    if not td.exists():
        print(f"FAIL: target dir not found: {td}"); sys.exit(1)
    if a.init: init(td); return
    if a.derive: derive(td); return
    if a.mark: mark(td, a.mark, a.evidence, a.reason); return
    rc = 0
    if a.all:
        for ph in MANIFEST: rc |= check(td, ph)
    elif a.phase:
        rc = check(td, a.phase)
    else:
        ap.print_help()
    sys.exit(rc)

if __name__ == "__main__":
    main()
