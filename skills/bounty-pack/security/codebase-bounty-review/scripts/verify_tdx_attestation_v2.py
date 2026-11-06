#!/usr/bin/env python3
"""Independent verifier for a GET /attestation/v2-shaped TEE endpoint.

Second implementation of the vendor's attestation verifier, written from the spec so that agreement
between the two is real evidence. Born from a Lit Chipotle (TDX + dstack) review; every check below
corresponds to a documented guarantee, not to the vendor's code.

Usage:
    python verify_tdx_attestation_v2.py [origin]           # fetch live and verify
    python verify_tdx_attestation_v2.py recorded.json      # verify a saved {"att","info","nonce"}

Deps: pycryptodome, cryptography, ecdsa. Edit POLICY + INTEL_SGX_ROOT_PUBKEY + PINNED_* for the target.

Exit 0 = every check passed. On failure it prints `FAIL <label>` and exits 1.
"""
import hashlib
import json
import re
import secrets
import sys
import urllib.request

import ecdsa
from Crypto.Hash import keccak as _keccak
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# ─── policy: EDIT PER TARGET ─────────────────────────────────────────────────────────────────────
POLICY = {
    "app_id": "<20-byte dstack app id, lowercase hex, no 0x>",
    "kms_contract": "0x<DstackKms address>",
    # pin the KMS roots: this is what stops a dishonest RPC substituting its own root
    "kms_k256": "<compressed secp256k1 root key hex>",
    "kms_ca": "<DER SPKI CA key hex>",
}
INTEL_SGX_ROOT_PUBKEY = "<uncompressed P-256 hex for Intel SGX Root CA>"

STATEMENT_DOMAIN = b"chipotle-attestation-v2:"   # change with the target's domain separator
KMS_ISSUED_PREFIX = b"dstack-kms-issued:"
DSTACK_EVENT = 0x08000001
SIGNER_PURPOSE = "chipotle-attestation-v2"


def check(cond, label):
    if not cond:
        print("FAIL  " + label)
        raise SystemExit(1)
    print("ok    " + label)


def keccak(b):
    h = _keccak.new(digest_bits=256)          # pycryptodome needs the size explicitly
    h.update(b)
    return h.digest()


def der(raw64):
    """cryptography wants DER; TDX/Intel quotes carry raw r||s. This is the #1 time sink."""
    return encode_dss_signature(int.from_bytes(raw64[:32], "big"), int.from_bytes(raw64[32:], "big"))


def le16(b, o):
    return b[o] | (b[o + 1] << 8)


def le32(b, o):
    return b[o] | (b[o + 1] << 8) | (b[o + 2] << 16) | (b[o + 3] << 24)


def recover_signer(sig_hex, digest):
    """secp256k1 recoverable signature -> compressed pubkey hex."""
    raw = bytes.fromhex(sig_hex)
    assert len(raw) == 65, "expected 65-byte r||s||v"
    v = raw[64] - 27 if raw[64] >= 27 else raw[64]
    cands = ecdsa.VerifyingKey.from_public_key_recovery_with_digest(
        raw[:64], digest, curve=ecdsa.SECP256k1, sigdecode=ecdsa.util.sigdecode_string
    )
    return cands[v].to_string("compressed").hex()


