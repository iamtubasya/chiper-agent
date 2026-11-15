## Core Mechanics: Attack Vectors and Exploitation Patterns

Core Mechanics: Attack Vectors and Exploitation Patterns
Understanding the fundamental mechanics of how vulnerabilities are discovered and exploited remains paramount, even with the advent of new technologies. Core attack patterns, while sometimes applied in novel ways, continue to be the bedrock of many breaches.

Injection Attacks: An Enduring Threat
Injection attacks, a class of vulnerabilities that has persisted for decades, continue to be a significant concern. The evolution of these attacks spans from traditional SQL injection and command injection to modern prompt injection in AI systems . The underlying principle remains the same: introducing untrusted data into a trusted application's execution flow. Prompt injection, in particular, leverages the natural language interface of LLMs to manipulate their behavior, leading to unauthorized actions or data exfiltration .

Chain Reactions and Amplification
A critical aspect of modern exploitation is the concept of attack chaining, where multiple, seemingly minor vulnerabilities are linked together to achieve a significant impact. This can involve escalating an "out-of-scope" Cross-Site Scripting (XSS) vulnerability into a full account takeover through techniques like iframe sandwiching . Similarly, arbitrary file writes (AFW), while often demonstrating limited impact in isolation, can be escalated to Remote Code Execution (RCE) by finding an appropriately executed destination within the target environment . The success of these chains depends heavily on understanding the execution context, including the operating system, language runtime, and framework versions .

Exploiting Trust and Authentication Mechanisms
Attacks frequently target trust boundaries and authentication mechanisms. For example, misconfigured CORS policies or weak WAF rules can facilitate unauthorized access or data leakage . Bypassing multi-factor authentication (MFA) in AI agents and Interactive Voice Responses (IVRs) is another area of concern, often achieved through clever social engineering or exploiting flaws in the authentication logic . The eIDAS qualified signature system, used by numerous banks and government agencies, was found to have vulnerabilities allowing websites to read sensitive card data and potentially achieve drive-by RCE by leveraging flaws in its signing extension and native host .

Kernel-Level Exploitation and Evasion
For privilege escalation, attackers target kernel vulnerabilities. Techniques involve modifying kernel memory structures like the SSDT (System Service Dispatch Table) or using kernel drivers to gain SYSTEM privileges, even on systems with advanced memory isolation and kernel protection features . Advanced techniques also focus on EDR evasion, such as decrypting malicious code in GPU memory or weaponizing Windows Cloud Filter for fileless execution .

Supply Chain Compromise
The increasing reliance on third-party code and dependencies creates significant supply chain risks. Vulnerabilities in package managers like RubyGems or build systems like GitHub Actions can be exploited to compromise entire software supply chains . This includes issues like cache poisoning, where unauthenticated attackers can retrieve sensitive API keys from a CDN, or attacks that hijack cloud identities through reclaimed namespaces in global OIDC issuers .

## Notable Techniques and Emerging Attack Surfaces

Notable Techniques and Emerging Attack Surfaces
The application security community continuously innovates in discovering and weaponizing new vulnerabilities. Several recent developments and techniques stand out for their novelty and potential impact.

AI-Driven Vulnerability Discovery and Exploitation
AI, particularly LLMs, are no longer just tools for defense; they are becoming potent weapons for offense. Researchers are using AI to discover vulnerabilities that would be time-consuming or impossible for humans to find. For instance, an AI tool identified a 20-year-old RCE vulnerability in the original Call of Duty game . More sophisticated applications include using LLMs to chain together complex exploit primitives, such as identifying a pre-authentication RCE in WordPress by combining batch API validation bugs, SQL injection, cache poisoning, and privilege escalation . The "HTTP Terminator" project demonstrates how AI can autonomously invent new attack techniques and exploit live websites at scale, including novel HTTP desync triggers and exploits against banks, security solutions, and government infrastructure .

Weaponizing AI Agents and Chatbots
Beyond finding vulnerabilities in traditional applications, AI systems themselves are becoming targets. Attackers can weaponize chatbots via email to send phishing messages or trick them into performing unauthorized actions . Prompt injection is a prominent technique here, where carefully crafted inputs can manipulate LLMs into revealing sensitive information, bypassing safety guardrails, or executing malicious commands. The OWASP LLM Top 10 project identifies categories of vulnerabilities specific to LLM applications, providing a framework for understanding these new risks . Hijacking AI coding agents from major providers like Anthropic, Google, and OpenAI through a single untrusted GitHub issue is a stark reminder of the potential for compromising development workflows .

Exploiting Browser and Web Technologies
Novel attacks continue to emerge targeting web browsers and their extensions. CSS can be weaponized within webmail clients to bypass sanitizers, exfiltrate tokens, spoof UI elements, and steal passwords across various email providers . Techniques include nesting attribute selectors to brute-force tokens or using font-height oracles with animations to exfiltrate numeric tokens when Content Security Policy (CSP) blocks external resources. Understanding the attack surface of browser extensions, including content scripts, service workers, and extension pages, is crucial, as misconfigurations or vulnerabilities in these components can lead to significant compromise .

Arbitrary File Write Escalation in Modern Environments
The path from an arbitrary file write (AFW) to RCE is often challenging, particularly in modern, stripped-down containerized environments . Research categorizes AFW-to-RCE techniques by exploiting the operating system, language runtime, or framework. While traditional methods like cron or SSH access are less common in containers, techniques like writing to /etc/ld.so.preload remain potent as they trigger on every new process execution. The "Write Once, Shell Everywhere" research systematically catalogues existing techniques, introduces environment fingerprinting to turn writes into read primitives, and provides specific methods for containerized environments .

Exploiting Connected Systems and IoT
Vulnerabilities in systems that bridge the physical and digital worlds are increasingly reported. The Connective signing extension, used by major Belgian banks and government agencies, was found to allow unauthorized access to eID and Maestro card data and enabled drive-by RCE through a vulnerable native binary . This highlights the critical need for security in applications that interact with hardware and sensitive personal identity data. Hacking Android and IoT applications by example is a focused area of study, emphasizing deep dives into static and dynamic analysis, instrumentation techniques, and specific exploit methods .