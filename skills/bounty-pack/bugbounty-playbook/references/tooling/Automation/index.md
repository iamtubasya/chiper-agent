# Automation

> tags: tooling, automation

> related: Tooling/Nuclei/, Tooling/ffuf/, Tooling/Burp-Suite/, Tooling/AI-Assisted/

Automation
Automation in bug bounty is about scale and speed on recon, not about replacing manual testing. I automate the parts that don't require judgment - subdomain enumeration, live host probing, port scanning, screenshot capture, change detection. The actual exploitation is still manual.
The goal: get to a high-quality target list faster than competitors, then do better manual work on it.
Axiom: Distributed Scanning
Axiom spins up cloud VPS instances, distributes work across them, then tears them down. Essential for large programs where scanning from a single IP is too slow or gets rate-limited.
# Install
bash <(curl -s raw.githubusercontent.com/pry0cc/axiom/master/interact/axiom-configure)
 
# Initialize a fleet of 10 instances
axiom-fleet recon -i 10
 
# Distribute subdomain enumeration
axiom-scan targets.txt -m subfinder -o subs-out.txt
 
# Distributed httpx probing
axiom-scan subs-out.txt -m httpx -o live-hosts.txt
 
# Distributed nuclei
axiom-scan live-hosts.txt -m nuclei -o nuclei-results.txt -- -tags exposed-panels,misconfig
 
# Tear down fleet when done
axiom-fleet rm recon
Per-run cost is usually under $5 for a medium program. Don't leave fleets running.
Recon-to-Scan Pipeline
My standard flow, assembled from individual tools. This runs on a VPS for large scopes.
#!/bin/bash
# recon-pipeline.sh
TARGET=$1
OUTPUT_DIR=~/recon/$TARGET
mkdir -p $OUTPUT_DIR
 
echo "[*] Starting recon for $TARGET"
 
# 1. Subdomain enumeration (passive + brute)
subfinder -d $TARGET -silent -o $OUTPUT_DIR/subs-passive.txt
amass enum -passive -d $TARGET -o $OUTPUT_DIR/subs-amass.txt
cat $OUTPUT_DIR/subs-*.txt | sort -u > $OUTPUT_DIR/subs-all.txt
echo "[*] $(wc -l < $OUTPUT_DIR/subs-all.txt) subdomains found"
 
# 2. DNS resolution and live host probing
dnsx -l $OUTPUT_DIR/subs-all.txt -silent -o $OUTPUT_DIR/resolved.txt
httpx -l $OUTPUT_DIR/resolved.txt \
  -silent \
  -mc 200,301,302,401,403 \
  -tech-detect \
  -title \
  -status-code \
  -json \
  -o $OUTPUT_DIR/live-hosts.json
 
cat $OUTPUT_DIR/live-hosts.json | jq -r '.url' > $OUTPUT_DIR/live-urls.txt
echo "[*] $(wc -l < $OUTPUT_DIR/live-urls.txt) live hosts"
 
# 3. Screenshot capture (visual triage)
gowitness file -f $OUTPUT_DIR/live-urls.txt -P $OUTPUT_DIR/screenshots/
 
# 4. Nuclei scan on live hosts
nuclei -l $OUTPUT_DIR/live-urls.txt \
  -s high,critical \
  -etags ssl,dns \
  -json \
  -o $OUTPUT_DIR/nuclei-results.jsonl
 
# 5. Content discovery on interesting targets
# (Filter to 200/403 hosts, run ffuf on those)
cat $OUTPUT_DIR/live-hosts.json | jq -r 'select(.status_code == 200 or .status_code == 403) | .url' > $OUTPUT_DIR/fuzz-targets.txt
 
while read url; do
  ffuf -u "$url/FUZZ" \
    -w ~/wordlists/SecLists/Discovery/Web-Content/raft-medium-directories.txt \
    -mc 200,301,302,401,403 \
    -ac \
    -silent \
    -of json \
    -o "$OUTPUT_DIR/ffuf-$(echo $url | md5sum | cut -c1-8).json"