def verify_quote(quote_hex):
    b = bytes.fromhex(quote_hex[2:] if quote_hex.startswith("0x") else quote_hex)
    check(len(b) >= 640, "quote length >= 640")
    check(le16(b, 0) == 4, "quote version == 4")
    check(le16(b, 2) == 2, "quote tee type == 2 (ECDSA-P256)")
    check(le32(b, 4) == 0x81, "quote attestation-key type == 0x81 (TDX)")

    body = b[48:632]
    td_attr = body[120:128]
    check((td_attr[0] & 1) == 0, "TD is NOT in debug mode")

    signed_len = le32(b, 632)
    check(signed_len >= 134 and 636 + signed_len <= len(b), "quote signed-data length sane")
    s = b[636:636 + signed_len]
    signature = s[0:64]
    att_key = b"\x04" + s[64:128]

    check(le16(s, 128) == 6, "certification data type == 6 (PCK chain)")
    cert_data = s[134:134 + le32(s, 130)]
    check(len(cert_data) >= 450, "QE certification data >= 450B")
    qe_report = cert_data[0:384]
    qe_sig = cert_data[384:448]
    auth_len = le16(cert_data, 448)
    qe_auth = cert_data[450:450 + auth_len]
    inner = 450 + auth_len
    check(le16(cert_data, inner) == 5, "PCK chain is a PEM segment")
    pem = cert_data[inner + 6:inner + 6 + le32(cert_data, inner + 2)].decode()

    # 1. quote header+body signed by the attested key
    key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), att_key)
    try:
        key.verify(der(signature), b[0:632], ec.ECDSA(hashes.SHA256()))
        ok = True
    except Exception:
        ok = False
    check(ok, "quote signature valid (attested key, P-256/SHA-256)")

    # 2. QE report binds the attested key
    check(qe_report[320:352] == hashlib.sha256(s[64:128] + qe_auth).digest(),
          "QE report binds the attestation key")

    # 3. PCK chain to the pinned Intel root — each cert is signed by its PARENT
    certs, blob = [], pem.encode()
    while b"-----BEGIN CERTIFICATE-----" in blob:
        a = blob.index(b"-----BEGIN CERTIFICATE-----")
        z = blob.index(b"-----END CERTIFICATE-----") + len(b"-----END CERTIFICATE-----")
        certs.append(x509.load_pem_x509_certificate(blob[a:z]))
        blob = blob[z:]
    check(len(certs) == 3, "PCK chain has 3 certificates")
    leaf, ca, root = certs
    cn = lambda c: c.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    root_pub = root.public_key().public_bytes(Encoding.X962, PublicFormat.UncompressedPoint).hex()
    check(root_pub == INTEL_SGX_ROOT_PUBKEY.lower(), "chain ends at the pinned Intel SGX root key")
    check(cn(root) == "Intel SGX Root CA", "root CN correct")
    check(bool(re.match(r"^Intel SGX PCK (Platform|Processor) CA$", cn(ca))), "PCK CA CN correct")
    check(cn(leaf) == "Intel SGX PCK Certificate", "PCK leaf CN correct")

    for c in certs:
        root.public_key().verify(c.signature, c.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))
    check(True, "root self-signature valid")
    root.public_key().verify(ca.signature, ca.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))
    check(True, "PCK CA signed by root")
    ca.public_key().verify(leaf.signature, leaf.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))
    check(True, "PCK leaf signed by CA")
    leaf.public_key().verify(der(qe_sig), qe_report, ec.ECDSA(hashes.SHA256()))
    check(True, "QE report signed by PCK leaf")

    m = lambda o: body[o:o + 48].hex()
    return {
        "mrtd": m(136), "rtmr0": m(328), "rtmr1": m(376), "rtmr2": m(424), "rtmr3": m(472),
        "tee_tcb_svn": body[0:16].hex(), "report_data": body[520:584].hex(),
        "td_attributes": td_attr.hex(),
    }


def replay_event_log(event_log):
    entries = json.loads(event_log)
    check(isinstance(entries, list) and len(entries) <= 4096, "event log is a list <= 4096")
    rtmrs = [bytes(48) for _ in range(4)]
    events, seen = {}, set()
    for e in entries:
        imr, et = e.get("imr"), e.get("event_type")
        check(isinstance(imr, int) and 0 <= imr <= 3 and isinstance(et, int), "event entry shape")
        if et == DSTACK_EVENT:
            payload = bytes.fromhex(e.get("event_payload") or "")
            digest = hashlib.sha384(bytes([1, 0, 0, 8]) + b":" + e["event"].encode() + b":" + payload).digest()
            if e.get("digest"):
                check(digest.hex() == e["digest"], "event digest matches: " + e["event"])
            check(imr == 3, "dstack event lives in RTMR3")
            check(e["event"] not in seen or e.get("event_payload") == "", "no duplicate event")
            seen.add(e["event"])
            if e.get("event_payload"):
                events[e["event"]] = e["event_payload"]
        else:
            check(len(e.get("digest") or "") == 96, "raw event digest is 96 hex chars")
            digest = bytes.fromhex(e["digest"])
        rtmrs[imr] = hashlib.sha384(rtmrs[imr] + digest).digest()
    return [r.hex() for r in rtmrs], events


