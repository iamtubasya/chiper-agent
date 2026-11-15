<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/sqli.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Attack Vectors

Notable Techniques and Attack Vectors
SQL injection techniques have evolved significantly, moving beyond simple error messages to exploit subtle behaviors and advanced database features. Understanding these methods is crucial for both offensive and defensive perspectives.

In-Band SQLi (Error-Based and UNION-Based)
This is the most common category, where attackers receive results or error messages directly through the application's response channel .

• 
 Error-Based SQLi: Exploits detailed error messages that applications might inadvertently expose. Attackers craft payloads that cause specific SQL errors, and the resulting messages leak information about the database schema, data, or even internal configurations .

 For example, in Snowflake, an attacker can force a compilation error using the SYSTEM$WAIT function combined with expressions that cannot be folded into a constant. The error message itself contains the folded expression, revealing sensitive information .

• 
 UNION-Based SQLi: This technique uses the UNION operator to combine the results of the original query with the results of a malicious query crafted by the attacker. This allows attackers to retrieve data from tables not normally accessible within the application's context . A key requirement is that the attacker's query must match the number and data types of columns in the original query's result set.

 A payload might look like: ' UNION SELECT username, password FROM users--

Inferential (Blind) SQLi
Blind SQLi is employed when an application does not directly return database errors or query results. Attackers infer information by observing indirect clues, such as differences in page content, response times, or out-of-band signals .

• 
 Boolean-Based Blind SQLi: Attackers construct payloads that result in a true or false condition. By observing differences in the application's response (e.g., a page loads, or a specific element appears/disappears), they can infer information one character or bit at a time .

 Example: ' OR 1=1-- (returns true) vs. ' OR 1=2-- (returns false).

• 
 Time-Based Blind SQLi: When boolean-based responses are unreliable, attackers inject commands that cause a time delay (e.g., SLEEP(5), pg_sleep(5), WAITFOR DELAY '0:0:5') only if a specific condition is met. By measuring the server's response time, attackers can confirm the truth of the condition .

 Example payload for PostgreSQL: ' AND pg_sleep(5)--

Out-of-Band (OOB) SQLi
This technique is used when direct feedback channels are blocked. Attackers force the database to make external network calls (like DNS lookups or HTTP requests) to a server they control, exfiltrating data via these callbacks . This often relies on database functions that can initiate network connections, such as xp_dirtree in SQL Server or load_file() in MySQL.

Second-Order SQLi
In second-order SQLi, the malicious payload is not executed immediately. Instead, it is stored in the database (e.g., in a user profile comment or a feedback entry) and then executed later when that stored data is retrieved and used in a different SQL query . This makes detection more challenging as the immediate request doesn't show obvious signs of compromise.

Advanced and Context-Specific Techniques

• 
 Abusing Database Features: Attackers can leverage legitimate database functionalities for malicious purposes. For instance, Oracle's embedded Java Virtual Machine (JVM) can be used to compile and execute malicious Java code stored as database objects, turning the database itself into a malware host . PostgreSQL's CREATE JAVA SOURCE and SQL functions like query_to_xml can also be weaponized .

• 
 GraphQL API SQLi: Despite GraphQL's API nature, it's not immune. Vulnerabilities can arise from improper handling of input parameters within GraphQL queries, leading to traditional SQLi .

• 
 LLM Gateway Exploitation: Applications acting as gateways for Large Language Models (LLMs), like LiteLLM, have become targets. Exploiting API key verification processes can lead to pre-authentication SQL injection, granting access to sensitive LLM provider credentials .

• 
 WAF Bypass: Web Application Firewalls (WAFs) are often bypassed using various encoding, obfuscation, and mutation techniques. These can include character substitution, comment injection, HTTP parameter pollution (HPP), and even leveraging the way WAFs parse JSON payloads .

• 
 PostgreSQL Specifics: PostgreSQL has unique features that can be exploited, such as its handling of invalid multibyte characters by psql leading to SQL injection , or the abuse of COPY TO/FROM PROGRAM if available . Specific functions like lo_export can facilitate file reads, and chained exploits can lead to OS command execution .

• 
 Constraint-Based Attacks: Some attacks focus on manipulating database constraints rather than directly injecting commands. This can involve exploiting how databases handle string trimming or length constraints, as demonstrated in a MySQL example where trailing whitespace in a username could lead to account takeover .

• 
 NoSQL Injection: While distinct from SQLi, NoSQL databases are also susceptible to injection attacks where unsanitized input manipulates query operators (e.g., $gt, $ne, $where in MongoDB) .