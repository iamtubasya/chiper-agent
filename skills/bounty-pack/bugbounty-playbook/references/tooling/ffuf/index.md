# ffuf

> tags: tooling, ffuf

> related: Tooling/Burp-Suite/, Tooling/Nuclei/, Tooling/Automation/

ffuf
Fast, flexible, and does exactly what I tell it. I use ffuf for content discovery, parameter fuzzing, and anything Burp Intruder would throttle to death on the free tier. Learn the filter flags - they're what separate useful results from garbage.
Installation
go install github.com/ffuf/ffuf/v2@latest
Wordlist Selection Strategy
Your wordlist is everything. The right list beats tool configuration every time.
SecLists is the baseline. Clone it, keep it updated: git clone github.com/danielmiessler/SecLists.git ~/wordlists/SecLists
My go-to lists by use case:
# Directory/path discovery (start here)
~/wordlists/SecLists/Discovery/Web-Content/raft-large-directories.txt
 
# File discovery (extensions matter)
~/wordlists/SecLists/Discovery/Web-Content/raft-large-files.txt
 
# API endpoint discovery
~/wordlists/SecLists/Discovery/Web-Content/api/api-endpoints.txt
~/wordlists/SecLists/Discovery/Web-Content/api/objects.txt
 
# Backup and config files (high signal)
~/wordlists/SecLists/Discovery/Web-Content/CommonBackupExtensions.txt
~/wordlists/SecLists/Discovery/Web-Content/big.txt
 
# Subdomains (pair with DNS tools, not ffuf)
~/wordlists/SecLists/Discovery/DNS/subdomains-top1million-5000.txt
Building custom wordlists. After initial discovery, scrape the app with cewl and combine with SecLists:
cewl target.com -d 3 -m 4 -w cewl-target.txt
cat cewl-target.txt ~/wordlists/SecLists/Discovery/Web-Content/raft-large-directories.txt | sort -u > combined.txt
Also pull JS files and grep for path strings:
cat js-files.txt | xargs -I{} curl -s {} | grep -oP '["'"'"'][/a-zA-Z0-9_\-\.]+["'"'"']' | tr -d '"'"'" | sort -u >> combined.txt
Basic Discovery
# Standard directory discovery
ffuf -u target.com/FUZZ -w ~/wordlists/SecLists/Discovery/Web-Content/raft-large-directories.txt \
  -mc 200,201,204,301,302,307,401,403 \
  -t 40 \
  -o results.json -of json
 
# With extensions
ffuf -u target.com/FUZZ -w ~/wordlists/SecLists/Discovery/Web-Content/raft-large-files.txt \
  -e .php,.asp,.aspx,.jsp,.bak,.old,.txt,.config,.xml \
  -mc 200,201,204,301,302,401,403
Filter Configuration
This matters more than the wordlist. Unfiltered ffuf output is unusable.
# -fc: filter by status code
ffuf -u target.com/FUZZ -w wordlist.txt -fc 404
 
# -fs: filter by response size (remove the default "not found" page size)
# First, check what 404 pages look like:
curl -s target.com/doesnotexist123 | wc -c
# Then filter that exact size:
ffuf -u target.com/FUZZ -w wordlist.txt -fs 1234
 
# -fw: filter by word count in response
ffuf -u target.com/FUZZ -w wordlist.txt -fw 12
 
# -fl: filter by line count
ffuf -u target.com/FUZZ -w wordlist.txt -fl 5
 
# Combine filters (AND logic)
ffuf -u target.com/FUZZ -w wordlist.txt -fc 404 -fs 1234 -fw 12
 
# -fr: filter by regex (powerful for false positive removal)
ffuf -u target.com/FUZZ -w wordlist.txt -fr "page not found|404 error"
Calibration mode - let ffuf auto-detect filter values:
ffuf -u target.com/FUZZ -w wordlist.txt -ac
Use -ac as a starting point, then verify it isn't filtering true positives before trusting it.
Recursive Fuzzing
# Auto-recursive (follow discovered directories)
ffuf -u target.com/FUZZ -w wordlist.txt \
  -recursion \
  -recursion-depth 3 \
  -mc 200,301,302,401,403
 
# Recursive with rate limiting (be considerate)
ffuf -u target.com/FUZZ -w wordlist.txt \
  -recursion -recursion-depth 2 \
  -t 20 -rate 50
Parameter Fuzzing
This is where ffuf earns its keep beyond content discovery.
Query string parameter discovery:
ffuf -u "target.com/api/user \
  -w ~/wordlists/SecLists/Discovery/Web-Content/burp-parameter-names.txt \
  -fs 0 -mc all
POST body fuzzing:
# JSON body parameter fuzzing
ffuf -u target.com/api/update \
  -w ~/wordlists/SecLists/Discovery/Web-Content/burp-parameter-names.txt \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"FUZZ":"test"}' \
  -fs 0
 
# Form data
ffuf -u target.com/login \
  -w ~/wordlists/SecLists/Passwords/xato-net-10-million-passwords-1000.txt \
  -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=FUZZ" \
  -fc 200 -mc all
Header fuzzing:
# Find headers the app responds to differently
ffuf -u target.com/admin \
  -w ~/wordlists/SecLists/Discovery/Web-Content/BurpSuite-ParamMiner/Miscellaneous/Headers.txt \
  -H "FUZZ: 127.0.0.1" \
  -mc 200
Rate Limiting and Headers
Always identify yourself and be respectful:
ffuf -u target.com/FUZZ -w wordlist.txt \
  -H "User-Agent: Mozilla/5.0 (compatible; BugBounty/1.0)" \
  -H "X-Bug-Bounty: yourhandle" \
  -t 20 \
  -rate 30 \
  -p 0.1
-p adds a delay in seconds between requests. -rate caps requests per second globally.
Output and Post-Processing
# JSON output for scripting
ffuf -u target.com/FUZZ -w wordlist.txt -of json -o ffuf-results.json
 
# Extract just the URLs from JSON
cat ffuf-results.json | jq -r '.results[].url'
 
# Quick interesting paths check
cat ffuf-results.json | jq -r '.results[] | select(.status == 200) | .url'
Linked Notes

Burp Suite - send interesting ffuf hits to Burp for deep dive
Nuclei - feed discovered paths into Nuclei templates
Automation - integrate ffuf into recon pipelines
