# Working video-PoC pipeline (verified 2026-10, ffmpeg 9.0, Windows + git-bash)

Everything below ran end-to-end. Adapt the paths and the capture files; keep the structure.

## 0. Layout

```
<poc-dir>/
  raw/            curl transcripts, headers, response bodies  (the source of truth)
  build/          intermediate segment mp4s
  verify/         extracted check frames
  final.mp4
```

Rule: the renderer reads ONLY from `raw/`. Never hand-transcribe a response into the video.

## 1. Capture (the source of truth)

```python
import subprocess, os, json
from pathlib import Path

def curl(args, timeout=45):
    env = dict(os.environ); env["MSYS_NO_PATHCONV"] = "1"   # MSYS bash mangles leading '/'
    return subprocess.run(["curl","-s","-m",str(timeout)]+args,
                          capture_output=True, text=True, env=env).stdout

# headers + body, saved so the renderer can quote them verbatim
hdr  = curl(["-D","-","-o","/dev/null","-X","POST",URL,"-H","Content-Type: application/json","-d",body])
resp = curl(["-X","POST",URL,"-H","Content-Type: application/json","-d",body])
Path("raw/step1.headers.txt").write_text(hdr, encoding="utf-8")
Path("raw/step1.body.json").write_text(resp, encoding="utf-8")

# redact the live credential but keep a checkable fingerprint
import hashlib
sec = json.loads(resp).get("client_secret","")
Path("raw/secret_meta.txt").write_text(
    f"len={len(sec)} sha256={hashlib.sha256(sec.encode()).hexdigest()[:16]}", encoding="utf-8")
```

## 2. Frame renderer — one frame at a time (never a list)

```python
from PIL import Image, ImageDraw, ImageFont
W, H, FPS = 1920, 1080, 30
MONO = "C:/Windows/Fonts/consola.ttf"
SANS, SANSB = "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"
BG=(13,17,23); BAR=(33,38,45); TXT=(201,209,217); DIM=(139,148,158)
GREEN=(63,185,80); RED=(248,81,73); BLUE=(88,166,255); WHITE=(240,246,252); HILITE=(48,40,10)
CAPPY = 930          # commentary band occupies 930..1080

def frame(title, lines, hi, cap, badge=None):
    if hi is None: hi = ()
    elif isinstance(hi, int): hi = (hi,) if hi >= 0 else ()   # <- easy bug: int passed as index
    else: hi = tuple(hi)
    img = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,54], fill=BAR)                          # terminal title bar
    for i,c in enumerate([(255,95,86),(255,189,46),(39,201,63)]):
        d.ellipse([24+i*30,19,44+i*30,39], fill=c)
    d.text((140,17), title, font=ImageFont.truetype(SANS,20), fill=DIM)
    y = 88
    for i,(t,c) in enumerate(lines):
        if i in hi: d.rectangle([40,y-4,W-40,y+27], fill=HILITE)   # highlight the key line
        d.text((60,y), t, font=ImageFont.truetype(MONO,21), fill=c); y += 31
    d.rectangle([0,CAPPY,W,H], fill=(9,12,17)); d.rectangle([0,CAPPY,W,CAPPY+3], fill=(48,54,61))
    d.text((60,CAPPY+26), cap, font=ImageFont.truetype(SANSB,29), fill=WHITE)
    if badge:
        bb = d.textbbox((0,0), badge, font=ImageFont.truetype(SANSB,22))
        bw = bb[2]-bb[0]+34
        d.rounded_rectangle([W-bw-60, CAPPY+22, W-60, CAPPY+64], radius=8, fill=(23,54,35))
        d.text((W-bw-43, CAPPY+30), badge, font=ImageFont.truetype(SANSB,22), fill=GREEN)
    return img

def render(seg):
    """GENERATOR. Holding frames in a list = MemoryError at 1920x1080."""
    cur = []
    for _ in range(int(seg.get("pre",1.2)*FPS)): yield frame(seg["title"],cur,(),seg["caption"],seg.get("badge"))
    for txt,col,hi,typed in seg["script"]:
        if typed:                                  # typewriter effect
            for k in range(1,len(txt)+1):
                yield frame(seg["title"],cur+[(txt[:k],col)],hi,seg["caption"],seg.get("badge"))
            cur = cur+[(txt,col)]
            for _ in range(7): yield frame(seg["title"],cur,hi,seg["caption"],seg.get("badge"))
        else:
            for l in wrap(txt,108):
                cur.append((l,col))
                for _ in range(3): yield frame(seg["title"],cur,hi,seg["caption"],seg.get("badge"))
            for _ in range(9): yield frame(seg["title"],cur,hi,seg["caption"],seg.get("badge"))
    for _ in range(int(seg.get("post",2.0)*FPS)): yield frame(seg["title"],cur,(),seg["caption"],seg.get("badge"))
```

## 3. Frames → mp4 (streamed into ffmpeg)