def pinned_images(app_compose):
    compose = json.loads(app_compose)["docker_compose_file"]
    images = [m.group(1) for m in re.finditer(r'^\s*image:\s*["\']?([^\s"\'#]+)', compose, re.M)]
    check(len(images) > 0, "compose declares at least one image")
    for i in images:
        check(bool(re.search(r"@sha256:[0-9a-f]{64}$", i)), "image digest-pinned: " + i[:56])
    return images


def fetch(origin):
    nonce = secrets.token_hex(32)

    def get(path):
        req = urllib.request.Request(origin + path, headers={"User-Agent": "att-verify/1.0"})
        with urllib.request.urlopen(req, timeout=30) as f:
            return json.loads(f.read())

    att = get("/attestation/v2?nonce=" + nonce)
    info = get("/info")
    json.dump({"att": att, "info": info, "nonce": nonce}, open("recorded_att_v2.json", "w"))
    return att, info, nonce


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg and arg.endswith(".json"):
        blob = json.load(open(arg))
        att, info, nonce = blob["att"], blob["info"], blob["nonce"]
    else:
        att, info, nonce = fetch(arg or "https://api.example.com")

    check(att.get("version") == 2, "response version == 2")
    check(att.get("nonce") == nonce, "response echoes this request's nonce")

    signer = att["signer"]
    check(signer.get("purpose") == SIGNER_PURPOSE, "signer purpose is pinned")
    signer_key = signer["public_key"]
    check(len(signer_key) == 66 and signer_key[:2] in ("02", "03"), "signer key is compressed secp256k1")

    quote_bytes = bytes.fromhex(att["quote"][2:] if att["quote"].startswith("0x") else att["quote"])
    q = verify_quote(att["quote"])

    # freshness: statement signature binds this nonce to this quote
    digest = keccak(STATEMENT_DOMAIN + bytes.fromhex(nonce) + keccak(quote_bytes))
    check(recover_signer(att["signature"], digest) == signer_key,
          "statement signature covers nonce+quote and recovers to the signer")

    rtmrs, events = replay_event_log(att["event_log"])
    for i in range(4):
        check(rtmrs[i] == q["rtmr%d" % i], "event log replays into quoted RTMR%d" % i)

    check(events.get("app-id") == POLICY["app_id"], "measured app-id matches policy")
    compose_hash, os_hash = events["compose-hash"], events["os-image-hash"]

    tcb = info["tcb_info"]
    if isinstance(tcb, str):
        tcb = json.loads(tcb)
    check(isinstance(tcb.get("app_compose"), str), "/info carries app_compose")
    check(hashlib.sha256(tcb["app_compose"].encode()).hexdigest() == compose_hash,
          "sha256(app_compose) == measured compose-hash")
    check(info["app_id"].replace("0x", "") == POLICY["app_id"], "/info app_id agrees")
    check(info["compose_hash"].replace("0x", "") == compose_hash, "/info compose_hash agrees")
    vm = json.loads(att["vm_config"]) if isinstance(att["vm_config"], str) else att["vm_config"]
    check((vm.get("os_image_hash") or "").replace("0x", "") == os_hash,
          "vm_config os_image_hash == measured os-image-hash")
    pinned_images(tcb["app_compose"])

    # KMS key-release chain: app key signs purpose:signer, KMS root signs app-key issuance
    app_key = recover_signer(signer["app_signature"],
                             keccak(("%s:%s" % (signer["purpose"], signer_key)).encode()))
    kms_signer = recover_signer(signer["kms_signature"],
                                keccak(KMS_ISSUED_PREFIX + bytes.fromhex(POLICY["app_id"])
                                       + bytes.fromhex(app_key)))
    check(kms_signer == POLICY["kms_k256"], "KMS chain ends at the PINNED root key")

    kp = json.loads(bytes.fromhex(events["key-provider"]).decode())
    check(kp.get("name") == "kms" and kp.get("id", "").replace("0x", "") == POLICY["kms_ca"].replace("0x", ""),
          "quote's key-provider == governed KMS CA key")

    print("\nALL CHECKS PASSED")
    print("mrtd:", q["mrtd"])
    print("report_data:", q["report_data"], "(all-zero is normal: freshness is in the statement)")


if __name__ == "__main__":
    main()
