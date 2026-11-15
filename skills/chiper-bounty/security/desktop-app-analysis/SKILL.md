---
name: desktop-app-analysis
description: "Use when a bug-bounty scope includes desktop clients (Windows MSI/EXE, macOS DMG/PKG) or their download/update channel. Covers signature verification, installer extraction, updater-key analysis, local-storage and shell-extension review, and the supply-chain classes programmes actually pay for."
metadata:
  hermes:
    tags: [security, bug-bounty, desktop, msi, dmg, windows, macos, tauri, electron, supply-chain, auto-update]
version: 1.0.0
---

# Desktop app analysis (MSI / DMG / installers)

Class-level playbook for the in-scope desktop clients of a web2 target and for the
download/update channel that feeds them. Distinct from `mobile-pentest` (APK/IPA) and
from `codebase-bounty-review` (source you can read): here the artefact is a signed
installer and the interesting classes are supply chain, local storage, and update
integrity.

## When to use

- The programme's scope table lists "Windows app", "macOS app", "desktop application".
- The target publishes installer download links (often a short-link service that 302s to
  an object-storage bucket).
- You need to decide whether a desktop finding is worth a report before spending time.

## Order of work (do not skip 1 and 2 — they close whole classes cheaply)

1. **Signature check first.** An unsigned or badly signed installer is the finding; a
   valid EV signature closes the class in one command. Windows:
   `Get-AuthenticodeSignature <file>` — read `Status`, `SignatureType`, `SignerCertificate`,
   `TimeStamperCertificate`. macOS: look for the Apple OCSP/CRL URLs in the binary and
   check the `LC_CODE_SIGNATURE` superblobs.
