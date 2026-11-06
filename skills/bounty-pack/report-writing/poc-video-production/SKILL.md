---
name: poc-video-production
description: Use when a vendor/triager asks for a video proof-of-concept for a vulnerability finding.
---

# Video PoC production (for vulnerability reports)

Trigger: a program or vendor says "we need a video PoC", or the operator hands you a finding /
PDF report and asks for a demonstration video.

## Rule 0 — re-run the exploit chain BEFORE you storyboard

**Do not plan the video from the written report.** The report may describe behaviour the live target
no longer has, and a video faithfully animating a stale claim is worse than no video.

Session case that created this rule: the report said the crafted OAuth authorize URL lands the victim
on the vendor's legitimate login page. Re-running it showed the chain from the `api.` host 302s into a
**404** — the SPA login is served on the `app.` host instead. A video built from the report would have
displayed a 404 and handed the triager a reason to reject the finding.

So: reproduce every reported step against the live target (or lab) first, capture the REAL output, and
only then decide what the video can honestly claim. If a step no longer behaves as documented, tell the
operator before building anything — that is a **report correction**, and finding it is the most
valuable thing you can do in this task.

## Route selection

| Situation | Route | Why |
|---|---|---|
| Exploit re-runnable in a browser or over an HTTP API | **A — hybrid: rendered terminal + Playwright** | highest fidelity; shows the real requests *and* the real page |
| CLI / API only | **B — rendered terminal from real transcripts** | no invented output, full control of pacing and highlighting |
| Only a static PDF exists | **C — page walkthrough with zoom/pan** | weakest. A triager asking for "video PoC" wants to see it happen. Say so before spending effort. |
| The proof needs real browser *chrome* — DevTools Network panel, extensions, a genuine address bar — or the page must be driven like a human would | **D — real window screen capture (Windows: `ffmpeg -f gdigrab` + ctypes `SendInput`)** | only route that records DevTools; also the escape hatch when Playwright video comes back blank (pitfall 11) |

Default to **A** for web findings: terminal segments carry the request/response proof, the browser
recording carries the visible impact.

**Operator rule (2026-10-29): the browser segment must be a REAL browser with the REAL address bar
visible — never a rendered mock-up.** The operator's words were "lewat browser asli, biar di acc":
triagers reject videos that look synthesised. Record the page with a real engine, composite the
address bar from the URL the browser actually reported (`page.url()`), and keep the bar truthful —
if the request 301'd to an internal host, the bar shows the URL that was requested and the page
shows the real failure, not a prettified success.

### Route D — real window recording (validated 2026-10, Windows)

Use it when the evidence lives in browser UI that Playwright cannot see (a docked DevTools panel is a
separate WebUI view — it never appears in `record_video`, even though it is visibly docked in the
window). Shape of the run:

1. Launch the browser with a **fresh profile** and remote debugging, e.g.
   `chrome.exe --user-data-dir=<tmp> --remote-debugging-port=9333 --no-first-run
   --auto-open-devtools-for-tabs --start-maximized <url>`, then talk to the `devtools://` target over
   a websocket (`websockets` + `Page`/`Runtime`/`Input` domains).
2. Read every coordinate you will click from **DOM rects** (`Runtime.evaluate` piercing shadow roots —
   DevTools is shadow-DOM all the way down), and map DOM→screen with a measured constant.
   **Validate the mapping with a self-checking click** (click a known tab, re-query the selected
   state) before the recorded run.
3. Drive the timeline with **real input** (`ctypes` `SendInput`: `SetCursorPos` + left-down/up, VK
   keys, mouse wheel) so the recording shows a real cursor doing real things. One Python process
   starts `ffmpeg -f gdigrab … -t N`, sleeps, then executes the timed clicks/keys.
4. Verify afterwards two ways: pixel stats on extracted frames **and** the DOM end-state (selected
   tab, `scrollTop`, selected request row) — the second is the ground truth that the recorded
   actions really landed.

