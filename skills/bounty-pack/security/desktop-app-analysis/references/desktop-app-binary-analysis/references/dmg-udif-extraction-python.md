# Extracting a DMG (UDIF) in pure Python — no macOS, no 7-Zip

A `.dmg` is a UDIF disk image. On Windows with no `7z`/`dmg2img`, this recipe reconstructs the
partition image from the chunk map. Verified live on a 43 MB Hivenet installer.

## Structure
```
[ data fork: zlib/raw chunks ]  …  [ XML plist (resource-fork) ]  …  [ 512-byte 'koly' trailer ]
```
The file often *starts* with a zlib header (`78 da`) because the first chunk is compressed —
that is not the whole-file format. Do not try `zlib.decompress(whole_file)`; it yields 512 bytes
and 43 MB of `unused_data`.

## Step 1 — locate the XML plist

```python
import re, plistlib
d = open("HivenetInstaller.dmg","rb").read()
i = d.rfind(b"<?xml")                 # or: for m in re.finditer(rb"<\?xml", d)
end = d.find(b"</plist>", i)
pl = plistlib.loads(d[i:end+8])
blkx = pl["resource-fork"]["blkx"]    # list of partition/chunk entries
```

## Step 2 — parse each `blkx` entry (the `mish` block)

Each entry's `Data` is base64. The layout that works (verified empirically):

| offset | size | field |
|---|---|---|
| 0 | 4 | signature `mish` |
| 4 | 4 | version (1) |
| … | … | header fields, checksum (128 B) |
| **204** | — | **chunk table starts here** |
| 204 + n*40 | 40 | chunk: `type(u32) comment(u32) sectorNumber(u64) sectorCount(u64) offset(u64) length(u64)` |
| last | 40 | terminator, `type == 0xffffffff` |

```python
import struct, base64
HDR = 204
def chunks_of(e):
    s = e["Data"]
    raw = s if isinstance(s, bytes) else base64.b64decode(s + "=" * (-len(s) % 4))
    if raw[:4] != b"mish":
        return []
    out, off = [], HDR
    while off + 40 <= len(raw):
        ct, cmt, sn, sc, co, cl = struct.unpack(">IIQQQQ", raw[off:off+40])
        off += 40
        if ct == 0xffffffff:
            break
        out.append((ct, sn, sc, co, cl))
    return out
```

**How to confirm the header size empirically** (do this once per new DMG — do not trust 204
blindly): try candidate header sizes `h` where `(len(raw) - h) % 40 == 0`, decode chunk 0 for
each, and pick the `h` whose chunk 0 has a sane `type` (`0x80000005` zlib, `0x00000002` raw)
and a small `length`. A wrong `h` decodes to all-zeros or `0xffffffff`.

Chunk types: `0x00000000`/`0x00000002` raw, `0x00000001` zero-fill,
`0x80000005` zlib, `0x80000006` bzip2, `0x80000007` lzfse, `0x80000008` lzma.

## Step 3 — assemble the image

```python
img = bytearray(maxsec * 512)
for name, ch in parts:
    for ct, sn, sc, co, cl in ch:
        try:
            if ct in (0x00000000, 0x00000002): data = d[co:co+cl]
            elif ct == 0x00000001:             data = b"\x00" * (sc*512)
            elif ct == 0x80000005:             data = zlib.decompress(d[co:co+cl])
            else:                              data = b"\x00" * (sc*512)   # lzfse/lzma: note as unsupported
        except Exception:
            data = b"\x00" * (sc*512)
        if len(data) < sc*512:
            data += b"\x00" * (sc*512 - len(data))
        img[sn*512 : sn*512 + sc*512] = data[:sc*512]
open("dmg_full.img","wb").write(img)
```

Track `stats[hex(ct)]` and print it — if lzfse/lzma chunks dominate, say the payload was **not**
decompressed rather than claiming coverage.

## Step 4 — analyse the image
- `img.find(b"NXSB")` → APFS container; `img.find(b"H+")` → HFS+.
- Strings sweep (ASCII + UTF-16LE) over the whole image, then the pattern set in the
  `desktop-app-binary-analysis` SKILL.md (urls, secrets, updater, keychain, entitlements).
- Mach-O code signatures: search for the `LC_CODE_SIGNATURE` load command rather than a raw
  magic — a naive magic scan returns 0 even on signed binaries.
- macOS hardening markers worth recording: `com.apple.security.app-sandbox`,
  `com.apple.security.network.client`, `com.apple.security.application-groups`, absence of
  `get-task-allow`, plus `SecItem` / `LocalAuthentication` / `CommonCrypto` for secure storage.

## Pitfalls
- `plistlib.loads` needs the **complete** plist document — slice to `</plist>` inclusive.
- Base64 `Data` values from plist are `bytes` in Python 3.9+; handle both `bytes` and `str`.
- The `koly` trailer is 512 bytes and its field order is easy to get wrong; you rarely need it
  if you locate the plist with `rfind(b"<?xml")`.
