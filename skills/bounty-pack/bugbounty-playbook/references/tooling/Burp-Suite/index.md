# Burp Suite

> tags: tooling, burp-suite

> related: Tooling/Browser-DevTools/, Attack-Surface/Web/SSRF/, Tooling/Nuclei/, Tooling/ffuf/

Burp Suite
The center of my workflow. Everything else feeds into it or out of it. Pro license is non-negotiable - the free version's Intruder throttling alone makes it unusable for serious work.
Essential Extensions
Install these before touching anything else. Bapp Store mostly, a few from GitHub.
Autorize - Auto-tests every request at your privilege level against a lower-privilege token. Set it up once per engagement, let it run while you browse. Catches IDOR and broken access control passively. Configure the low-priv token in the header inject field and check the "Unauthenticated" column too.
Logger++ - Way more usable than the built-in HTTP history. Color-code rules for status codes, filter by regex, export clean CSVs. I use it to grep my own traffic for keywords mid-test.
Param Miner - Guesses hidden parameters on every endpoint. Run it on interesting targets from the right-click context menu. The "Guess params" option hits headers, body params, and query strings. Has found me cache poisoning and business logic bypasses on endpoints I thought I understood.
Active Scan++ - Extends the active scanner with extra checks. Especially good for SSTI, header injection, and edge-case SQLi patterns the default scanner misses. Set it and let it augment your scans - it's additive, not a replacement.
JS Miner - Passively rips endpoints, secrets, and interesting strings from every JS file in scope. Check the "Findings" tab after any JS-heavy app crawl. Complements Browser DevTools manual analysis.
Intruder Attack Types
Sniper - One payload list, one insertion point at a time. Use this for fuzzing a single parameter (password spray, SQLi wordlist, IDOR ID enumeration). The default go-to.
Battering Ram - Same payload inserted into every marked position simultaneously. Use when all params need the same value, like testing if session tokens are validated across multiple fields.
Pitchfork - Multiple lists, one-to-one pairing. List A position 1, List B position 2, same index. Use for credential stuffing (username list paired with password list). Fast and clean.
Cluster Bomb - Cartesian product of all lists. Every combination. Use sparingly - payload count explodes fast. Good for small brute-force grids (2FA codes + username list).
Match and Replace Tricks
Project Options > Match and Replace. These stay per-project.
# Strip security headers to bypass client-side enforcement
Match (response header): X-Frame-Options: .*
Replace: (empty)
 
# Downgrade to HTTP/1.1 for cache testing
Match (request header): Upgrade-Insecure-Requests: 1
Replace: Upgrade-Insecure-Requests: 0
 
# Inject custom header on every request for Burp Collaborator OOB
Match (request header): (add header)
Replace: X-Forwarded-For: YOUR.BURP.COLLABORATOR.ID
 
# Swap role claim in JWT body (after setting up Burp to intercept)
Match (response body): "role":"user"
Replace: "role":"admin"
Collaborator Workflow
Burp > Burp Collaborator Client. Generate a payload, embed it anywhere OOB interaction is possible: SSRF parameters, file upload filenames, XXE entity URLs, email fields, webhook URLs.
Poll manually while testing. For async interactions (email-based features, background jobs) leave Collaborator open and check back. DNS hits confirm blind SSRF/XXE even when the HTTP response gives nothing away.
For SSRF testing I'll inject the collaborator URL into every parameter that looks like it touches a URL: url=, redirect=, webhook=, image=, fetch=, dest=, host=.
Session Handling Macros
Project Options > Sessions > Session Handling Rules. Critical for apps with complex auth flows.
Macro setup for CSRF token refresh:

Recorder > record the login + navigate-to-page sequence
Define macro that GETs the page, extracts the CSRF token via regex
Set the macro to run before every Intruder/Scanner request
Map extracted token to the csrf_token parameter

Multi-step auth (OTP apps, consent screens):

Chain macros: step 1 gets session, step 2 submits OTP, step 3 completes flow
Set scope to only run on in-scope hosts
Test the macro standalone first using "Test macro" before attaching to rules

Extension token handlers - For OAuth/JWT heavy apps, combine session handling with the JWT Editor extension. Macro re-fetches token, JWT Editor signs it, Intruder uses the fresh signed token. Keeps your attack payloads from dying mid-run.
Scope and Project Setup
Start every engagement by importing scope as a project-level target config. Use regex for wildcard scopes like .*\.target\.com. This gates Scanner, Intruder, and passive analysis to stay on target.
Annotate interesting requests in HTTP history with colors: red for confirmed vulns, orange for leads, yellow for revisit. Add comments with the finding type. Makes writing the report later much faster.
Linked Notes

Nuclei - pipeline automation complement
ffuf - content discovery feeding Burp
Browser DevTools - manual JS analysis
