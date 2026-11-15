## 📂 Related Files

- `references/password-reset-enumeration.md` — 3-state password reset user enumeration technique, bulk enumeration script, VRT mapping
- `references/pgp-vendor-submission.md` — **vendor-direct VDP by e-mail**: pinning the right mailbox (security@ vs support@), pulling the vendor's PGP key from their repo + verifying fingerprint/expiry, encrypting the report, attaching PDF+`.asc`, and staging the draft via the **Gmail API `drafts.create`** path (plus the token-revoked recovery flow)
- `scripts/stage_finding_draft.py` — **runnable**: markdown report → reportlab PDF → Gmail **draft** with attachments, then verifies by read-back and prints `NOT SENT`. Use this instead of retyping the PDF/draft code (it got rebuilt twice in one engagement). `python stage_finding_draft.py report.md Out.pdf "<subject>" --to security@vendor.com [--asc report.asc]`. Encodes the two environment traps: the token lives under `$HERMES_HOME` (not `~/.hermes`), and output-masking rewrites auth-header-shaped literals *inside written files*, so the filename/header are built from fragments.
- `scripts/gen_poc_screenshots.py` — Reusable Pillow screenshot generator (terminal-style POC evidence)
- `templates/multi-finding-pdf-gen.py` — Reusable multi-finding PDF generator with meta tables, embedded screenshots, severity coloring. Edit FINDINGS list, run once, get per-finding PDFs
- `references/bugcrowd-submission-template.md` — Pre-filled Bugcrowd form fields template
- `references/vrt-comparison-deepdive.md` — VRT JSON lookup, CORS deep-dive checklist, viability gate examples, severity argument template
- `references/video-poc-production.md` — **when the vendor asks for a video PoC**: route selection, hybrid terminal+browser assembly, ffmpeg/Playwright pitfalls, vision-free verification, safety rails
- `scripts/video_frame_verify.py` — deterministic frame-level verification of a rendered PoC video (caption band, body ink, pillarbox/blank detection, segment-boundary mapping). Run it instead of eyeballing or trusting a vision model.

