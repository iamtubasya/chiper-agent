## Notable Techniques

Notable Techniques
Hardcoding and Embedding: The most fundamental technique is hardcoding secrets directly into source code, configuration files (e.g., .env, mcp.json), or environment variables. This practice persists despite awareness, often due to convenience or lack of proper tooling . Secrets are also embedded in container images, often through ARG or ENV instructions, making them part of the image metadata and accessible through image inspection . Even seemingly inert files like archive formats (.zip, .tar.gz) can contain hardcoded secrets .

Supply Chain Compromise: Malicious actors inject credential-stealing logic into popular open-source packages. This can occur through compromised build scripts (build.rs in Rust crates), preinstall scripts in npm packages, or by manipulating package manager upload mechanisms . The "Shai-Hulud" worm variants are prime examples, targeting SAP npm packages and others, exfiltrating cloud configurations and GitHub Actions secrets .

AI-Assisted Development Risks: AI coding assistants introduce novel risks. They can ingest secrets from prompts or cached commands, potentially leaking them into generated code or configuration files. For instance, the .claude/settings.local.json file has been observed leaking API keys . Similarly, AI agents may require local credentials to perform tasks, increasing the risk on developer endpoints. Some AI agent frameworks use "Model Context Protocol" (MCP) configuration files, which have been found to contain numerous secrets .

CI/CD Pipeline Exploitation: Compromised GitHub Actions workflows are a significant vector. Vulnerabilities like pull_request_target triggers, cache poisoning, or the exploitation of OIDC tokens can allow attackers to exfiltrate secrets stored in the CI/CD environment . Webhooks from systems like Harbor can also be exploited via SSRF to expose cloud IAM credentials .

Developer Endpoint as Attack Surface: Developer machines are becoming prime targets due to the accumulation of secrets. This includes secrets in shell history, .env files, AI tool configurations, browser storage (via DPAPI), and SSH keys . Tools like Lazagne, SharpChrome, and DonPAPI can harvest these credentials.

Collaboration Tools and Non-Code Sources: Secrets are frequently found in collaboration platforms like Slack, Jira, and Confluence, often in plain text messages or issue descriptions . GitHub comments, Gists, and even deleted commit histories can also reveal sensitive information .

Credential Verification and Harvesting: Attackers often don't just find secrets; they verify them. Automated scripts can test leaked API keys against cloud provider APIs or specific service endpoints to confirm their validity before attempting malicious actions .

Persistence Mechanisms: In some cases, attackers establish persistence. This can involve planting secret-dumping workflows, leveraging compromised tokens for ongoing access, or using mechanisms like Python's .pth files for stealthy execution .

Cloud Environment Exposure: Cloud IAM credentials, service account tokens, and API keys are frequently exposed in public repositories or via misconfigured cloud resources (e.g., unsecured S3 buckets, exposed container registries). This can lead to unauthorized access, data exfiltration, and resource abuse, such as cryptocurrency mining campaigns .