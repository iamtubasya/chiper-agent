# Live evidence renderer — real screenshots of real traffic (finanzen.net VDP, 2026-10-16)

Rule 0d requires a screenshot per finding. When the flow needs authenticated session cookies +
custom headers (researcher-identification header), or the WAF blocks a cold browser, the reliable
recipe is: **a local HTTP server that performs the actual request when the page renders, then
headless Chrome screenshots that page.** The pixels contain real server responses; nothing is
typed in by hand.

## Architecture

```
evidence_server.py  (local,127.0.0.1:8888-style port)
  route /f1  -> renders a page that runs a LIVE cross-origin fetch from JS (page origin = attacker-style)
  route /f2  -> handler does: login(session helper) -> POST state-changing endpoint -> fetch victim view -> print raw request+response
  route /f3  -> handler does: GET the CSRF trigger -> GET the page that proves state change
  route /f4  -> handler does: anonymous POST -> prints status + rendered results table
headless Chrome --headless=new --screenshot=<png> http://127.0.0.1:<port>/fN
```

Key properties:
- The page body shows the EXACT request line, then the RAW response (html-escaped `<pre>` on a
  dark terminal-style sheet). Values come from the live call, so screenshot == evidence.
- For CORS findings, serve the page from `http://127.0.0.1:<port>` so the browser's own `fetch()`
  runs with an attacker-style origin — the screenshot then shows "BODY READ BY THIS PAGE: {...}",
  which is the demonstrated impact. Note: browsers consume ACAO/ACAC headers (page JS sees `null`
  for them) while still allowing the body read — print the server-side header truth (curl capture)
  in a static block on the same page so the figure carries both halves.
- Login-per-render (fresh session each screenshot) is fine and simpler than cookie export; the
  session helper = RSA-OAEP credential encryption + auth POST + callback, whatever the target uses.

## Chrome invocation (Windows host)

```bash
CH="/c/Program Files/Google/Chrome/Application/chrome.exe"
"$CH" --headless=new --disable-gpu --hide-scrollbars \
  --user-data-dir="$R/cp<N>" --window-size=1280,1500 \
  --virtual-time-budget=14000 --timeout=70000 \
  --screenshot="C:\\...\\evidence_png\\F<n>-name.png" "http://127.0.0.1:<port>/f<n>"
```

- **Fresh `--user-data-dir` per shot.** A shared profile gets locked by lingering headless
  processes and the run silently produces NOTHING (no file, no error). Symptom: the first shot
  with a profile works, later shots with the same profile emit nothing.
- `--virtual-time-budget` only when the page must run JS before capture (CORS demo); server-rendered
  pages need plain `--timeout` (the navigation waits for the server, which does its live work first).
- After a run, kill lingering `chrome.exe` processes (they accumulate one per shot).

## Verification (never ship an unverified PNG)

1. **Ink check** (blank-detection): PIL on the greyscale image — `unique_grey` in the hundreds,
   `ink_ratio = pixels>40 / total`. Dark terminal sheet: ~0.01–0.04. White interstitial page:
   ~0.99 with low `unique_grey` variance is also fine (white bg + text). `unique_grey == 1` or
   `min==max` = blank, throw away.
2. **Content cross-check**: `chrome --dump-dom <same-url>` must contain the same key strings the
   screenshot should show (HTTP status lines, response bodies, ids). dump-dom and screenshot come
   from the same page generation, so this validates the pixels indirectly when the vision model is
   unavailable.
3. If `vision_analyze` is up, one pass confirming the visible text beats both.

## Chain proof with mitmproxy (open-redirect / client-side navigation class)

For redirect findings the strongest figure is the **flow chain**: run Chrome through mitmdump and
attach the log lines showing `GET <attacker-controlled start>` immediately followed by
`GET <off-site target>`:

```bash
mitmdump -p 8888 --set flow_detail=1 > mitm_f5.log 2>&1   # terminal background=true
CHROME --proxy-server=http://127.0.0.1:8888 --ignore-certificate-errors \
  --user-data-dir=$R/cp<N> --virtual-time-budget=15000 --dump-dom "<start-url>" > run<N>.html
grep -E "start-host|target-host" mitm_f5.log > f5_mitm_chain.txt   # attach this excerpt
```

- Check the proxy port is actually free first (`netstat -ano | grep :8080`); on a box running the
  audit pipeline, **8080 may already be held by another local listener** — bind fails with
  `Errno 13` in mitmdump's log. Fall back to 8888 and state the port deviation in the evidence file.
- `curl -x http://127.0.0.1:<port> https://example.com` returning `000` does not prove mitmdump is
  down (some CONNECT paths fail); Chrome traffic in the log is the real liveness check.
- An Akamai interstitial as the final page is fine as proof: it quotes the requested URL
  (`You don't have permission to access "http://<offsite-host>/"`), which is the browser proving
  where it ended up. Save the final DOM (`--dump-dom`) alongside the PNG — the DOM text is
  copy-pasteable evidence for the report body.

## Attachments layout (per finding)

```
reports/report_F<n>.md          # contains the ![caption](abs/path.png) line + Tool-assistance section
reports/body_F<n>.txt           # validator-checked email body
reports/finanzen-F<n>-*.pdf     # built from md (image embedded), qa_pdf_layout clean
reports/evidence_F<n>_*.txt     # raw request/response + chain excerpt
reports/evidence_png/F<n>-*.png # the live screenshot (also embedded in the PDF)
```
