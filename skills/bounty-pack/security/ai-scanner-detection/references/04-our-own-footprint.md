# 04 — Our own footprint (what a client SOC sees when WE scan)

This is the self-awareness half, and it is a real deliverable.

## What our pipeline emits

| our source | visible as | changeable? |
|---|---|---|
| subdomain enum | DNS query patterns, TLS SNI bursts, certificate-transparency correlation | partly |
| httpx / probes | HTTP/2 or HTTP/1.1 GETs, default UA set, no browser behaviours | yes |
| nuclei / sqlmap / ffuf / dalfox / katana | each tool's **default** UA + pacing + payload shape | yes, via flags |
| browser-driven checks (CDP) | real browser fingerprint — looks human, but pauses are unnatural | no |
| the recording proxy (if used) | a listening loopback port + a CA on OUR host, not on theirs | n/a |
| report/evidence traffic | none — offline | n/a |

## Why this matters operationally

1. **False-positive friction.** If we trip the client's production alerting, they may cut the
   engagement mid-run. Telling them the pattern up front (and asking for an allow-list window) keeps
   us inside scope.
2. **It demonstrates competence.** A brief that says "your SIEM will see A, B, C; here is how to
   distinguish us from a real attacker; here is what we will NOT do" is exactly what a mature
   programme wants.
3. **Honesty about limits.** We must state plainly that UA-based detection of US is trivially
   bypassable — and therefore that a clean alert does not prove a clean network.

## Template for the brief

```
Scan visibility note — <engagement>
Source addresses / ranges: <...>          [will be stable | will rotate]
Window: <...>                              [request allow-list for this window]
Static fingerprints: <UA set, tool list>   [changeable at our discretion]
Behavioural pattern: recon -> probe -> auth within one session; adaptive retries after 4xx
What we will NOT do: destructive commands, data exfil pipes, rate that exceeds <x> rps
Suggested benign handling: allow-list source, or suppress the correlation rule for the window
Limitation: absence of our fingerprints is not evidence of a clean network
```
