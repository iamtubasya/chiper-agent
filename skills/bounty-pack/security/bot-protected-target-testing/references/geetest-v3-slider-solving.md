# Geetest v3 — decorative-captcha check, slider solve, and the handoff fallback

Worked case: **Blink (`consent.blink.sv/www.blink.sv`, Galoy-derived Lightning wallet), 2026-10-12.**
Registration/log-in on the consent app is phone-only and Geetest-gated; the whole test-account
provisioning step hinged on getting past it. Numbers below are from that run.

---

## 0. First question: is the captcha even real?

Geetest's server SDK has a "downtime / bypass" branch. From the open-source Galoy
`core/api/src/services/geetest.ts` (which is the reference implementation here):

```ts
const bypasscache = await getBypassStatus()          // GET https://bypass.geetest.com/v1/bypass_status.php?gt=<id>
if (bypasscache === "success") {
  result = await gtLib.register(...) / gtLib.successValidate(...)   // REAL validation
} else {
  result = await gtLib.localRegister() / gtLib.failValidate(...)     // local fallback
}
```

and the SDK's fallback (`lib/gt3-server-node-express-sdk/geetest-lib.js`):

```js
failValidate(challenge, validate, seccode) {
  if (!this.checkParam(challenge, validate, seccode)) { /* fail: params must be non-empty */ }
  else { this.libResult.setAll(1, "", "") }           // <-- status 1 = PASS
  return this.libResult
}
```

**So: non-`success` bypass status ⇒ any three non-empty strings pass.** Two one-request checks:

```bash
# 1. ask Geetest directly
curl -s "https://bypass.geetest.com/v1/bypass_status.php?gt=$GT"
#   {"status": "success"}  -> real wall
#   anything else / timeout -> decorative

# 2. ask the site's own captcha-init call (Galoy returns it explicitly)
curl -s -X POST https://api.<target>/graphql -H 'content-type: application/json' \
  -d '{"query":"mutation{captchaCreateChallenge{result{id challengeCode newCaptcha failbackMode}}}"}'
#   result.id = gt, result.challengeCode = challenge, result.failbackMode = (success === 0)
```

Observed on Blink: `bypass_status -> {"status":"success"}` and `failbackMode: false` ⇒ **real wall.**
Sending `validationCode:"1", secCode:"1"` against a live challenge returned
`{"errors":[{"message":"Captcha validation failed."}]}` — which is exactly the control you want to
confirm before spending an hour on the solver. Do this check first, every time.

Also identify the challenge *type* before planning a solve:

```bash
curl -s "https://api.geetest.com/gettype.php?gt=$GT&callback=geetest_$RAND"
# {"status":"success","data":{"type":"fullpage", ..., "slide":"/static/js/slide.7.9.3.js", ...}}
# the widget still ran product:"bind" and served slide.7.9.3.js / type=slide3 in practice:
# watch the Network log for  /pictures/gt/<hash>/bg/<id>.webp  +  /slice/<id>.png  -- those confirm slide3.
```

---

## 1. The three canvases (and which two you diff)

After the widget renders, the DOM holds:

| selector | content | notes |
|---|---|---|
| `canvas.geetest_canvas_bg` | background **with** the notch | displayed, 260×160 backing store, ~258.14 px CSS |
| `canvas.geetest_canvas_fullbg` | background **without** the notch | `getBoundingClientRect()` is 0×0 (hidden) but `toDataURL()` is full |
| `canvas.geetest_canvas_slice` | the puzzle piece at its current x | alpha channel = the piece silhouette |

`bg − fullbg` isolates the notch. The piece's initial `x` comes from `alpha(slice)`'s leftmost
non-zero column.

---

## 2. Threshold band — the first trap

`|bg − fullbg|` summed over channels, per-column, on a 260×160 canvas:

```
diff stats: max 353  mean 10.3  p99 220
thr= 20  count=3422  bbox x[ 50..219]  w=170   <-- bleeds into the piece's shadow
thr= 40  count=2654  bbox x[ 50..218]  w=169   <-- same
thr= 60  count=1813  bbox x[174..218]  w= 45   <-- the real notch
thr=100  count=1726  bbox x[175..217]  w= 43
thr=150  count=1201  bbox x[175..217]  w= 43
thr=200  count= 543  bbox x[175..216]  w= 42
```

Rule that reproduces `x=175` deterministically:

```python
band = diff[max(0, piece_top-2) : piece_bottom+3, :]   # restrict to the piece's rows
col  = band.sum(axis=0)
thr  = max(0.40 * col.max(), 1.0)
notch_left = int(np.where(col > thr)[0][0])
```

---

## 3. Centre, not edge — the trap that cost the most time

The notch bbox is **45 px** wide; the piece silhouette is **52–59 px** wide. The notch is a
threshold-eroded copy of the piece, so:

