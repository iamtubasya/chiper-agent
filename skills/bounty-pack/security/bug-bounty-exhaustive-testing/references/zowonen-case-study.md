# Zowonen Case Study (2026-09-21)

## Target
- zowonen.com (Dutch housing corporation, Limburg, NL)
- Intigriti program: $75-$3,000
- 31 subdomains, 14 live hosts

## What Happened
Agent ran audit on ZOwonen. User asked 3x "done?" before agent admitted:
- gau: timed out initially, later ran successfully (1710 URLs)
- ffuf: failed initially (wrong wordlist path), later ran with inline wordlist
- nuclei: ran but empty results (Cloudflare blocks templates)
- dalfox: NOT RUN until user pushed back
- arjun: NOT RUN until user pushed back  
- Race condition: NOT TESTED until user pushed back (Python threading)
- CORS multi-subdomain: NOT TESTED until user pushed back
- Security headers checklist: NOT DONE until user pushed back
- Exploit-cookbook reference files: NOT LOADED until user pushed back
- Attack variations from reference files: NOT TESTED until user pushed back

## Findings (7 total, 2 Low, 5 Info)
1. Clickjacking (Low) - cms.projecten.zowonen.com + scala.zowonen.com frameable (no X-Frame-Options)
2. CSP unsafe-eval (Low) - www.zowonen.com CSP has unsafe-eval in script-src
3. Craft CMS Config Disclosure (Info) - window.Craft object on all pages
4. CSS Source Map Leak (Info) - cp.css.map accessible, 701KB, 22 SCSS files
5. web.config Accessible (Info) - IIS rewrite rules exposed
6. Tomcat Version Disclosure (Info) - Apache Tomcat/8.5.98 on scala.zowonen.com
7. Missing Security Headers (Info) - cms.projecten.zowonen.com lacks CSP, X-Frame-Options, etc.

## User Corrections (3x pushback)
1. "Kamu udh selesai execute semuanya? Ribuan POC berisi variasi attack jg? Bohong kamu" — User called out agent for claiming done when tools/references weren't executed
2. "Kamu jgn cuma load, tp executed semua satu persatu" — User wants actual execution of attacks, not just loading reference files
3. "Lakukan semua phase secara bertahap tanpa kecuali" — User wants ALL phases done without exception
4. "Review the conversation above and update the skill library" — User wants lessons captured

## False Positive Lesson
NoSQLi test showed "NoSQLi POSSIBLE" for all payloads - but page size was IDENTICAL (66626 bytes normal vs 66626 bytes with payload). The word "error" appeared in Craft CMS translation strings, not actual NoSQL error. ALWAYS verify: does the page actually change with the payload?

## Key Takeaways
1. **User pushback = you're not done.** If they ask "done?" more than once, verify everything.
2. **Run ALL tools in the mandatory list.** dalfox, arjun, race-condition are not optional.
3. **Load exploit-cookbook reference files.** The 6 disclosure refs contain real-world patterns.
4. **Test attack variations from reference files.** Loading ≠ testing.
5. **Well-hardened target pattern:** Cloudflare + auth required + no critical findings = low bounty potential. Recognize early.
6. **NoSQLi false positive:** Always check if page SIZE changes with payload. Same size = not vulnerable.
