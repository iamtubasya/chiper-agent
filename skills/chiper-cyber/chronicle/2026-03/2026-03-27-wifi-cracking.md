# 2026-03-27 — WiFi cracking practice

**Skill:** chiper-wifi-pentest · **Scope:** lab only (own AP + 2 lab targets) · **Author:** chiper-cyber

## Summary

| Metric | Value |
|---|---|
| Targets scanned | 3 |
| Handshakes captured | 2 |
| Keys recovered | 2 (lab PSK) |
| Time on target | ~45 min |
| Tooling | `airmon-ng`, `airodump-ng`, `aireplay-ng`, `hashcat -m 22000` |

## Timeline

1. **20:04** — Monitor mode up on `wlan0mon`; regulatory domain confirmed (`iw reg get`).
2. **20:07** — Survey on 2.4 GHz + 5 GHz; three lab APs isolated, one with WPA2-PSK, one WPA3-SAE transition.
3. **20:15** — Deauth burst against lab-AP-1 (own equipment) produced an EAPOL 4-way in 11 s.
4. **20:29** — Second handshake from lab-AP-2 after client reconnect; captured with `--write`.
5. **20:38** — Converted both captures to `22000` format; offline crack against the lab wordlist recovered both PSKs.

## What worked

- Targeted deauth (2 frames, 1 s interval) beats continuous jamming — client comes back politely.
- Converting early to `hashcat` format avoids re-capturing when the first tool fails.

## What did not

- WPA3-SAE transition AP resisted every offline attempt — expected, SAE is not capture-able this way.
- 5 GHz capture dropped frames at default rate; raising `--manufacturer`/channel hop interval helped only partly.

## Lessons

- Always confirm the regulatory domain first; channel 12/13 assumptions broke the first survey.
- Two handshakes beat one — capture both sides when the client roams.

## Next

- Practice PMKID (`hcxdumptool`) path on lab-AP-3.
- Re-run with `hcxpcapngtool` to drop the deauth dependency entirely.
