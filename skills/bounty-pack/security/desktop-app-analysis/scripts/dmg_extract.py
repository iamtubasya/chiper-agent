#!/usr/bin/env python3
"""Extract a UDIF (.dmg) disk image to a raw file, on any OS with Python stdlib.

Parses the resource-fork plist, walks each blkx entry's mish chunk table, decompresses
zlib chunks and assembles a sector-addressed image. Raw and zero-fill chunks are handled;
LZFSE/bzip2/LZMA chunks are zero-filled and reported.

Usage:
    python dmg_extract.py <file.dmg> [out.img]

Notes:
  - mish header is 204 bytes; chunk entries are 40 bytes; terminator type is 0xffffffff.
  - The plist is located by searching for '<?xml' rather than parsing the koly trailer,
    whose field order is easy to get wrong.
  - Verify the result: an APFS image contains b'NXSB', an HFS+ image contains b'H+'.
"""
import base64
import plistlib
import struct
import sys
import zlib

MISH_HDR = 204
CHUNK = 40
TERMINATOR = 0xFFFFFFFF
ZLIB = 0x80000005
RAW_TYPES = (0x00000000, 0x00000002)
ZERO = 0x00000001
SECTOR = 512


def find_plist(d):
    i = d.find(b"<?xml")
    if i < 0:
        raise SystemExit("no XML plist found — not a UDIF dmg?")
    end = d.find(b"</plist>", i)
    if end < 0:
        raise SystemExit("plist not terminated")
    return plistlib.loads(d[i:end + 8])


def chunks_of(entry):
    """Yield (type, sectorNumber, sectorCount, offset, length) for one blkx entry."""
    raw = entry["Data"]
    if isinstance(raw, str):
        raw = base64.b64decode(raw + "=" * (-len(raw) % 4))
    if raw[:4] != b"mish":
        return
    off = MISH_HDR
    while off + CHUNK <= len(raw):
        ctype, _cmt, sn, sc, co, cl = struct.unpack(">IIQQQQ", raw[off:off + CHUNK])
        off += CHUNK
        if ctype == TERMINATOR:
            return
        yield ctype, sn, sc, co, cl


def extract(dmg_path, out_path):
    d = open(dmg_path, "rb").read()
    pl = find_plist(d)
    entries = pl.get("resource-fork", {}).get("blkx", [])
    if not entries:
        raise SystemExit("no blkx entries in the resource fork")

    parts = []
    max_sector = 0
    for e in entries:
        ch = list(chunks_of(e))
        if ch:
            parts.append(ch)
            for _t, sn, sc, _o, _l in ch:
                max_sector = max(max_sector, sn + sc)
    if not parts:
        raise SystemExit("no mish chunks found")

    img = bytearray(max_sector * SECTOR)
    stats = {}
    unsupported = 0
    for ch in parts:
        for ctype, sn, sc, co, cl in ch:
            stats[hex(ctype)] = stats.get(hex(ctype), 0) + 1
            try:
                if ctype in RAW_TYPES:
                    data = d[co:co + cl]
                elif ctype == ZERO:
                    data = b"\x00" * (sc * SECTOR)
                elif ctype == ZLIB:
                    data = zlib.decompress(d[co:co + cl])
                else:
                    unsupported += 1
                    data = b"\x00" * (sc * SECTOR)
            except Exception:
                unsupported += 1
                data = b"\x00" * (sc * SECTOR)
            if len(data) < sc * SECTOR:
                data += b"\x00" * (sc * SECTOR - len(data))
            img[sn * SECTOR:sn * SECTOR + sc * SECTOR] = data[:sc * SECTOR]

    open(out_path, "wb").write(img)
    print("entries      : %d" % len(parts))
    print("sectors      : %d (%d bytes)" % (max_sector, len(img)))
    print("chunk types  : %s" % stats)
    print("unsupported  : %d (zero-filled)" % unsupported)
    for sig, name in ((b"NXSB", "APFS"), (b"H+", "HFS+")):
        i = img.find(sig)
        if i >= 0:
            print("filesystem   : %s (magic at %d)" % (name, i))
    print("written      : %s" % out_path)
    if unsupported:
        print("NOTE: image has holes — unsupported chunk types were zero-filled.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src + ".img"
    extract(src, dst)
