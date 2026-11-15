# Scoping & Rules of Engagement

> tags: methodology, beginner, intermediate

> related: Methodology/Target-Selection, Programs/Selection/Reading-Scope

Scoping & Rules of Engagement
Scope documents are contracts. Read them like one.
Most hunters skim the scope section, note which domains are listed, and start firing tools. Then they submit a finding on api-internal.example.com and get an immediate "out of scope" close - something that would've been obvious if they'd read past the first bullet point. Don't be that hunter.
The Core Mindset
You're looking for two things when you read a scope doc: what's explicitly in, and what's explicitly out. Everything in the gray zone between those two is where you need to slow down and think before you touch anything.
In scope is not the same as "fair game." Some programs list assets as in-scope but include carve-outs that gut the actual attack surface. Some programs have blanket out-of-scope clauses that apply across all their programs company-wide, not just the one you're reading.
Wildcard Scopes  -  What They Actually Mean
*.example.com looks like a gift. It isn't always.
Read the exclusions section. Almost every wildcard scope has follow-on language that modifies it:





























What it saysWhat it means*.example.comAll subdomains, including nested ones like a.b.example.com  -  unless exclusions say otherwise*.example.com excluding admin.example.comEverything except that one subdomain  -  don't test it, don't pass traffic through it*.example.com (owned and operated assets only)Third-party services on subdomains  -  Zendesk, Intercom, Salesforce  -  are not in scope even if they're on the domainapp.example.com and related subdomainsOnly what the program defines as "related"  -  ambiguous, and you should ask*.example.com (US users only)If you test from a non-US IP or against data belonging to non-US users, you may be outside scope
That last one trips people up more than any other. Geographic scope restrictions exist and they're serious.
Common Exclusions That Bite People
Third-party services. If help.example.com is a CNAME to Zendesk, and Zendesk is run by Zendesk, any vulnerability there is Zendesk's problem - not example.com's. Sending a Zendesk RCE to a program that uses Zendesk will get you an immediate close. The scope almost always says "owned and operated infrastructure only" somewhere, often buried.
"Do not perform automated scanning." This one varies wildly. Some programs mean "don't run Burp active scan." Some mean "don't use any tools that generate more than N requests per second." Some mean literally no automation at all. When a program says this and you're unsure, ask. Or be conservative.
Social engineering and phishing. Almost universally out of scope. Even on programs with wide technical scope. Don't test it unless the scope doc affirmatively says it's allowed.
Production data. Some programs explicitly prohibit accessing, downloading, or using real user data - even if an IDOR lets you. You can demonstrate the issue with your own test account data, but pulling actual production records, even to prove impact, can get you banned from the platform and potentially in legal trouble.
DoS/DDoS. Always assume this is out of scope unless explicitly permitted. And even if it's in scope, don't run a denial test against production.
Safe Harbor Language
Look for it. If it isn't there, that's a signal.
Good safe harbor language will say something like: the company won't initiate legal action against researchers who follow responsible disclosure guidelines and stay within scope. It should be explicit, not implied.
Vague language like "we appreciate researchers who report issues responsibly" isn't safe harbor. It's PR copy. It won't protect you if something goes sideways and the company decides to get aggressive.
If a program has no safe harbor language, the program hasn't made an explicit legal commitment. That doesn't mean you can't participate - but it means the risk profile is different. Know that going in.
When Scope Is Ambiguous
You have three choices: skip it, ask, or make a conservative call.
Skipping is often the right answer. If an asset feels borderline, there are probably 50 unambiguously in-scope things you haven't tested yet. Borderline assets also tend to produce findings that get closed on technicalities.
Asking works on programs with active program managers. Use the program's messaging feature. Keep it short: "Is staging.example.com considered in scope under the *.example.com wildcard?" You'll either get confirmation or clarification. Either way you're protected.
Making a conservative call means: if you can't tell whether something is in scope, act as if it isn't. This is the right answer when the program is unresponsive and the asset is genuinely ambiguous. Document your reasoning.
Tricky Scope Language  -  Worked Examples
"All externally-facing assets owned by ExampleCorp."
This is a wide statement but it has an implicit limit - you need to verify ownership. An IP that resolves to an ExampleCorp hostname but is actually operated by their AWS partner org isn't necessarily in scope. Verify before you go deep.
"Severity-based scope: only critical and high vulnerabilities are eligible for bounty."
This doesn't mean lows and mediums are out of scope. It means they're in scope but won't pay. You can still report them for recognition, or if you need to demonstrate a chain. Read this as a bounty limitation, not a testing restriction.
"The following assets are out of scope unless the identified vulnerability meets our critical criteria."
Unusual language. This is a conditional in-scope - the asset is out of scope by default, but if you find something critical on it, you can submit. Handle this carefully: you need to confirm criticality before touching the asset deeply, which is difficult to do without testing it. When in doubt, ask.
"Legacy applications may be in scope but won't receive bounty."
Classic hedge. They want the intel but don't want to pay for it. Your call whether that's worth your time.
See Also

Target Selection
Reading Scope Documents
