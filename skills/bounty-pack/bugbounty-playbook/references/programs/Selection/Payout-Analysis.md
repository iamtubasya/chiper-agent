# Payout Analysis

> tags: programs, methodology

> related: Programs/Selection/Competition-Assessment, Programs/Platforms/HackerOne, Programs/Platforms/Bugcrowd, Programs/Selection/New-Programs

Payout Analysis
The highest bounty table on the platform is not the highest expected payout per hour. Confusing these is one of the most common mistakes researchers make when picking programs. Let's break down what the numbers actually mean.

The Difference Between Maximum Payout and Expected Value
A program that pays $50,000 for critical findings sounds amazing. A program that pays $5,000 for critical findings sounds less impressive. But if the $50K program has 500 active researchers, a mature attack surface with most surface-level bugs long gone, and a triage team that downgrades aggressively, your expected hourly rate on that program might be $0.
Expected value per hour is what you're actually optimizing for. It's a function of:

Probability of finding a valid bug in a given time window
Probability that valid bug achieves your target severity
Bounty amount at that severity
Time to payout


Reading the Bounty Table
Bounty tables have a few things to pay attention to beyond the max:
Minimum payout: Programs that start at $50 for low/medium are telling you something about how they value research time. Programs that start at $200+ treat researchers more like professionals.
Critical/high ratio: If critical pays $20,000 but high pays $500, there's a cliff. That's a sign the program is hoping for unicorn bugs without valuing the solid work in between. The best programs have bounty tables where the ratio between tiers is reasonable (usually 2-5x between adjacent tiers).
Payout ranges vs fixed amounts: "Up to $10,000" is a red flag compared to "$5,000-$10,000." The word "up to" means they can pay $100 and technically honor the table. Fixed ranges are more honest.
"Determined at discretion": Walk away. Or at minimum, check disclosed reports to see what they actually paid versus what the table implies.

Using Platform Statistics
H1, Bugcrowd, and Intigriti all expose program statistics. Here's how to use them:
flowchart TD
    A["Program Stats"] --> B["Total reports resolved"]
    A --> C["Median time to bounty"]
    A --> D["Response rate %"]
    A --> E["Researcher thank count"]
    B --> F{"High = mature, Low = fresh"}
    C --> G{"Low days = good, High = slow"}
    D --> H{"Below 85% = warning sign"}
    E --> I{"Proxy for competition level"}

Total resolved reports: A program with 3,000 resolved reports has had a lot of eyes on it. The easy stuff is gone. You need more sophisticated approaches. A program with 50 resolved reports is comparatively fresh.
Median time to bounty: This is the payout cycle. A 30-day median means you get paid in about a month. A 180-day median means your capital is tied up for six months, which affects your effective hourly rate.
Researcher thank count: Rough proxy for how many unique researchers have found valid bugs. More researchers means more competition. This isn't the same as how many researchers are actively testing right now, but it's a reasonable signal.

Historical Payout Data
Disclosed reports on H1 and Bugcrowd often include the bounty amount. This is more reliable than the bounty table for predicting what you'll actually get, because it reflects how the program interprets their own table in practice.
Find disclosed reports in the same severity range as your target finding. If a program's table says $1,000-$3,000 for high, but every disclosed high you can find paid exactly $1,000, that's useful calibration.
Some programs have a pattern of paying minimums consistently. Others pay at the high end for well-written reports with strong impact statements. Both patterns are real and useful to know before you invest time.

The Time-to-Payout Factor
Bounty dollars aren't fungible across programs because of time delays. $1,000 paid in 15 days is worth more to your hourly rate than $1,500 paid in 120 days, because the latter ties up the hours you already spent.
If you're comparing two programs with similar expected bounties, the faster-paying one is more valuable. Check median time to bounty in program stats.

Low vs High Volume Programs
Two different strategies, both valid:
High-volume, lower-payout approach: Many medium-severity bugs, faster cycle, consistent income. Works best on programs with broad scope, less competition, and reliable $200-$500 medium bounties. You're grinding volume.
Low-volume, high-payout approach: Fewer reports, deeper research, hunting for criticals and highs. Works best on programs with complex application logic, high bounty ceilings, and willingness to pay top dollar. You're accepting feast-or-famine in exchange for potential large payouts.
Know which mode you're in for a given program and budget your time accordingly.

Constructing a Simple Expected Value Estimate
Before committing significant time to a program, do a rough calculation:

Look at disclosed reports. What's the average payout for a valid medium finding?
Estimate your hit rate on this type of target based on your skill set.
Estimate hours per valid finding at your current skill level on similar programs.
Divide.

Example: Program pays $750 average for mediums. You expect to find one valid medium per 8 hours of testing based on your experience. That's $93/hour before accounting for dry stretches. Is that worth it for you?
This is rough, but it's better than picking programs by bounty ceiling alone.

Related

Competition Assessment
HackerOne
Bugcrowd
New Programs
