#!/usr/bin/env python3
"""
net_intercept_check.py — 2-layer network diagnosis: DNS hijack + TCP interception.

WHY THIS EXISTS
    When a recon/search tool silently returns nothing on a home or mobile-ISP
    network, the cause is usually the OPERATOR'S NETWORK, not the target. There are
    two independent layers and only diagnosing the first wastes an hour:

      layer 1  DNS hijack        -> resolver returns a foreign IP
                                     fix: DoH + --host-resolver-rules / --resolve  (sufficient)
      layer 2  TCP interception  -> resolver is right, route is hijacked, TLS answers
                                     as the target regardless of SNI
                                     fix: DNS bypass is NOT enough; use a browser path

    Symptom that misleads: plain `curl` -> http=000, AND
    `curl --doh-url https://cloudflare-dns.com/dns-query` -> ALSO 000.
    DoH fixes the NAME, not the ROUTE. Confirm layer 2 with:
        curl --resolve <host>:443:<real-ip>   # works  => layer 2 present
        curl <host>                           # fails  => consistent with interception

DETECTION TRICK (layer 2)
    Connect to the REAL IP but send a FOREIGN SNI (example.com). A correct server
    presents its own cert or resets; a transparent interceptor presents the cert for
    the SNI you asked for -- i.e. the certificate follows the SNI, not the IP.
    That inversion is the tell.

USAGE
    python net_intercept_check.py                 # default search hosts
    python net_intercept_check.py example.com foo.tld
    python net_intercept_check.py --json          # machine-readable

EXIT CODES
    0  clean (no hijack, no interception)
    1  DNS hijack only            -> DoH + host-resolver-rules fully repairs it
    2  DNS hijack + interception  -> must use a browser path, curl will not work

NOTE ON CERT PARSING
    ssl.getpeercert() returns {} when verify_mode == CERT_NONE, so the cert MUST be
    read with binary_form=True and parsed. `cryptography` is usually available (it
    ships with CloakBrowser); the DER-regex fallback covers when it is not.
"""
import argparse
import json
import re
import socket
import ssl
import subprocess
import sys
import urllib.request

DEFAULT_HOSTS = [
    "duckduckgo.com", "html.duckduckgo.com", "lite.duckduckgo.com",
    "links.duckduckgo.com", "improving.duckduckgo.com",
]

DOH_ENDPOINTS = [
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/resolve",
    "https://dns.quad9.net:5053/dns-query",
]

# block-page markers seen in ISP resolver PTRs / answers
HIJACK_MARKERS = ("block.", "internetpositif", "trustpositif", "nav.", "static-")


# ─────────────────────────────── layer 1: DNS ───────────────────────────────

