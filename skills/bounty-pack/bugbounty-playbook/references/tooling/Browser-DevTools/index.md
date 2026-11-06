# Browser DevTools

> tags: tooling, browser-devtools

> related: Tooling/Burp-Suite/, Tooling/AI-Assisted/, Attack-Surface/Web/Injection/XSS/

Browser DevTools
DevTools is underrated in bug bounty circles. Everyone talks about Burp but the browser itself exposes things Burp can't easily see - live DOM state, event listeners, service worker internals, WebSocket frames. Learn to use it well and you'll find XSS, auth bugs, and logic flaws that proxy-only hunters miss.
I work in Firefox and Chrome. Firefox's DevTools are better for JS debugging; Chrome's are better for performance and memory analysis. Keep both installed.
Network Tab
Request replay. Right-click any request > "Copy as fetch" or "Copy as cURL". Faster than repro-ing from scratch. For quick parameter testing without leaving the browser, use "Edit and Resend" (Firefox) - it's a lightweight Repeater.
Header analysis. I scan response headers in the Network tab while browsing, looking for: internal hostnames in Server or custom headers, version disclosure, inconsistent security headers across subdomains, X-Forwarded-For reflection.
WebSocket inspection. Network tab > filter "WS". Click the WebSocket connection to see the Frames tab. Every message, both directions, timestamped. Look for:

Auth tokens sent in WS messages (often weaker than HTTP auth)
User IDs or role claims in message bodies
Server-side logic errors exposed by unexpected message sequences
Unauthenticated channels (open the WS URL in a fresh incognito window)

For replaying WebSocket messages, I use the browser console: right-click the WS connection and copy the WebSocket URL, then:
const ws = new WebSocket('wss://target.com/ws');
ws.onopen = () => ws.send(JSON.stringify({action: "getUser", id: 2}));
ws.onmessage = (e) => console.log(e.data);
Console: DOM XSS Hunting
The console is your runtime analysis environment. I use it constantly for XSS hunting and understanding app logic.
Find all event listeners on a suspicious element:
// Chrome only
getEventListeners(document.querySelector('#search-input'))
// Returns object with event types and handlers
Trace where user input goes:
// Hook input fields to watch value flow
const input = document.querySelector('input[name="q"]');
const orig = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
Object.defineProperty(input, 'value', {
  set(v) {
    console.trace('value set to:', v);
    orig.set.call(this, v);
  }
});
Check for dangerous sinks receiving user-controlled data:
// Hook innerHTML to trace DOM writes
const origSet = Object.getOwnPropertyDescriptor(Element.prototype, 'innerHTML').set;
Object.defineProperty(Element.prototype, 'innerHTML', {
  set(v) {
    if (v.includes(location.hash.slice(1)) || v.includes(location.search.slice(1))) {
      console.warn('Potential DOM XSS sink:', v);
      console.trace();
    }
    origSet.call(this, v);
  }
});
Find all eval calls and document.write usage:
// Audit dangerous functions passively
['eval', 'document.write', 'document.writeln'].forEach(fn => {
  const parts = fn.split('.');
  const obj = parts.length > 1 ? window[parts[0]] : window;
  const name = parts[parts.length - 1];
  const orig = obj[name];
  obj[name] = function() { console.trace(fn, arguments); return orig.apply(this, arguments); };
});
Application Tab
This is where auth bugs live.
localStorage and sessionStorage. Check both for tokens, user data, and anything that shouldn't be client-side. Look for JWTs, API keys, user role claims. If you see a role or permission stored here, it's worth testing whether the server actually validates server-side or trusts the client value.
Cookies. Application > Cookies. Check each one:

HttpOnly missing on session tokens? XSS can steal it.
Secure missing? Downgrade risk.
SameSite missing or None? CSRF surface.
Expiry far in the future on sensitive tokens? Account takeover persistence risk.
Token format: JWT? Click Inspect > decode it in console with atob(token.split('.')[1]).

Service Workers. Application > Service Workers. Service workers intercept all network requests. Check registered workers for:

Caching sensitive responses (auth tokens, API responses)
Serving stale auth states (logout bypass)
Fetch event handlers that modify requests

To force a service worker update or unregister for clean testing:
navigator.serviceWorker.getRegistrations().then(regs => regs.forEach(r => r.unregister()));
IndexedDB and Cache Storage. Frequently overlooked. Apps store more here than developers realize - full API responses, user data, session artifacts.
Sources Tab: JS Analysis
Pretty-print minified JS with the {} button in the bottom toolbar. Then set breakpoints on interesting functions.
Find all URLs and endpoints in loaded JS:
// Run in console after page loads
performance.getEntriesByType('resource')
  .filter(r => r.initiatorType === 'script')
  .map(r => r.name)
Then open each one, pretty-print, and search for fetch(, XMLHttpRequest, axios, /api/, endpoint, token.
Conditional breakpoints. Right-click a line number in Sources > Add conditional breakpoint. Break only when req.userId !== currentUser.id - saves enormous time over stepping through everything.
Performance Tab: Race Condition Timing
Record a transaction (login, purchase, submit) and examine the timeline. Look for parallel requests that modify shared state. If the app fires two state-mutating requests within the same frame, it's worth testing with Turbo Intruder or a script sending concurrent requests.
// Rough race condition test in console
const requests = Array(20).fill(null).map(() =>
  fetch('/api/coupon/apply', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({code: 'SAVE50', orderId: '12345'})
  }).then(r => r.json())
);
Promise.all(requests).then(results => console.log(results));
Check the Network tab timing after - did multiple requests get 200? Did the discount apply multiple times?
Linked Notes

Burp Suite - proxy complement, deeper request manipulation
AI Assisted - feed JS to LLMs after extracting with DevTools
XSS - DOM XSS hunting techniques
