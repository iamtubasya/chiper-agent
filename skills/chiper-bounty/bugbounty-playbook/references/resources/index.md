# Resources

> tags: resources

> related: Attack-Surface/Web3/Tooling

Resources
Curated, not exhaustive. I've deliberately kept this short because a list of 500 links is useless. If something's on this list I've actually used it.
Practice Labs
PortSwigger Web Security Academy - portswigger.net/web-security
The single best free resource for learning web security. Structured by topic, practitioner and expert level labs, written by people who understand the material. If you haven't finished the practitioner-level labs, do that before anything else.
Hack The Box - www.hackthebox.com
Better for network/infrastructure pentest skills than web app bug bounty, but the web challenges are solid and retired boxes with writeups are great for learning.
PentesterLab - pentesterlab.com
Paid, worth it. Well-structured exercises with smooth progression from basic to advanced. The white badge and black badge tracks are particularly good.
APIsec University - www.apisecuniversity.com
API-specific testing labs, free.
Ethernaut - ethernaut.openzeppelin.com
OpenZeppelin's Solidity CTF for smart contract vulns.
Damn Vulnerable DeFi - www.damnvulnerabledefi.xyz
web3-focused challenges.
Capture the Ether - capturetheether.com
Solidity security primer.
Disclosed Reports
HackerOne Hacktivity - hackerone.com/hacktivity
Filter by disclosed, read the high-severity ones. Pay attention to the writing quality of reports that get resolved quickly with high payouts. That's your benchmark.
Pentester.land Writeups - pentester.land/writeups/
Aggregated writeups from across the community. Good for browsing when you want inspiration or want to learn about a specific vuln class.
References
OWASP Testing Guide - owasp.org/www-project-web-security-testing-guide/
The definitive methodology reference. Dense but comprehensive. Use it as a checklist, not a tutorial.
HackTricks - book.hacktricks.xyz/
Massive collection of techniques and commands. Not always well-organized, but when you need the specific syntax for exploiting X in context Y it's usually there.
Tools
Most tools are referenced in context within the Tooling section. Short list of essentials:

Burp Suite Pro - If you're serious about web testing the Pro license is worth it. Repeater, Intruder, Collaborator, and extensions are indispensable.
Caido - Modern alternative to Burp. Worth watching as it matures.
ffuf - Fastest directory/content fuzzer. My daily driver for content discovery.
Nuclei - Template-based vulnerability scanner. Custom templates are the real value.
subfinder - Passive subdomain enumeration. Start of every recon pipeline.
httpx - HTTP probing with tech detection. The glue between recon stages.

Books
The Web Application Hacker's Handbook - Stuttard & Pinto. Dated in some areas but the foundational methodology chapters are still good.
Bug Bounty Bootcamp - Vickie Li. Best structured introduction specifically for bug bounty. Good for intermediate hunters filling knowledge gaps.
Real-World Bug Hunting - Peter Yaworski. Case-study approach with real disclosed vulns. Good for understanding what programs actually pay for.
Newsletters
Bug Bytes by Intigriti - Weekly newsletter with disclosed reports, new tools, and community news. Consistently the best aggregated bug bounty content.
tl;dr sec by Clint Gibler - Weekly security research digest.
AI/LLM Security
OWASP LLM Top 10 - genai.owasp.org/llm-top-10/
The reference taxonomy.
Promptfoo - www.promptfoo.dev
Test harness for prompt-injection regression.
Legal & Safe Harbour
disclose.io - disclose.io/
Standardised safe-harbour language and organisations that adopt it.
Bugcrowd Standard Disclosure Terms - www.bugcrowd.com/resources/levelling-up/bugcrowd-disclosure-policy/
One of the cleanest safe-harbour templates.
EFF Coders' Rights - www.eff.org/issues/coders
Legal resources for security researchers.
What I Don't Recommend
Not listing YouTube channels, Discord servers, or Twitter accounts because the signal-to-noise ratio changes too fast. Find the researchers whose disclosed reports impress you, follow them, unfollow anyone who stops being useful.