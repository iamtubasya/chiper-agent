# Methodology

> tags: methodology, beginner, intermediate

> related: Methodology/Target-Selection, Methodology/Scoping, Methodology/Recon-Driven-Hunting, Methodology/Time-Boxing, Methodology/Chain-Thinking, Methodology/Post-Submission, Methodology/Dispute-Handling, Methodology/Legal-Protections, Methodology/Specializing

Methodology
Most hunters don't have a methodology. They pick a target, open Burp, click around for an hour, fire some payloads at whatever input they find first, get bored, move on. Then wonder why they're not finding anything.
Having a repeatable process doesn't make hunting boring. It just means you stop wasting the first two hours of every session doing the same recon you already did last week.
The Workflow
flowchart TD
    A["Target Selection"] --> B["Scope Analysis"]
    B --> C["Recon"]
    C --> D{"New assets?"}
    D -->|Yes| E["Asset Triage"]
    D -->|No| F["Broaden recon or rotate"]
    E --> G["Targeted Testing"]
    G --> H{"Finding?"}
    H -->|Yes| I{"Chainable?"}
    H -->|No| J["Switch vuln class or asset"]
    I -->|Yes| K["Chain Development"]
    I -->|No| L["Report and Submit"]
    K --> L
    J --> G
    L --> M["Post-Submission"]
    M --> C

This isn't linear in practice. You'll bounce between recon and testing constantly. New JS endpoints show up while you're testing auth flows. A 403 on one path sends you back to content discovery with a different wordlist. The diagram shows the phases, not a rigid sequence.
Sections
Target Selection
How to pick programs that are worth your time. The highest bounty table doesn't mean the highest expected payout.
Scoping & Rules of Engagement
Scope docs are contracts. Misread one and your valid critical becomes an out-of-scope DQ, or worse, a legal problem.
Recon-Driven Hunting
Let your recon output dictate your attack path instead of defaulting to "open the login page and try SQLi."
Time-Boxed Hunting
Structured sessions with clear objectives. How long to spend, when to pivot, when to walk away.
Chain Thinking
The mental model that turns medium-severity findings into critical payouts.
Post-Submission Workflow
What happens after you hit submit. Triage response, follow-ups, retests, and when to push back.
Dispute Handling
What to do when a valid report is closed as N/A or duplicate. Counter-arguments, impact clarification patterns, platform mediation, and when to walk away.
Legal Protections
The legal landscape for bug bounty research: CFAA, DOJ good-faith policy, safe harbour clauses, the Computer Misuse Act, and what actually triggers criminal referral.
Specialising
When and how to pick a niche. The generalist trap, competition-to-reward ratios by surface, how to test a potential specialisation, and when to pivot.