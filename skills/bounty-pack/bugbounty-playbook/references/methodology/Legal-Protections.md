# Legal Protections

> tags: methodology, intermediate, advanced

> related: Methodology/Scoping, Programs/Selection/Reading-Scope

Legal Protections
This is not legal advice. It's a researcher's map of where the legal risks actually live, because the consequences of getting this wrong are not a rejected report  -  they're criminal charges.
Treat this page as orientation, not authorisation. If you're in any of the situations described in the final section, talk to a lawyer.
The CFAA  -  The US Federal Risk
The Computer Fraud and Abuse Act is a 1986 law that has been used, occasionally, against security researchers. The core offence is accessing a computer "without authorisation" or "exceeding authorised access." Both terms are famously vague.
The key case history for researchers: Van Buren v. United States (2021). The Supreme Court held that the "exceeds authorised access" clause applies to accessing information you aren't permitted to access, not to using otherwise-authorised access for a bad purpose. This narrowed the CFAA slightly. It didn't eliminate the risk of "without authorisation" charges for testing systems you have no account on.
In 2022, the DOJ updated its charging policy to say it would not prosecute good-faith security research under the CFAA. The exact language: "the policy focuses the Department's resources on cases of intentional criminal conduct, not good-faith security research." That policy is meaningful but it is not a legal defence. A change in administration, a change in policy, or a determined prosecutor in a district that disagrees can still bring charges. The DOJ policy is guidance, not statute.
Good-faith markers that the policy and courts look for: you stayed within the scope of the disclosure programme, you reported the vulnerability rather than exploiting it for gain, you did not access real user data beyond what was necessary to demonstrate the issue, and you acted promptly after discovery.
Safe Harbour Clauses  -  What They Actually Mean
Standard HackerOne programme language grants participating researchers a safe harbour: the company commits not to initiate legal action against researchers who act in good faith and stay within the programme's stated scope. Bugcrowd's standard terms are similar.
What "good faith" means in practice on these platforms:

You used test accounts, not production accounts belonging to real users
You did not exfiltrate, retain, or share data beyond what was needed for your report
You reported the issue rather than exploiting it
You stayed within the scope document

Safe harbour is a contractual promise, not a statutory immunity. If you break the conditions, the safe harbour dissolves. If the company decides to violate their own terms and sue anyway, you'd need to argue the contract in civil court before you could even reach the safe harbour question.
Programmes without a safe harbour clause have made no promise. Some are genuine oversights  -  small companies that copied a bare-bones disclosure form. Some are deliberate. Either way, the absence of safe harbour means you're relying on prosecutorial discretion alone if something goes wrong. Factor that into which programmes you work on.
disclose.io
disclose.io is a non-profit framework for standardised safe harbour language. Programmes that adopt the disclose.io terms use one of several tiers, with the "full safe harbour" tier providing the strongest researcher protections. The framework has been adopted by hundreds of programmes including major platforms and enterprise programmes.
The practical value: when you see a disclose.io badge on a programme, you know the safe harbour language has been reviewed against a known standard. That's more meaningful than programme-specific language you'd need to evaluate yourself.
Check disclose.io/policylist to see which programmes have adopted it.
Computer Misuse Act  -  UK Researchers
If you're based in the UK, the Computer Misuse Act 1990 is the relevant statute. The core offences are similar to the CFAA: unauthorised access to computer material (s.1), access with intent to commit further offences (s.2), and unauthorised modification of computer material (s.3).
The UK does not have an equivalent to the DOJ's 2022 policy. There has been ongoing advocacy from the UK security community for reform and a formal safe harbour for good-faith researchers, but as of 2026 no statutory change has been made. You are relying on programme safe harbour language and the Crown Prosecution Service's charging discretion.
The practical implication for UK researchers: treat out-of-scope testing even more conservatively than your US counterparts. The legal backstop is narrower.
EU Landscape
The EU does not have a single equivalent to the CFAA. Member states have their own computer crime laws, harmonised (partially) by the Directive on Attacks Against Information Systems (2013). National implementations vary.
Two regulatory developments are worth knowing about:
GDPR. If your testing inadvertently accesses real personal data, you may be touching GDPR obligations. Accessing another user's personal data in the course of demonstrating an IDOR, even with no intent to retain it, puts you in complicated territory. Some EU programmes explicitly address this in their scope docs; many don't. The safest position: stop at proof of access, don't pull actual personal data, and document that you stopped.
NIS2 (2022). The Network and Information Security Directive 2 increases mandatory breach notification requirements for certain sectors across EU member states. If your testing accidentally causes a disruption to a NIS2-covered entity, that programme may have regulatory reporting obligations. Not a direct legal risk to you in most cases, but it affects how programmes respond to certain findings.
What Triggers Criminal Referral
Programmes don't usually call law enforcement over a well-scoped vulnerability report. The pattern that does trigger referrals:

Mass automated scanning against out-of-scope assets or with high request volumes that affect production availability
Data exfiltration  -  downloading large volumes of user records, even to "prove" the vulnerability. This is the single biggest trigger. You don't need more than one record to prove an IDOR.
Testing secondary targets  -  using access to the in-scope app to pivot into adjacent infrastructure (cloud environments, partner systems, internal tools on a different domain)
Social engineering or physical access without explicit programme permission
Returning after a N/A or out-of-scope close to test the same asset again

Even within a programme with safe harbour, these behaviours void the protections.
Staying on the Right Side
Test accounts: always use test accounts you control. Create them fresh for each programme if the programme allows self-registration. If the programme requires special test accounts, ask for them through the programme messaging before you test anything that requires account access.
Data access: stop at the minimum necessary to establish the vulnerability. One account's data to prove an IDOR. One file's metadata to prove path traversal. The moment you start pulling data beyond proof-of-concept, your risk profile changes.
Scope boundaries: if an asset is ambiguous, ask before you touch it. Document that you asked and what you were told. This creates a record that you were acting in good faith on the programme's guidance.
Rate limiting: don't run tooling in a way that affects service availability. Throttle automated scanning. If a programme says "no automated testing," follow it.
When to Talk to a Lawyer

Any programme that has no safe harbour clause and you're about to test something significant
Any finding that involves real user data you've accidentally accessed
Any approach from law enforcement  -  even a polite inquiry  -  about your security research activities
Any situation where a company has sent you a cease-and-desist or threatened legal action
Any testing you've done that you're unsure was within scope

The cost of a one-hour consultation with a lawyer who understands computer crime law is trivial compared to the cost of the alternative. Don't wait until you need it urgently.
See Also

Scoping & Rules of Engagement
Reading Scope Documents
