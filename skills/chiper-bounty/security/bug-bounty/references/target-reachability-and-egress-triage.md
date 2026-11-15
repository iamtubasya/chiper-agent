# Target reachability & egress triage (recon)

## Symptom
A host resolves (`dnsx -a`) but every HTTP call times out: `curl` reports `code=000` with
`time_total≈timeout`, httpx prints nothing for it. Easy to misread as "target down" or "WAF" —
it is almost always one of the two causes below.

## Two causes, one diagnostic
1. **Your egress IP is blocked/flagged** (VPN / Cloudflare WARP / datacenter range). DataDome and
   similar WAFs score the *source IP*: the same request answered **200 via a WARP egress** and
   **403 from the local ISP IP** in one live run. So "WAF blocks everything" is often just "this IP
   is dirty".
2. **The host is an IP-allowlisted partner API.** It may be published in scope but only accepts TCP
   from allowlisted source IPs — unreachable from *any* non-allowlisted box, whatever the egress.

Run this before concluding anything:

```bash
# raw TCP probe — bypasses the HTTP stack entirely
timeout 6 bash -c 'cat < /dev/null > /dev/tcp/<ip>/443' && echo OPEN || echo FILTERED

# change egress, confirm it actually changed, repeat the probe
"/c/Program Files/Cloudflare/Cloudflare WARP/warp-cli" disconnect   # or `connect`
curl -s -m8 https://api.ipify.org ; echo
```

- Still FILTERED on **every** egress → IP allowlist (cause 2). Record it as "resolves, not reachable
  from non-allowlisted IPs; cannot be tested externally" and **stop** — do not burn cycles retrying.
- Reachable on one egress but not another → cause 1. Keep the egress that works for the run, and
  **restore the user's VPN state** (`warp-cli connect`) when done — you changed their environment.

## Don't declare "WAF blocks everything" from one IP
Try **at least two** egress IPs before writing a target off. A 403 that flips to 200 under a
different source IP is an egress-scoring artefact, not a dead end. (And a `000` that persists across
every egress is a network-layer filter, not an application decision.)

## MSYS/bash gotchas that cost real cycles
- `curl -o relative.json` after `cd /tmp` writes into the **Windows** cwd, not the MSYS cwd — the
  shell then `ls`es an empty directory and you think curl failed. Use an absolute path: `-o /tmp/out.json`.
- `curl … | python3 - <<'PY'` parses an **empty string**: the heredoc becomes python's stdin and the
  piped body is discarded. Write the parser to a file, then `python3 parser.py < out.json`.
- `strings` is not present in this MSYS; mine DEX/APK strings with a python regex over the raw bytes
  (`re.findall(rb'[\x20-\x7e]{6,}', open(path,'rb').read())`).
