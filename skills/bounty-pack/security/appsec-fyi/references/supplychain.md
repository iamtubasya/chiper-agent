## Notable Techniques and Findings

Notable Techniques and Findings
The landscape of supply chain attacks is dynamic, with attackers constantly refining their methods. Several techniques and findings stand out for their impact and technical sophistication.

Self-Propagating Worms
Worms like Shai-Hulud and its variants (Mini Shai-Hulud, SHA1-Hulud, Cosmic Cat) represent a significant evolution. These malware strains are designed to not only steal credentials and deploy RATs but also to actively find and compromise other accessible packages and repositories. They often leverage stolen npm tokens or GitHub credentials to publish malicious versions of other software, effectively turning the trusted software ecosystem into a propagation network . The ability of these worms to cross ecosystem boundaries (e.g., from npm to PyPI) further complicates detection and containment.

Credential Harvesting Sophistication
Credential theft remains a primary objective. Attackers employ increasingly sophisticated methods to extract sensitive information:

• Targeting Cloud and CI/CD Secrets: Beyond static files, malware actively scans CI runner memory for OIDC tokens and other ephemeral credentials. Stolen tokens are then used for cloud control plane infiltration or to forge signed artifacts with valid provenance .
• Browser Credential Theft: Malware targets browser profiles (Chrome, Brave, Edge) to extract saved passwords, session cookies, and even cryptocurrency wallet credentials .
• SSH Key and API Token Exfiltration: Stolen SSH keys are used for lateral movement and persistence . API keys for cloud providers, package managers, and AI services are also prime targets.
• Disguised Exfiltration: Data is often disguised as legitimate network traffic, encrypted chat messages, or DNS queries to evade network-based detection .
Exploiting Build and Runtime Behaviors
Attackers meticulously study how software is built and run to find blind spots:

• Lifecycle Script Abuse: As mentioned, preinstall, install, and postinstall scripts in npm, or build scripts like binding.gyp in Node.js, are consistently abused to execute arbitrary code during the build or installation phase . The Miasma malware, for example, weaponized binding.gyp for execution outside of typical lifecycle script controls .
• Runtime Execution Bypassing Install Scripts: Techniques like using Bun or embedding payloads within native add-ons can allow code execution even if installation scripts are disabled or bypassed .
• Pickle Deserialization RCE: In Python, insecure deserialization of pickled data, such as LSP symbol caches, can lead to arbitrary code execution on project activation .
• DLL Sideloading: Malicious DLLs can be placed alongside legitimate executables, forcing the system to load the malicious code during execution .
• eBPF for Stealth: Extended Berkeley Packet Filter (eBPF) programs can be used for kernel-level persistence and stealthy operations in Linux environments .
Code Signing and Provenance Forgery
The integrity of software artifacts is often verified through digital signatures and provenance information. Attackers actively seek to subvert these mechanisms:

• Compromised Certificates: Trusting compromised code-signing certificates, such as the eMudhra certificates exploited by Apple, allows attackers to sign malicious code with apparent legitimacy .
• SLSA Provenance Forgery: By compromising the CI/CD pipeline, attackers can generate fake SLSA provenance attestations, making malicious builds appear trustworthy and passing automated checks .
• Signature Verification Bypass: Vulnerabilities in security scanning tools themselves, like the CVE-2024-43405 in Nuclei, can allow attackers to bypass signature validation logic .
AI Ecosystem Attacks
The rapid adoption of AI tools and platforms has opened new avenues for attackers:

• AI Model Registries: Hugging Face and similar platforms are targeted by distributing malicious models that contain executable code .
• Prompt Injection: Exploiting AI agents through crafted prompts can lead to data exfiltration, configuration changes, or the execution of malicious commands. This can affect both AI models and the code review/generation tools used by developers .
• Slopsquatting AI-Related Names: Attackers register package names that AI might hallucinate or that are related to AI projects, tricking users into installing malicious dependencies .
• AI-Assisted Attack Creation: AI can automate reconnaissance, vulnerability discovery, and exploit generation, drastically accelerating the pace and sophistication of attacks . The TeamPCP group has been linked to using AI for more effective reconnaissance and attack automation .

## Notable Techniques

Notable Techniques

