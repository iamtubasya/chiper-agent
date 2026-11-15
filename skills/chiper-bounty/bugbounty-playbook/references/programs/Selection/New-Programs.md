# New Programs

> tags: programs, methodology

> related: Recon, Programs/Selection/Competition-Assessment, Programs/Selection/Payout-Analysis, Programs/Selection/Reading-Scope, Programs/Platforms/HackerOne

New Program Strategy
When a new bug bounty program launches, there's a window where the return on time invested is dramatically higher than any other point in the program's lifecycle. The first 48 hours are often the highest-value window you'll ever have on that target. You need a plan before the program launches, not after.

Why the First 48 Hours Matter
A new program means an uncovered attack surface. No researcher has run recon on it. No one has tested the authentication flow. The low-hanging fruit, the obvious IDOR patterns, the predictable admin endpoints - all of it is still there.
By day 7, the obvious stuff is gone. By day 30, the medium-difficulty stuff is gone. By day 90, you're competing with researchers who have three months of context on the application. You're still building that context.
The opportunity cost of missing the launch window is real. Being second by a few hours on a critical finding means a duplicate notification instead of a bounty.

Setting Up Launch Alerts
You need to know about new programs before most other researchers do:

H1: Follow the H1 Twitter/X account and enable notifications. New public programs are announced.
Bugcrowd: Similar, plus their newsletter.
Intigriti: Their platform announces new programs; follow their social channels.
Platform RSS/API: Some researchers build automation to watch for new program announcements. If you're comfortable with a bit of scripting, H1 has a GraphQL API and program listings pages you can monitor.
Community channels: Discord servers and Slack communities focused on bug bounty often have channels dedicated to new program announcements. Be in them.

The goal is to know within an hour of launch. The difference between knowing at launch versus knowing 12 hours later is significant on a competitive program.

What to Prioritize in the First Hours
Speed matters, but not at the cost of accuracy. A duplicate is worse than being slow. Here's the triage order:
graph TD
    A[Program launches] --> B[Read full scope doc: 15 min]
    B --> C[Enumerate primary targets: 30 min]
    C --> D{Quick wins first}
    D --> E[Auth: registration, login, password reset]
    D --> F[IDOR: any object ID in URL/API]
    D --> G[Obvious injection points]
    E & F & G --> H{Found something?}
    H -->|Yes| I[Write and submit immediately]
    H -->|No| J[Deeper recon and enumeration]
    I --> J

Authentication flows first: Password reset vulnerabilities, registration logic flaws, and login bypass are often implemented quickly and checked less rigorously than core features. Test these before anything else.
IDOR on primary objects: Whatever the application's primary object is (user profiles, orders, projects, documents), test whether you can access other users' objects by manipulating IDs. These are often present from day one because access control isn't the first thing developers think about.
Obvious injection surfaces: Search boxes, filter parameters, anything that accepts user input and might hit a database.

Speed vs Depth Tradeoff
In the first 48 hours, optimize for speed on surface-level attacks. You're sweeping for obvious vulnerabilities, not doing deep application logic analysis. Save the logic flaws and complex chains for week two and three when the competition thins out.
The mindset shift: in the first 48 hours, you're asking "what didn't they check before launch?" In weeks two through four, you're asking "what requires understanding the application deeply?" Different questions, different approaches.
Don't skip writing good reports in the rush. A sloppy report on a valid finding gets triaged slowly, sometimes incorrectly. Take 20 minutes to write a proper report. Losing 20 minutes to thorough documentation is much better than having a valid finding triaged as informational because you rushed the write-up.

Recon at Launch
On a new program, your initial recon should be fast but structured:

Subdomain enumeration: Run passive recon immediately. New programs often have dev/staging subdomains that haven't been secured yet.
Asset fingerprinting: What tech stack? What third-party services? New programs sometimes have default configurations in place.
API discovery: Spider the main application for API endpoints. New programs often haven't cleaned up debug or legacy endpoints.
JavaScript review: Frontend JS often reveals internal API routes, access tokens, and application logic that isn't visible from the UI alone.

For tooling, see Recon notes on subdomain enumeration and JS analysis.

The Late Starter Adjustment
If you miss the first 48 hours, adjust strategy. By the end of the first week:

Don't compete on surface-level bugs. They're gone or being duplicated.
Pivot to application logic: complex workflows, multi-step processes, role interactions.
Look at what other researchers have disclosed from previous programs this company ran (or similar companies).
Find the features that require domain knowledge to understand. Those are still available.

The window closes but it doesn't slam shut. Programs launched a month ago still have undiscovered vulnerabilities. They just require more skill and effort to find.

Private Program Launches
When you get invited to a private program launch (or when a new private program appears in your available programs list), the same 48-hour principle applies with a smaller competition pool. If you're one of 50 invited researchers instead of competing with the entire platform, the window is still valuable but less panicked.
Prioritize these over public launches if you have to choose. Less competition and the same fresh attack surface.

Related

Competition Assessment
Payout Analysis
Reading Scope
HackerOne
