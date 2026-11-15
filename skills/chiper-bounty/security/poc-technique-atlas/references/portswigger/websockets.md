# PortSwigger WSA — WebSockets
Source: https://portswigger.net/web-security/websockets

## Technique headings
- WebSockets
- Read more
- Labs
- Manipulating WebSocket traffic
- Intercepting and modifying WebSocket messages
- Note
- Replaying and generating new WebSocket messages
- Manipulating WebSocket connections
- WebSockets security vulnerabilities
- Manipulating WebSocket messages to exploit vulnerabilities
- Manipulating the WebSocket handshake to exploit vulnerabilities
- Using cross-site WebSockets to exploit vulnerabilities
- How to secure a WebSocket connection
- Find WebSocket vulnerabilities using Burp Suite

## Sub-topic pages
- https://portswigger.net/web-security/websockets/cross-site-websocket-hijacking
- https://portswigger.net/web-security/websockets/what-are-websockets


## Labs (2026-10-18 — per-lab scenarios & solutions), 2 lab)

- **Manipulating the WebSocket handshake to exploit vulnerabilities** (`lab-manipulating-handshake-to-exploit-vulnerabilities`)
  - Click "Live chat" and send a chat message. In Burp Proxy, go to the WebSockets history tab, and observe that the chat message has been sent via a WebSocket message. Right-click on the message and select "Send to Repeater". Edit and resend the message containing a basic XSS payload, such as: <img src=1 onerror='alert(1)'> Observe that the attack has been blocked, and that your WebSocket connection has been terminated.
- **Manipulating WebSocket messages to exploit vulnerabilities** (`lab-manipulating-messages-to-exploit-vulnerabilities`)
  - Click "Live chat" and send a chat message. In Burp Proxy, go to the WebSockets history tab, and observe that the chat message has been sent via a WebSocket message. Using the browser, send a new message containing a < character. In Burp Proxy, find the corresponding WebSocket message and observe that the < has been HTML-encoded by the client before sending. Ensure that Burp Proxy is configured to intercept WebSocket 
