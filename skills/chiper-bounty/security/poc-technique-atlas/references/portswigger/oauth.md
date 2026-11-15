# PortSwigger WSA — OAuth Authentication
Source: https://portswigger.net/web-security/oauth

## Technique headings
- OAuth 2.0 authentication vulnerabilities
- Labs
- What is OAuth?
- Note
- How does OAuth 2.0 work?
- Read more
- OAuth authentication
- How do OAuth authentication vulnerabilities arise?
- Identifying OAuth authentication
- Recon
- Exploiting OAuth authentication vulnerabilities
- Vulnerabilities in the OAuth client application
- Improper implementation of the implicit grant type
- Flawed CSRF protection
- Leaking authorization codes and access tokens
- Flawed redirect_uri validation
- Stealing codes and access tokens via a proxy page
- Flawed scope validation
- Scope upgrade: authorization code flow
- Scope upgrade: implicit flow
- Unverified user registration
- Extending OAuth with OpenID Connect
- Preventing OAuth authentication vulnerabilities
- Find OAuth 2.0 authentication vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/oauth/grant-types
- https://portswigger.net/web-security/oauth/openid
- https://portswigger.net/web-security/oauth/preventing


## Labs (2026-10-18 — per-lab scenarios & solutions), 5 lab)

- **Authentication bypass via OAuth implicit flow** (`lab-oauth-authentication-bypass-via-oauth-implicit-flow`)
  - Solution • While proxying traffic through Burp, click "My account" and complete the OAuth login process. Afterwards, you will be redirected back to the blog website. • In Burp, go to "Proxy" > "HTTP history" and study the requests and responses that make up the OAuth flow. This starts from the authorization request GET /auth?client_id=[...] . • Notice that the client application (the blog website) receives some basic information about the user from the OAuth service. It then logs the user in by sending a POST request containing this information to its own /authenticate endpoint, along with the
- **Forced OAuth profile linking** (`lab-oauth-forced-oauth-profile-linking`)
  - Solution • While proxying traffic through Burp, click "My account". You are taken to a normal login page, but notice that there is an option to log in using your social media profile instead. For now, just log in to the blog website directly using the classic login form. • Notice that you have the option to attach your social media profile to your existing account. • Click "Attach a social profile". You are redirected to the social media website, where you should log in using your social media credentials to complete the OAuth flow. Afterwards, you will be redirected back to the blog website. 
- **OAuth account hijacking via redirect_uri** (`lab-oauth-account-hijacking-via-redirect-uri`)
  - Solution • While proxying traffic through Burp, click "My account" and complete the OAuth login process. Afterwards, you will be redirected back to the blog website. • Log out and then log back in again. Observe that you are logged in instantly this time. As you still had an active session with the OAuth service, you didn't need to enter your credentials again to authenticate yourself. • In Burp, study the OAuth flow in the proxy history and identify the most recent authorization request. This should start with GET /auth?client_id=[...] . Notice that when this request is sent, you are immediat
- **Stealing OAuth access tokens via an open redirect** (`lab-oauth-stealing-oauth-access-tokens-via-an-open-redirect`)
  - Solution • While proxying traffic through Burp, click "My account" and complete the OAuth login process. Afterwards, you will be redirected back to the blog website. • Study the resulting requests and responses. Notice that the blog website makes an API call to the userinfo endpoint at /me and then uses the data it fetches to log the user in. Send the GET /me request to Burp Repeater. • Log out of your account and log back in again. From the proxy history, find the most recent GET /auth?client_id=[...] request and send it to Repeater. • In Repeater, experiment with the GET /auth?client_id=[...
- **Stealing OAuth access tokens via a proxy page** (`lab-oauth-stealing-oauth-access-tokens-via-a-proxy-page`)
  - Solution • Study the OAuth flow while proxying traffic through Burp. Using the same method as in the previous lab , identify that the redirect_uri is vulnerable to directory traversal. This enables you to redirect access tokens to arbitrary pages on the blog website. • Using Burp, audit the other pages on the blog website. Observe that the comment form is included as an iframe on each blog post. Look closer at the /post/comment/comment-form page in Burp and notice that it uses the postMessage() method to send the window.location.href property to its parent window. Crucially, it allows messages
