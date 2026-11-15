#!/usr/bin/env python3
"""Build a legacy Solana tx from a JSON spec and SIMULATE it (never submit).

  python simulate_solana_ix.py spec.json [--rpc URL]

spec.json:
{
  "rpc": "https://api.mainnet-beta.solana.com",
  "instructions": [
    {"kind": "ata_create_idempotent", "owner": "<b58>", "mint": "<b58>"},
    {"program": "<b58>", "accounts": [{"pubkey":"<b58>","is_signer":true,"is_writable":true}],
     "data_hex": "4eb74d6f..."}      # or "data_b64"
  ]
}

Rules learned the hard way (see references/solana-read-only-simulation.md):
  * message-level counts = shortvec; ANCHOR Vec lengths INSIDE data = u32 LE
  * account-creating ix MUST precede the ix that reads that account
  * key order: writable signers, writable non-signers, readonly signers, readonly non-signers
"""
import base64, json, sys, urllib.request

ATA = "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
TOKEN = "Tokenkeg" + "QfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SYSTEM = "11111111111111111111111111111111"


def shortvec(n):
    out = bytearray()
    while True:
        e = n & 0x7F
        n >>= 7
        if n == 0:
            out.append(e)
            return bytes(out)
        out.append(e | 0x80)


def rpc(url, method, params, timeout=45):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def expand(spec):
    import base58
    out = []
    for ix in spec["instructions"]:
        if ix.get("kind") == "ata_create_idempotent":
            from solders.pubkey import Pubkey
            owner, mint = ix["owner"], ix["mint"]
            ata, _ = Pubkey.find_program_address(
                [bytes(Pubkey.from_string(owner)), bytes(Pubkey.from_string(TOKEN)),
                 bytes(Pubkey.from_string(mint))], Pubkey.from_string(ATA))
            ata = str(ata)
            out.append({
                "program": ATA, "data_hex": "01", "_ata": ata,
                "accounts": [
                    {"pubkey": ix.get("payer", owner), "is_signer": True, "is_writable": True},
                    {"pubkey": ata, "is_signer": False, "is_writable": True},
                    {"pubkey": owner, "is_signer": False, "is_writable": False},
                    {"pubkey": mint, "is_signer": False, "is_writable": False},
                    {"pubkey": SYSTEM, "is_signer": False, "is_writable": False},
                    {"pubkey": TOKEN, "is_signer": False, "is_writable": False},
                ],
            })
        else:
            out.append(ix)
    return out


def build(spec):
    import base58
    ixs = expand(spec)
    flags = {}
    for ix in ixs:
        for a in ix["accounts"]:
            s, w = flags.get(a["pubkey"], [False, False])
            flags[a["pubkey"]] = [s or a.get("is_signer", False), w or a.get("is_writable", False)]
        flags.setdefault(ix["program"], [False, False])

    sw = [k for k, (s, w) in flags.items() if s and w]
    sr = [k for k, (s, w) in flags.items() if s and not w]
    ow = [k for k, (s, w) in flags.items() if not s and w]
    orr = [k for k, (s, w) in flags.items() if not s and not w]
    keys = sw + sr + ow + orr
    idx = {k: i for i, k in enumerate(keys)}
    header = bytes([len(sw) + len(sr), len(sr), len(orr)])

    body = bytearray()
    for ix in ixs:
        data = bytes.fromhex(ix["data_hex"]) if ix.get("data_hex") else base64.b64decode(ix["data_b64"])
        ai = [idx[a["pubkey"]] for a in ix["accounts"]]
        body += bytes([idx[ix["program"]]]) + shortvec(len(ai)) + bytes(ai)
        body += shortvec(len(data)) + data     # shortvec = message level only

    r = rpc(spec["rpc"], "getLatestBlockhash", [{"commitment": "confirmed"}])
    bh = base58.b58decode(r["result"]["value"]["blockhash"])
    msg = header + shortvec(len(keys)) + b"".join(base58.b58decode(k) for k in keys) + bh \
        + shortvec(len(ixs)) + bytes(body)
    nsig = len(sw) + len(sr)
    tx = bytes([nsig]) + b"\x00" * (64 * nsig) + msg
    return tx, {"nkeys": len(keys), "nix": len(ixs),
                "ata": next((ix["_ata"] for ix in ixs if ix.get("_ata")), None)}


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    if "--rpc" in sys.argv:
        spec["rpc"] = sys.argv[sys.argv.index("--rpc") + 1]
    spec.setdefault("rpc", "https://api.mainnet-beta.solana.com")

    tx, info = build(spec)
    print("built tx: %d bytes, %d keys, %d ixs%s" % (
        len(tx), info["nkeys"], info["nix"], ", ata=" + info["ata"] if info["ata"] else ""))

    res = rpc(spec["rpc"], "simulateTransaction",
              [base64.b64encode(tx).decode(),
               {"sigVerify": False, "replaceRecentBlockhash": True,
                "commitment": "processed", "encoding": "base64"}])
    val = res.get("result", {}).get("value", {})
    print("ERR:", val.get("err"))
    for line in val.get("logs") or []:
        print("  LOG:", line)
    if val.get("err") is None:
        print("VERDICT: program ACCEPTED the instruction (signature is the remaining gate)")


if __name__ == "__main__":
    main()
