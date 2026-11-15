# Time-Boxed Hunting

> tags: methodology, intermediate

> related: Methodology/Target-Selection, Methodology/Chain-Thinking

Time-Boxed Hunting
Unstructured hunting sessions feel productive and produce almost nothing.
You open Burp, click around for a bit, run some tools, chase an interesting thread for 45 minutes that turns into nothing, realize you've been on this one subdomain for two hours, and call it a night. You covered a lot of ground in a way that's completely impossible to reproduce or build on.
Time-boxing isn't about being mechanical. It's about having enough structure that you can actually measure what you're doing and improve it.
The 20-Minute Rule
If you haven't found anything interesting in 20 minutes on an asset, move to the next one.
"Interesting" doesn't mean a confirmed vulnerability. It means a behavior that you want to understand better - an unexpected response, an access control difference, a parameter that seems to affect something it shouldn't. If 20 minutes in you're looking at a completely unremarkable CRUD app with standard behavior and no anomalies, your time is better spent elsewhere.
This rule saves you from the sunk cost trap: "I've already spent an hour on this, I might as well keep going." No. An hour wasted plus another hour wasted is two hours wasted. Move.
Exception: if your recon flagged something specific about this asset - legacy tech, unusual behavior, a potential vulnerability class you want to confirm - the 20-minute rule doesn't apply. That's targeted investigation, not general coverage.
Time Allocation by Phase
Rough splits that I've found work. Adjust for target complexity.






























PhaseTime allocationNotesRecon & triage20–30%More on a fresh target, less on a target you've mapped beforeAsset investigation40–50%Structured exploration of prioritized assetsDeep dive on a finding20–30%Chain development, root cause, proof of conceptReporting10–15%Write while details are fresh
The numbers will drift. A live chain takes over. That's fine - that's the point. The structure keeps you from spending 80% of your session on recon and never testing anything.
Per-Asset Time Limits
Set a hard limit before you start each asset. Stick to it unless you find something.

Static content / marketing site: 5 minutes, look for upload functionality or interesting headers, move on
Standard CRUD web app: 20 minutes initial pass. If nothing surfaces, deprioritize.
SPA with rich API surface: 45 minutes minimum. JS analysis alone takes time.
Admin panel or internal tool: 30 minutes. High-value target, focused testing on auth and access control.
Staging / dev environment: 30 minutes. More permissive than prod. Check for debug modes, test credentials, verbose errors.
Something your recon flagged as unusual: No time limit - this is where the work is.

When to Pivot vs. Go Deeper
Pivoting is the right call when:

You've exhausted the obvious attack surface with no signals
You've been on the same theory for 30+ minutes with no progress
You're tired and forcing it - you're running payloads without thinking about what you expect to happen

Going deeper is the right call when:

You have a concrete anomaly you're trying to explain
You're one missing piece away from a complete chain
Your instinct says something is wrong even though you can't prove it yet (act on this judiciously - it's often right, but give yourself a time limit)

The mistake most people make is going deeper when they should pivot. That's how you spend four hours on a hunch that leads nowhere. Give the hunch 30 minutes. If you can't convert it to something concrete, note it and move on.
Session Planning
A session works best when you know what you're trying to accomplish before you open Burp.
Before each session, write down:

Which target or targets you're working on
Which assets are your priority (from your triage notes)
What you're specifically looking for  -  not "bugs" but "IDOR on the order management API" or "auth bypass on the admin panel I found last session"
Your session end time

Vague intent produces vague results. "I'm going to look for vulnerabilities" is not a plan. "I'm going to spend 45 minutes on the API endpoints I extracted from app.js yesterday, focusing on the /admin/ routes that shouldn't be accessible to my test user" is a plan.
Energy Management
Hunting is cognitively expensive. You don't have unlimited hours of high-quality attention.
High-focus work: business logic testing, auth flow analysis, chain development, manual source code review. Do this when you're fresh. Do not do this at midnight after a full workday.
Medium-focus work: content discovery analysis, reviewing recon output, reading new JS for endpoints, constructing PoCs for findings you've already identified.
Low-focus work: running automation, checking monitoring alerts, reviewing nuclei output, updating notes. Do this when you're tired.
If you try to do business logic testing when you're fried, you'll miss things that you'd catch in five minutes at peak focus. I've gone back to targets I "tested" during low-energy sessions and found obvious issues I completely overlooked. Now I don't test when I can't focus. I run tooling instead.
A Practical Session Structure
Here's a two-hour session structure for an active target I've already done initial recon on:
0:00 - 0:10  Review notes from last session. What did I leave unfinished?
             What anomalies did I flag but not follow up on?
 
0:10 - 0:30  Check for new recon output (new subdomains, config changes).
             Triage anything new. Add to priority list if warranted.
 
0:30 - 1:10  Targeted testing on the #1 priority asset or thread.
             Specific goal, time limit, clear success condition.
 
1:10 - 1:35  Second priority asset. If I got a finding in the first block,
             this slot becomes chain development instead.
 
1:35 - 1:55  Documentation. Update notes whether I found anything or not.
             Note what I tested, what I observed, what's left to explore.
 
1:55 - 2:00  Set up for next session. What's the #1 priority next time?
The documentation step isn't optional. I used to skip it when I didn't find anything ("nothing to write up"). Big mistake. Notes from unproductive sessions tell you where you've already been, which is valuable when you come back to a target in three weeks.
See Also

Target Selection
Chain Thinking