Working recipe, code snippets and the verification pattern:
`references/windows-screen-recording.md`; reusable Win32 input helpers: `scripts/win32_input.py`.

### Route E — real TERMINAL recording (use this when a rendered terminal would be rejected)

A PIL-rendered terminal built from real transcripts is honest, but operators report that triagers
**reject videos whose terminal "looks rendered"** (2026-10-16: `buat pakai terminal asli, karna ini
nampak di render, bakal d tolak videonya`). So when a segment is a CLI demo, record an actual
terminal emulator with actual keystrokes:

1. **Terminal = mintty from Git for Windows** (`…\hermes\git\usr\bin\mintty.exe`, dark theme
   `-o ThemeFileDir=…/themes -o ThemeFile=monokai-dimmed`, `Font=Courier New`, `FontHeight=16`,
   `-s COLSxROWS` for an exact grid, `-T "<title>"`, and `-e bash --rcfile rc.sh -i` with
   `PS1='$ '` in the rcfile so no username/hostname leaks into the frame).
2. **Size the grid, not the pixels:** measure one launch (client ÷ cols/rows), then relaunch with
   `-s` computed for the target window size, and capture the window's *visible* bounds via
   `DwmGetWindowAttribute(DWMWA_EXTENDED_FRAME_BOUNDS)` (not `GetWindowRect`, which includes the
   invisible resize border).
3. **Drive it with real keystrokes**: `SendInput` `KEYEVENTF_UNICODE` per character with 75 ms ±
   jitter pacing, `VK_RETURN` for Enter. Prove it works before recording by typing
   `echo … > /tmp/marker` and checking the file exists.
4. **Scrolling: mintty ignores synthetic wheel events and Shift+PageUp.** Use the real scrollbar —
   **drag the thumb** with `SetCursorPos` + left-down + move steps + left-up (from y≈210 to y≈55 =
   top of the buffer; to y≈window_bottom-10 = back to the end). Clicking y≈40 / the bottom edge hits
   the scrollbar **arrows**, which scroll one line and look like "the scroll did nothing".
5. **Warm the interpreter before the capture starts** — the first `python3` run under Defender can
   stall long enough that the take records a blank screen: type `python3 -c "pass" > /dev/null 2>&1`
   + Enter, then `clear` + Enter, *then* start `ffmpeg`.
6. **QA-gate every take with OCR.** Extract the money-shot frames, invert them (light-on-dark text
   must be black-on-white for tesseract), OCR, and assert the disclosure strings are present
   (`names`, `storeType`, `GET /health/ HTTP/1.1`, …). Re-record on failure. This is what caught a
   take whose screen froze after Enter and one where the JSON never printed.

Composition matches Route D: crop the taskbar rows, `scale=1920:970:force_original_aspect_ratio=
increase,crop=1920:970:0:0`, `vstack` the caption band. Keep the real title bar in frame — it is
part of the evidence that this is a real window.

Working code (mintty launch line, DWM bounds, unicode typing, the scrollbar-drag table, the warm-up
sequence, the take timeline and the QA loop): `references/real-terminal-recording.md`. Money-shot
assertion: `scripts/ocr_frame_qa.py`.

## Segment order that works

1. **Title card** — finding title, target, endpoint, severity, researcher, date.
2. **The primitive**, as real HTTP: the unauthenticated request and its success response.
3. **"No auth gate" proof** — send a deliberately-invalid body and show the server answers with a
   *validation* error (400) rather than *unauthorized* (401). This demonstrates there is no auth check
   to fail, without creating extra state on the target.
4. **The control / negative case** that makes the finding precise (e.g. an unregistered redirect URI
   returns 400 while the registered one returns 302). This is what makes a triager trust the report.
5. **Browser recording** — the visible consequence, with a composited address bar.
6. **Closing card** — impact, plus an explicit statement of what was NOT done (no victim account used,
   no interaction).

Target 60-120 s. Triage attention is short.