def doh_resolve(host, rrtype="A", timeout=10):
    """Resolve *host* via DoH (the ground truth). Returns list of IPv4 strings."""
    for ep in DOH_ENDPOINTS:
        try:
            req = urllib.request.Request(
                f"{ep}?name={host}&type={rrtype}",
                headers={"accept": "application/dns-json", "user-agent": "net-check/1.0"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
            ips = [a["data"] for a in d.get("Answer", [])
                   if a.get("type") == 1 and re.match(r"^\d+\.\d+\.\d+\.\d+$", a.get("data", ""))]
            if ips:
                return ips
        except Exception:
            continue
    return []


def system_resolve(host):
    """Resolve via the OS resolver. Returns list of IPv4 strings."""
    out = []
    try:
        p = subprocess.run(["nslookup", host], capture_output=True, text=True, timeout=15)
        for m in re.finditer(r"Address:\s+(\d+\.\d+\.\d+\.\d+)", p.stdout or ""):
            out.append(m.group(1))
    except Exception:
        pass
    return out


def hijack_state(host):
    """(hijacked, system_ips, real_ips). Compares OS answer against DoH truth."""
    sys_ips = system_resolve(host)
    real_ips = doh_resolve(host)
    if not sys_ips:
        return False, sys_ips, real_ips
    hijacked = bool(real_ips) and not (set(sys_ips) & set(real_ips))
    if not hijacked:
        try:
            p = subprocess.run(["nslookup", sys_ips[0]], capture_output=True, text=True, timeout=10)
            if any(mk in (p.stdout or "").lower() for mk in HIJACK_MARKERS):
                hijacked = True
        except Exception:
            pass
    return hijacked, sys_ips, real_ips


# ───────────────────────────── layer 2: TLS / TCP ─────────────────────────────

def tls_cert_cn(ip, sni, timeout=12):
    """(cn, detail) of the cert served by *ip* when asking for *sni*."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((ip, 443), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=sni) as s:
                der = s.getpeercert(binary_form=True)   # must be binary: CERT_NONE -> {} otherwise
        if not der:
            return None, "ERR:no cert"
        try:
            from cryptography import x509
            from cryptography.hazmat.backends import default_backend
            cert = x509.load_der_x509_certificate(der, default_backend())
            cn = ""
            for attr in cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME):
                cn = attr.value
            return cn, f"CN={cn} | issuer={cert.issuer.rfc4514_string()}"
        except Exception:
            cand = [x.decode("latin-1") for x in
                    re.findall(rb"[A-Za-z0-9*][A-Za-z0-9.*_-]{3,60}\.[A-Za-z]{2,10}", der)]
            return (cand[0] if cand else None), f"der-candidates={cand[:3]}"
    except Exception as e:
        return None, f"ERR:{type(e).__name__}"


def interception_state(host, timeout=12):
    """(intercepted, evidence). The tell: foreign SNI still yields the HOST's cert."""
    ips = doh_resolve(host)
    if not ips:
        return False, {"why": "no DoH answer"}
    ip = ips[0]
    own, _ = tls_cert_cn(ip, host, timeout)
    foreign, detail = tls_cert_cn(ip, "example.com", timeout)
    if own is None:
        # TLS never completed -> INCONCLUSIVE. Do NOT report this as "ok".
        return False, {"ip": ip, "sni_own": None, "sni_foreign_gets": foreign,
                       "inconclusive": True, "detail": detail}
    leaked = bool(foreign) and not str(foreign).startswith("ERR") and (
        host.split(".")[-2] in str(foreign) or str(foreign) == own)
    if leaked and "example.com" not in str(foreign):
        return True, {"ip": ip, "sni_own": own, "sni_foreign_gets": foreign,
                      "evidence": "cert follows SNI, not IP -> transparent interception"}
    return False, {"ip": ip, "sni_own": own, "sni_foreign_gets": foreign}


def doh_reachable():
    try:
        req = urllib.request.Request(
            "https://cloudflare-dns.com/dns-query?name=example.com&type=A",
            headers={"accept": "application/dns-json", "user-agent": "net-check/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception:
        return False


# ──────────────────────────────── reporting ────────────────────────────────

def diagnose(hosts):
    out = {"dns_hijack": {}, "tcp_intercept": {}, "doh_endpoint_ok": None}
    for h in hosts:
        hj, sys_ips, real_ips = hijack_state(h)
        out["dns_hijack"][h] = {"hijacked": hj, "system": sys_ips, "real": real_ips}
    for h in hosts:
        if not out["dns_hijack"][h]["real"]:
            continue
        ic, ev = interception_state(h)
        out["tcp_intercept"][h] = {"intercepted": ic, **ev}
    out["doh_endpoint_ok"] = doh_reachable()
    return out


def report(d):
    hj = any(v["hijacked"] for v in d["dns_hijack"].values())
    ic = any(v.get("intercepted") for v in d["tcp_intercept"].values())

    print("=== LAYER 1: DNS hijack (wrong answer?) ===")
    for h, v in d["dns_hijack"].items():
        print(f"  {h:26s} sys={','.join(v['system']) or '-':16s} "
              f"real={','.join(v['real']) or '-':16s} {'HIJACKED' if v['hijacked'] else 'ok'}")

    print("\n=== LAYER 2: TCP interception (right answer, hijacked route?) ===")
    if not d["tcp_intercept"]:
        print("  (skipped -- no real IP resolved)")
    for h, v in d["tcp_intercept"].items():
        if v.get("intercepted"):
            print(f"  {h:26s} INTERCEPTED  ip={v.get('ip')}")
            print(f"     own-SNI cert    : {v.get('sni_own')}")
            print(f"     foreign-SNI cert: {v.get('sni_foreign_gets')}   <- follows SNI, not IP")
        elif v.get("inconclusive") or not v.get("sni_own"):
            print(f"  {h:26s} INCONCLUSIVE ip={v.get('ip')} (TLS failed: {v.get('sni_foreign_gets')})")
        else:
            print(f"  {h:26s} ok         ip={v.get('ip')} cert_own={v.get('sni_own')}")

    print(f"\n=== DoH endpoint (cloudflare-dns.com): "
          f"{'reachable' if d['doh_endpoint_ok'] else 'UNREACHABLE'} ===")

    print("\n=== VERDICT ===")
    if ic:
        print("  DNS HIJACK + TCP INTERCEPTION")
        print("  -> DoH / --resolve alone is NOT enough on this network.")
        print("  -> Use a browser path that pins the IP and validates the cert")
        print("     (Camoufox: network.trr.mode=3 + network.trr.uri=<DoH URL>).")
    elif hj:
        print("  DNS HIJACK only")
        print("  -> DoH + --host-resolver-rules (or curl --resolve) fully repairs it.")
    else:
        print("  clean -- no hijack, no interception")
    return hj, ic


def main():
    ap = argparse.ArgumentParser(description="2-layer network intercept diagnosis")
    ap.add_argument("hosts", nargs="*", help="hosts to check (default: search hosts)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()
    hosts = a.hosts or DEFAULT_HOSTS
    d = diagnose(hosts)
    if a.json:
        print(json.dumps(d, indent=1))
        hj = any(v["hijacked"] for v in d["dns_hijack"].values())
        ic = any(v.get("intercepted") for v in d["tcp_intercept"].values())
    else:
        hj, ic = report(d)
    sys.exit(2 if ic else (1 if hj else 0))


if __name__ == "__main__":
    main()
