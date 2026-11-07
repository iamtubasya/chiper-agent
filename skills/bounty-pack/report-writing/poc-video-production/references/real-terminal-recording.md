# Real-terminal recording — mintty + gdigrab (Route E) working code

Session: 2026-10-16 FlowCrypt CAND-HEALTH-01 video PoC. Two terminal segments (`curl | head -50`,
`curl | python3 -m json.tool`) had to be recorded in a REAL terminal after the operator rejected
PIL-rendered terminal frames. Everything below is the code that actually produced the passing takes.

## 1. Launch mintty on an exact grid

mintty sizes itself from the font, so ask for a grid, then measure and re-derive:

```python
MINTTY = r"~/.chiper/git/usr/bin/mintty.exe"
BASH   = r"~/.chiper/git/usr/bin/bash.exe"
THEMES = r"~/.chiper/git/usr/share/mintty/themes"

# rcfile: keep PS1 bare so no username/hostname/host-path leaks into the frame
open(RCFILE, "w").write(
    'export PATH="/usr/bin:/mingw64/bin:$PATH"\n'
    'PS1="$ "\n'
    'unset PROMPT_COMMAND\n')

cmd = [MINTTY, "-s", f"{cols}x{rows}", "-p", "0,0",
       "-T", "bash — curl",
       "-o", "Font=Courier New", "-o", "FontHeight=16",
       "-o", f"ThemeFileDir={THEMES}", "-o", "ThemeFile=monokai-dimmed",
       "-o", "CursorType=block", "-o", "CursorBlinks=yes",
       "-o", "Transparency=off",
       "-e", BASH, "--rcfile", RCFILE, "-i"]
subprocess.Popen(cmd)
```

Two-pass sizing that worked on a 1366x768 desktop: launch at 100x30, divide the DWM bounds by the
grid to get the cell size (~13.2 x 24.1 px at FontHeight 16), then relaunch with cols/rows computed
for the target window height. Result: 102x28 -> 1347x678 visible bounds, aspect 1.987 vs the
1.979 target (1920x970 content box) — close enough that `increase`+`crop` trims <2%.

## 2. Capture bounds — DWM, not GetWindowRect

```python
dwmapi = ctypes.WinDLL("dwmapi")
DWMWA_EXTENDED_FRAME_BOUNDS = 9
def window_rect(hwnd):
    r = wt.RECT()
    dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS,
                                 ctypes.byref(r), ctypes.sizeof(r))
    return r   # left/top/right/bottom in *visible* pixels
```

`GetWindowRect` includes the invisible Win10 resize border; capturing that region records a strip of
desktop wallpaper on each side. Find the window by title (`FindWindowW(None, "bash — curl")`), call
`SetForegroundWindow` first so the take is not occluded.

## 3. Real keystrokes

`SendInput` with `KEYEVENTF_UNICODE` (0x0004), `wVk=0`, `wScan=ord(char)` — one event pair per
character, 75 ms +/- 35 ms jitter. Enter is `VK_RETURN` (0x0D) via the plain key helper. Prove the
pipe works before recording by typing a marker write and checking the file:

```python
type_text("echo typed-by-real-keystrokes > /c/.../marker.txt"); press_enter()
assert open(marker).read().strip() == "typed-by-real-keystrokes"
```

## 4. Scrolling — drag the scrollbar, never the wheel

mintty swallowed both `MOUSEEVENTF_WHEEL` and `Shift+PageUp` from `SendInput` (pitfall 19). The
scrollbar responds to real mouse input. Thumb position maps linearly over the buffer, so:

| intent | action (screen coords, scrollbar x = bounds.right - 5) |
|---|---|
| jump to top of output | drag `(sbx, 210)` -> `(sbx, 55)` |
| back to the newest lines | drag `(sbx, 210)` -> `(sbx, bounds.bottom - 10)` |

Do NOT click `y=40` or the bottom edge: those hit the arrow buttons, which scroll one line and
present as "the scroll did nothing". Drag = `SetCursorPos` + `LEFTDOWN` + 12 `SetCursorPos` steps
(40 ms apart) + `LEFTUP`; a plain click is just down+up.

## 5. Warm-up before the capture (this is what saved the take)

The first `python3` in a fresh shell stalled long enough under Defender that two takes recorded a
blank screen after Enter (pitfall 20). Before starting ffmpeg:

```python
type_text('python3 -c "pass" > /dev/null 2>&1'); press_enter(); time.sleep(2.0)
type_text("clear"); press_enter(); time.sleep(1.0)
```

Both commands run outside the recorded window, so they never appear in the video.

## 6. Capture command (even dimensions!)

```python
w -= w % 2; h -= h % 2      # libx264 rejects 1347x678 with "width not divisible by 2"
cmd = [FF, "-y", "-loglevel", "error", "-f", "gdigrab", "-framerate", "30",
       "-offset_x", str(x), "-offset_y", str(y), "-video_size", f"{w}x{h}",
       "-draw_mouse", "1", "-i", "desktop", "-t", "42",
       "-c:v", "libx264", "-preset", "ultrafast", "-crf", "15",
       "-pix_fmt", "yuv420p", out_raw]
subprocess.Popen(cmd, stdin=subprocess.PIPE)
```

Assert `nb_frames > 0` from ffprobe after the take (pitfall 21: the encoder failure left an empty
file while the timeline printed normally and exited 0).

## 7. Take timeline shape that filled 40 s honestly

One command + scroll + a second real command, all live:

```
type cmd1 (~4 s) -> enter -> hold 5 s (bottom of output)
-> drag to top -> hold 8 s (dns / hostnames / IPs — the money shot)
-> drag to bottom -> hold 5 s (server block)
-> click into text area -> type cmd2 (~6 s) -> enter -> hold 6 s
```

Two cmd2s used, both real and both on-message:
* `curl -s -o /dev/null -w 'HTTP %{http_code} in %{time_total}s\n' https://flowcrypt.com/health/`
  -> `HTTP 200 in 0.908614s` (proves the status line the report claims; `curl -s` alone hides it)
* `curl -sv https://flowcrypt.com/health/ -o /dev/null 2>&1 | grep '^>'` -> the four request lines
  `> GET /health/ HTTP/1.1`, `> Host:`, `> User-Agent:`, `> Accept:` with NO Authorization/Cookie —
  this is the "no auth gate" evidence in a real terminal

## 8. QA gate (loop until the take passes)

After every take, before compositing:

```python
QA = [(16.0, ["names", "de2-leader"]), (25.0, ["storeType"]), (40.0, ["HTTP 200"])]
```

Grab each timestamp with accurate seek, invert, OCR, assert. On failure, re-record (max 3 tries);
both takes passed on attempt 1 once the warm-up and scrollbar drag were in place. Post-composite,
re-run the same needles on the FINAL file with in-segment timestamps (not boundaries — pitfall 22).

## 9. Composition

```bash
ffmpeg -y -i seg_raw.mp4 -loop 1 -t 40 -i band.png -filter_complex \
 "[0:v]trim=0:40,setpts=PTS-STARTPTS,fps=30,\
scale=1920:970:force_original_aspect_ratio=increase,crop=1920:970:0:0,setsar=1[base];\
[1:v]fps=30,setsar=1[bd];[base][bd]vstack=inputs=2[v]" \
 -map "[v]" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -r 30 -fps_mode cfr \
 -t 40 -an sN_terminal.mp4
```

Keep the real window title bar in frame: it is part of the evidence that this is a real window, not
a render. The only synthetic layer is the caption band.
