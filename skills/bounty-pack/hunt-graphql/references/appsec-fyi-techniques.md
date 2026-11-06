<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/graphql.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques

Notable Techniques
The attack surface presented by GraphQL is multifaceted, encompassing vulnerabilities rooted in its fundamental design principles as well as common web application security flaws.

Introspection Abuse
GraphQL's introspection system is a powerful feature that allows clients to query the API schema for information about types, fields, queries, mutations, and their relationships. While invaluable for developers during development and for tooling, enabling introspection in production environments can be a significant security risk. Attackers can leverage this to gain a comprehensive understanding of the API's structure, identify sensitive data types, discover deprecated fields, and map out potential attack paths, effectively creating a blueprint for further exploitation. 

Injection Attacks
While GraphQL itself is a query language, the underlying resolvers that process these queries can be vulnerable to traditional injection attacks if input is not properly validated or sanitized. This includes:

• SQL/NoSQL Injection: Arguments passed to GraphQL queries or mutations can be directly incorporated into database queries, leading to SQL or NoSQL injection if not parameterized. 
• Command Injection: Similar to SQL injection, if resolver logic constructs shell commands using unsanitized user input, OS command injection is possible. 
• Server-Side Request Forgery (SSRF): Fields that accept URLs as input (e.g., for webhooks, image fetching) can be exploited to make the server issue requests to arbitrary internal or external resources. 
• Cross-Site Scripting (XSS): If mutation inputs are later rendered on a web page without proper sanitization, stored XSS vulnerabilities can be introduced. 
Authorization and Access Control Flaws
GraphQL’s flexible querying model complicates the implementation of robust access control. Without proper validation at the resolver level, attackers can exploit various flaws:

• Broken Object-Level Authorization (BOLA) / Insecure Direct Object Reference (IDOR): This is one of the most critical and common vulnerabilities. If resolvers do not verify that the authenticated user has permission to access a specific object or record (often identified by sequential IDs), attackers can manipulate identifiers to access or modify data belonging to other users or tenants. This has been observed in critical systems like airline booking APIs. 
• Broken Function-Level Authorization: Attackers might bypass authorization checks for specific operations or functions that should be restricted to certain roles. 
• Privilege Escalation: Flaws in authorization logic can allow users to gain administrative privileges, leading to full system compromise. 
• Unrestricted Access to Sensitive Business Flows: Certain business processes exposed via GraphQL mutations might not have adequate controls, allowing unauthorized execution. 
Denial of Service (DoS) and Resource Exhaustion
The client's ability to define complex queries can be exploited to overwhelm server resources:

• Deeply Nested Queries (Query Depth): Attackers can craft queries with excessive nesting levels, forcing the server to perform a disproportionately large number of recursive calls, exhausting CPU and memory. 
• Query Complexity and Alias Overloading: Queries can be designed to include a vast number of fields or aliases, leading to significant computational load. 
• Batching Attacks: GraphQL servers often support batching multiple queries or mutations into a single HTTP request. This can be abused to bypass rate limits, perform brute-force attacks (e.g., on login credentials or OTPs), or cause DoS by sending a large number of operations at once. 
• Field Duplication: Including the same field multiple times within a query can force the server to process redundant computations. 
• Circular Queries: Exploiting relationships between types to create queries that infinitely loop or traverse the same data structures repeatedly. 
Supply Chain and Code Injection Risks
Vulnerabilities in GraphQL implementations can also have broader supply chain implications, as demonstrated by recent GitLab vulnerabilities.

• Code Injection via GraphQL Directives: Exploiting flaws in how GraphQL directives are processed can lead to unauthenticated code injection, allowing attackers to modify or delete public projects and data. 
Broken Authentication
GraphQL implementations are not immune to classic authentication bypass vulnerabilities. If authentication mechanisms are improperly implemented or bypassed, attackers can gain unauthorized access. 