# Synology DSM 7.x under QEMU (XPenology / ARC loader)

Stand up a real DSM instance locally so you can fuzz/RE it with zero authorization limits.
Synology's program pays the **highest tier for DSM** (RCE / auth bypass / path traversal /
priv-esc), not for `*.synology.com` web services — this is where the value is.

## Pieces

| Piece | Source / how |
|---|---|
| Loader | **ARC** (AuxXxilium/arc) — XPenology boot helper. `releases/latest` → `arc-<v>.img.zip` (~1 GB) |
| DSM image | Synology download centre, `.pat`. Public URL pattern: `https://global.download.synology.com/download/DSM/release/<ver>/<build>/DSM_<Model>_<build>.pat` |
| QEMU | `winget install --id SoftwareFreedomConservancy.QEMU -e` |

Working `.pat` (verified 200): `.../7.2.2/72806/DSM_DS3622xs+_72806.pat` (also DS920+, DS1621+,
RS4021xs+). Older builds (7.2.1/69057, 7.2/64570) returned 403.

## Build the disks

```bash
ConvertFrom-raw: qemu-img convert -f raw -O qcow2 arc.img arc.qcow2   # 3.9 GB raw -> ~1 GB sparse
qemu-img create -f qcow2 dsm-data.qcow2 24G                            # DSM install target (sparse)
rm -f arc.img arc-*.zip                                                # free the space
```

## First boot + configure

Boot headless with the NIC/ports you want (see SKILL.md launch line). ARC shows a text menu on
the VGA console and an **Arc Web Config on :7080**. Two ways to drive it:

**Screen route (what worked headless):** the menu is `dialog`. Scroll up (PageUp) — the top entry
`1 Choose Model` is often scrolled off the 80x25 console.

1. `1` **then** `Ret` → model list ("Reading Models...").
2. **Type the model name fast** (`DS3622xs+` = `ds3622xs+`/`shift-equal`) so the search buffer
   accumulates; verify the highlighted row, then `Ret`. Slow per-key sends land you on the wrong
   model (it grabbed `SA3600`, then `DS1019+`).
3. Pick DSM version (dialog shows e.g. `7.4 (90080)`).
4. Answer **Yes** to *"Do you want to use Automated Mode?"* → ARC auto-configures, builds
   (`Config: yes`, `Build:` runs "Patching DSM Image… → Ramdisk: apply 4.x/apollolake/7.x fixes →
   addons"), then `kexec`s into DSM (`Booting Arc DSM Mode → Loading arc Kernel → Booting DSM`).

**Web route (management, not build):** `http://127.0.0.1:7080` → "Arc Management" (Preact SPA,
`app.js`). Endpoints: `auth.cgi` (`action=login&username=root&password=arc`), `get-config.cgi`,
`get-sysinfo.cgi`, `start/stop-services.cgi`, `shutdown.cgi`. Default creds **root:arc**. This UI
does NOT trigger the build — it's post-build management.

**SSH route:** plan ahead and forward `22` (`-netdev user,hostfwd=tcp::2222-:22`). The ARC
buildroot is openSSH **root:arc**; drive it with `paramiko` (no sshpass on Windows):
`c.connect("127.0.0.1",2222,username="root",password="arc",look_for_keys=False,allow_agent=False)`.
Handy for `sed`/`grep` of `/opt/arc/arc-functions.sh` (the menu logic) without the screen.

## The blocker to expect: DSM `:5000` never serves

Observed: loader **builds and boots fine**, ARC sysinfo shows `Platform: apollolake`,
`Kernel: official (4.4.302)`, screen says *"Use http://10.0.2.15:5000 …"* — but the host-forwarded
`:5000` returns `000` (guest resets). ARC reports the NIC as **`virtio_net (Unknown)`** → the DSM
4.4.302 kernel has no working virtio-net, so DSM's services don't come up.

**Fix step 1 — emulated Intel NIC.** Present `-device e1000` instead of virtio for the DSM boot
(same `-netdev user`; DSM ships the e1000 driver natively). After the switch ARC correctly reports
**`e1000 (1000Mb/s): 10.0.2.15`** — so the NIC itself is fixed.

**⚠️ Necessary but NOT sufficient (verified this session).** Even with `e1000` recognized, DSM
`:5000` still returned `000` — i.e. the NIC was not the whole story, or not the story at all. Do
**not** conclude the job is done when the NIC reads `e1000`. Next moves, in order:

1. **Change the model.** `DS1019+` (apollolake) and `SA3600` are flaky in emulation. Rebuild the
   loader for **`DS3622xs+`** (broadwellnk) or **`DS920+`** (geminilake) — broadwellnk 4.x is the
   most reliable in QEMU.
2. **Change the DSM version.** The wizard defaulted to `7.4 (90080)`; a `7.2.2 (72806)` build is
   better-tested. Note `DS1019+` only offered apollolake.
3. **Read the DSM boot log** instead of guessing: add `console=ttyS0` to the loader cmdline and
   `-serial file:dsm-boot.log` to QEMU, then read why DSM stops after `Booting DSM Mode`.
4. Only after `:5000/webman/index.cgi` returns **200** is DSM actually up.

Budget realistically: getting the loader to build+boot is ~1 hour; making DSM itself serve is
further debugging, and finding a real DSM vuln afterwards is a **multi-day research project** —
say so rather than letting the operator assume one session is enough.

## Verify

```bash
curl -sS -m 8 -k -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5000/webman/index.cgi   # 200 = DSM up
```

Then install DSM (select model/pat in the XPenology/DSM install UI) and only THEN enumerate:
`aggresive local testing is fine here — nmap, fuzz, RE, debug — it is your VM.`

## Resume / artefacts

Everything lives under the lab dir (e.g. `~/dsm-lab`): `arc.qcow2`, `dsm-data.qcow2`,
`DSM_*.pat`, plus `*.png` screen dumps. Relaunch QEMU to resume; the loader boots from `arc.qcow2`.
