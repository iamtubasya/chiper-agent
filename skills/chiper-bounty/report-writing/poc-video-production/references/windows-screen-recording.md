# Route D — real window recording (Windows)

Record a *real* application window (Chrome + docked DevTools) with real mouse/keyboard input, for
video PoC segments where Playwright cannot see the evidence. Validated end to end 2026-10 building
the FlowCrypt `/health/` PoC video: 42 s gdigrab capture → 40 s segment → 177 s final MP4, every
recorded action cross-checked against DOM state.

## 1. Launch the browser in a recorded-friendly way

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" \
  --user-data-dir="C:\\...\\cprofile" \
  --remote-debugging-port=9333 --no-first-run --no-default-browser-check \
  --hide-crash-restore-bubble --disable-session-crashed-bubble \
  --auto-open-devtools-for-tabs --start-maximized "https://target.example/health/"
```

- **Fresh profile** = no extensions, no bookmarks, no signed-in account → nothing personal can leak
  into the frames (the script checklist always says "no personal data on screen").
- Not launched by Playwright ⇒ no "controlled by automated test software" banner.
- Targets: `curl http://127.0.0.1:9333/json` lists the page and the `devtools://` view. Attach to
  each with `websockets` and use `Runtime.evaluate` / `Input.dispatchKeyEvent` / `Page.reload`.

## 2. Find coordinates in the DOM, then VALIDATE with a self-checking click

DevTools is shadow-DOM all the way down, so pierce shadow roots:

```js
(() => { const out=[]; const walk=(el,d)=>{ if(!el||d>70||out.length>6) return;
  if(el.shadowRoot){ walk(el.shadowRoot,d); const k=el.shadowRoot.children; for(let i=0;i<k.length;i++) walk(k[i],d+1); }
  if(el.id==='tab-network'){ const r=el.getBoundingClientRect();
    if(r.width>0) out.push({x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}); }
  const k2=el.children; if(k2) for(let i=0;i<k2.length;i++) walk(k2[i],d+1); };
  walk(document.documentElement,0); return JSON.stringify(out[0]||null); })()
```

Mapping to screen: `screen_x = dom_x + client_left`, `screen_y = dom_y + <client top>`. On a maximized
1366×768 window the constant was **87 px** (tab strip + toolbar) — but treat it as a measurement, not
a fact: click a known element (Network tab at its computed screen point), re-query the DOM
(`tabbed-pane-header-tab … selected`), and only proceed when the state changed. That single check
catches both a wrong offset and a wrong z-order/focus situation, and the same queries become your
post-run proof that the recorded clicks landed.

Useful DevTools handles found this way: `#tab-network` / `#tab-elements` (tab strip), the "Clear
network log" button (`aria-label^="Clear network log"`, shortcut Ctrl+L), request rows as
`TD.name-column` inside the grid, the headers pane as the element with
`scrollHeight > clientHeight + 80 && clientHeight > 150`. Network log is cleared by a reload unless
"Preserve log" is ticked — leave it unticked so the refresh shows exactly one fresh row.

## 3. Drive real input with ctypes `SendInput`

Use `scripts/win32_input.py` (correct 40-byte `INPUT` union — a hand-rolled keyboard struct is
silently rejected, pitfall 14). Pattern per beat:

```python
to_foreground()          # SetForegroundWindow + settle
move(1117, 100)          # hover, so the recording shows the cursor travelling
click(1117, 100)         # click the Network tab
key(0x74)                # F5 on the page (click the page area first to focus it)
wheel(-120, x=1150, y=500)   # NOTE: negative delta = scroll DOWN; 1 tick of |120| ≈ 100 px here — measure it
```

Measure wheel px/tick at runtime (read `scrollTop`, tick 3×, read again) instead of assuming; DevTools
and the page scroll by different amounts.

## 4. Record

```bash
ffmpeg -y -loglevel error -f gdigrab -framerate 30 -draw_mouse 1 -i desktop -t 42 \
  -c:v libx264 -preset ultrafast -crf 16 -pix_fmt yuv420p seg_raw.mp4
```

One Python process: reset state (clear log, park the cursor, close DevTools if the script wants to
show it opening) → `Popen(ffmpeg)` → `sleep(1.0)` → timed timeline (`at(t)` helper computing the
remaining sleep) → `proc.wait()`. Keep every beat's coordinates recomputed from the DOM right before
the beat, so a layout change (DevTools reopening docked right vs bottom) cannot desync the run.

## 5. Fit the recording into the canvas

Screen is 1366×768; canvas is 1920×1080 with a caption band at the bottom. Crop the taskbar away,
fill the content box, stack the band:

```
[0:v]trim=0:40,setpts=PTS-STARTPTS,fps=30,
     scale=1920:970:force_original_aspect_ratio=increase,
     crop=1920:970:0:0,setsar=1[base];
[1:v]fps=30,setsar=1[bd];
[base][bd]vstack=inputs=2[v]
```

`-ss`-less `trim` + `setpts` keeps audio-less timing exact; `-r 30 -fps_mode cfr -t N` at the output
side normalises for concat. Crop anchored at the top keeps the tab strip and address bar (the part a
triager looks at); the bottom status bar is what gets cut.

## 6. Verify — pixels AND DOM

- Pixel side, adapted to your layout: caption strip (970..1080) must have ink in **every** sampled
  frame; terminal identified by its status chip in the title row; browser by a bright top 74 rows;
  browser segment's left/right 30 px must not be near-black (pillarbox). Expected transitions are
  **tag changes**, not per-segment starts — adjacent same-tag segments merge.
- DOM side, the stronger proof: after the run, read the state back (selected tab, `scrollTop` at
  max, selected row's aria label, the visible header names). In the validated session this read back
  `Request Headers (18)` rows `accept-encoding … user-agent` with no `authorization`/`cookie` — the
  exact claim the video makes.

## 7. Frame-diff sanity for the recorded segment

Sample ~16 frames across the raw recording, print frame-to-frame mean-absolute-difference per phase:
layout change (DevTools opening) ≈ 2, scroll bursts ≈ 2, holds ≈ 0.02. A phase table that lines up
with the scripted timeline proves the recording contains the intended beats even when you cannot
inspect pixels visually (no vision model on this box — pitfall 6).