## Hard rules for the artifact

- **MP4 / H.264 / `yuv420p` / `+faststart`.** That combination is what vendor portals accept.
- **English** captions and labels (external artifact) — including narration lines the operator wrote
  in their own language. Translate, do not copy: 2026-10-16 an Indonesian recording script produced
  an Indonesian-caption video and the correction was `always use English` (`kamu jgn pakai bahasa
  indonesia`). Command strings, endpoints and captured output stay verbatim; only the narration/
  label language changes.
- **Redact real secrets.** Render as `first8…[REDACTED, N chars]`; keep the full value's
  `len + sha256` in a side file for your own verification. Never put a live `client_secret` / token /
  key into a frame.
- **Never perform the destructive or impacting step.** Demonstrate the primitive and the mechanism,
  then state in the closing card that no victim interaction occurred. For a pre-auth RCE against live
  third-party production, build a local lab running the vulnerable version instead of firing the
  payload at them.
- **Minimise state created on live third-party services.** One registration, not five. Write every
  artifact ID you create into a file and tell the operator, so they can add it to the revocation list.
- **All on-screen text must come from real captured output.** Typed-looking terminal frames are fine;
  invented responses are not.
- **Deliver ONE version.** When the re-run forces a change and the submission has NOT happened yet,
  rebuild so the report and the video agree and ship that as the single version — no "correction",
  "v2", "corrected", "previously" or "superseded" framing anywhere, and do not leave the old build
  where it can be submitted by mistake (park it in `superseded/`). A correction section is only for a
  report that was *already* submitted. Name the video exactly as the report references it so the two
  are visibly a pair.
- **Prove the frames contain only your text.** Re-render the same card with PIL and diff it against the
  frame extracted from the finished MP4: H.264 noise is ~0.05 %, so a matching text bbox and an
  identical text-row count proves no extra line slipped in (this is how a wrong contact alias was
  cleared). Also grep the build scripts for anything that must not appear.

## Pitfalls (each one cost real time in the session)

1. **Playwright's video records the VIEWPORT ONLY — no address bar, no browser chrome.** If the whole
   point is "the URL stayed on the legitimate domain", you must composite the address bar back in
   (PIL-rendered PNG + `ffmpeg overlay`). Take the URL from `page.url()` / the redirect chain so the
   bar carries the truth.
2. **`ffmpeg` 9.x removed `-vsync`.** Use `-fps_mode cfr`. `Unrecognized option 'vsync'` means 9.x.
3. **Mixing frame rates in a concat silently truncates a segment.** A 25 fps Playwright recording
   concatenated with 30 fps segments collapsed from 15 s to ~8 s while the following card grew to
   absorb the difference — the total duration still looked correct, so nothing errored. Force
   `fps=30` inside every segment's filter chain AND pass `-r 30 -fps_mode cfr` at concat, then verify
   the timeline.
4. **Verify the finished file by sampling it, never by trusting the build log.** Extract frames at
   fixed timestamps and classify them by pixel composition (title bar present? address bar bright?
   caption strip populated?). That is what caught the truncated segment, a missing address bar, and
   pillarboxing. `scripts/verify_video_timeline.py` does exactly this.
5. **`force_original_aspect_ratio=decrease` + `pad` pillarboxes the page** — a 16:9 recording in a
   2.24:1 frame left 21 % dead bars. Use `increase` + `crop` to fill.
6. **Do not use an auxiliary vision model to QA the frames.** In this setup it could not see the image
   at all, and the reportlab skill records an unrelated case where it confidently described a
   different document. Use DOM text (`page.inner_text('body')`), `page.title()`, and pixel statistics.
   For *text content* — "is the disclosure string actually in this frame?" — the strongest check is
   **local tesseract OCR**: crop the content area, invert it (light-on-dark terminal text must become
   black-on-white), `tesseract frame_inv.png out --psm 6 -l eng`, then assert the needles;
   `scripts/ocr_frame_qa.py` does exactly this against a finished MP4, and it is what caught a frozen
   take and a command that never printed (Route E step 6). OCR garbles glyphs (`AttesterTs store`,
   `flowerypt.com`), so treat a fuzzy hit as present but a clean miss as a real miss.
