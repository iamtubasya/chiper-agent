# Specialising

> tags: methodology, intermediate, advanced

> related: Methodology/Target-Selection, Methodology/Time-Boxing, Business-of-Bounties/Career-Strategy

Specialising
The researchers consistently finding critical bugs on competitive programmes aren't better at everything. They're much better at one or two things.
The generalist path feels safer early on. You can test web, do some mobile, dabble in API security, run a few cloud misconfig checks. You'll find things  -  especially at the beginning when basic IDOR and XSS work appears on almost every target. Then the programmes you're on fill up with other researchers, your duplicate rate climbs, and your finding rate on the same surface plateaus. That's the generalist trap.
Why Generalising Hurts at Scale
High-competition programmes  -  the ones with large public researcher pools and well-publicised bounty tables  -  have been tested extensively across the common web vulnerability classes. The low-hanging fruit was found years ago. What remains takes either deep knowledge of a specific attack surface or access to newer, less-tested areas.
When you know 80% of every surface, you're competing with every other researcher who knows 80% of every surface. The duplicate rate on straightforward web findings on a mature programme can exceed 60%. That's not a skill problem. It's a competition problem.
The surfaces with better competition-to-reward ratios currently: cloud infrastructure and IAM, CI/CD pipeline security, mobile (particularly Android deep link abuse and iOS entitlement issues), and AI/LLM injection surfaces. Web2 application testing at the generic level is the most crowded. It's not going to get less crowded.
Testing a Potential Specialisation
Before committing months to a new area, spend 30 days on a focused experiment.
Pick one attack surface you don't know well but find interesting. Spend those 30 days reading every public resource you can find: CVE analyses, researcher writeups, conference papers, tool documentation. Then spend the second half of the 30 days testing programmes that have that surface in scope, specifically targeting it.
Signals that the experiment is going well:

You're finding novel behaviours within the first two weeks of testing
Your questions are getting more specific  -  you're not asking "how does SAML work" but "why does this specific implementation skip the InResponseTo check"
You're starting to see the same patterns across different programmes, which means you're building transferable knowledge, not just lucky once

Signals to try something else:

You've read everything and still feel like you're pattern-matching without understanding the underlying mechanics
The surface feels like a chore rather than a problem you want to solve
Finding rates in the 30-day window are zero or near-zero

Interests matter more than the competition-to-reward analysis. A surface you find genuinely interesting will hold your attention through months of zero findings. A surface you picked only because someone said it pays well won't.
Signals You've Found Your Niche
You know a specialisation is working when:

Your finding rate on the target surface is meaningfully above your historical average
Your impact statements get shorter because you don't need to explain the vulnerability class, just the specific instance
Reports in your niche resolve faster because triagers recognise the vulnerability pattern and your ability to describe it clearly
You're finding issues other researchers missed on the same target, not because you got lucky but because you know where to look

That last one is the clearest signal. When you start finding bugs on assets other researchers have tested and cleared, you're operating at a level of specificity they weren't.
Narrow-Niche Examples
The narrower the niche, the better the economics tend to be. Some examples of researchers who have gone deep on a single surface:
SAML only. SAML is used everywhere in enterprise SSO and has a consistent class of implementation bugs  -  XML signature wrapping, InResponseTo replay, audience restriction bypass. A researcher who deeply understands SAML can move through enterprise programme SSO implementations quickly and find issues that generic application testers miss entirely.
WebAuthn / FIDO2. Adoption is growing, implementation quality varies enormously, and very few researchers understand the specification well enough to test it properly. The barrier to entry is high. So is the expected payout.
Snowflake and data warehouse security. Misconfigured Snowflake instances, insecure data shares, and privilege escalation via ACCOUNTADMIN roles show up on cloud-focused programmes and in direct disclosure. Few researchers have deep warehouse security knowledge.
Kubernetes admission controllers. RBAC misconfigurations, webhook bypass, and namespace isolation failures on Kubernetes clusters appear in cloud infrastructure programmes. Deep knowledge here pairs well with any programme that runs containerised infrastructure.
The pattern: find a surface where the specification is complex, adoption is growing, and researcher coverage is thin. That combination produces the best finding rates.
Building Public Reputation in a Niche
Depth without visibility doesn't compound as fast as depth with visibility.
Write about what you find  -  not just the findings, but the methodology. A post explaining how you approach SAML testing step by step does more for your reputation than a tweet saying you found a SAML bug. Researchers, programme managers, and employers read the methodology posts. They use them to calibrate how sophisticated your understanding is.
Conference talks in a niche work well because the CFP pool for highly specific topics is small. A "SAML implementation errors I've found in 2025" talk will get through a BSides CFP more reliably than a generic application security methodology talk. You have something specific to say and a small number of people saying the same thing.
Disclosed reports are your most credible portfolio. When you can link to programme-disclosed findings on HackerOne or Bugcrowd, any reader can see the scope, the severity, and the validation. Ten disclosed findings in a single niche is more convincing than fifty generic web bugs.
When to Pivot
Specialising too long in a declining surface has real costs.
Signals it's time to move:

Payout levels for the vulnerability class are dropping (programmes are patching the common patterns, bounty tables are being revised down)
You're experiencing the same findings repeatedly with no escalation path  -  every SAML bug you find is a low-impact ACS URL manipulation, never a full account takeover
The platforms are seeing fewer programmes with that surface in scope
You've been working the same niche for two or more years without finding anything new to say about it

Pivoting doesn't mean starting from zero. The skills transfer. A researcher who deeply understands XML parsing quirks for SAML will adapt quickly to understanding JSON handling in JWT implementations. The mental model for "how does this parser differ from the specification" is the same.
See Also

Target Selection
Time-Boxed Hunting
Career Strategy