2. **Update channel.** Find the feed (appcast.xml, latest.yml, SUFeedURL) and the
   verification key. If the key is real and the downloaded file is verified, the whole
   "malicious update" class is closed. If the key is a stub, auto-updates are usually
   disabled — which is a hardening note, not a vuln.

   **Measure the feed against the artifact it claims to describe — divergence is the lead.**
   A Sparkle appcast is a signed manifest, so the interesting question is not "is it signed"
   but "does what it signs match what is actually served". Measured on a live Mac-app
   target (2026-10-26):

   ```bash
   # 1. inventory the feed
   curl -s https://<updates-host>/v3/appcast.xml -o appcast.xml
   grep -c '<enclosure' appcast.xml                 # 74
   grep -c 'sparkle:edSignature' appcast.xml        # 14  (Ed25519)
   grep -c 'sparkle:dsaSignature' appcast.xml       # 60  (legacy DSA)
   # unsigned enclosures = the real gap:
   grep '<enclosure' appcast.xml | grep -vc -e edSignature -e dsaSignature

   # 2. the artifact the vendor actually serves
   curl -sI https://<updates-host>/v3/<App>-latest.dmg   # 200, Last-Modified, Content-Length

   # 3. is it writable?
   curl -X PUT --data-binary '<rss/>' -H 'Content-Type: text/xml' \
        https://<updates-host>/v3/appcast.xml -o /dev/null -w '%{http_code}\n'   # 403
   ```

   On that target every enclosure was signed and the feed was read-only — both controls
   holding, both worth recording as verified negatives. But the **newest appcast item was
   dated 27 May 2021** while `latest.dmg` carried `Last-Modified: <today>` and a
   `Content-Length` (50,445,640) matching **no** enclosure in the feed (nearest declared
   length 27,483,136 — roughly half).

   What that proves and what it does not: a client trusting the appcast would never be
   offered the current build, and the artifact actually served has no signed manifest entry
   covering it. It does **not** prove an attacker can serve a malicious update. Two checks
   close it, in order:
   1. **Does the app consume this feed?** Grep the binary for the appcast URL and for
      `SUFeedURL` / Sparkle framework strings. If the app points elsewhere, a stale feed is
      hygiene, not a finding.
   2. **Does the update path verify?** If the app fetches `latest.dmg` (or any URL) and
      installs without checking `sparkle:edSignature` against the embedded public key, that
      is the supply-chain finding. If it verifies, the divergence is a maintenance bug.

   Until (2) is answered, ship it as `UNPROVEN-IMPACT` with the exact repro, the missing
   step, and the benign explanation — see the reporting bar in `authed-webapp-audit`.
   Note also the **signature-type mix** (legacy DSA alongside Ed25519): older enclosures
   signed only with DSA are the ones a modern Sparkle build may refuse, which is another
   reason the feed and the served artifact can drift apart without anyone noticing.

   ### 2b. There is often a SECOND feed — and the app points at the stale one

   Before concluding "the feed is stale", enumerate **every** appcast the vendor serves.
   Measured 2026-10-26 on the same target: a second feed existed on a different host,
   reachable with **no authentication at all**, and it was the live one.

   | | feed A (`SUFeedURL` in Info.plist) | feed B (found by grepping the binary) |
   |---|---|---|
   | host | `updates.<vendor>.com/v3/appcast.xml` | `api.<vendor>.cloud/v1/client/appcast` |
   | auth | none | **none — 200 unauth, also with `?access_token=` empty or invalid** |
   | items / enclosures | 30 / 74 | **78 / 78** |
   | newest | **3.7.1 — 2021-05-27** | **5.0.2 — 2026-10-26** |
   | signatures | 14 ed+dsa, 60 dsa-only | **78/78 `edSignature`** |
   | contains current build | **no** | yes, `length` byte-identical to `latest.dmg` |

   How feed B was found: the app binary's string heap contained
   `/v1/client/appcast?access_token=` and `/v1/client/{activate,check,check-for-updates,migrate,unlink}`
   — a **desktop-client API surface on a different host from the web app**. Grepping the binary
   for `/v1/` and for `appcast` is what surfaces it; probing only the `SUFeedURL` host does not.

   **The reportable observation is the mismatch, not the staleness.** `Info.plist` names feed A,
   feed A stops five years before the shipped build, and the live feed B is unauthenticated.
   Whether that is a security finding still depends on which feed the updater actually reads and
   whether it verifies — answer those before claiming anything, and record both feeds in the
   table either way.

   ### 2c. Sparkle Ed25519 verification — what "I could not verify" actually means

   Do not write "the feed signatures are invalid" from a failed local verification. Measured
   2026-10-26: **0 of 78** enclosures in the live feed and **0 of 10** in the stale one validated
   against the app's embedded `SUPublicEDKey`, across 12 message constructions:

   ```
   url\0length · url\0length\0 · url\0length\0version · url\0length\n · url\0length\r\n
   url length · url|length · url:length · url\0length (utf-16le) · url only
   url\0version\0length · length\0url
   ```
   plus raw SHA-256 of the artifact, hex SHA-256, and `url\0sha256hex`.

   Three things were checked **before** calling it unresolved, and all three are mandatory:
   1. **Verifier self-test.** Generate a fresh Ed25519 keypair, sign a known message, verify it.
      If the round-trip fails the bug is yours. (It passed — `pynacl`.)
   2. **Byte-exact attribute extraction.** Parse the `url` / `length` straight out of the raw
      enclosure attribute text rather than re-serialising them, so percent-encoding and
      whitespace cannot drift.
   3. **Key-uniqueness sweep.** Grep the whole `.app` bundle for base64 32-byte blobs
      (`[A-Za-z0-9+/]{43}=`) and confirm there is only one Ed25519-shaped key. On this target
      there was exactly one — the `SUPublicEDKey` in `Info.plist` — so it is **not** a
      key-rotation situation.

   With all three clear, the honest verdict is: *either Sparkle 2.9.6 uses a construction not
   reproduced here, or the feeds are signed with a different key.* That is an
   **unresolved observation**, not a finding. Closing it needs a known-good Sparkle-signed pair
   (generate a key, sign with the real algorithm, confirm the verifier reproduces Sparkle's
   result). Until then it is written up as `UNPROVEN-IMPACT` with the exact constructions tried
   and the self-test evidence — never as "signature verification fails".
3. **Where does the update URL come from?** If it is read from a file inside a per-user
   install directory, any process running as that user can repoint the updater. Combined
   with a signature check the effect is limited to serving vendor-signed content (forced
   downgrade) — report as hardening unless you can demonstrate the downgrade end-to-end.
4. **Identify the framework** before analysing: Tauri (wry / WebView2 strings) vs
   Electron (electron, nodeIntegration, asar) vs .NET (DotNetRuntimeDebugHeader export,
   WinRT type names). The analysis path differs completely.
5. **Secrets sweep** on the raw binary and on every extracted file.
6. **Local storage and IPC**: token files, wrapped master keys, local HTTP listeners,
   custom protocol handlers, shell extensions.