7. **State your colour scale when bucketing.** A "suspiciously flat, mostly black" verdict was wrong:
   after integer division by 32 the bucket `(7,7,7)` is **white (224-255)**, not black. Print the
   actual light / dark / edge-density fractions instead of a verdict derived from a bucket label.
8. **`-t <seconds>` on a short input does not extend it.** With `-loop 1` stills it pads, but check the
   real source duration — a Playwright recording's length is the whole context lifetime, not just the
   part you wanted.
9. **`MemoryError` mid-render: never accumulate frames in a list.** A 1920x1080 RGB frame is ~6.2 MB,
   so a few hundred held frames exhaust a 6 GB box. Make the renderer a **generator** (`yield` one
   frame), write each into ffmpeg's stdin, then `del f`. The first build worked only because the
   machine happened to have RAM at the time; the rerun died with `MemoryError` at the same code.
10. **The operator asking for "comments in the video" means commentary on EVERY segment**, not just a
    closing card. Put a commentary band (dark strip + one bold sentence of plain English, optionally a
    status badge like `NO AUTH REQUIRED`) at the bottom of every segment, including the terminal ones.
    Verify with pixels that the band is populated in every sampled frame.

11. **Playwright `record_video` can produce a recording that goes blank after the first few
    seconds — and it looks like a successful build.** Verified 2026-10-13: a 21.8 s webm sampled at
    t=5 gave `std=69.8 / ink 90 %`, while t=10 and t=18 gave **`std` exactly `0.0`** — a completely
    flat frame. `ctx.close()` had been called correctly and the file was a well-formed 1.0 MB webm,
    so nothing in the build log hinted at it. **Discriminator:** extract 3-4 frames from the raw
    recording *before* compositing and print `np.std` for each. `std == 0.0` (exactly, not "low")
    means the frame is flat — discard the recording. **Fallback that works:** capture real
    `page.screenshot(path=..., full_page=False)` at each state instead, then build the browser
    segment from those stills with a slow PIL zoom (`crop` → `resize` → composite) so it still has
    motion. Screenshots were reliable in the same session where video was not, and they carry the
    same evidential value because the DOM facts (`page.title()`, `innerText.length`,
    `outerHTML.length`) are captured alongside them and quoted on screen.
12. **When the vulnerability IS an empty or broken render, the verifier's "content must have ink"
    check false-fails — and the failure is correct about the pixels, wrong about the finding.** A
    page returning `HTTP 500 / Content-Length: 0` renders as a pure-white blank document; measured
    `content_ink` was `0.00 %` and the segment was flagged FAIL four times. The blank region was
    real evidence, not a compositing bug. **Fix on the artifact:** do not ship a bare flat rectangle
    — overlay the measured DOM facts in a contrasting band (`Empty document rendered` /
    `HTTP 500 · Content-Length: 0` / `body text 0 chars · title ""`), which is both legible and still
    100 % derived from captured data. **Fix on the verifier:** exempt the intentionally-blank region
    from the ink floor and assert *separately* that the annotation is present (e.g. require
    `content_ink` > 0.5 % once an `annotate=True` flag is set for that phase), otherwise the check
    will keep failing on the very segment that carries the finding.

13. **Playwright cannot record DevTools — when the proof IS the DevTools Network panel, record the
    real window (Route D).** Docked DevTools is its own WebUI view; `record_video` captures the page
    surface only, so a "page + DevTools" setup produces a recording of the page and nothing else.
    Confirmed by DOM geometry (page 811×641 + DevTools 555 wide in the same window) versus a
    Playwright-era assumption that the whole window is recorded.
