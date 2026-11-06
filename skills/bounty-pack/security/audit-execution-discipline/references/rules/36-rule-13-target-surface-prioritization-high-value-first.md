## ⛔ RULE 13: Target Surface Prioritization — High-Value First

**User correction (2026-09-22): "cari celah d prod... pastikan ini: sebagai attacker sy bisa apa? celah ini apakah berbahaya bagi user, data, dana dan sistem?"**

Don't test endpoints equally. Prioritize by attacker value:

**Attack surface priority order (web apps):**
1. **Financial endpoints** — payment, withdrawal, voucher, coupon, SPayLater, coins, balance
2. **Authentication system** — login, registration, password reset, OAuth, session management
3. **User data endpoints** — profile, orders, addresses, messages, account settings
4. **Seller/partner portals** — admin panels, sub-accounts, product management, order management
5. **API endpoints with auth bypass potential** — IDOR, broken access control, privilege escalation
6. **File upload/processing** — image proxy, document processing, SSRF vectors
7. **Third-party integrations** — webhook callbacks, OAuth redirects, SSO
8. **Everything else** — headers, info disclosure, version enumeration

**For EACH finding, answer 4 questions before reporting:**
1. Apa yang bisa attacker lakukan? (concrete action, not theoretical)
2. Apakah berbahaya bagi user? (data theft, account compromise, financial loss)
3. Apakah berbahaya bagi dana? (price manipulation, unauthorized transactions, fund theft)
4. Apakah berbahaya bagi sistem? (RCE, SSRF, data corruption, DoS)

If answer to ALL 4 is "no/tidak signifikan" → it's informational, skip it.

**Shopee session lesson (2026-09-22):** Spent 11 phases testing 30+ endpoint categories. Most turned out:
- Client-side keys in page source = BY DESIGN (designed for frontend)
- Test/UAT environments = test envs, not production data
- CORS wildcard on test envs = not impactful
- Error disclosure = informational only
- OAuth endpoints returning SPA shell = catch-all, not real OAuth

**RESULT:** Only 1 potentially reportable finding (partner CORS) out of 8 "findings" — 7 were informational. User frustrated: "kamu gk bener kerjanya, selalu low atau informational terus."

**FIX:** Start with financial + auth endpoints. If those are solid, move to seller/admin portals. Don't waste time on header checks or version disclosure until HIGH-VALUE targets are exhausted.

