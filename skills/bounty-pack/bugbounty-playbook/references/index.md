# The Bug Bounty Playbook

> related: Methodology/, Recon/, Attack-Surface/, Chains/, Attack-Surface/Web3/Tooling, Reporting/, Programs/, Business-of-Bounties/

A living collection of TTPs, methodology, and tradecraft for bug bounty hunting. Opinionated and incomplete. Some pages are polished, some are rough notes jotted down between targets.
A finished playbook would mean I stopped learning, so don't hold your breath.
Who this is for
Hunters who already know the basics. If you need someone to explain what Burp Suite does, start with PortSwigger's Web Security Academy and come back when you've done the practitioner-level labs.
If you're past that and want to find bugs that actually pay, chain findings into crits, and navigate the business side of bounty hunting, you're in the right place.
Sections

Methodology
Zero to payout
Recon
Discovery, enumeration, target mapping
Attack Surface
Web, API, mobile, cloud, CI/CD
Chains
Multi-vuln escalation patterns
Tooling
Configs, scripts, and automation
Reporting
Reports that get paid, not triaged as informational
Programs
Platform strategy, program selection, the meta-game
Business of Bounties
The stuff nobody talks about

Open the graph view to see how everything connects. Every technique links to the recon that surfaces it, the chains that escalate it, and the reporting patterns that get it paid.
Philosophy
PoC or GTFO. Every technique page should give you something you can run right now. Theory belongs in a textbook.
Chain thinking. A single medium is fine. Two mediums chained into a critical is a career. Every time you find something, ask what it lets you reach next.
The report is the product. You don't get paid for finding bugs. You get paid for convincing triage that what you found matters. Excellent findings get closed as informational when the report is two sentences and a screenshot.
Tags
Pages are tagged by difficulty, severity potential, and attack surface. Contributions and feedback welcome.
About
I'm Griffin, an information security engineer and penetration tester. Over a decade in consulting, pentesting, red teaming, and bug bounty.
I've reported high-risk vulnerabilities to Google, Microsoft, Apple, Anthropic, Oracle, United Airlines, the U.S. Department of Defense, Yahoo, Riot Games, Red Hat, and F5. Top reporter for web application vulnerabilities at Mozilla since 2013.
I was one of the first to document subdomain takeover risks through dangling CNAME records pointing to deprovisioned services like Heroku, GitHub Pages, and AWS CloudFront.
I also co-founded the first multinational bank bug bounty program in the United States, which gave me a perspective most researchers never get: what the program side looks like from the inside.
This playbook is the methodology I actually use, not the one I'd put in a slide deck.
Find me on X/Twitter.