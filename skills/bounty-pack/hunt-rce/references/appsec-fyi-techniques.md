<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/rce.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Vulnerabilities

Notable Techniques and Vulnerabilities
The following sections highlight specific techniques and notable vulnerabilities that have demonstrated significant impact or represent emerging trends in RCE exploitation.

PHP2Shell (CVE-2026-109618 & CVE-2026-109619)
This critical vulnerability, impacting core PHP components, affected a vast percentage of websites and was rapidly exploited in the wild. It involved memory corruption and stale global state issues, leading to RCE. Multiple attack chains were identified, including those leveraging out-of-memory conditions and exploiting memory disclosure vulnerabilities. AI-assisted tooling played a significant role in the discovery and exploitation attempts even before the official patch release. 

Spring4Shell (CVE-2022-22965)
A critical RCE vulnerability in the Spring Framework, exploitable via data binding mechanisms. Attackers could manipulate data binding to influence the ClassLoader, enabling arbitrary code execution. 

Server-Side Template Injection (SSTI) Variants
SSTI remains a potent RCE vector across numerous template engines. Notable examples include:

• Smarty, Pug, Jinja2: Demonstrated in practical guides, these engines are susceptible to RCE when user input is not properly sanitized before rendering. 
• Form Tools: Similar SSTI vulnerabilities have been identified. 
• Craft CMS: Exploiting Twig templates with authenticated access. 
• OpenMetadata: SSTI via FreeMarker email templates. 
• Airbyte: SSTI in connection builder Docker images. 
Deserialization Exploitation in Enterprise Java Platforms
Enterprise Java applications frequently rely on serialization mechanisms like XStream or BinaryFormatter. Vulnerabilities in these areas, especially when handling untrusted data, can lead to RCE. Examples include:

• Bonita BPM: Exploiting XStream deserialization with authentication bypass. 
• Apache OFBiz: Abusing signed tokens and the widget engine. 
• Ivanti EPMM: Chain of vulnerabilities including unsafe Java EL injection. 
• JetBrains TeamCity: Exploiting agent polling protocol deserialization. 
• Cisco Secure Firewall Management Center: Exploiting serialized Java objects. 
Container Escapes and Cloud Native Exploitation
The widespread adoption of containers and cloud-native technologies introduces new attack surfaces.

• runC: Vulnerabilities like CVE-2024-21626 allow container escapes by exploiting leaked file descriptors, granting host filesystem access. 
• Docker Desktop/Sandboxes on Mac: Virtio-fs sandbox escape via symlink race conditions. 
• NVIDIA Container Toolkit: Container escapes leading to host compromise. 
• Cloud Platform Misconfigurations: Bucket squatting, misconfigured AI SDKs, and exposed JDWP ports can lead to RCE and privilege escalation within cloud environments. 
AI-Assisted Exploit Development and AI Infrastructure Targeting
AI is increasingly a factor in RCE:

• AI for Discovery: LLMs and specialized AI models are being used to discover new vulnerabilities, reconstruct complex exploit chains, and even generate exploitation code. 
• Targeting AI Infrastructure: AI orchestration platforms, AI agents, and AI models themselves are becoming targets, with vulnerabilities like prompt injection, sandbox escapes in AI environments, and insecure handling of model files leading to RCE. 
• AI for Post-Exploitation: AI agents are being integrated into post-compromise activities, automating reconnaissance, lateral movement, and persistence. 
Kernel Exploitation
Vulnerabilities in operating system kernels (Linux, Windows) can grant the highest level of privileges.

• Linux Kernel Memory Corruption: Vulnerabilities like "Copy Fail" (CVE-2026-31431) allow precise memory writes, enabling root privilege escalation and container escapes with minimal code. 
• Windows Kernel Exploitation: Techniques like Volume Shadow Copy abuse (BlueHammer), manipulation of specific kernel drivers (e.g., bsitf.sys), and exploitation of core services like Netlogon and IKE extend RCE to the kernel level. 
Supply Chain Attacks
Compromises in the software supply chain can have widespread RCE implications.

• NPM Packages: Malicious preinstall scripts or vulnerabilities in popular packages can lead to code execution during the build or installation process. 
• CI/CD Pipelines: Compromises in platforms like GitHub Actions or AWS CodeBuild can lead to the execution of malicious code within build environments, potentially impacting downstream artifacts or accessing cloud resources. 
• Development Tools: IDEs, AI coding assistants, and build tools are increasingly targeted, with vulnerabilities allowing code execution in developer environments or within the tools themselves. 