14. **`SendInput` needs `sizeof(INPUT) == 40` on x64 with a union body.** A hand-built keyboard
    struct (`type` + `KEYBDINPUT`, ~24 B) is rejected and `SendInput` returns 0 — the keypress
    silently never happens, which presents as "F5 didn't reload the page" and sends you debugging the
    target instead of the input. Mouse input built as `type + MOUSEINPUT` happens to be exactly 40 B,
    so clicks work while keys don't — that asymmetry is what makes it confusing. Always check the
    returned event count and raise. `scripts/win32_input.py` has the correct struct.
15. **`EnumWindows` callbacks must `return True` on every path.** Returning `None`/`False` at the
    first title-less window halts enumeration, and you get an empty window list that reads as "the
    window doesn't exist" (this cost a detour into phantom window theories).
16. **Measure the DOM→screen mapping, never assume it.** A docked DevTools document reports its own
    viewport coordinates, and `window.screenX/screenY` of a docked view are not the view's origin.
    Validate with a **self-checking click** — click a known element (Network tab), re-query the DOM
    (selected class, `scrollTop`, row selection) — and only then trust those coordinates for the
    recorded run. The same DOM queries double as post-run proof that the recorded actions landed.
17. **Screen resolution ≠ canvas.** This desktop is 1366×768 while the deliverable canvas is
    1920×1080: crop the gdigrab recording to the window's client area (drop the taskbar rows), then
    `scale=…:force_original_aspect_ratio=increase,crop=…` to fill the content box above the caption
    band. Anchor the crop at the top so the tab strip and address bar survive; the bottom status-bar
    rows are what get cut. Never `decrease` + `pad` (pitfall 5).
