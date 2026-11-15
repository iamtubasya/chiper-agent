<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/osint.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Tactics

Notable Techniques and Tactics
For application security professionals, understanding specific OSINT techniques can directly inform vulnerability discovery and risk assessment.

Google Dorking
Google's advanced search operators, often referred to as "Google dorks" or "Google hacking," allow for highly precise queries that can uncover information not readily discoverable through standard searches . These operators can target specific file types, keywords within URLs or page titles, and even exclude certain domains or subdomains .

Examples include:

• site:example.com filetype:pdf confidential to find sensitive PDF documents on a specific domain .
• site:example.com inurl:admin to locate potential administrative interfaces .
• intitle:"index of" site:example.com to find directory listings .
• filetype:env site:example.com to discover environment files that may contain credentials or API keys .
The Google Hacking Database (GHDB) serves as a repository of pre-built dorks for various categories . Automation of Google dorking is also possible for continuous monitoring .

Social Media Intelligence (SOCMINT)
Social media platforms are rich sources of information about individuals and organizations. SOCMINT involves gathering and analyzing data from these platforms to understand trends, sentiments, and behaviors . Techniques include profile analysis, network mapping (identifying connections and interactions), and hashtag tracking to understand how information propagates . Geolocation data embedded in posts or inferred from visual cues can also be critical . For application security, this can reveal employee habits, company structures, and potentially exposed credentials or sensitive information shared inadvertently .

Publicly Exposed Files and Metadata Analysis
Tools like Metagoofil and FOCA can extract valuable metadata from publicly available documents (PDFs, Office files, etc.) . This metadata can reveal internal usernames, file paths, software versions, and other details that can aid in reconnaissance and understanding an organization's internal structure . Similarly, tools can scan for exposed files and directories on domains .

Certificate Transparency (CT) Logs
Certificate Transparency logs, which are publicly accessible, can reveal hostnames, including those for internal applications that may have been unintentionally exposed when certificates were requested . Tools like CertSpotter can query these logs, essentially acting like Shodan but for domain names .

Internet-Connected Device Discovery
Engines like Shodan and Censys are invaluable for discovering internet-connected devices and services . They index open ports, service banners, SSL certificates, and device metadata, allowing security professionals to identify exposed systems, misconfigurations, and outdated software that could be targeted .

Username Enumeration
Tools like Sherlock, WhatsMyName, and user-scanner can check username availability across hundreds of platforms . This helps in building a profile of an individual or identifying if an alias is reused across different services, which is crucial for SOCMINT and fraud investigations .

Dark Web Intelligence (DARKInt)
DARKInt focuses on gathering information from the dark web, a part of the internet accessible only through specific software like Tor . This includes monitoring hacker forums, marketplaces, and leaked databases for stolen credentials, illicit goods, and discussions about exploiting vulnerabilities . Tools like Intelligence X and DarkSearch.io facilitate this type of investigation .

Typing Style as a Digital Fingerprint
Emerging research highlights that typing patterns (speed, rhythm, keystroke timings) can act as a unique digital fingerprint, potentially bypassing traditional anonymization techniques . While not a direct OSINT tool, this concept underscores the depth of passive biometric data that can be exfiltrated, adding another layer to identity analysis.