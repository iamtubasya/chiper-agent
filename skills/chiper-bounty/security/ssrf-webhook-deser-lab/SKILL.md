---
name: ssrf-webhook-deser-lab
description: Use for local SSRF/webhook/deser probe calibration.
---

# SSRF / Webhook / Deserialization calibration range

Local Docker range at `D:/isplab/web2-lab-ssrf`. Fills the gap Juice Shop + DVWA
leave: they have **no real SSRF sink**, no webhook-trust surface, no deserializer.

## Why it is built this way

`lab-internal` has **no published port**. A response from it appearing in
`lab-app`'s output can therefore only have been fetched server-side — Docker NAT
cannot fabricate it. Every vulnerable endpoint has a matching **control** that
must REFUSE, so a probe can be shown to *discriminate*, not merely to fire.

## Topology

| Service | Port | Internet | Role |
|---|---|---|---|
| lab-app | 8090 | 127.0.0.1 only | vulnerable app |
| lab-internal | **none** | no | SSRF target |
| lab-receiver | 8091 | 127.0.0.1 only | attacker webhook receiver |

## Bring up

```bash
cd /d/isplab/web2-lab-ssrf && docker compose up -d --build
sleep 8 && python calibrate.py     # expect 19/19
```

`docker compose up` gets blocked by the foreground-daemon guard — run it with
`background=true` + `notify=true`, then `process(action='wait')`.

## Endpoints

Vulnerable: `/ssrf/fetch?url=` (echo), `/ssrf/blind?url=` (no echo),
`/ssrf/fetch-weak?url=` (startswith allowlist), `/orders/{id}/notify`
(callback_url), `/webhook/pay` (unsigned), `/deser/pickle`, `/deser/yaml`.

Controls: `/ssrf/fetch-safe` (hostname allowlist), `/webhook/pay-safe` (HMAC),
`/deser/json`.

## Verified procedure

1. `python calibrate.py` → 19/19, split ssrf 7 / webhook 7 / deser 4.
2. nuclei, 3 templates, fires all three classes:
   ```bash
   nuclei -u http://127.0.0.1:8090 -t tools/n-ssrf-content.yaml \
          -t tools/n-s3-webhook.yaml -t tools/n-s3-deser.yaml -silent -no-color
   ```
3. Negative control via nuclei must be **silent**:
   `tools/n-ssrf-should-not-match.yaml` (blind + safe endpoints).
4. Blind SSRF: run `interactsh-client`, POST its domain to `/ssrf/blind`.
   Endpoint returns `{"queued":true}` with **no body**, yet interactsh logs DNS +
   HTTP with `User-Agent: python-requests/*` — server-side, not a browser. This
   is the only valid proof for a blind sink.

## PITFALLS

1. **`-mc 200` false-positives on any proxying sink** — `/ssrf/fetch` returns 200
   even when the upstream 404s, so every word matches. Filter on body content, or
   `-fs <404 body size>` (285 bytes here).
2. **Inside a container, `127.0.0.1:8091` is itself**, not the host. The app must
   reach the receiver by service name: `http://lab-receiver:8080`.
3. **`localhost` → IPv6 on Windows** (`::1`). Use `127.0.0.1` for nuclei/ffuf
   unless the service binds IPv6.
4. **nuclei re-encodes `%3B`** — in raw templates use a literal `;`.
5. **YAML single-quoted regex**: `\\d` is not `\d`. Prefer `[0-9]` classes.
6. **Cookie names are case-sensitive** (`PHPSESSID`); a wrong-case cookie silently
   drops the session and every authenticated template reads zero.
7. **Blind SSRF cannot be proven by content matching.** A silent content matcher
   is correct behaviour, not a miss. Only OOB proves it.

## Honest limitation

For SSRF/webhook/deser the paired control lives inside this range, so it shows
internal consistency, **not** transfer. Transfer is only demonstrated for DVWA's
four classes (low vs impossible). Never claim a lab-validated probe works on a
real target without re-validating against a patched oracle.
