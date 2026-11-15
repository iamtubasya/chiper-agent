# The ffmpeg video pipeline (concrete commands)

All segments are built at the same canvas: `1920x1080`, 30 fps, H.264, `yuv420p`. Uniformity is the
whole game — every pitfall below comes from a segment that drifted from the others.

## 1. Terminal / title / closing segments — PIL frames piped into ffmpeg

Render frames with Pillow (which gives exact control over monospace layout, highlighting and a typed
effect) and pipe raw RGB into ffmpeg. No temp PNGs, no `ImageMagick`.

```python
def frames_to_mp4(frames, path, W=1920, H=1080, FPS=30):
    ff = shutil.which("ffmpeg") or "ffmpeg"
    p = subprocess.Popen(
        [ff, "-y", "-loglevel", "error",
         "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(path)],
        stdin=subprocess.PIPE)
    for f in frames:
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait()
    return path
```

Typed effect = one frame per character of the command line; output lines appear instantly. Hold each
state for 6-8 frames so it does not strobe. Fonts on this Windows box:
`C:/Windows/Fonts/consola.ttf` (mono), `consolab.ttf` (mono bold), `segoeui.ttf`, `segoeuib.ttf`.

Keep a per-line colour and an optional "highlight row" index so the leak/response line gets a
background band — that is the thing the triager's eye lands on.

## 2. Browser segment — Playwright native recording, then composite the chrome back

```python
ctx = browser.new_context(
    viewport={"width": 1600, "height": 900},
    record_video_dir=str(VID_DIR),
    record_video_size={"width": 1600, "height": 900},
    locale="en-US",
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
)
page.on("framenavigated", lambda f: hops.append(f.url) if f is page.main_frame else None)
page.on("response", lambda r: hops.append(f"{r.status} {r.url}"))
page.goto(URL, wait_until="domcontentloaded"); page.wait_for_timeout(7000)
final_url = page.url()          # <- this is what the address bar must show
ctx.close()                     # <- video is flushed here; nothing after this is recorded
```

`viewport` is the recording size; the byte count is tiny for a mostly-static page. **No chrome is
recorded** — build the address bar yourself as a PNG and overlay it.

Address-bar PNG (PIL): `1920x74`, background `#21262D`, three window dots, a rounded pill `#0D1117`
with the real URL in `#C9D1D9`, then a right-aligned green label. Make TWO of them (the pre-redirect
URL and the post-redirect URL) if you want the bar to change mid-segment.

Composite graph — note the explicit colour canvas, and `increase`+`crop` instead of `pad`:

```python
bar_h, cap_h = 74, 150
vid_h = H - bar_h - cap_h                      # 856
fil = (
    f"color=c=0x0D1117:s={W}x{H}:d=1[bg];"
    f"[0:v]scale={W}:{vid_h}:force_original_aspect_ratio=increase,"
    f"crop={W}:{vid_h},setsar=1[base];"
    f"[bg][base]overlay=0:{bar_h}[v0];"
    f"[v0][1:v]overlay=0:0:enable='lt(t,7)'[v1];"      # bar A before the redirect
    f"[v1][2:v]overlay=0:0:enable='gte(t,7)'[v2];"     # bar B after
    f"[v2][3:v]overlay=0:{bar_h+vid_h}[v3];"           # caption strip at the bottom
    f"[v3]fps=30,format=yuv420p[vout]"
)
cmd = [ff, "-y", "-loglevel", "error", "-i", recording,
       "-loop", "1", "-i", bar_a_png, "-loop", "1", "-i", bar_b_png, "-loop", "1", "-i", caption_png,
       "-filter_complex", fil, "-map", "[vout]",
       "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
       "-r", "30", "-fps_mode", "cfr", "-t", "15", out]
```

`fps=30` inside the graph is mandatory — the Playwright source is not 30 fps, and an unconverted
segment silently loses time at concat.

## 3. Concat

Write a concat list and re-encode (do not stream-copy; you want the fps normalised end-to-end):

```bash
ffmpeg -y -f concat -safe 0 -i concat.txt \
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p \
  -r 30 -fps_mode cfr -movflags +faststart -an OUT.mp4
```

`-an` because there is no audio track, and `+faststart` so the portal can preview it.

## 4. Verify (do not skip)

```bash
ffprobe -v error -show_entries format=duration,size:stream=codec_name,width,height,r_frame_rate,pix_fmt,nb_frames \
        -of default=nw=1 OUT.mp4
```

Then run `scripts/verify_video_timeline.py` — the ffprobe block only proves the file is well-formed,
not that the right frames are in the right places. The pixel sampling is what proves that.

## 5. GIF variant (optional, for issue comments)

```bash
ffmpeg -y -i OUT.mp4 -vf "fps=12,scale=960:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 out.gif
```

Keep the MP4 as the primary deliverable — portals ask for video, and a GIF loses the captions.