```
left-edge alignment : piece_left := notch_left            -> overshoots by ~4-5 px  -> FAIL
centre alignment    : piece_left := notch_centre - piece_w/2   -> correct          -> (needs a good track)
```

Measured example: notch `x[175..217]` ⇒ centre 196; piece `w=52` ⇒ `piece_left := 196 - 26 = 170`,
whereas left-edge alignment said 175. Five pixels is well outside Geetest's tolerance.

---

## 4. Slider → piece mapping is 1:1 (calibrate, don't derive)

Read `alpha(slice)`'s leftmost column, move the button exactly `T = 40 px`, read it again:

```
calib: moved 40.0px -> piece 1 -> 41   ratio(px_per_sliderpx) = 1.000
```

Canvas→CSS conversion is `cssWidth / canvasWidth` = `258.14 / 260 ≈ 0.9928` — i.e. negligible, but
apply it anyway so the closed loop and the open-loop estimate agree.

**Better than any estimate: close the loop while the button is still held.** Re-read the slice bbox
every few steps and stop when the piece's centre equals the notch's centre. Verified trace:

```
hist: [(30.0, 31, 70), (60.0, 61, 40), (90.0, 91, 10), (99.9, 101, 0)]   # (button_x, piece_x, error)
```

The piece tracked the button exactly; final error 0. **And the server still answered `FAIL`** — which
is the whole lesson: position is necessary, not sufficient.

---

## 5. Trajectory is the second gate

Geetest posts an encrypted `w` containing `aa` = the `[x, y, t]` mouse track. Observations:

| track | verdict |
|---|---|
| 5 big jumps (30 px each, 15–28 ms apart) | `FAIL` |
| 78 smoothstep steps (~1.5 px, 9–20 ms), position pixel-perfect | `FAIL` |
| 94 steps, centre-aligned | `ERR:[object Object]` (different failure — challenge/transport, not position) |
| ~5 steps, positions exact via closed loop | `FAIL` |

So the position was never the (only) problem. Before investing further, **read the verdict**:

```js
// initGeetest is assigned dynamically -> intercept with a setter, not a wrapper after load
(() => { let _v; Object.defineProperty(window,'initGeetest',{configurable:true,
  get(){return _v;},
  set(v){ _v=v; const w=function(o,cb){ return v(o,function(obj){ window.__gt=[];
      try{obj.onSuccess(()=>window.__gt.push('SUCCESS'));}catch(e){}
      try{obj.onError(e=>window.__gt.push('ERR:'+String(e).slice(0,40)));}catch(e){}
      try{obj.onFail&&obj.onFail(()=>window.__gt.push('FAIL'));}catch(e){}
      window.__gtObj=obj; return cb(obj); });};
    Object.defineProperty(window,'initGeetest',{value:w,writable:true,configurable:true}); }});})();
```

`window.__gt === ['FAIL']` + a pixel-perfect hold = the *behaviour* was rejected. That is the
decision point: either invest in behavioural modelling, or hand it to the operator (§6).

---

## 6. The operator handoff (do this earlier than you think)

A human drag is a **1-second** action. The pattern that works:

1. Drive the flow to the widget (`fill` phone → `select_option` channel → click submit → poll for
   `.geetest_slider_button`).
2. Print a loud marker: `>>> CAPTCHA READY — drag the slider <<<`.
3. Launch with `--start-maximized --window-position=0,0`. **A window the operator cannot see is the
   #1 reason a handoff "fails"** — the first attempt here timed out at 240 s with a small window.
4. Poll for the URL to leave the captcha route (`/login/verification`, or `?code=`), up to 10–15 min.
5. Then poll a **file** for the OTP (`solver/code.txt`) so the operator only has to paste digits.
6. Run the whole thing as a `background=true` job and poll it — never close the browser context
   between turns, and save `storage_state` before exiting.

Note: the app under test may auto-continue once the captcha passes — on Blink the page's own
`onSuccess` handler immediately calls `sendPhoneCode(...)`, so the OTP is sent without any further
action from you.

---

## 7. Adjacent gotchas from the same flow

- **Delivery channel is country-gated.** `+62` (ID) → `['TELEGRAM','WHATSAPP']`. No SMS option.
  Read `select[name=channel]` options *after* selecting the country.
- **`react-phone-number-input` needs the international form.** Plain `fill` of a national number
  with the wrong country select parses as another country (`0822…` → `+82` South Korea) and the
  server answers *"Invalid phone number type. Please use a mobile number."* Type `+62…` instead;
  then verify with `input_value()` before submitting.
- **Dev-only captcha skip exists in the source** (`if (env.CI || env.NODE_ENV === "development")`
  in the consent phone action) — it is not reachable in production, but it confirms the server
  treats the captcha as the sole gate.
- **Body text is not state.** `document.querySelector('.geetest_panel_error').innerText` returned
  `"Timed outRetry"` on every run — that element is a hidden template (`display:none`). Always read
  `getComputedStyle(el).display` together with `innerText` before concluding anything from it.
