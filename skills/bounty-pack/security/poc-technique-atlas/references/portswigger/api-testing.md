# PortSwigger WSA — API Testing
Source: https://portswigger.net/web-security/api-testing

## Technique headings
- API testing
- Related pages
- API recon
- API documentation
- Discovering API documentation
- Using machine-readable documentation
- Identifying API endpoints
- Interacting with API endpoints
- Identifying supported HTTP methods
- Note
- Identifying supported content types
- Using Intruder to find hidden endpoints
- Finding hidden parameters
- Mass assignment vulnerabilities
- Identifying hidden parameters
- Testing mass assignment vulnerabilities
- Preventing vulnerabilities in APIs
- Test APIs for vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/api-testing/server-side-parameter-pollution
- https://portswigger.net/web-security/api-testing/top-10-api-vulnerabilities


## Labs (2026-10-18 — per-lab scenarios & solutions), 3 lab)

- **Exploiting an API endpoint using documentation** (`lab-exploiting-api-endpoint-using-documentation`)
  - Solution • In Burp's browser, log in to the application using the credentials wiener:peter and update your email address. . • In Proxy > HTTP history , right-click the PATCH /api/user/wiener request and select Send to Repeater . . • Go to the Repeater tab. Send the PATCH /api/user/wiener request. Notice that this retrieves credentials for the user wiener . . • Remove /wiener from the path of the request, so the endpoint is now /api/user , then send the request. Notice that this returns an error because there is no user identifier. . • Remove /user from the path of the request, so the endpoint 
- **Finding and exploiting an unused API endpoint** (`lab-exploiting-unused-api-endpoint`)
  - Solution • In Burp's browser, access the lab and click on a product. . • In Proxy > HTTP history , notice the API request for the product. For example, /api/products/3/price . . • Right-click the API request and select Send to Repeater . . • In the Repeater tab, change the HTTP method for the API request from GET to OPTIONS , then send the request. Notice that the response specifies that the GET and PATCH methods are allowed. . • Change the method for the API request from GET to PATCH , then send the request. Notice that you receive an Unauthorized message. This may indicate that you need to b
- **Exploiting a mass assignment vulnerability** (`lab-exploiting-mass-assignment-vulnerability`)
  - Solution • In Burp's browser, log in to the application using the credentials wiener:peter . . • Click on the Lightweight "l33t" Leather Jacket product and add it to your basket. . • Go to your basket and click Place order . Notice that you don't have enough credit for the purchase. . • In Proxy > HTTP history , notice both the GET and POST API requests for /api/checkout . . • Notice that the response to the GET request contains the same JSON structure as the POST request. Observe that the JSON structure in the GET response includes a chosen_discount parameter, which is not present in the POST