```python
import subprocess, shutil
def to_mp4(frames, path):
    ff = shutil.which("ffmpeg") or "ffmpeg"
    p = subprocess.Popen([ff,"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
        "-s",f"{W}x{H}","-r",str(FPS),"-i","-","-c:v","libx264","-preset","medium","-crf","20",
        "-pix_fmt","yuv420p","-r","30","-fps_mode","cfr",str(path)], stdin=subprocess.PIPE)
    n = 0
    for f in frames:
        p.stdin.write(f.tobytes()); n += 1; del f     # one frame resident at a time
    p.stdin.close(); p.wait()
    return path, n
```

`-fps_mode cfr` replaces `-vsync cfr`, which ffmpeg 9.x removed.

## 4. Browser recording (Playwright)

```python
from playwright.sync_api import sync_playwright
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")   # headless UA gets bot-blocked on some hosts

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width":1600,"height":900},
                        record_video_dir="raw_video",
                        record_video_size={"width":1600,"height":900},
                        locale="en-US", user_agent=UA)
    pg = ctx.new_page()
    hops = []
    pg.on("framenavigated", lambda f: hops.append(f.url) if f is pg.main_frame else None)
    pg.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(7000)                      # let the SPA hydrate before judging the page
    final_url, title = pg.url, pg.title()
    body = pg.inner_text("body")                   # <-- the truth about what RENDERED
    ctx.close(); b.close()                         # video is only flushed on ctx.close()
```

**The recording has no address bar.** Composite the real URL back in (next step).

## 5. Composite the browser segment (canvas first, then overlays)

Overlay coordinates are relative to the *current* chain, so build an explicit canvas:

```python
bar_h, cap_h = 74, 150
vid_h = H - bar_h - cap_h

fil = (
    f"color=c=0x0D1117:s={W}x{H}:d=1[bg];"
    f"[0:v]scale={W}:{vid_h}:force_original_aspect_ratio=increase,"      # increase+crop = fill
    f"crop={W}:{vid_h},setsar=1[base];"                                  # decrease+pad = letterbox
    f"[bg][base]overlay=0:{bar_h}[v0];"
    f"[v0][1:v]overlay=0:0:enable='lt(t,7)'[v1];"      # address bar, phase 1 (before redirect)
    f"[v1][2:v]overlay=0:0:enable='gte(t,7)'[v2];"     # address bar, phase 2 (after redirect)
    f"[v2][3:v]overlay=0:{bar_h+vid_h}[v3];"           # commentary band at the bottom
    f"[v3]fps=30,format=yuv420p[vout]"
)
subprocess.run([ff,"-y","-loglevel","error","-i",webm,
    "-loop","1","-i","bar_a.png","-loop","1","-i","bar_b.png","-loop","1","-i","cap.png",
    "-filter_complex",fil,"-map","[vout]","-c:v","libx264","-crf","20","-pix_fmt","yuv420p",
    "-r","30","-fps_mode","cfr","-t","15",OUT])
```

Render the bar/caption PNGs with PIL rather than ffmpeg `drawtext` — URLs contain `?`, `&`, `%`, `:`
and drawtext escaping is a time sink.

## 6. Concat

```python
lst = "build/concat.txt"
lst.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8")
subprocess.run([ff,"-y","-loglevel","error","-f","concat","-safe","0","-i",lst,
    "-c:v","libx264","-crf","20","-pix_fmt","yuv420p",
    "-r","30","-fps_mode","cfr","-movflags","+faststart","-an",FINAL])
```

Normalise `-r 30 -fps_mode cfr` here even if every part is already 30 fps. A single 25 fps part
silently reshuffles segment durations.

## 7. VERIFY (mandatory)

```python
for t in np.arange(0.5, total, 1.0):
    extract_frame(t, "verify/s.png")
    a = np.asarray(Image.open("verify/s.png").convert("RGB")).astype(int)
    band = a[935:1075]; body = a[60:925]
    caption_ink = (band.sum(axis=2) > 330).mean()     # commentary band present
    body_ink    = (body.sum(axis=2) > 120).mean()
    left  = (body[:, :120].max(axis=2) < 90).mean()   # pillarbox detector
    right = (body[:, -120:].max(axis=2) < 90).mean()
```

Signals that mean something is wrong:

| Reading | Meaning |
|---|---|
| a segment has no caption ink | band missing / wrong overlay order |
| `body_ink` stays flat at ~0% | typing animation not advancing, or blank frame |
| left/right strip dark >5% | pillarbox from `decrease + pad` |
| segment duration ≠ its build duration | fps mismatch in concat |

Also confirm the browser segment really rendered the page, not a 404: check `page.title()` /
`inner_text` at capture time, and look for a small brand-colour blob in the composite.

Do **not** rely on the vision tool for this — it may be unavailable, and rendering QA by sampling is
deterministic and cheaper.
