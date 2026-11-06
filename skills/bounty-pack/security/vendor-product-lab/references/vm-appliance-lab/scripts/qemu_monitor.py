#!/usr/bin/env python3
"""Headless QEMU control over the TCP monitor.

Launch the VM with:  -vnc 127.0.0.1:0 -monitor tcp:127.0.0.1:4444,server,nowait
Then:
    python qemu_monitor.py shot  screen      # screendump -> screen.png
    python qemu_monitor.py key   ret         # sendkey (also: 1 d s x shift-equal pgup up esc)
    python qemu_monitor.py raw   "info status"
    python qemu_monitor.py info
Requires: Pillow for PPM->PNG (pip install pillow). Falls back to leaving the .ppm.
"""
import socket, sys, time

MON = ("127.0.0.1", 4444)
OUT = "."  # set to your lab dir

def mon(cmd, wait=0.6):
    s = socket.create_connection(MON, timeout=10)
    time.sleep(0.3)
    try: s.recv(65536)            # banner
    except Exception: pass
    s.sendall((cmd + "\n").encode())
    time.sleep(wait)
    try: data = s.recv(65536).decode(errors="ignore")
    except Exception: data = ""
    s.close()
    return data

def shot(name="screen"):
    ppm = f"{OUT}/{name}.ppm"
    mon(f"screendump {ppm}", wait=1.2)
    try:
        from PIL import Image
        png = f"{OUT}/{name}.png"
        Image.open(ppm).convert("RGB").save(png)
        return png
    except Exception as e:
        return f"PPM->PNG failed ({e}); raw: {ppm}"

def key(k, times=1, delay=0.15):
    for _ in range(times):
        mon(f"sendkey {k}", wait=delay)

def type_text(s, delay=0.05):
    """Type a literal string; fast enough that dialog search buffers accumulate.
    Charted: letters/digits map to their own key; '+'->shift-equal, ' '->spc, '_'->shift-minus."""
    special = {"+": "shift-equal", " ": "spc", "_": "shift-minus", ".": "dot",
               "-": "minus", "/": "slash", ":": "shift-semicolon", "@": "shift-2"}
    for ch in s:
        k = special.get(ch, ch.lower() if ch.isalpha() else ch)
        mon(f"sendkey {k}", wait=delay)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "shot"
    if cmd == "shot":
        print(shot(sys.argv[2] if len(sys.argv) > 2 else "screen"))
    elif cmd == "key":
        key(sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
        print("sent", sys.argv[2])
    elif cmd == "type":
        type_text(sys.argv[2]); print("typed", sys.argv[2])
    elif cmd == "raw":
        print(mon(sys.argv[2]))
    elif cmd == "info":
        print(mon("info status"), mon("info vnc"))