18. **The bundled verifier's region model is layout-specific, and expected boundaries must be tag
    CHANGES, not segment starts.** `scripts/verify_video_timeline.py` assumes BAR 0..74 / CAP
    930..1080 and a bright address bar, so a dark card layout mislabels every span (its own "browser"
    verdict fired on a title card's 6 px accent bar). Write a classifier matched to your layout —
    e.g. caption strip at 970..1080 must have ink, terminal identified by its status chip in the
    title row, browser by a bright top 74 rows — and compute expected transitions as *changes between
    consecutive segment tags**: two adjacent same-tag segments (terminal→terminal) merge into one span,
    and comparing that against per-segment start times reports a false MISMATCH.

19. **mintty ignores synthetic input that real terminals honour — verify input BEFORE you storyboard
    a scroll.** `MOUSEEVENTF_WHEEL` ticks and `Shift+PageUp` sent via `SendInput` did nothing at all
    in mintty, so a take recorded "scroll 10 notches" as a perfectly static screen. What works:
    clicking/dragging the real scrollbar (thumb position maps to the buffer, arrows scroll one line).
    Generalise it: prove every input primitive the storyboard depends on (wheel, hotkey, drag, unicode
    typing) against the actual window class in a throwaway take, before the recorded take exists —
    an input that silently no-ops costs a whole re-record, not one debug cycle.
20. **A "blank screen after Enter" was the interpreter, not the video pipeline — isolate the command
    in the same shell before blaming the recording.** `curl … | python3 -m json.tool` drew nothing
    until warmed; `python3 -m json.tool < file` worked instantly. Running the identical pipeline
    through `| wc -l` (a real number returned) proved the pipe was fine and the stall was startup
    cost. Cheap discriminator to keep in the take script: before recording, run
    `python3 -c "pass" > /dev/null 2>&1` + `clear`, and treat a take whose frames are byte-identical
    for seconds after Enter as a discarded take, not a mystery.
21. **`libx264` rejects odd capture sizes, and gdigrab hands you odd sizes.** A real window's DWM
    bounds came back `1347x678`; the encoder died with `width not divisible by 2` and wrote an empty
    file while the input timeline ran to completion — the script printed its whole timeline and
    exited 0. Always `w -= w % 2; h -= h % 2` on the `-video_size` you pass to gdigrab, and assert
    the output file's `nb_frames > 0` right after the take instead of trusting the exit code.
22. **`-ss` before `-i` is a fast seek and lies about segment boundaries.** Frame extraction with
    `-ss T -i file` on a freshly-concatenated MP4 returned the *neighbouring* segment's content at
    the boundary timestamps, which reads as "the money shot is missing". For final-artifact QA use
    the accurate form `-i file -ss T -frames:v 1`, and always sample *inside* a segment (e.g. 1.5 s
    before its end) rather than on the boundary frame.
23. **A long-running `gdigrab` capture is a corruption trap — always bound it with `-t <seconds>`
    so ffmpeg finalises the MP4 itself.** Verified 2026-10-26: a 13-minute open-ended capture was
    stopped with `kill -INT` / `kill -9` from the MSYS bash shell; neither signal reached the native
    Windows ffmpeg process, so the moov atom was never written and the 10.7 MB file was unreadable
    (`moov atom not found`) — and **it cannot be repaired afterwards** (`ffmpeg -i broken.mp4 -c copy`
    fails for the same reason, because the input cannot be opened at all). Two attempts were lost.
    The fix that works: **plan the duration up front and pass `-t N`**, letting ffmpeg exit on its
    own (a 300 s take produced a valid 4.6 MB H.264 file, verified with ffprobe). If you genuinely
    must stop early, terminate the native process properly —
    `MSYS_NO_PATHCONV=1 /c/Windows/System32/taskkill.exe /F /PID <pid>` (plain `taskkill //F`
    fails with `Invalid argument/option - '//F'` because MSYS mangles the switches) — but treat
    that as a last resort, not the plan. Also note `rm` on a file ffmpeg still holds open fails with
    `Device or resource busy`, which is how you discover a "killed" capture is still alive.
24. **`-t N` does not rescue a take whose input is odd-sized, and the exit code will not tell you.**
    Same session: `libx264` refused an odd `-video_size` and wrote an empty file while the input
    timeline ran to completion and the wrapper script printed its whole timeline and exited 0. Always
    `w -= w % 2; h -= h % 2` on the capture size and assert `nb_frames > 0` on the output right after
    the take. Related: pitfall 21.

## Environment this was built on

Present: `ffmpeg` 9.0 (WinGet), Python `playwright` with Chromium installed, `cv2`, `Pillow`,
`PyMuPDF`. Absent: `asciinema`, `agg`, `ImageMagick`, `gifski`. So render terminal frames with PIL and
pipe raw RGB into ffmpeg — do not plan a pipeline around asciinema.

Windows specifics (this box): desktop is 1366×768 (canvas is 1920×1080 — see pitfall 17), and there
is no GUI input driver (`hermes computer-use install` reports cua-driver is macOS-only), so real UI
interaction for Route D is driven with ctypes `SendInput` — `scripts/win32_input.py` plus the recipe
in `references/windows-screen-recording.md`.

## Engagement pitfalls (Social Deal, 2026-10-29)

Producing a 65 s browser PoC for an information-disclosure finding. Every item below cost a rebuild
and none is covered by the pitfalls above.

- **The evidence is usually below the fold.** A viewport screenshot of a JSON endpoint shows only the
  first screenful, so the field carrying the impact (an IBAN, a token, a secret) can be absent from
  the frame while the caption claims it. Before shooting, scroll the needle into view: walk text
  nodes with `createTreeWalker`, find the node containing the needle, call
  `scrollIntoView({block:'center'})`, wait, then shoot. Then OCR the frame and assert the needle is
  readable — that check is what catches it.
- **A centred zoom crops the evidence out.** Centring the crop means any zoom above ~1.2 pushes
  top-left-anchored content (JSON bodies, log lines) outside the frame; the segment then measures
  `content_ink 0.00 %` while looking structurally fine. Anchor the crop top-left (`x0, y0 = 0, 0`)
  whenever the needle sits at the top of the page, and keep the zoom gentle (1.0 → 1.10).
- **Sparse is not blank.** A 25-byte JSON response renders mostly white with `content_ink` around
  0.2 %. Do not "fix" that by zooming harder — OCR the frame and assert the needle string.
  `std == 0.0` exactly is the blank discriminator; low ink with readable text is a pass.
- **Gmail rejects attachments over 25 MB.** A 65 s 1080p24 PoC of static pages came out at 35.9 MB.
  Re-encode with `-preset slow -crf 26` (16 MB) and re-run the OCR check on the compressed file —
  text stayed fully legible at CRF 26. Do not go past CRF 28 without re-checking legibility.
- **PIL `ellipse()` takes a coordinate list, not four ints.** `d.ellipse(x0, y0, x1, y1, fill=c)`
  raises `TypeError: got multiple values for argument 'fill'`; use
  `d.ellipse([x0, y0, x1, y1], fill=c)`. `rounded_rectangle` already takes a list, which is why the
  two look inconsistent.
- **`/tmp` is not a path Python on Windows understands**, and `tesseract` is not on the Python
  subprocess PATH even when it is on the bash PATH. Write frames to a project-local `qa/` directory
  and invoke `C:/Program Files/Tesseract-OCR/tesseract.exe` by absolute path.
- **When browser automation will not launch, switch engine instead of retrying the same one.** A
  launch that times out twice (headed and headless) will not recover on a third attempt; Playwright's
  bundled Chromium produced a clean recording in the same session. Record the fallback that worked,
  not a claim that the first engine is broken.
- **Verify the finished MP4 by OCR, not by pixel ink alone.** `content_ink` says a frame has marks;
  only OCR says the marks are the disclosure string. Sample one frame per segment, invert
  light-on-dark frames only (a white browser page with dark text needs no inversion), and assert the
  needles.

## Supporting files

- `references/ffmpeg-video-pipeline.md` — concrete filter graphs and commands: segment encode from
  PIL frames, the address-bar overlay graph, fps-normalised concat, ffprobe checks.
- `references/windows-screen-recording.md` — Route D end to end: gdigrab capture of a real window,
  ctypes `SendInput` driving (with the 40-byte INPUT fix), CDP/shadow-root coordinate discovery and
  the self-checking click, taskbar-crop → canvas scaling, and layout-matched frame verification.
- `scripts/verify_video_timeline.py` — deterministic post-build verification: per-segment
  duration/fps table plus timestamped frame classification of the final MP4. Its region model is for
  its own layout (pitfall 18) — clone and adapt the classifier, do not reuse the constants blindly.
- `scripts/win32_input.py` — ctypes helpers for real UI input on Windows: `click`, `move`, `key`,
  `hotkey`, `wheel`, foreground/window-rect helpers, and a `__main__` sanity check of the INPUT
  struct size.
- `references/real-terminal-recording.md` — Route E end to end: the working mintty launch line and
  rcfile, DWM extended-frame bounds, unicode typing with a marker-file proof, the scrollbar-drag
  table (and why wheel/Shift+PageUp are useless), the Defender warm-up, an honest 40 s timeline, the
  even-dimension capture command, the take QA loop, and the composition filter.
- `scripts/ocr_frame_qa.py` — money-shot assertion for any recorded segment or final MP4: grab
  timestamps with accurate seek, invert dark frames, OCR with tesseract, assert the disclosure
  needles; exits non-zero on a clean miss. Use it to gate takes (Route E step 6) and to spot-check
  the finished artifact from inside each segment, never on a concat boundary.

## Absorbed playbooks (complete sub-packages under `references/`)
- `references/video-poc-production/PLAYBOOK.md` — the same class from a second engagement: the three
  routes (re-runnable exploit / CLI-API / static PDF), the capture-to-MP4 pipeline, and the
  verification step that catches truncated segments and letterboxed frames. Its
  `references/correcting-a-submitted-report.md` covers when the video and the shipped PDF disagree.
