# PortSwigger WSA — Race Conditions
Source: https://portswigger.net/web-security/race-conditions

## Technique headings
- Race conditions
- PortSwigger Research
- Limit overrun race conditions
- Detecting and exploiting limit overrun race conditions with Burp Repeater
- Read more
- Detecting and exploiting limit overrun race conditions with Turbo Intruder
- Hidden multi-step sequences
- Note
- Methodology
- 1 - Predict potential collisions
- 2 - Probe for clues
- 3 - Prove the concept
- Multi-endpoint race conditions
- Aligning multi-endpoint race windows
- Connection warming
- Abusing rate or resource limits
- Single-endpoint race conditions
- Session-based locking mechanisms
- Partial construction race conditions
- Time-sensitive attacks
- How to prevent race condition vulnerabilities
- Find race condition vulnerabilities using Burp Suite


## Labs (2026-10-18 — per-lab scenarios & solutions), 6 lab)

- **Limit overrun race conditions** (`lab-race-conditions-limit-overrun`)
  - Solution - Burp Suite Professional Predict a potential collision • Log in and buy the cheapest item possible, making sure to use the provided discount code so that you can study the purchasing flow.. • Consider that the shopping cart mechanism and, in particular, the restrictions that determine what you are allowed to order, are worth trying to bypass.. • In Burp, from the proxy history, identify all endpoints that enable you to interact with the cart. For example, a POST /cart request adds items to the cart and a POST /cart/coupon request applies the discount code.. • Try to identify any rest
- **Bypassing rate limits via race conditions** (`lab-race-conditions-bypassing-rate-limits`)
  - Passwords 123123 abc123 football monkey letmein shadow master 666666 qwertyuiop 123321 mustang 123456 password 12345678 qwerty 123456789 12345 1234 111111 1234567 dragon 1234567890 michael x654321 superman 1qaz2wsx baseball 7777777 121212 000000
- **Multi-endpoint race conditions** (`lab-race-conditions-multi-endpoint`)
  - Solution Predict a potential collision • Log in and purchase a gift card so you can study the purchasing flow.. • Consider that the shopping cart mechanism and, in particular, the restrictions that determine what you are allowed to order, are worth trying to bypass.. • From the proxy history, identify all endpoints that enable you to interact with the cart. For example, a POST /cart request adds items to the cart and a POST /cart/checkout request submits your order.. • Add another gift card to your cart, then send the GET /cart request to Burp Repeater.. • In Repeater, try sending the GET /car
- **Single-endpoint race conditions** (`lab-race-conditions-single-endpoint`)
  - Solution Predict a potential collision • Log in and attempt to change your email to anything@exploit-<YOUR-EXPLOIT-SERVER-ID>.exploit-server.net . Observe that a confirmation email is sent to your intended new address, and you're prompted to click a link containing a unique token to confirm the change.. • Complete the process and confirm that your email address has been updated on your account page.. • Try submitting two different @exploit-<YOUR-EXPLOIT-SERVER-ID>.exploit-server.net email addresses in succession, then go to the email client.. • Notice that if you try to use the first confirmat
- **Exploiting time-sensitive vulnerabilities** (`lab-race-conditions-exploiting-time-sensitive-vulnerabilities`)
  - Solution Study the behavior • Study the password reset process by submitting a password reset for your own account and observe that you're sent an email containing a reset link. The query string of this link includes your username and a token.. • Send the POST /forgot-password request to Burp Repeater.. • In Repeater, send the request a few times, then check your inbox again.. • Observe that every reset request results in a link with a different token.. • Consider the following:. • The token is of a consistent length. This suggests that it's either a randomly generated string with a fixed numb
- **Partial construction race conditions** (`lab-race-conditions-partial-construction`)
  - Hint You may need to experiment with different ways of lining up the race window to successfully exploit this vulnerability. .