7. **Registration surface** from the installer's own tables (protocol, COM, services).

## Pitfalls that cost real time

- **`msiexec /a` needs elevation.** Plain invocation silently does nothing. Wrap it:
  `Start-Process msiexec -ArgumentList '/a','<msi>','/qn','TARGETDIR=<dir>' -Wait -Verb runAs`.
- **`cabarchive` cannot do LZX**, which is what MSI payload streams use. Use the
  administrative install above instead of carving CABs by hand.
- **Read MSI tables without installing** via the Windows Installer COM object
  (`OpenDatabase(path, 0)` then `OpenView("SELECT * FROM Registry")`) — this is how you
  get protocol-handler and COM registrations without touching the machine.
- **A DMG is not readable with `strings`.** The payload is zlib-compressed inside a UDIF
  chunk map. Use `scripts/dmg_extract.py` in this skill.
- **Not every DMG is zlib — check the magic before reaching for the extractor.** Modern
  Apple Disk Images are **LZFSE**-compressed and start with the bytes `bvxn` (`62 76 78 6e`),
  not a zlib header. Measured 2026-10-26: a 50 MB DMG whose `koly` trailer parsed to nonsense
  sector counts and whose body yielded **zero** inflatable zlib streams. `scripts/dmg_extract.py`
  (blkx + zlib) cannot open it.

  The reliable path on this host needs no new tooling — **WSL ships `7z`**, and 7-Zip 23.01
  reads UDIF directly, LZFSE included:

  ```bash
  wsl -e sh -c 'cd "$(wslpath "C:\path\to\dir")" && 7z l CleanShot-X-latest.dmg'
  # Type = Dmg · Method = Zero2 LZFSE CRC · Blocks = 83
  # Path = 4.apfs · Size = 145186816 · Comment = CleanShot X 5
  wsl -e sh -c 'cd "$(wslpath "C:\path\to\dir")" && 7z x -oext CleanShot-X-latest.dmg'
  ```

  Two things `7z l` gives you before you extract anything: the **archive `Comment` field**
  (here `CleanShot X 5` — the product major version) and the **APFS volume creation
  timestamp** (`Created = 2026-10-26 21:12:34`), which is how you date the build without
  mounting it. The `Method` column is also the LZFSE tell.

  If you must parse the trailer by hand, the fixed part is 76 bytes
  (`>4sIIIIQQQQIIQQ`) and the XML plist sits after it — but `rsrcForkOffset` and `sectors`
  come back as garbage on LZFSE images, so do not trust them; read the `blkx` table's
  `mish` blocks instead (`sig 'mish'`, then `>QQQ` at offsets 8/16/24 for
  startSector / sectorCount / dataOffset).
- **A 0-byte 200 on a storage node is a catch-all**, not an endpoint. Only trust paths
  that return a body; check `Content-Length` before calling something alive.
- **A wildcard certificate SAN is not a host list.** `*.roca.example.com` on a shared cert
  means those names resolve but do not serve. Test with a random label before believing
  an enumeration.
- **A signed appcast does not mean the update path is safe.** Signing every enclosure and
  refusing `PUT` closes two classes, but the feed can still be *stale relative to the
  artifact actually served* — a `latest.dmg` whose `Last-Modified` is today and whose size
  matches no enclosure is a supply-chain lead, not a closed class. Answer "does the app
  consume this feed" and "does it verify the signature" before calling it either way.
- **Reading a DMG's version from a byte range rarely works.** The payload is zlib-compressed
  inside a UDIF chunk map, so a `Range: bytes=0-2000000` fetch yields no printable version
  strings and no `CFBundleShortVersionString`. Use `scripts/dmg_extract.py` and read the
  extracted `Info.plist` instead of grepping the download.

## Reading a macOS code signature without `codesign` (Windows host)

`codesign -dv` needs macOS. On Windows the whole signature is readable from the binary with
`struct` — and it answers the question that matters (is this a real Developer ID signature or
an ad-hoc one) in about forty lines. Measured 2026-10-26 on a signed universal binary.

**Step 1 — is it a FAT (universal) binary?** `magic == 0xcafebabe` (or `0xcafebabf` for
64-bit fat) means yes, and the arch table follows at offset 8: 20 bytes per entry for
`FAT_MAGIC` (`>iiIII` = cputype, cpusubtype, offset, size, align), 32 for `FAT_MAGIC_64`.
Slice each architecture separately. `0xcffaedfe` read little-endian is a plain 64-bit Mach-O.

