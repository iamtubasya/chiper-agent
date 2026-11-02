---
name: chiper-edge-computing-attack
description: "Use when Attacks against edge computing platforms — Cloudflare Workers (V8 isolate), Fastly Compute@Edge (WASM/Wasmtime), AWS Lambda@Edge and CloudFront Functions, Ak"
version: "0.2.0"
author: Chiper (Chiper-Cyber)
metadata:
  Chiper:
    tags: [pentest, security, kali-linux, chiper-cyber, edge, computing, attack]
references:
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-attack/SKILL.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-attack/payloads.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-attack/test-cases.md
  - path: ~/.chiper/skills/chiper-cyber/chiper-edge-computing-attack/guides
---

# Edge Computing Attack

## When to Use

This skill targets **edge computing** — where code runs in geographically-distributed nodes close to end users, typically in V8 isolates (Cloudflare Workers), WASM sandboxes (Fastly Compute@Edge), or restricted JavaScript engines (AWS CloudFront Functions, Lambda@Edge). The attack surface differs from origin-side attacks: edge platforms handle TLS termination, request routing, and caching, and their security model assumes a trusted-but-curious operator with strong tenant isolation.

**Tools**: wrangler, fastly-cli, sam-cli (SAM Local), gcloud edge, akamai-cli, vercel-cli, deno, vitesspa, chrom

## Core Tools

### Cloudflare Workers
- **wrangler** — official Workers CLI; deploy, dev, KV, R2
- **miniflare** — local Workers emulator for testing
- **cloudflare-api-cli** — direct REST API access
- **workers-typescript-template** — boilerplate for TS Workers

## Methodology Overview

### Phase 1 — Reconnaissance
- Identify edge platform via HTTP headers (`Server: cloudflare`, `X-Fastly`, `X-Amz-Cf-Pop`, `X-Akamai-Transformed`, `X-Vercel-*`)
- Identify edge functions in use (timing analysis, behavior fingerprinting)
- Map edge KV store usage (timing, error patterns)
- Identify origin WAF patterns (security headers)
- Map request routing (geo DNS, edge POPs)

## Instructions

Read the referenced chiper-cyber files for full methodology:
- **SKILL.md** — Step-by-step methodology, attack chain, tools, and defense perspective
- **payloads.md** — Ready-to-use attack payloads organized by type and technique
- **test-cases.md** — Structured test procedures with prerequisites and expected results
- **guides/** — Deep-dive learning materials and scripts

Full skill content at: `~/.chiper/skills/chiper-cyber/chiper-edge-computing-attack/`

## Examples

See `payloads.md` in the referenced directory for ready-to-use attack payloads.

## Test Cases

See `test-cases.md` in the referenced directory for structured test procedures.

## Notes

- Source: Chiper-Cyber v1.0.0 — Security Skills Ecosystem (Chiper 2026)
- Defense Triple: Defense Perspective + Detection Methods + Evasion Techniques
- Update: `cd ~/.chiper/skills/chiper-cyber && git pull`
