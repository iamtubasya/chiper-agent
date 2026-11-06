# Video PoC production (when the triager/vendor asks for a video)

Some programs reply to a text+PDF report with *"please provide a video proof of concept"*. This is a
deliverable-production job, not a new hunt: you already have the finding, you need it **watchable**.
Verified end-to-end 2026-10 (Todoist OAuth DCR, 73 s / 800 KB MP4 accepted as the submission artifact).

## 0. Before you render a single frame: re-run the PoC

A recorded video is far more expensive to redo than a PDF. The written report may already be stale —
vendors redeploy, and a chain you described three days ago may not render the same page today.

In the Todoist case the report said `api.todoist.com/oauth/authorize` redirects the victim to the
login page. It returns the documented **302**, but the chain ends on `api.todoist.com/auth/login`,
which serves a **404** — the login SPA is only served from `app.todoist.com`. Re-running the identical
request on the *other host* produced the real login page. Discovering that at recording time is
exactly right; discovering it after the PDF shipped is not.

So: re-execute every step, capture verbatim, and only then decide what the video shows. If the
observed behaviour differs from the written report, tell the operator **before** producing the video —
they may still be able to correct the submission.

## 1. Pick the route from what the PoC actually is

| PoC shape | Route | Fidelity |
|---|---|---|
| Exploit can be re-run (web/API) | **Hybrid**: synthesized terminal segments for the HTTP steps + a real Playwright browser recording for the visible impact | highest |
| CLI / API only, no UI | Synthesized terminal segments from the **real captured transcripts** | high |
| Only a static PDF exists, nothing re-runnable | Render the PDF pages with slow zoom + captions | **weakest — this is a slideshow, not a PoC.** Say so and prefer building something re-runnable |

A triager asking for "video PoC" wants to watch the exploit happen. A slideshow of the report often
reads as an attempt to avoid re-running it.

## 2. Hybrid assembly (the shape that worked)

Build each segment as its own MP4, then concat. Uniform 1920x1080 / H.264 / yuv420p / 30 fps / no audio
== maximum portal compatibility.

```
00 title card          headline, target, endpoint, severity, researcher, date
01 step 1              real curl + real response body (highlighted status line)
02 control test A      e.g. empty body -> 400 validation, NOT 401 auth
03 step 2              the crafted request -> 302 with the real Location header
04 control test B      the negative control (what IS correctly enforced)
05 browser recording   real Playwright capture of the victim-visible effect
06 closing card        impact, plus an honesty note on what was NOT done
```

**Terminal segments come from captured transcripts, never from retyping.** Write the real response
body to a file during the probe, then have the renderer read that file. Any hand-transcribed output is
a fabricated-evidence risk (see the "Evidence Authenticity" section of the parent skill).

## 3. Browser recording — Playwright has no address bar

`record_video_dir` captures **the viewport only**. For an OAuth/redirect finding the entire point is
"the URL stays on the vendor's domain", and that evidence is invisible in a raw Playwright video.

Fix: composite the truth back in. Grab the real values from the run, then overlay:

```python
cap = {"start": START_URL, "final_url": None, "hops": []}
pg.on("framenavigated", lambda f: cap["hops"].append(f.url) if f is pg.main_frame else None)
pg.goto(START_URL, wait_until="domcontentloaded", timeout=60000)
pg.wait_for_timeout(7000)
cap["final_url"] = pg.url          # <-- the REAL final URL, for the address bar
```

Render two address-bar PNGs with PIL (start URL, then final URL) and overlay them with
`enable='lt(t,7)'` / `enable='gte(t,7)'`. PIL beats `drawtext` here — URLs are full of `?`, `&`, `%`,
`/` and `:` and ffmpeg's text escaping is a time sink.

**Verify the page actually rendered; do not assume.** A Google/user-agent string helps, and note the
SPA may be served from a different host than the API (hence §0). Dump `pg.inner_text("body")` and
assert it contains the expected copy before you build a video around it.

## 4. ffmpeg / PIL pitfalls that cost real time

