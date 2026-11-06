## ⛔ RULE 11: Craft CMS Specific Testing

When auditing Craft CMS targets, ALWAYS test these CVEs and endpoints:

**CVEs to check:**
- CVE-2025-32432: Pre-auth RCE via `actions/assets/generate-transform` (Craft 3.x <3.9.15, 4.x <4.14.15, 5.x <5.6.15)
- CVE-2026-25495: SQLi via `criteria[orderBy]` parameter (Craft 4.x <4.16.17, 5.x <5.6.x)

**Key endpoints (return 400 = exists, 404 = not found):**
- `/actions/assets/save-asset` — file upload
- `/actions/entries/save-entry` — content creation
- `/actions/users/set-password` — password change
- `/actions/users/save-user` — user creation
- `/actions/users/login` — authentication
- `/actions/users/send-password-reset-email` — password reset (user enumeration check)
- `/actions/assets/generate-transform` — image processing (CVE-2025-32432 target)
- `/actions/elements/index` — element listing (CVE-2026-25495 target)

**Version detection:**
- Check `cpresources/[hash]` pattern — Craft 3 vs 4 have different hash lengths
- Check admin page for version hints in meta tags or JS
- Check `window.Craft` object for `systemUid`, `actionUrl`, `resourceBaseUrl`

**User enumeration check:**
- Compare response for known email vs nonexistent email on password reset
- Craft CMS returns SAME response for both (good) or DIFFERENT (vuln)

