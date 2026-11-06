# Recon-Driven Hunting

> tags: methodology, intermediate

> related: Recon/, Methodology/Target-Selection

Recon-Driven Hunting
The worst way to hunt is to open the login page and start trying SQL injection.
Not because SQLi doesn't exist anymore - it does. But because you're starting with a heuristic ("login pages sometimes have SQLi") instead of actual intelligence about this specific target. That's guessing dressed up as methodology.
Recon-driven hunting inverts this. You don't pick a vulnerability class and go looking for it. You let the recon tell you what to look for and where.
The Anti-Pattern
Here's what most beginners - and plenty of intermediate hunters - actually do:

Open the target's main domain
Poke at the login form (SQLi, XSS)
Check for IDOR on any visible IDs
Run a quick directory brute
Give up after two hours, target is "too hard"

This is coverage without intelligence. You're hitting the most-tested surface (the main app login), using the most-tried payloads, on the most obvious endpoints. You're running the same playbook as the 300 other researchers who signed up for this program.
The Recon-First Approach
Before you test anything, you should know:

Every subdomain, what it's running, and roughly how old it looks
Which assets are running unusual or legacy tech stacks
Which ports are open beyond 80/443
What the JS bundles expose about internal APIs and routes
Which assets look different from the rest  -  different framework, different login UI, different behavior

Only then do you decide where to start.
The Recon → Triage → Test Loop
flowchart TD
    A["Run recon pipeline"] --> B["Triage into priority buckets"]

    B --> C["Tier 1: Old tech, admin panels, staging"]
    B --> D["Tier 2: Complex auth, APIs, mobile backends"]
    B --> E["Tier 3: Static content, CDN, marketing"]

    C --> F["Deep targeted testing"]
    D --> F
    E --> G["Deprioritize"]

    F --> H{"Finding?"}
    H -->|Yes| I["Document, chain, submit"]
    H -->|"No after time-box"| J["Next asset, note observations"]

    I --> K["Return to recon"]
    J --> K
    K --> A

Asset Triage Methodology
Old Tech Stacks Get Priority
An asset running PHP 5.6, ASP.NET MVC 4, or Ruby on Rails 3 isn't old because the team forgot about it. It's old because it's not a priority. Which means it's probably not getting security reviews either.
Signals of an old or forgotten asset:

Different framework from the main app
Older UI design that doesn't match the rest of the product
X-Powered-By headers revealing legacy versions
Response headers suggesting different CDN or hosting from the main app
Certificate issued years before the main domain's cert

These are the assets where you find things. Not because old tech is inherently vulnerable - but because nobody's been reviewing them.
Unusual Ports Get Attention
If naabu or nmap surfaces something on port 8080, 8443, 3000, 8888, or anything non-standard - look at it. Developers run test instances, internal tools, and staging environments on non-standard ports. These are often minimally secured because "they're internal." Except they're not, because you found them.
A Grafana dashboard on port 3000 with default credentials is more valuable than a week of hunting the main app. A Jenkins instance on 8080 with guest access is a critical. A Spring Boot actuator on 8443 that exposes /env and /heapdump is a data leak plus potential credential extraction. These things exist in scope right now on programs you're looking at.
JS-Heavy SPAs Get Deep Analysis
Single-page apps built on React, Vue, Angular - they move all the logic to the client. Which means they expose all their API routes in the JavaScript. Extract them. Every endpoint that JS calls is an endpoint you can test.
Run getJS against the domain, pipe the JS files through linkfinder, and look at what comes out. You'll find:

API routes not linked from the UI
Commented-out debug endpoints
Internal service hostnames
Hardcoded tokens or API keys in older codebases
GraphQL endpoints with introspection enabled

The app.js bundle is often the most valuable recon artifact you can collect.
Connecting Recon Output to Attack Path
Recon shouldn't just surface targets. It should tell you what to test.





































Recon findingWhat to testOld Rails/Django appMass assignment, insecure deserialization, outdated gem/package vulnerabilitiesNon-standard port, custom serviceAuth bypass, exposed debug interfaces, default credentialsAPI endpoints in JSIDOR on object IDs, auth missing on internal endpoints, parameter tamperingStaging/dev subdomainWeaker auth, debug mode enabled, verbose error messages, test data with real patternsS3 bucket on subdomainPublic read/write, bucket takeover if DNS is danglingAdmin panel subdomainCredential stuffing, auth bypass, exposed functionalityGraphQL endpointIntrospection enabled, batch query abuse, authorization failures at field level
When your recon gives you a finding - a Grafana instance, an exposed .git directory, a subdomain pointing to an unclaimed service - that isn't a distraction from "real" testing. That is the finding. Follow it.
See Also

Recon
Target Selection