• Broccoli2Shell/Node2Shell (CVE-2026-111497): An out-of-bounds write vulnerability in the Brotli decompression library affecting Node.js, Python, and others. Exploitable when decompressing Brotli-compressed request bodies .
• PHP2Shell (CVE-2026-109618, CVE-2026-109619): Critical RCE vulnerabilities in the PHP engine itself, reachable before application code runs .
• Gheist Campaign: Mass abuse of stolen GitHub tokens to plant secret-dumping workflows, impacting public repositories and succeeding in private ones .
• LiteLLM Compromise: Malicious v1.107.0 package contained a credential stealer and RAT, exploiting GitHub CLI OAuth tokens and a pyproject.toml directive .
• Tensorlake@0.5.144 Compromise: Contained the Shai-Hulud credential-stealing worm, published with valid provenance via a compromised GitHub Actions workflow .
• BYOVD (Bring Your Own Vulnerable Driver): Loading vulnerable drivers to disable kernel-level security monitoring .
• Agentic SDLC Vulnerabilities: AI agents introducing new attack vectors like prompt injection and breaking traditional governance. The OWASP AISVS and EU AI Act emphasize logging and oversight for AI systems .
• Package Manager Integrity Issues: Many package managers have integrity verification problems; fewer than half use default lockfiles for tampering checks, and some don't verify every downloaded package .
• Runtime SBOM Generation: Deriving Software Bill of Materials from live process information (/proc filesystem) offers a more accurate view than build-time SBOMs .
• Web3 C2 Infrastructure: Using blockchain smart contracts for dynamic botnet command and control, evolving from static C2 to dynamic updates .
• GitLab Incoming Email Abuse: Project email addresses functioning as long-lived tokens, allowing unauthorized code pushes and CI/CD execution without proper authentication .
• XCSSET Malware: Found in Flutter packages, planted SSH keys not removed upon uninstall, and capable of runtime reconstruction of tools like xxd .
• Coder Registry Compromise: Served tampered modules for 14 hours, leading to credential exfiltration, exploiting Terraform external data blocks .
• JFrog Artifactory Vulnerability (CVE-2026-82329): A critical authentication bypass exploited within days of patching .
• TeamPCP Global Supply Chain Attacks: Charged for compromising over 1000 organizations, stealing over 500k credentials, and exfiltrating 300GB of data, often utilizing the Shai-Hulud worm .
• Rust Supply Chain Attack (e.g., arrayref): Targeting Solana-related build pipelines, introducing typosquatted dependencies, and exfiltrating credentials from developer workstations and CI environments .
• ChainDrop npm Worm: Infected over 400 packages, stealing OIDC tokens and credentials from GitHub Actions runners, using blockchain for C2 .
• PostGIS Extension Vulnerability (address\_standardizer): Enabled privilege escalation and RCE on multiple managed PostgreSQL providers .
• easy-day-js npm Attack: A typosquatted package with crypto-stealer logic in its postinstall script, part of the Mastra AI supply chain incident .
• Injective Labs SDK Backdoor: Runtime telemetry exfiltrated crypto wallet keys .
• AsyncAPI npm Compromise: Leveraged GitHub Actions pull_request_target and import-time payload delivery via Miasma RAT .
• Jscrambler npm Attack: Compromised packages delivered cross-platform native binaries during installation .
• Ghostcommit: Multimodal prompt injection in images targeting AI code review tools to exfiltrate secrets .
• GitLost Vulnerability: Prompt injection in GitHub Agentic Workflows via issues to exfiltrate data from private repos .
• Phantom Gyp: A technique used by Miasma malware to bypass install-script controls by embedding malicious code in binding.gyp files .
• Miasma Malware Campaign: Evolved from Shai-Hulud, targeting Red Hat packages, abusing binding.gyp, and using GitHub for C2 .
• Red Hat npm Packages Compromise: Used Miasma variant with trusted publishing bypass and credential theft .
• Malicious AI Tooling Packages: npm packages posing as AI tools to steal authentication tokens and expose build pipelines .
• SLSA Provenance Forgery: Attackers compromise CI/CD pipelines to create signed artifacts with forged provenance .
• Axios npm Compromise: Distributed WAVESHAPER.V2 RAT; attributed to North Korean actor UNC1069 .
• XZ Utils Backdoor (CVE-2024-3094): A stealthy, multi-year build-time injection attack enabling SSH authentication bypass and RCE .
• tj-actions/changed-files Compromise (CVE-2025-30066): Poisoned a foundational GitHub Action, leading to secrets leakage from CI logs .
• SleeperGem Attack: Used dormant RubyGems accounts to distribute payloads, often with custom persistence mechanisms.