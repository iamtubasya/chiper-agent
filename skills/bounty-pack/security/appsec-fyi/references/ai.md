## Notable Techniques and Exploitation Patterns

Notable Techniques and Exploitation Patterns
The evolving threat landscape has produced a range of specific techniques that exploit AI systems:

• Agent Swarms and Autonomy: Groups of AI agents can coordinate to perform complex attacks, mimicking human attacker tactics but at machine speed . The ARTEX framework, for example, has been used in attacks against South Korean financial institutions and software vendors . Hermes AI agent was observed in 'YOLO' mode during an intrusion at Thailand's Ministry of Finance .
• LLMJacking: Threat actors hijack cloud billing accounts to fund unauthorized AI usage, often by exploiting GCP infrastructure to link external projects to victim billing accounts for mass LLM execution .
• Credential Exfiltration via LLM Interaction: AI agents can be tricked into revealing API keys or other secrets. This can happen through crafted prompts, by processing malicious external data, or by abusing the tools they have access to .
• Sandboxing and Container Escapes: AI models running in sandboxed or containerized environments can be vulnerable to escape techniques. For instance, vulnerabilities in the NVIDIA Container Toolkit have allowed root access to host systems . Exploiting structural pattern matching in AWS MCP Servers can lead to sandbox escapes .
• AI-Generated Package Slopsquatting (Hallucination Squatting): Attackers register package names that LLMs are likely to hallucinate or mistype, redirecting users to malicious code .
• Voice Over IP (VoIP) Fraud Planning: AI is being used to plan complex fraud schemes, including VoIP fraud .
• AI-Assisted Firmware Analysis and Repair: AI can be used to analyze and potentially repair vulnerabilities in firmware .
• Business Logic Flaw Discovery: AI can identify complex business logic flaws that traditional scanners might miss .
• Cross-Tenant Compromise: Vulnerabilities in cloud services, such as Azure API Connections, can allow attackers to compromise resources across different tenants .
• Identity Provider (IdP) Attacks: Compromising IdPs like Okta, Entra, and Cognito remains a critical target, often leveraged by AI-driven attack tooling .
• LLM Hallucination Leading to Insecure Code: LLMs can "hallucinate" insecure code suggestions, especially when influenced by persona prompts or incomplete understanding .
• AI Model Risk Tied to Reachability and Connected Systems: The risk of an AI model is not just its inherent flaws but its ability to interact with other systems, particularly agents and MCP servers .
• Prompt Injection via Embedded Text/Data: AI agents are influenced by embedded instructions within external data sources, enabling indirect prompt injection attacks .
• Adversarial Probing for AI Fuzzing: AI models can be used to generate inputs that probe for vulnerabilities in other AI systems or software .
• Agent Impersonation/Cloaking: AI agents can be used to impersonate legitimate entities (e.g., fake Googlebots) to evade detection or gain trust .
• AI Agent Controlling HTTP Headers: Agents can be manipulated to control HTTP headers, potentially leading to various web application attacks .
• AI Agents Executing Arbitrary Code via HTTP Headers: This technique demonstrates a direct path for code execution through agent manipulation .
• AI Agent Behavior Modification Based on Triggers: Agents can be influenced to alter their behavior based on specific input triggers, potentially leading to malicious actions .
• Agentic AppSec: The concept of AI agents running entire application security programs, shifting security left and automating complex security tasks .
• Exploiting Structural Pattern Matching for Sandbox Escape: Advanced techniques that leverage how AI systems match patterns to bypass sandboxing mechanisms .
• Untrusted Repository Content Steering AI Agents: AI agents can be steered by malicious content found in untrusted code repositories .
• AI-Assisted Exploitation of XSS and Prompt Injection: AI models can enhance the discovery and exploitation of common web vulnerabilities alongside prompt injection techniques .
• Malicious LLM API Routers: Attackers can compromise or create malicious API routers that direct LLM traffic to compromised or untrusted endpoints .