# DMG analysis on Windows (no macOS tooling)

A `.dmg` is a UDIF disk image. `strings` on it shows almost nothing because the payload is
zlib-compressed inside a chunk map. This is the format, then the extractor.

## Layout

```
[ data fork: compressed chunks ...................... ]
[ XML plist (resource-fork) : blkx chunk map ....... ]
[ 512-byte "koly" trailer .......................... ]
```

- The **koly** trailer is the last 512 bytes and starts with the ASCII `koly`. Parsing it
  for `xmlOffset`/`xmlLen` is fiddly (field order is easy to get wrong) — it is faster to
  just `d.rfind(b"<?xml")` and read to `</plist>`.
- The plist has `resource-fork.blkx[]`, one entry per partition, each with a base64
  `Data` field holding a **mish** block.

## The mish block (empirically verified layout)

```
offset  size  field
0       4     signature 'mish'
4       4     version (1)
8       4     headerSize (often 0 — ignore it)
12      4     flags
16      8     runningDataForkOffset
24      8     dataForkOffset
32      8     dataForkLength
40      4     rsrcForkOffset
44      4     rsrcForkLength
48      4     segmentNumber
52      4     segmentCount
56      16    segment UUID
72      128   data checksum
200     4     chunksCount
204     ...   chunk table, 40 bytes per entry
```

**Header is 204 bytes.** Verify before trusting it: `(len(raw) - 204) % 40 == 0` and the
first chunk decoded at 204 should look like `(0x80000005, 0, 0, 1, 0, <small length>)`.
A terminator entry with type `0xffffffff` ends the table.

Chunk entry (40 bytes, big-endian):

```
type, comment, sectorNumber, sectorCount, offset, length
```

Chunk types seen in the wild:

| Type | Meaning |
|---|---|
| `0x00000000` / `0x00000002` | raw — copy bytes straight from the data fork |
| `0x00000001` | zero fill `sectorCount * 512` |
| `0x80000005` | zlib — `zlib.decompress(d[offset:offset+length])` |
| `0x80000007` | LZFSE — needs `liblzfse`; not available on a bare Windows Python |
| `0xffffffff` | terminator, stop |

## Assembling the image

Every blkx entry is sector-addressed, so build one buffer of
`max(sectorNumber + sectorCount) * 512` bytes and write each decompressed chunk at
`sectorNumber * 512`. Do not concatenate — the entries are not contiguous and the GPT
entries interleave with the data partition.

Expect one entry named `disk image (Apple_APFS : N)` with ~90 chunks; that is the payload.
The GPT/MBR entries are 1 chunk each and are noise.

## What to look for once you have the image

```
img.find(b"NXSB")      # APFS container superblock
img.find(b"H+")        # HFS+ (older images)
```

Then sweep the assembled image for strings — the payload is now uncompressed, so the
secrets sweep actually means something:

| Marker | Meaning |
|---|---|
| `com.apple.security.app-sandbox` | sandboxed (good) |
| `com.apple.security.network.client` | network entitlement |
| `get-task-allow` | **debug entitlement — a finding if present** |
| `SecItem`, `Keychain`, `LocalAuthentication`, `CC_SHA` | proper platform crypto |
| `SUFeedURL`, `edSignature`, `Sparkle`, `SUAllowedURLSchemes` | Sparkle updater with EdDSA and a scheme allowlist |
| `hivenet://<host>/path/callback` | custom-scheme OAuth redirect |

Bundle id and protocol registration live in the app's `Info.plist`, which is inside the
APFS volume — carving it out needs a full APFS reader, but the strings above are usually
enough to answer the security questions.

## Honest limits

- `LC_CODE_SIGNATURE` superblobs were **not** findable by a naive magic scan on the
  assembled image. The Apple OCSP/CRL URLs prove a signature exists; verifying its
  validity needs macOS tooling. Say exactly that, not "the app is signed".
- LZFSE chunks cannot be decompressed without an extra library. If the image has holes,
  say which chunk types were unsupported rather than presenting a partial image as whole.
