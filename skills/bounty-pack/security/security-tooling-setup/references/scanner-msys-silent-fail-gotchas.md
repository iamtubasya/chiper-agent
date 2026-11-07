# Scanner silent-fail gotchas on this Windows/MSYS host (2026-11-02, Glia run)

The user caught a whole session where "toolchain running" was actually one `http.client`/`urllib`
loop in `execute_code`. When I finally deployed the real scanners, three concrete gotchas made
them write **0-byte outputs with exit 0** — which reads as "0 findings" when it is really "the tool
never ran". All three are MSYS-vs-native-path / flag-name traps, not tool defects.

## 1. `~` is NEVER translated for native Go binaries (nuclei, ffuf, httpx, subfinder, dnsx, gau, katana)

In git-bash `~` expands, but the Go binary does not resolve `~/wordlists/x.txt` or `-o ~/foo.json`.
Pass **native Windows paths** (`/home/agentuser/...`):

```bash
# WRONG — writes nothing, exit 0
ffuf -u https://app/FUZZ -w ~/wordlists/api-endpoints.txt -o ~/ffuf.json
# RIGHT
ffuf -u "https://app/FUZZ" -w "/home/agentuser/wordlists/api-endpoints.txt" \
     -o "/home/agentuser/bounty/web2-50/glia/ffuf.json"
```

`nuclei -t` is the same: it needs the **native** template dir (`/home/agentuser/nuclei-templates/...`),
and the bash `~` form gets from-defaulted-away ("Could not find template"). Verify the template dir
exists first (`find /home/agentuser/nuclei-templates -name '*.yaml' | wc -l` → 14k+).

## 2. `httpx` this build uses `-threads`, NOT `-c`

`httpx -c 3` → `exit 2` instantly (flag not recognized). Correct:
`httpx -l subs.txt -sc -title -tech-detect -rl 3 -threads 3 -timeout 15 -silent -o live.txt`.

## 3. nuclei chokes on httpx/`-o` output with `[...]`/title text — strip to bare URLs first

`httpx -sc -title` writes rows like `https://x [404] [Amazon CloudFront,...]`. Feeding that whole
file to `nuclei -l` produced `[url] failed to parse url ... invalid control character in URL` for
every row and "no templates provided / no results". Normalize to host-only before scanning:

```bash
awk '{print $1}' httpx_live.txt | tr -d '\r' | sed 's/[[:space:]]//g' | sort -u > live_clean.txt
nuclei -l live_clean.txt -t "/home/agentuser/nuclei-templates/http/exposures/" \
       -rl 5 -c 2 -timeout 12 -silent -o nuclei_out.txt
```

## 4. nuclei / ffuf write 0-byte output on a genuinely clean run — distinguish from "never ran"

`nuclei -silent -o out.txt` with zero findings legitimately writes a **0-byte** file AND prints
"Scan completed ... No results found" (or exits with a summary). A **0-byte .err with no summary**
means it died before loading templates (bad `-t` path). Always read the `.err`/stderr line, not
just `wc -l` the output. Confirm the lane works: run the same template set against ONE host you
know (`-u <host>`) before trusting a 113-host mass verdict.

## 5. ghauri/sqlmap on a statically-returning endpoint = 20+ min of pointless boolean-blind grinding

If you already proved the endpoint returns a constant JSON (placeholder) regardless of input, do
NOT let ghauri/sqlmap run full blind battery — set a hard timebox (`timeout 180` background +
notify) and read the *verdict line* ("does not seem to be injectable" / "not injectable"), which is
the actual signal. The endpoint is not the interesting trace.

## 6. A tool that only "prints progress" then exit 0 is STILL a valid run — read the ledger, not the console

`ffuf` floods `:: Progress: [N/272]` to stderr; the JSON at `-o` is the result. When it exits 0
with `results: 0` that is a real negative for those FUZZ positions — log it, don't re-run.