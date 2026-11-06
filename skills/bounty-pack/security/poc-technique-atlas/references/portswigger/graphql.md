# PortSwigger WSA — GraphQL API
Source: https://portswigger.net/web-security/graphql

## Technique headings
- GraphQL API vulnerabilities
- More information
- Finding GraphQL endpoints
- Note
- Universal queries
- Common endpoint names
- Request methods
- Initial testing
- Exploiting unsanitized arguments
- Discovering schema information
- Using introspection
- Probing for introspection
- Running a full introspection query
- Visualizing introspection results
- Suggestions
- Bypassing GraphQL introspection defenses
- Bypassing rate limiting using aliases
- GraphQL CSRF
- How do CSRF over GraphQL vulnerabilities arise?
- Preventing GraphQL attacks
- Preventing GraphQL brute force attacks
- Preventing CSRF over GraphQL
- Test GraphQL APIs using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/graphql/what-is-graphql


## Labs (2026-10-18 — per-lab scenarios & solutions), 5 lab)

- **Accessing private GraphQL posts** (`lab-graphql-reading-private-posts`)
  - Solution Identify the vulnerability . • In Burp's browser, access the blog page. . • In Burp, go to Proxy > HTTP history and notice the following: . • Blog posts are retrieved using a GraphQL query. • In the response to the GraphQL query, each blog post has its own sequential id . • Blog post id 3 is missing from the list. This indicates that there is a hidden blog post. • Find the POST /graphql/v1 request. Right-click it and select Send to Repeater . . • In Repeater, right-click anywhere in the Request panel of the message editor and select GraphQL > Set introspection query to insert an intro
- **Accidental exposure of private GraphQL fields** (`lab-graphql-accidental-field-exposure`)
  - Solution Identify the vulnerability . • In Burp's browser, access the lab and select My account . . • Attempt to log in to the site. . • In Burp, go to Proxy > HTTP history and notice that the login attempt is sent as a GraphQL mutation containing a username and password. . • Right-click the login request and select Send to Repeater . . • In Repeater, right-click anywhere within the Request panel of the message editor and select GraphQL > Set introspection query to insert an introspection query into the request body. . • Send the request. . • Right-click the message and select GraphQL > Save G
- **Finding a hidden GraphQL endpoint** (`lab-graphql-find-the-endpoint`)
  - Solution Find the hidden GraphQL endpoint . • In Repeater, send requests to some common GraphQL endpoint suffixes and inspect the results. . • Note that when you send a GET request to /api the response contains a "Query not present" error. This hints that there may be a GraphQL endpoint responding to GET requests at this location. . • Amend the request to contain a universal query. Note that, because the endpoint is responding to GET requests, you need to send the query as a URL parameter. . For example: /api?query=query{__typename} . . • Notice that the response confirms that this is a GraphQ
- **Bypassing GraphQL brute force protections** (`lab-graphql-brute-force-protection-bypass`)
  - Tip This lab requires you to craft a large request that uses aliases to send multiple login attempts at the same time. As this request could be time-consuming to create manually, we recommend you use a script to build the request. . The below example JavaScript builds a list of aliases corresponding to our list of authentication lab passwords and copies the request to your clipboard. To run this script: . • Open the lab in Burp's browser. • Right-click the page and select Inspect . • Select the Console tab. • Paste the script and press Enter. You can then use the generated aliases when craftin
- **Performing CSRF exploits over GraphQL** (`lab-graphql-csrf-via-graphql-api`)
  - Solution • Open Burp's browser, access the lab and log in to your account. . • Enter a new email address, then click Update email . . • In Burp, go to Proxy > HTTP history and check the resulting request. Note that the email change is sent as a GraphQL mutation. . • Right-click the email change request and select Send to Repeater . . • In Repeater, amend the GraphQL query to change the email to a second different address. . • Click Send . . • In the response, notice that the email has changed again. This indicates that you can reuse a session cookie to send multiple requests. . • Convert the r
