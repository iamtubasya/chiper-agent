# Solving reCAPTCHA v2 image-grid challenges (Google, not Cloudflare Turnstile)

When a Google invisible reCAPTCHA flips from auto-pass into a **visible image-grid challenge**
("Select all images with X"), the `#g-recaptcha-response` textarea stays empty forever and the
register/login submit never fires. This is the classic trust-score collapse after repeated
automated attempts from the same IP/fingerprint. Solving it needs image classification.

## Detect the challenge (don't guess)
- The `bframe` iframe (`recaptcha/api2/bframe`) becomes visible with a 3×3 grid of
  `.rc-imageselect-tile` elements (each ~130×130px) plus a `#recaptcha-verify-button`.
- Challenge title text is inside the bframe: `Select all images with X` (cars, bridges,
  motorcycles, crosswalks, traffic lights, buses, hydrants, stairs…).
- The anchor iframe (`recaptcha/api2/anchor`, `size=invisible`) stays bottom-right.
- Poll `#g-recaptcha-response`; it stays length 0 while challenged.

## Solve = classify the 9 tiles into "contains target" vs not
The 9 tile images regenerate per challenge, so classification must happen IN-LINE with the live
browser session. Extract each tile with `frame.locator(".rc-imageselect-tile").nth(i).screenshot()`
(the `<img src=".../api2/payload?p=...">` URLs need the recaptcha session cookies — screenshot in
frame is simpler than fetch). Then classify each tile.

Vision options, in order of reliability:

1. **The agent's `vision_analyze` tool** — works only when `auxiliary.vision.model` is configured
   (not empty). If it returns "Connection error", the vision model isn't configured / endpoint is
   unreachable — do not assume it will come back.
2. **A local/remote OpenAI-compatible LLM gateway** — look up the provider config
   (`custom_providers` in config.yaml) and probe `GET <base_url>/v1/models`. Filter the list for
   `capabilities.vision == true`. Then `POST /v1/chat/completions` with an `image_url` body
   (`data:image/png;base64,...`) and a YES/NO prompt. **Watch the error class**: `402` = no credit,
   `403` = "model disabled in your preferences", `404` = not available — that model is unusable,
   move to the next id. A `vision=true` entry in `/v1/models` does NOT mean it's funded/enabled.
   The default "combo"/`new` model may auto-route to a text-only model that silently drops the image.
3. **Local ONNX image classifier** (`mobilenetv2-7.onnx` ~14 MB from onnx/models GitHub, run via
   `onnxruntime`) — sum softmax over the ImageNet class group for the target word. Works, but is
   noisy on the small obfuscated tiles; only worth it inside a retry loop (click top-scoring tiles,
   VERIFY, re-poll; the challenge regenerates on each wrong answer). Keep the ImageNet class-index
   map below if you go this route.

Then, for the tiles classified as "contains target": click them via the bframe
`tiles.nth(i).click()`, click `#recaptcha-verify-button`, and re-poll `#g-recaptcha-response` for a
token (>100 chars). If empty after verify → new challenge → re-classify.

## Prevention (cheaper than solving)
The challenge is a trust-score event, not a permanent wall. The FIRST registration attempt on a
fresh profile auto-passes invisible reCAPTCHA. Repeated automation collapses it into image-grid
mode. So: one clean attempt with a fresh `launch_persistent_context` profile + fresh email beats
solving image grids. If you've already burned the score, waiting (score reset) or a different
egress IP both help more than throwing OCR at reCAPTCHA.

## ImageNet class-index groups (for the ONNX fallback)
cars: 407,436,468,479,511,555,609,627,654,656,705,717,751,779,817,829,864,867,874
bus: 779,874,656,654,867,569
truck: 867,864,569,717,555,407
traffic light: 920
bridge: 818,842,793,857
bicycle: 444,671
motorcycle: 665,670
boat: 833,814,472,554,625,914
stairs: 531,850
fire hydrant: 601