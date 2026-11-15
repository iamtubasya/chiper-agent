# AI-Assisted Hunting

> tags: tooling, ai

> related: Tooling/Browser-DevTools/, Tooling/Automation/, Tooling/Nuclei/

AI-Assisted Hunting
I'll give you the honest take: AI helps in specific, narrow ways and is useless or actively harmful in others. The hype is way ahead of the reality. That said, the places where it actually helps are genuinely high-leverage, so it's worth building real workflows around them.
The core principle: AI is a force multiplier for reading and understanding code/data at scale. It's not a vulnerability scanner.
JS Bundle Analysis
This is the highest-value AI use case I've found. Minified JS bundles are painful to read manually. LLMs handle them surprisingly well.
The workflow:

Extract all JS files from a target. Use DevTools Network tab filtered to JS, or:

# Grab all JS from a URL using wget
wget --mirror --page-requisites --no-parent \
  -A "*.js" -P ./js-dump/ target.com
 
# Or use hakrawler + filter
echo "target.com" | hakrawler -js | grep "\.js$" | sort -u > js-urls.txt
xargs -a js-urls.txt -I{} curl -s {} -o ./js-dump/{#}.js

Feed individual bundles to Claude (or GPT-4) with a targeted prompt. Don't dump everything at once.

Effective prompts for JS analysis:
Analyze this minified JavaScript file. Find and list:
1. All API endpoints (absolute paths, relative paths, hardcoded URLs)
2. Any hardcoded secrets, tokens, API keys, or credentials
3. Authentication logic: where tokens are set, checked, or validated
4. Any references to admin, internal, or privileged functionality
5. Client-side routing paths that don't appear in the visible nav
Respond only with findings, grouped by category. Skip generic library code.
In this JS code, identify all places where user-controlled input flows into:
- innerHTML, outerHTML, document.write
- eval(), Function(), setTimeout with string argument
- jQuery html(), append() with unsanitized values
- location.href, location.replace() with user input
Show the code path from source to sink for each one.

Manually verify every finding. LLMs hallucinate endpoints and misread obfuscated code. Treat output as a list of hypotheses, not confirmed findings.

What this finds: Hidden API endpoints not visible through browsing, hardcoded dev/staging API keys accidentally shipped to prod, feature flag names to guess at disabled features, admin routes gated only by client-side checks.
Agentic Recon Workflows
I'm experimenting with agentic setups - giving an LLM tools to run commands and iterate on recon. The current state is promising but immature.
Practical setup using Claude with tool use:
# Rough pattern: give Claude bash tool access for recon tasks
# Not production code, concept illustration
 
tools = [
    {"name": "run_command", "description": "Run a bash command and return output"},
    {"name": "read_file", "description": "Read a file"},
    {"name": "write_file", "description": "Write findings to file"}
]
 
initial_prompt = """
You're a recon assistant. Your target is {domain}.
Your goal: enumerate subdomains, find live hosts, identify interesting technology stacks.
Use the tools available. Be methodical. Document what you find.
Start with passive subdomain enumeration.
"""
Where this works: the LLM makes reasonable decisions about what to run next without needing step-by-step instructions. It can chain subfinder → httpx → tech detection → tailored nuclei runs without me scripting every transition.
Where it breaks: it hallucinates tool flags, misinterprets ambiguous output, and sometimes goes off-script in ways that cause noise or miss obvious next steps. Still needs supervision.
Code Review with Claude
When a program gives you source code access or when you find a GitHub repo, LLM-assisted code review is fast.
Effective patterns:
Review this [language] code for security vulnerabilities. Focus on:
- SQL injection and ORM-level injection
- Authentication and authorization bypasses
- Insecure deserialization
- Path traversal
- Business logic flaws (anything that assumes client-provided values are trustworthy)
For each finding: file and line, vulnerability type, why it's exploitable, suggested test case.
This is the authentication middleware for a web app. Walk through every code path.
For each path: what happens, can it be bypassed, what would an attacker send to reach
an authenticated endpoint without valid credentials?
For large codebases: don't dump everything. Ask the LLM to analyze specific files, then follow up on interesting functions. The context window is large but analysis quality degrades at the far end.
Triage Assistance
After a big automation run, I sometimes feed nuclei/ffuf output to an LLM for prioritization:
Here's ffuf output from a directory scan of a financial services app.
Classify each discovered path by likely risk level (high/medium/low/noise).
For high-risk paths, explain what you'd look for there.
 
[paste output]
This is faster than reading 500 lines of output manually. The LLM's risk classification is roughly correct about 80% of the time - good enough for triage, not good enough for final call.
Where AI Actually Helps

Reading and understanding large JS bundles (high value)
Code review when you have source (high value)
Explaining unfamiliar tech stacks or frameworks quickly
Writing Nuclei templates from a description of what you want to detect
Generating targeted wordlists for a specific app type
Summarizing API documentation to find under-documented endpoints
Drafting report writeups (give it your notes, ask for clean prose)

Where AI Doesn't Help (Yet)

Automated exploitation. It doesn't reliably turn "there's a SQLi here" into a working payload for a non-trivial case.
Identifying novel vulnerability classes. It knows what's in its training data.
Real-time interaction with live targets. Latency and context limits make iterative exploitation impractical.
Understanding app-specific business logic from observation alone. It can't watch you click through the app.
Replacing manual testing on complex auth flows, multi-step logic, or race conditions.

Practical Setup
My primary tool is Claude Code (Anthropic's CLI). It has direct filesystem access, can read and analyze files, run commands, and iterate on findings without copy-pasting between tools.
# Point Claude Code at a JS bundle
claude "Analyze js-dump/app.bundle.js for API endpoints, hardcoded secrets, and auth logic"
 
# Feed it recon output for triage
claude "Read nuclei-output.txt and classify findings by risk. Flag anything that looks like a real vulnerability vs scanner noise"
 
# Code review a specific file
claude "Review src/auth/middleware.js for authentication bypasses. Show every code path that reaches an authenticated endpoint"
For the API directly:
import anthropic
 
client = anthropic.Anthropic()
 
with open('bundle.js') as f:
    js_code = f.read()
 
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    messages=[{
        "role": "user",
        "content": f"Analyze for security issues:\n\n{js_code}"
    }]
)
print(message.content[0].text)
Claude Code handles large files well since it can read them directly rather than needing you to paste into a chat window. For very large bundles, point it at the file and let it chunk the analysis itself.
Linked Notes

Browser DevTools - extract JS files to feed into LLMs
Automation - LLM triage layer on automation output
Nuclei - use LLMs to write custom templates faster
