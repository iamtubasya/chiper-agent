## Notable Techniques and Attack Vectors

Notable Techniques and Attack Vectors
IDOR vulnerabilities manifest in numerous ways, often disguised by the application's normal functionality. Advanced hunters look beyond simple numeric ID manipulation to uncover more complex attack vectors.

Sequential and Predictable Identifiers
The most basic form of IDOR involves easily predictable identifiers, typically sequential integers. An attacker can enumerate these by incrementing or decrementing the ID in a request parameter. For example, GET /user/profile?id=123 can be tested with id=124 or id=122 . This technique is highly effective for targets with many user-generated objects where IDs are assigned sequentially and not properly restricted . While switching to GUIDs or UUIDs mitigates brute-force enumeration, it does not inherently fix the underlying authorization flaw if these IDs are exposed or guessable .

Exploiting Object References in Various Request Components
IDORs are not limited to URL parameters. Attackers actively probe other areas of HTTP requests:

• Request Bodies: JSON payloads, form data, and multipart/form-data uploads can contain object identifiers. Manipulating userId in a JSON object or a hidden form field can lead to unauthorized access or modification .
• HTTP Headers: Custom headers, such as X-User-ID or Authorization tokens containing embedded IDs, can be targeted for manipulation .
• File Paths and Names: Applications serving files based on user-supplied filenames can be vulnerable to IDOR combined with path traversal, allowing access to arbitrary files on the server .
• GraphQL Queries: In GraphQL, specific object IDs within queries or mutations can be manipulated. If a resolver fails to validate ownership for the requested object, it can lead to data disclosure or unauthorized actions .
Second-Order and Multi-Step IDORs
These vulnerabilities are harder to detect as the initial interaction may appear secure.

• Second-Order IDOR: The user-supplied identifier is stored and then used later in a process without re-validating its ownership . For instance, an input might be stored and later used in an internal API call where authorization is not checked .
• Multi-Step IDOR: Authorization checks might be missing or weak across multiple steps in a workflow. While individual steps may be secure, the final step that saves or processes data might fail to re-verify permissions, allowing an attacker to manipulate data from earlier steps .
Mass Assignment and Parameter Pollution
Modern applications often use object-oriented structures or parameter parsing that can be exploited.

• Mass Assignment: If an application automatically assigns user input to object properties without proper filtering, an attacker might be able to inject additional fields like isAdmin=true or modify sensitive attributes .
• Parameter Pollution: Providing multiple values for the same parameter or using different parameter names can confuse the backend's parsing logic, potentially bypassing authorization checks .
Blind IDORs
In blind IDORs, the application may not directly return data, but the action (e.g., deletion, update) succeeds on another user's object. Confirmation might come from observing side effects like email notifications, webhook callbacks, or time differences in response .

IDORs in Account Recovery and Password Reset Flows
A critical attack vector involves IDORs within password reset functionalities. If the system generates a reset token or link using a user-controllable identifier and fails to validate ownership, an attacker can reset another user's password and take over their account .

IDORs in Role/Permission Management
Some IDORs allow regular users to access or modify administrative functions or data by manipulating identifiers related to roles or permissions .