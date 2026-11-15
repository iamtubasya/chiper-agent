# Post-Submission Workflow

> tags: methodology, intermediate

> related: Reporting/Severity-Escalation, Reporting/

Post-Submission Workflow
You hit submit. Now you wait. Except you don't just wait - you manage the process.
Most hunters treat submission as the endpoint. The report goes in, the payout comes out (maybe), and they move on. That's leaving significant value on the table. How you handle the post-submission phase affects your payout rate, your relationships with programs, and your reputation on the platform.
Triage Timelines  -  What's Normal
Expectations vary by platform and program. If you don't know what normal looks like, you'll either panic too early or let a legitimate issue sit dormant too long.








































Platform / contextTypical first responseTypical resolutionHackerOne top-tier programs3–7 days2–6 weeksHackerOne mid-tier / newer programs1–3 weeks4–12 weeksBugcrowd managed programs1–2 weeks4–8 weeksIntigriti5–10 days3–8 weeksDirect (company-run) programsWildly variableWildly variableNew program, first 30 daysOften faster  -  they're watchingFaster if they're engaged
These are rough numbers. Programs with active managers who are in the platform daily can turnaround in 48 hours. Programs where the security team gets to the queue once a week can take a month just for triage acknowledgment.
If a critical has been sitting without any response for 3+ weeks, it's appropriate to send a polite nudge. Not a demand - a nudge. "Just following up on this submission, happy to provide additional evidence or clarification if helpful."
Responding to Triage Questions
Triagers will ask for clarification. This is a good sign - it means they're actually reviewing your report, not auto-closing it.
Common triage questions and how to handle them:
"Can you confirm your test account?"
Tell them. Always. Some programs need to verify you only touched your own data or that the affected endpoint was indeed reachable from your account tier. Have your test account credentials or identifiers ready.
"We can't reproduce this. Can you provide more detail?"
Don't get frustrated - get specific. Walk through the exact steps again, include your exact payload, and attach a screen recording if the flow is at all complex. The goal is to make reproduction so easy they'd have to actively try to fail.
"What's the impact here?"
This means your impact section wasn't convincing. Write a concise, specific paragraph about what an attacker achieves. Avoid generic phrases like "could lead to data compromise." Say: "an authenticated attacker in the free tier can read the private documents of any paying customer by changing the doc_id parameter, with no other prerequisites." Specific, concrete, quantifiable.
"We consider this to be low severity because [X]."
This is an opening, not a final decision. Respond with your reasoning, calmly and factually. More on this below.
Handling N/A Decisions
N/A (Not Applicable) means they don't consider it a valid finding. This can be:

Genuinely out of scope  -  accept it and move on
Misunderstood  -  your report wasn't clear enough about the vulnerability class or impact
Wrong  -  they're incorrect, and you need to explain why

For #2: rewrite your summary and impact section in your response. Don't argue. Clarify. Assume good faith - triagers process huge volumes and misreadings happen.
For #3: be precise about why their reasoning is incorrect. If they said "this requires authentication" and you demonstrated it doesn't, show the unauthenticated request. If they said "this is by design," explain why the design enables user harm. Reference OWASP or CVSSv3 if it helps frame the issue.
Accept that some N/A decisions are final even when you're right. Platforms have processes, and pushing too hard or too many times flags you as difficult to work with. If you're confident the decision is wrong and you've made your case once clearly, escalate via the platform's dispute mechanism - don't just send increasingly frustrated follow-up messages.
Handling Duplicates
Duplicates hurt. There's not much to say here except: move faster on your next submission.
A few things worth knowing:

On HackerOne, if you can demonstrate you found the vulnerability independently and your report is clearly superior, you can sometimes get a partial payout or at least a reputation point
The duplicate might not have been fully patched yet - you can submit your findings as an additional report noting the partial fix or bypasses
The duplicate timestamp is based on when the other report was submitted, not when it was triaged - even if it was sitting unread for weeks, the timestamp is what matters

Handling Severity Downgrades
Programs downgrade severity for two reasons: they're wrong, or the CVSS calculation actually does produce a lower score when you factor in their specific deployment context.
If they downgraded because the vulnerability requires user interaction, a non-default configuration, or other environmental factors that don't exist on their specific instance - that's legitimate. Their environment changes the effective severity.
If they downgraded because they don't understand the impact, that's worth pushing back on. Use Severity Escalation as your framework. Be specific about the CVSS vectors you believe apply, and explain why. Give them a path to agreement.
When to Push Back vs. Accept
Push back when:

You have evidence they've misunderstood the vulnerability or the impact
The downgrade contradicts the CVSS scoring framework they claim to follow
The N/A is based on a factual error you can disprove

Accept when:

You've made your case once and they've acknowledged it but disagree
Their reasoning is legitimate even if you don't prefer it
The program has a track record of fair dealing and this is an isolated disagreement
The difference in payout is small and the relationship is worth more than the argument

One well-reasoned response is usually the right amount. Two if the first response introduces new information. Three or more and you're grinding away goodwill for diminishing returns.
Retesting After Fixes
When a program fixes your finding and asks you to retest, do it promptly. This is a positive signal - programs that retest properly have better security cultures and are worth maintaining a relationship with.
Don't just test the exact payload you submitted. Test variations. The fix might have addressed the specific parameter you hit while leaving the root cause in place. Finding a bypass during retest is a new finding - you can submit it, and it'll be fast-tracked because the triager already has context.
Building Relationships With Triage Teams
The researchers who get fast triage, accurate severity assessments, and benefit of the doubt on borderline cases aren't necessarily the best technically. They're the ones triage teams trust.
Trust comes from:

Clear, reproducible reports that make the triager's job easy
Professional, measured responses when there's disagreement
Not crying wolf on every edge case or theoretical finding
Following through on retests and responding to questions promptly
Being human in your communications  -  a brief thank-you when something gets triaged well costs you nothing

Some programs have the same two or three people reading every report. They remember researchers by name. Be the researcher they're glad to see a new submission from.
See Also

Severity Escalation
Reporting
