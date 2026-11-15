## Notable Techniques

Notable Techniques
Several techniques are frequently leveraged by attackers targeting Python applications:

• Deserialization of Untrusted Data (CWE-502): This is a pervasive vulnerability. For example, the Ultralytics library's load_dataset_cache_file function was found to be vulnerable to RCE via insecure pickle deserialization . Similarly, Xoscar allowed unauthenticated RCE through actor message deserialization , and Serena suffered from RCE via insecure pickle deserialization of LSP symbol caches . Flask-Ninja's HttpBearer component could leak internal headers through deserialization gadgets . Azure Core Python library also had a critical RCE due to insecure deserialization . LangChain Core had a vulnerability (CVE-2025-68664) that allowed secret leakage or object instantiation via the 'lc' key, exploiting its serialization mechanism . Fickling's handling of cProfile.run() in pickle analysis led to RCE (CVE-2026-22607) . PLY had an undocumented picklefile parameter leading to RCE (CVE-2025-56005) . Exploiting shelve, which relies on pickle, is another vector .

• Server-Side Template Injection (SSTI): This allows attackers to inject malicious template code that gets executed on the server. For instance, Jinja2 has been a target, with filter bypasses enabling RCE . SGLang had an RCE via malicious GGUF model files exploiting Jinja2 SSTI .

• Command Injection: This occurs when unsanitized user input is used to construct system commands. This can be achieved through functions like os.system() or the subprocess module. The subprocess module itself is not inherently unsafe, but its misuse with untrusted input is a common cause of vulnerabilities . Langflow experienced a code injection vulnerability via exec() (CVE-2026-33017) . CrewAI had multiple RCE vulnerabilities, including through Docker fallback (CVE-2026-2287) and via its Code Interpreter tool falling back to SandboxPython . Langflow's Agentic Assistant had an RCE via LLM-generated code execution (CVE-2026-33873) .

• Directory Traversal: Improper validation of file paths allows attackers to access files outside the intended directory. Flask-Admin was affected by such a vulnerability due to its use of startswith() for path validation . CrewAI also suffered from arbitrary local file read via a JSON loader (CVE-2026-2285) .

• Privilege Escalation: Vulnerabilities in input validation or kernel logic can lead to privilege escalation. Python 3.11.0a3 to 3.15.0b2 had insecure input validation on Windows, potentially leading to privilege escalation . The Linux Kernel 'Copy Fail' vulnerability (CVE-2026-31431) can be leveraged for root access .

• Authentication Bypass: Vulnerabilities like Host header manipulation can bypass authentication. Starlette's BadHost vulnerability (CVE-2026-48710) allowed authentication bypass by manipulating the Host header . Marimo had a pre-authenticated RCE via its WebSocket endpoint lacking authentication (CVE-2026-39987), which was rapidly exploited for credential theft .

• Supply Chain Attacks: This is a significant threat vector.

• Malicious Packages on PyPI: Attackers use typosquatting or compromise legitimate packages. Examples include 'sisaws' and 'secmeasure' packages delivering the SilentSync RAT , and the 'colorama' copycat package with advanced backdoors .

• Compromised CI/CD Pipelines: The LiteLLM package was trojanized by TeamPCP, reportedly via a compromise of the CI/CD pipeline (Trivy, Checkmarx KICS) . This involved versions 1.82.7 and 1.82.8. TeamPCP also compromised Durable Task's Microsoft Python client .

• Exploitation of Startup Hooks: Malicious .pth files in Python's module search path can execute code at interpreter startup, providing persistence. This was seen in the LiteLLM attack .

• Typo-squatting and Domain Takeovers: Attackers can register similar domain names or exploit legacy bootstrap scripts to compromise package management systems like PyPI .

• Malicious Model Files: In AI/ML contexts, malicious model files (e.g., GGUF) can contain exploits like Jinja2 SSTI . NeMo and Uni2TS libraries were vulnerable to RCE via malicious model metadata due to Hydra instantiation .

• Credential Harvesting and Exfiltration: Attackers actively seek to steal credentials from environment variables, SSH keys, cloud tokens, and other sensitive sources. The LiteLLM compromise, for instance, delivered a credential stealer .

• Exploiting Structural Pattern Matching: AWS MCP's Python sandbox escape was achieved by exploiting structural pattern matching and __match_args__ .

• Container Breakout: Vulnerabilities like shared page cache issues can enable attackers to break out of containers .

• Use of Obfuscated Code: Attackers often use obfuscation to evade detection, making analysis more difficult .

• Cross-Site Scripting (XSS) in Templating Engines: Jinja2 has had XSS vulnerabilities, such as CVE-2024-22195 . AIOHTTP also had an XSS vulnerability due to HTTP Response Splitting (CVE-2026-34519) .

• Insecure Use of eval() and Related Functions: Directly using eval() or exec() with untrusted input is a direct path to RCE .

• Exploiting Undocumented Features: The PLY library's undocumented picklefile parameter was used for RCE .

• Arbitrary File Read: CrewAI had a vulnerability allowing arbitrary local file read via a JSON loader (CVE-2026-2285) .

• Sandbox Escapes: Redash had an unpatched Python sandbox escape vulnerability that granted attackers full server access .

• Bypassing Static Analysis Tools: Techniques exist to bypass tools like Picklescan. For example, using pip.main() can allow RCE by enabling the installation of malicious packages . PickleScan itself had multiple bypass vulnerabilities related to file extensions, ZIP archive handling, import blacklists, and hidden file detection .

• File Extension Bypass and Archive Manipulation: Attackers use techniques like file extension bypasses and ZIP archive manipulation to evade malware detection .

• Monkey-Patching: Modifying classes or modules at runtime can be used for malicious purposes .

• SSRF via Unvalidated URLs: CrewAI's RAG search tools were vulnerable to SSRF .

• JWT Security Testing: Techniques like bruteforcing, algorithm confusion, and KID injection are used to compromise JWT-based authentication .

• Reverse Shells: Implementing reverse shells is a common post-exploitation technique .

• Leveraging Low-Level APIs: Using ctypes to interact with low-level APIs or dynamically loading Python libraries from C are advanced techniques that can be misused .

• Obfuscation: Attackers use obfuscation techniques to hide malicious code .