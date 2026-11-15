## Notable Techniques and Vulnerabilities

Notable Techniques and Vulnerabilities
A significant portion of authorization flaws stems from improper implementation of these core mechanics. Common attack patterns include:

• Insecure Direct Object Reference (IDOR): Applications expose object identifiers (e.g., numeric IDs, UUIDs) that can be manipulated by an attacker to access other users' data or resources . For example, changing a purchase inquiry ID in a URL might reveal another user's inquiry .
• Broken Object-Level Authorization (BOLA): This is a specific API-focused vulnerability where an API endpoint exposes an object identifier without verifying the API caller's permission to access that object. This is distinct from BOLA which might check if a user can perform an action, but not which specific object they can perform it on.
• Missing Function-Level Access Control: This occurs when an application fails to verify user permissions for specific functions or endpoints. For instance, an unauthenticated user might be able to access an administrative API endpoint . This is a common issue with APIs and internal administrative interfaces .
• Privilege Escalation: Attackers exploit vulnerabilities to gain higher-level access, such as moving from a standard user to an administrator or from a user to SYSTEM/root privileges. This can happen through misconfigurations in Active Directory (AD CS abuse, RBCD abuse) , kernel vulnerabilities , or flaws in application components .
• Mass Assignment: When an application blindly accepts and updates object attributes from user input, an attacker can potentially modify sensitive fields they shouldn't have access to, leading to identity drift or unauthorized actions .
• Path Traversal / Arbitrary File Write: Exploiting input validation flaws to read or write files outside the intended directory. This can often be chained with other vulnerabilities to achieve Remote Code Execution (RCE) . For example, unauthenticated path traversal in a guest portal could lead to RCE .
• JWT Manipulation: Weaknesses in JSON Web Token (JWT) validation, such as using weak secrets, algorithm confusion (e.g., accepting none algorithm), or improper signature verification, can lead to authentication bypass and privilege escalation .
• OAuth Application Authorization: Malicious OAuth applications can be authorized by users, granting them persistent access to user data and functionality even if the user's primary credentials change or multi-factor authentication is enforced .
• AI Agent Vulnerabilities:
• Agent Goal Hijack: Attackers manipulate AI agents to adopt attacker-controlled instructions as their own goals, overriding legitimate objectives .
• Prompt Injection: Adversarial inputs to AI models that cause them to behave in unintended or malicious ways, potentially bypassing authorization checks implicitly .
• Symlink Following in AI Tools: Some AI coding assistants have been found to exhibit symlink following vulnerabilities, allowing arbitrary file reads or writes, leading to RCE .
• AI-generated Code Flaws: AI tools can generate code with a significant percentage of design flaws or known security vulnerabilities, including authorization issues .
• Cloud-Native Exploits:
• Kubernetes RBAC Misconfigurations: Overly broad RBAC permissions granted to Kubernetes operators or service accounts create attack surfaces for privilege escalation and lateral movement .
• Cross-Tenant Compromise: Flaws in multi-tenant architectures, especially in cloud services, can allow attackers to access data or resources belonging to other tenants . This can happen via undocumented APIs or residual data issues .
• Service Account Misconfiguration: Excessive privileges granted to cloud service accounts (e.g., AWS IAM roles, GCP service agents) are a prime target for attackers seeking privilege escalation .
• Exploitation of Instance Metadata Service (IMDS): Pods running in cloud environments that can access IMDS (especially IMDSv2 if misconfigured) can potentially exfiltrate credentials, leading to further compromise .
• Kerberos Abuse: Complex attacks involving Kerberos delegation mechanisms, particularly when combined with weak configurations or protocol transitions, can lead to significant privilege escalation within Windows domains .
• Business Logic Flaws: Exploiting flaws in the intended application behavior, such as allowing users to order products for free or manipulate prices, often bypasses traditional authorization checks by exploiting the application's intended workflow .