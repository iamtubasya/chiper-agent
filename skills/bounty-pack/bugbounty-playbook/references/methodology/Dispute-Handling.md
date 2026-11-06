# Dispute Handling

> tags: methodology, intermediate

> related: Methodology/Post-Submission, Reporting/Severity-Escalation, Reporting/Impact-Statements

Dispute Handling
A valid report closed as N/A or duplicate isn't necessarily a final answer. How you handle the next ten minutes determines whether it stays closed.
Most disputes are lost not because the researcher was wrong, but because their response gave the triager no path to reverse the decision. You need to make it easy for them to say yes. That means understanding why they said no in the first place.
Common Triage Objections and What Actually Works
"We can't reproduce this."
This is almost never a lie. Triagers are working fast, their environment differs from yours, and reproduction steps that feel obvious to you are often missing a prerequisite. Don't argue. Reproduce it again yourself, record a video, and provide exact request/response pairs. Give them the Burp save file if the flow is complex. If you submitted a text description and they can't reproduce it, that's on the report, not on them.
"This is by design."
The hardest one. Sometimes they're right. If a feature allows users to see their own data in unexpected ways and that's the design intent, it's probably not a finding. But "by design" applied to a security boundary being crossable is worth pushing back on. Your counter-argument should be: "The design enables [user class X] to access [resource Y] belonging to [user class Z]. If the intent is to allow this, I'd expect the scope docs to say so, or a note in the product docs explaining the expected behaviour."
"The impact is insufficient."
They want severity criteria met. Your response is an impact clarification, not a resubmission. See below.
"Out of scope."
Read the scope doc before responding. If they're correct, accept it. If they've misread it, quote the relevant section and show the discrepancy directly. Don't say "I think this is in scope." Say "Section 3 of the scope doc lists *.api.example.com as in scope. The affected endpoint is payments.api.example.com, which matches that wildcard."
"This was already reported."
Ask when. If the other report was submitted after yours, request a timestamp check  -  HackerOne's duplicate logic is based on submission time. If it was submitted before yours, there's no argument to make. Move on.
The Impact Clarification Pattern
When a finding is marked N/A or downgraded because the triager didn't see the impact, the worst response is to re-explain the technical mechanics. They understood the mechanics. They didn't buy the impact.
The structure that works:

State what the attacker starts with (authentication state, account tier, external access only, etc.)
State what the vulnerability gives them that they didn't have
State what they can do with that access, in business terms
State who is affected and whether it's one user or many

For example, instead of "an attacker can modify the user_id parameter to access other users' data," write: "An unauthenticated attacker with network access can enumerate account IDs sequentially and retrieve the full profile of any registered user  -  name, billing address, and phone number  -  with a single GET request per account. No credentials or prior knowledge of the target required. At 10k requests per minute this covers the full user base in under two hours."
That's the same bug. The second version gives a triager everything they need to justify escalating severity internally.
Platform Mediation
Both HackerOne and Bugcrowd have formal dispute processes. Use them sparingly. They're for cases where you've already made your argument clearly, received a rejection, and believe the decision is genuinely wrong.
HackerOne mediation: Use the "Request mediation" option available after a report is marked resolved or N/A. HackerOne's mediation team  -  not the program  -  reviews the dispute. You'll need to summarise your position in a paragraph. They'll review both sides and make a recommendation. It's not binding on the program, but most programs follow it. Reserve this for cases involving $500+ at stake and a clear factual error.
Bugcrowd disputes: Submit through the program interface. Bugcrowd's ASE (Application Security Engineer) team reviews these. The process is similar. Response time varies.
Neither process is quick. Expect a week or more. During that time, don't send additional messages to the program about the same report. Let the process run.
Language Templates
The template that works isn't aggressive and isn't sycophantic. It's factual.
For an N/A you believe is wrong:

"Thanks for the review. I want to make sure I've communicated the impact clearly. [Impact clarification paragraph]. Happy to provide a screen recording demonstrating this end-to-end if that would help."

For a duplicate where you believe your report predates:

"Could you confirm the timestamp on the earlier report? My submission was at [time/date]. If mine predates the other, I'd appreciate a review of the timeline."

For a severity downgrade:

"I understand the concern about [their reasoning]. The CVSS vector I'd apply is [specific vector and score] because [brief justification]. Happy to walk through the scoring if it would help."

Never: "This is clearly valid," "Your triager is wrong," "I've seen this pay $X on other programs." None of that helps.
Documentation Habits That Protect You
Before you submit any report, your protection is your own records.

Take a timestamped screen recording of the full reproduction flow. Not just a static screenshot  -  a recording that shows the request being made and the response returning. Tools like OBS or Loom work fine.
Save your Burp project file for any non-trivial report.
Save the full HTTP request and response as a text file, separate from the Burp project.
Note the exact time of submission. Platform UIs sometimes show local time; convert to UTC and record it.

If a duplicate dispute comes down to timestamps, you want your own records, not just the platform's. Platforms have made timestamp errors before.
When to Walk Away
Not every reversible decision is worth reversing.
Walk away when:

You've made your case once clearly and the program has acknowledged your argument but disagrees
The payout difference is under $200 and the dispute has already taken two hours
The program has a consistent pattern of low N/A rates with no reversals  -  the culture there doesn't support it
You've used platform mediation and it went against you
The disagreement is about subjective severity criteria, not a factual error

Some programs are simply not good operators. A program that N/As valid reports and never reverses is telling you something. The cost isn't just this dispute  -  it's the ongoing expected value of hunting on that program. That number might be low enough that you should deprioritise them entirely.
Signal and Reputation Considerations
On HackerOne, frequent disputes that go nowhere don't help your signal score. Triagers on well-run programs talk to each other. A researcher who sends five frustrated follow-ups on every closed report develops a reputation that affects how their next report is read before anyone opens it.
This isn't an argument to accept bad decisions quietly. It's an argument to make one excellent case, clearly and calmly, then stop. One well-structured dispute response will do more for your reputation than ten increasingly frustrated messages, regardless of who was technically right.
The triager reading your report has seen 50 reports today. Many of them were garbage. A dispute response that arrives well-structured, evidence-first, and free of ego makes you stand out immediately  -  and makes it easy for them to forward your argument internally.
See Also

Post-Submission Workflow
Severity Escalation
Impact Statements That Pay
