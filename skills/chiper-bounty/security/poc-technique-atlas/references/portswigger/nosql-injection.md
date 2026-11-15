# PortSwigger WSA — NoSQL Injection
Source: https://portswigger.net/web-security/nosql-injection

## Technique headings
- NoSQL injection
- More information
- Types of NoSQL injection
- NoSQL syntax injection
- Detecting syntax injection in MongoDB
- Note
- Determining which characters are processed
- Confirming conditional behavior
- Overriding existing conditions
- Warning
- NoSQL operator injection
- Submitting query operators
- Detecting operator injection in MongoDB
- Exploiting syntax injection to extract data
- Exfiltrating data in MongoDB
- Identifying field names
- Exploiting NoSQL operator injection to extract data
- Injecting operators in MongoDB
- Extracting field names
- Exfiltrating data using operators
- Timing based injection
- Preventing NoSQL injection
- Find NoSQL injection vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/nosql-injection/nosql-databases


## Labs (2026-10-18 — per-lab scenarios & solutions), 3 lab)

- **Detecting NoSQL injection** (`lab-nosql-injection-detection`)
  - Solution • In Burp's browser, access the lab and click on a product category filter. . • In Burp, go to Proxy > HTTP history . Right-click the category filter request and select Send to Repeater . . • In Repeater, submit a ' character in the category parameter. Notice that this causes a JavaScript syntax error. This may indicate that the user input was not filtered or sanitized correctly. . • Submit a valid JavaScript payload in the value of the category query parameter. You could use the following payload: . Gifts'+' Make sure to URL-encode the payload by highlighting it and using the Ctrl-U 
- **Exploiting NoSQL operator injection to bypass authentication** (`lab-nosql-injection-bypass-authentication`)
  - Solution • In Burp's browser, log in to the application using the credentials wiener:peter . . • In Burp, go to Proxy > HTTP history . Right-click the POST /login request and select Send to Repeater . . • In Repeater, test the username and password parameters to determine whether they allow you to inject MongoDB operators: . • Change the value of the username parameter from "wiener" to {"$ne":""} , then send the request. Notice that this enables you to log in. • Change the value of the username parameter from {"$ne":""} to {"$regex":"wien.*"} , then send the request. Notice that you can also l
- **Exploiting NoSQL operator injection to extract unknown fields** (`lab-nosql-injection-extract-unknown-fields`)
  - Tip To solve the lab, you'll first need to exfiltrate the value of the password reset token for the user carlos . .
