## Companion Reference — `poc-technique-atlas` (additive, never overrides)

Method-level technique shelf extracted from a 2,223-repo local PoC corpus (filtered of
malware/scam, deduped) + PortSwigger WSA. **Read ONE class file per phase** — it does NOT
count against the phase context budget (on-demand shelf).

- `references/00-INDEX.md` → 27 classes (RCE 357, IDOR/BOLA 87, SQLi 83, Crypto 75,
  Auth-bypass 68, XSS 59, Info-disclosure 48, LFI 47, Deserialization 22, SSRF 19,
  Cloud 14, SSTI 7, Race 5, XXE 5, Prototype-pollution 2, …). 1,901 techniques total.
- `references/portswigger/00-INDEX.md` → 29 WSA topics.
- Use it to pick the *method* for the class you are testing; owner skill rules still win.