**Step 2 — walk the load commands** from `base + 32` (`>II` = cmd, cmdsize each) looking for
`0x1d` = `LC_CODE_SIGNATURE`. Its payload is `dataoff` + `datasize` (`>II` at `o+8`), giving
the superblob's file offset.

**Step 3 — parse the embedded signature superblob.** Magic `0xfade0cc0`, then
`>III` (magic, length, count) followed by `count` × `>II` (slot type, slot offset). The slot
map is the whole answer:

| slot | meaning |
|---|---|
| `0x0` | CodeDirectory |
| `0x2` | requirements |
| `0x5` | entitlements |
| `0x7` | DER entitlements |
| **`0x10000`** | **CMS blob — its presence is what makes it a real signature** |

**Step 4 — read the CodeDirectory** at slot `0x0`: `>II` magic+length, then
`>IIIIII` (version, flags, hashOffset, identOffset, nSpecialSlots, nCodeSlots). The
**identifier** is a NUL-terminated string at `identOffset` (e.g.
`pl.maketheweb.cleanshotx`), and `teamOffset` (a `>I` at cd[40:44], only for
version ≥ 0x20200) names the team — absent means ad-hoc.

**Step 5 — confirm the chain by grepping the CMS slot for certificate subjects.** Printable
strings inside slot `0x10000` yield the chain directly:
`Apple Root CA` → `Developer ID Certification Authority` → `Developer ID Application:
Make The Web O…` → `Apple Timestamp Certification Authority`. If those strings are present
and slot `0x10000` exists, the binary carries a genuine timestamped Developer ID signature.

**The distinction that matters:** `_CodeSignature/CodeResources` existing is *not* proof of
signing — it is just a plist of file hashes (`files`, `files2`, `rules`, `rules2` keys, no CMS).
A bundle can ship `CodeResources` and still be ad-hoc. The CMS slot is the test.

## Classes the programmes actually pay for (check each explicitly)

| Class | Where to look | Quick test |
|---|---|---|
| Insecure update / code signing | appcast + embedded key + install dir permissions | is the key real? is the URL user-writable? |
| Local data / credential leakage | token files, wrapped master keys, sync DBs | is the master key wrapped with a passphrase, DPAPI, or plaintext? |
| Keychain / secure-storage bypass | Keychain (SecItem), DPAPI, LocalAuthentication usage | does the app fall back to plaintext when no passphrase is set? |
| Improper certificate validation | TLS pinning code, bundled CA lists | grep for pinning / trust-anchor logic |
| Unprotected sensitive components | exported protocol handlers, shell extensions, local listeners | what does `hivenet://open?appUrl=` do with the argument? |
| RCE via deep link | custom scheme → WebView loadUrl / file open | is the URL validated against an allowlist? |

## Reporting honesty

Desktop analysis produces a lot of "control holds" — say so explicitly, because a
triager reads "I checked the signature and it is valid EV, timestamped" as evidence you
did the work. Equally, do not report a health endpoint that leaks RAM/CPU/version as a
finding unless the programme pays for info disclosure; record it as an observation with
the reason.

## Support files

- `references/msi-analysis-windows.md` — Authenticode, table reads, extraction, Tauri vs
  .NET identification, NetSparkle key extraction, per-user install traps.
- `references/dmg-analysis-on-windows.md` — UDIF/koly/blkx format, the extractor's
  assumptions, APFS assembly, entitlements and Keychain markers. **Note:** the extractor
  assumes zlib; modern LZFSE images need the WSL `7z` path described in the pitfalls above.
- `scripts/dmg_extract.py` — reusable DMG → raw disk image extractor (blkx + zlib).

**Overlap note:** `desktop-app-binary-analysis` covers substantially the same ground
(extraction, signing, updater key, local storage) with a stronger Windows/MSI emphasis and
its own extraction references. The two are complementary rather than duplicated — this skill
carries the update-channel and reporting discipline, that one the binary-walking detail — but
a future consolidation pass should merge them into one umbrella with per-platform references.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/desktop-app-binary-analysis/PLAYBOOK.md` — the zero-extra-tooling extraction route
  (MSI on Windows, DMG/UDIF in pure Python, tar.gz), code-signature and updater-integrity checks,
  where the update URL is read from, and local credential/key leakage. Read it when the installer
  must be unpacked on a machine without vendor tooling.