done < $OUTPUT_DIR/fuzz-targets.txt
 
echo "[*] Pipeline complete. Results in $OUTPUT_DIR"
Bash Orchestration Patterns
Parallel execution with GNU parallel:
# Run nuclei templates in parallel across targets
cat targets.txt | parallel -j 5 "nuclei -u {} -tags xss -silent -o nuclei-{#}.txt"
 
# Parallel ffuf runs
cat domains.txt | parallel -j 3 \
  "ffuf -u https://{}/FUZZ -w wordlist.txt -ac -silent -of json -o ffuf-{#}.json"
Change detection for continuous monitoring:
#!/bin/bash
# monitor-changes.sh -- run via cron
TARGET=$1
HASH_FILE=~/monitor/$TARGET.hash
 
current_hash=$(curl -s https://$TARGET | md5sum)
if [ -f "$HASH_FILE" ]; then
  prev_hash=$(cat $HASH_FILE)
  if [ "$current_hash" != "$prev_hash" ]; then
    echo "CHANGE DETECTED on $TARGET" | notify -provider slack
    # Trigger full recon
    ~/scripts/recon-pipeline.sh $TARGET
  fi
fi
echo $current_hash > $HASH_FILE
Notification Setup
I use notify from ProjectDiscovery to pipe alerts to Slack/Discord. It's the glue that makes monitoring actually useful.
go install -v github.com/projectdiscovery/notify/cmd/notify@latest
Config (~/.config/notify/provider-config.yaml):
slack:
  - id: "recon-alerts"
    slack_webhook_url: "hooks.slack.com/services/YOUR/WEBHOOK/URL"
    slack_format: "{{data}}"
    slack_username: "recon-bot"
 
discord:
  - id: "discord-alerts"
    discord_webhook_url: "discord.com/api/webhooks/YOUR/WEBHOOK"
    discord_format: "{{data}}"
    discord_username: "recon-bot"
Usage in pipelines:
# Alert on critical nuclei findings
nuclei -l targets.txt -s critical -silent | notify -provider slack
 
# Alert on new subdomains
comm -23 <(sort new-subs.txt) <(sort known-subs.txt) | notify -provider discord
Cron Scheduling
# Edit crontab
crontab -e
 
# Daily subdomain refresh at 6am
0 6 * * * /home/user/scripts/recon-pipeline.sh target.com >> /home/user/logs/recon.log 2>&1
 
# Hourly change detection for high-value targets
0 * * * * /home/user/scripts/monitor-changes.sh target.com >> /home/user/logs/monitor.log 2>&1
 
# Weekly nuclei template update
0 0 * * 0 nuclei -update-templates >> /home/user/logs/nuclei-update.log 2>&1
Python Orchestration
For more complex workflows where bash gets unwieldy:
#!/usr/bin/env python3
# triage.py -- parse httpx JSON, prioritize targets
import json, sys
 
with open(sys.argv[1]) as f:
    hosts = [json.loads(line) for line in f if line.strip()]
 
# Prioritize: login pages, API endpoints, admin panels
priority = []
for h in hosts:
    title = h.get('title', '').lower()
    url = h.get('url', '')
    tech = h.get('technologies', [])
 
    score = 0
    if any(k in title for k in ['login', 'admin', 'dashboard', 'portal']): score += 3
    if any(k in url for k in ['/api/', '/admin', '/internal']): score += 3
    if any(t in str(tech) for t in ['WordPress', 'Jira', 'Jenkins', 'Grafana']): score += 2
 
    priority.append((score, url, title, tech))
 
priority.sort(reverse=True)
for score, url, title, tech in priority[:20]:
    print(f"[{score}] {url} -- {title} -- {tech}")
Linked Notes

Nuclei - the core scanning engine in pipelines
ffuf - content discovery integrated into pipeline
Burp Suite - manual follow-up on pipeline findings
AI Assisted - LLM triage layer on automation output
