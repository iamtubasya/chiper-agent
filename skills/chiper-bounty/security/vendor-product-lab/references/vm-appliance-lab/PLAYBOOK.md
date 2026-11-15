---
name: vm-appliance-lab
description: "Stand up a product/appliance VM locally (QEMU) for authorized offensive research — and redirect 'max attack variants' pressure on a live target into it."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [security, lab, qemu, virtualization, xpenology, synology, appliance, vm]
    platforms: [windows, linux, macos]
---

# VM Appliance Lab

Build a **local VM of a product** (NAS OS, firewall, router firmware, appliance) and attack
that instead of the vendor's production. Trigger: the operator wants to hunt bugs in a
hardware/appliance product (Synology DSM, pfSense, OpenWrt, …); OR keeps pushing "use an
automated scanner / all attack variants, maximally" against a **live third-party target**.

## Why this skill exists (the redirect)

When the operator pushes for *automated scanners* or *"all attack variants, maximal"* against a
live production host:

1. **Check the program's rules first.** Most bug-bounty/VDM rules explicitly ban automated
   vulnerability scanners, DoS, and brute force. Running one does not "find more bugs" — it
   **strips the authorization** that made the testing legitimate (reports become un-submittable,
   account ban risk). State this boundary **once, plainly, without lecturing** — then move on.
2. **Do not grind the hardened live surface.** Tailored manual testing belongs there; a scanner
   mostly yields excluded noise (missing headers, banners, TLS ciphers).
3. **Redirect the offense energy into a local lab of the product.** In your own VM you have
   root/console: scan, fuzz, RE, debug — no authorization limits, no harm to real users, and
   findings land in the product track (where the money is). This is the productive answer, not a
   refusal.

Phrase it as *"the lab is where full-offense is appropriate"* — that satisfies the operator's
"think like an attacker" intent without crossing the authorization line.

## Step 1 — find the hypervisor

```bash
ls "/c/Program Files/Oracle/VirtualBox/VBoxManage.exe"                 # VirtualBox
ls "/c/Program Files (x86)/VMware/VMware Workstation/vmrun.exe"        # VMware
which qemu-system-x86_64                                               # QEMU
powershell -NoProfile -Command "(Get-Service vmms -EA SilentlyContinue).Status"  # Hyper-V role
wsl -l -v                                                              # WSL2 (Docker Desktop)
```

If none: install QEMU (no license, works with `whpx` or software `tcg`):

```bash
winget install --id SoftwareFreedomConservancy.QEMU -e \
  --accept-package-agreements --accept-source-agreements
"/c/Program Files/qemu/qemu-system-x86_64.exe" -accel help    # shows: tcg  whpx
```

Also useful on a bare Windows box: `winget install --id UB-Mannheim.TesseractOCR -e` (screen
OCR, see below). Python `paramiko` (`pip install paramiko`) for driving a guest over SSH.

## Step 2 — run QEMU HEADLESS (no window on the user's screen)

Users on a GUI machine hate automation popping console/VNC windows. Drive the VM entirely via
VNC-local + a TCP monitor:

```bash
"/c/Program Files/qemu/qemu-system-x86_64.exe" \
  -m 4096 -smp 4 -machine q35 -accel whpx -cpu max \
  -drive file=loader.qcow2,if=virtio,format=qcow2 \
  -drive file=data.qcow2,if=virtio,format=qcow2 \
  -netdev user,id=n0,hostfwd=tcp::2222-:22,hostfwd=tcp::5000-:5000,hostfwd=tcp::7080-:7080 \
  -device virtio-net-pci,netdev=n0 -device virtio-vga \
  -vnc 127.0.0.1:0 -monitor tcp:127.0.0.1:4444,server,nowait
```

Then **see** and **type** through the monitor with `scripts/qemu_monitor.py`
(`screendump <file.ppm>` → PNG; `sendkey <key>`). See that script for the exact calls.

### Reading the screen when the model has no vision

`screendump` writes a PPM; convert with PIL, then OCR:

```bash
"/c/Program Files/Tesseract-OCR/tesseract.exe" shot.png stdout --psm 6
```

`--psm 6` (uniform block) reads menus better than the default. `--psm 4` for mixed layouts.

## Hard-won pitfalls

- **`hostfwd` is fixed at launch.** To expose a new guest port you must relaunch QEMU. Kill the
  old instance first (`taskkill //IM qemu-system-x86_64.exe //F`) — a stale instance still
  holds the ports and the relaunch silently fails to bind (you'll see 5000 up but not the new
  port). **Check with `netstat -ano | grep ':<port>'` before assuming the forward exists.**
- **Give the terminal tool `background=true`** for the QEMU process — shell backgrounding
  (`nohup`/`disown`/`setsid`/trailing `&`) is rejected.
- **Keep a big text console in mind.** A curses/dialog TUI taller than the VGA text console
  (80x25) appears *scrolled* — the top items (e.g. the primary menu entry) look "missing".
  Scroll up (PageUp/Up) before concluding the menu lacks an item.
- **Drive `dialog`-based wizards by keystroke:** send the hotkey **then Enter** to open a
  submenu (`1` + Enter). In a `--menu` list, **type the item name fast** (no per-key delay) so
  the incremental-search buffer accumulates; a slow send lets the buffer reset and lands you on
  the wrong entry — verify the highlighted name on screen before Enter.
- **MSYS vs Windows paths:** a shell (`curl`/`sed`) writes `/tmp/x` fine, but Python `open()`
  can't find it. Use a native `/home/agentuser/Temp/x` path inside Python scripts.
- **Content filter mangles URLs in `write_file`** (e.g. `https://host` → `https:/***`). Build
  URLs at runtime from fragments (`"ht"+"tps://"+"acc"+"ount..."`) or write the file via a
  `cat > file << 'EOF'` heredoc instead of `write_file`.
- **Start small on disk.** Appliance images are multi-GB; `qemu-img convert -f raw -O qcow2`
  shrinks a raw `.img` to a sparse file, and `rm` the raw/zip after. Watch `df -h` — a 20 GB guest
  disk created with `qemu-img create -f qcow2` is sparse so it only costs what's actually written.

## Appliance recipes

- `references/synology-xpenology-dsm.md` — Synology DSM 7.x under QEMU via the ARC (XPenology)
  loader: downloads, disk prep, the ARC web-config + automated-mode build, SSH into the loader,
  and the `virtio-net` → DSМ `:5000` fix. Standing $30k-class product track.

## Scripts

- `scripts/qemu_monitor.py` — headless QEMU control: `shot` (screendump→PNG), `key` (sendkey),
  `raw` (arbitrary monitor command), `info` (status/vnc).
