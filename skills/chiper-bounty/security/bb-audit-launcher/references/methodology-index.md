# Methodology Index — Curated from 5 Repos
> Source repos for BB methodology. Cross-referenced with bb-audit-launcher.

## 1. vavkamil/awesome-bugbounty-tools ⭐6.3K
- Tool index: organized by category (recon, scanning, exploitation, reporting)
- URL: https://github.com/vavkamil/awesome-bugbounty-tools

## 2. devanshbatham/Awesome-Bugbounty-Writeups ⭐6.1K
- Writeups organized by bug type (SSRF, IDOR, XSS, SQLi, etc)
- URL: https://github.com/devanshbatham/Awesome-Bugbounty-Writeups

## 3. KingOfBugbounty/KingOfBugbountyTips ⭐5.5K
- Tips from well-known hunters
- Recon methodology, subdomain discovery, endpoint analysis
- URL: https://github.com/KingOfBugbounty/KingOfBugBountyTips

## 4. HolyBugx/HolyTips ⭐2K
- Checklists and writeups
- Web application security methodology
- URL: https://github.com/HolyBugx/HolyTips

## 5. xalgord/Massive-Web-App-Pentest-Notes ⭐1.9K
- Comprehensive pentest methodology
- Covers full lifecycle: recon → test → exploit → report
- URL: https://github.com/xalgord/Massive-Web-Application-Penetration-Testing-Bug-Bounty-Notes

---

## Extracted Playbooks

### Recon Methodology (from KingOfBugbountyTips)
1. Subdomain enumeration (amass/subfinder)
2. Port scanning (naabu/masscan)
3. Technology detection (whatweb/wappalyzer)
4. Endpoint discovery (gau/katana/waybackurls)
5. Parameter discovery (arjun/paramspider)
6. Virtual host discovery
7. S3 bucket discovery

### Testing Methodology (from Massive-Pentest-Notes)
1. Authentication testing
2. Authorization testing (IDOR/BOLA)
3. Input validation (XSS, SQLi, SSTI)
4. Business logic testing
5. File upload testing
6. API testing (REST, GraphQL)
7. Mobile API testing

### Reporting Tips (from Awesome-Bugbounty-Writeups)
- Write report for triager, not for hacker
- Include: impact, steps to reproduce, fix suggestion
- One report per vulnerability class
- Don't report low-severity issues as critical