- **ffmpeg 9 removed `-vsync`.** `Unrecognized option 'vsync'` → use **`-fps_mode cfr`**.
- **Mixed frame rates silently truncate segments on concat.** A 25 fps Playwright webm among 30 fps
  segments made the browser segment land as ~8 s instead of 15 s and stretched the closing card to
  ~20 s — total duration still looked right, so only a per-segment timeline probe caught it. Force
  `fps=30` inside the segment filter **and** `-r 30 -fps_mode cfr` on the concat.
- **`force_original_aspect_ratio=decrease` + `pad` pillarboxes.** A 16:9 source in a 2.24:1 strip left
  ~21 % of the frame as black bars. Use `scale=W:H:force_original_aspect_ratio=increase,crop=W:H`.
- **Never hold all frames in a list.** One 1920x1080 RGB frame is **6.2 MB**; a few hundred is
  gigabytes and dies with `MemoryError` on a small box. Make the renderer a **generator** and stream
  each frame straight into `ffmpeg` stdin:

  ```python
  p = subprocess.Popen([ff,"-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24",
      "-s",f"{W}x{H}","-r","30","-i","-","-c:v","libx264","-preset","medium",
      "-crf","20","-pix_fmt","yuv420p",str(out)], stdin=subprocess.PIPE)
  for f in frames:                      # `frames` is a generator, not a list
      p.stdin.write(f.tobytes())
  p.stdin.close(); p.wait()
  ```
- **Compute segment offsets from `ffprobe`, not from intent.** Derive each segment's real duration
  before mapping a timestamp to a segment, or your verification samples land in the wrong segment.
- `-t N` beyond the source length just holds the last frame; harmless but do not read meaning into it.

## 5. Verify the video without a vision model

Vision on rendered frames is unreliable (`vision_analyze` can return a generic apology instead of
reading the image). Use deterministic region statistics instead — sample frames and measure:

```python
a = np.asarray(Image.open(frame).convert("RGB")).astype(int)
band = a[935:1075]                                  # commentary band strip
bright_band = (band.sum(axis=2) > 330).mean()       # caption text present?
body_ink    = (a[60:925].sum(axis=2) > 120).mean()  # is the segment rendering at all?
left_bar    = (a[74:930, :120].max(axis=2) < 90).mean()   # letterbox detection
```

What this catches that eyeballing does not: a missing commentary band, a truncated segment, a
pillarboxed viewport, a blank page, and text that never finished typing (body ink should climb from
~0 % to its final value during a typed animation).

**Assert the text region is EXACTLY what you rendered.** Rebuild a card frame from the same source
strings, diff it against the extracted video frame, and compare bounding boxes plus text-row counts —
H.264 noise shows up as <0.1 % differing pixels, whereas one extra line (e.g. a stray contact address)
would move the bbox and the row count. That is how "the video contains no email address" was proven
rather than assumed.

## 6. On-screen commentary (operator preference — do it by default)

The operator asked for *"komentar di dalam video"*: a caption band on **every** segment, not just the
cards. Implement it as a fixed strip at the bottom of the frame (~150 px) carrying one plain-English
sentence per segment ("Step 1 — anyone can register an OAuth client. No API key, no login, no account
needed."), plus a small right-aligned badge for the punchline ("NO AUTH REQUIRED", "400 NOT 401").
English, like every other external artifact.

Keep commentary factual and matched to the frame — never describe a step the video does not show.

## 7. Naming and superseded artifacts

- The PDF and the video must share the **same basename** so the pair is obviously one deliverable
  (`<Program>-<Finding>-PoC.pdf` + `.mp4`).
- Park older versions in a `superseded/` subfolder the moment a new one exists. Left side by side, the
  operator submits the wrong file.
- See §8 of the parent SKILL.md on one-clean-version delivery.

## 8. Safety rails when the target is live and third-party

- **Do not complete the victim side.** Demonstrate up to the login/consent page and stop. A PoC that
  creates a real victim account to get the code is no longer a read-only demonstration.
- **Use reserved domains** for the attacker-side URI (`*.example.com`, `*.test`) so the recording never
  implies infrastructure that exists.
- **Minimise created state, then report it.** One test client for the video, not five. Record the
  identifier in the reply and in the report's "test artifacts to revoke".
- Never write a real issued secret into an artifact: store `len` + `sha256` + head/tail only, and show
  `"<43 characters, withheld>"` in the frames.
