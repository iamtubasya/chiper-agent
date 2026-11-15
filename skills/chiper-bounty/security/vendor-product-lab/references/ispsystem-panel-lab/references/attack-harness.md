# Attack harness recipes for ISPsystem mgr5 panels

Reusable pieces from the BILLmanager 6.154.6 run. All verified working.

## 0. Resolve the panel address

ihttpd binds the WSL VM IP, **not** 127.0.0.1. Every script must resolve it at runtime:

```python
import subprocess
IP = subprocess.run(["hostname","-I"],capture_output=True,text=True).stdout.split()[0]
HOST = f"{IP}:1500"
BASE = f"https://{HOST}/billmgr"
```

## 1. Session login (the part everyone gets wrong)

`urllib.request.urlopen()` **ignores your opener**, so `HTTPCookieProcessor` never fires and you
silently scan as anonymous. Use `opener.open(req)` and assert the cookie is non-empty:

```python
import urllib.request, urllib.parse, ssl, http.cookiejar, re, time
CTX = ssl.create_default_context(); CTX.check_hostname=False; CTX.verify_mode=ssl.CERT_NONE

def login(user, pw):
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=CTX),
        urllib.request.HTTPCookieProcessor(cj))
    d = urllib.parse.urlencode(
        {"func":"auth","username":user,"password":pw,"lang":"en","sok":"ok"}).encode()
    r = urllib.request.Request(BASE, data=d, headers={
        "X-Requested-With":"XMLHttpRequest",
        "Content-Type":"application/x-www-form-urlencoded",
        "User-Agent":"Mozilla/5.0"})
    op.open(r, timeout=30).read()                 # <-- opener.open, NOT urlopen
    ck = "; ".join(f"{c.name}={c.value}" for c in cj)
    assert "billmgrses5=" in ck, "LOGIN FAILED - scanning as anonymous!"
    return ck
```

## 2. Call with retry + optional referer

```python
def call(ck, params, referer=None, timeout=40):
    data = urllib.parse.urlencode(params).encode()
    h = {"X-Requested-With":"XMLHttpRequest",
         "Content-Type":"application/x-www-form-urlencoded",
         "User-Agent":"Mozilla/5.0"}
    if ck: h["Cookie"] = ck
    if referer: h["Referer"] = referer
    r = urllib.request.Request(BASE, data=data, headers=h)
    last = None
    for i in range(5):
        try:
            with urllib.request.urlopen(r, timeout=timeout, context=CTX) as f:
                return f.status, f.read().decode('utf-8','replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8','replace')
        except Exception as e:
            last = e; time.sleep(1 + i)
    return 0, str(last)

REF = f"https://{HOST}/billmgr"   # satisfies the referer_confirm gate
```

## 3. Correct response classifier (order matters)

```python
FUNC_NOT_FOUND = ("Failed to find the", "Не удалось найти функцию",
                  "associated module is missing", "управляющий модуль не загружен")

def classify(body):
    b = body[:6000]
    if any(s in b for s in FUNC_NOT_FOUND):      return "NOFUNC"   # module absent
    if '"$type":"access"' in b or "Insufficient privileges" in b:
        return "DENIED"                          # gate held
    m = re.search(r'"[$]type":"([a-z_]+)"', b)
    if m:
        p = re.search(r'"param":\[\s*\{\s*"[$]name":"([a-z_]+)"', b)
        return "GATE_OPEN:" + m.group(1) + (":"+p.group(1) if p else "")
    if '"doc"' in b: return "EXECUTED"           # form render / wizard step
    return "OTHER"
```

Order is the whole lesson: NOFUNC → access → any `$type` → doc. Reversing any pair manufactures
false findings.

## 4. Seed two competing tenants (needed for any IDOR proof)

```sql
-- subaccounts are auto-created per account; reuse them
SELECT id, account FROM subaccount;               -- 1 -> acct 2, 2 -> acct 3

INSERT INTO payment (id, subaccount, status, paydate, currency,
                     paymethodamount, subaccountamount, number, description)
VALUES (1,1,4,NOW(),1,1000.0000,1000.0000,'PAY-A-001','TenantA secret payment'),
       (2,2,4,NOW(),1,7777.0000,7777.0000,'PAY-B-777','TenantB secret payment');

INSERT INTO expense (id, subaccount, amount, cdate, name)
VALUES (1,1,500.0000,CURDATE(),'TenantA expense secret'),
       (2,2,9999.0000,CURDATE(),'TenantB expense secret');
```

Note: `subaccount`, `payment`, `expense` have **no AUTO_INCREMENT** — supply explicit `id` or the
insert fails with `Field 'id' doesn't have a default value`.

The proof shape is the **owner-vs-foreign `elid` pair**: the same call must return full data for
the owner's id and `access` for the foreign id. Capture both.

## 5. Full-surface sweep

```bash
# enumerate (plugin funcs live in billmgr_mod_*.xml too)
grep -oh 'func="[^"]*"' /usr/local/mgr5/etc/xml/*.xml | sed 's/func="//;s/"//' | sort -u > funcs.json

# then loop funcs.json through classify() with a level-16 session, 2 workers
```

Run it **three times**: level-16, level-29, and no cookie. The three-way diff is what separates
"user-reachable by design" from "admin-only but reachable" from "unauthenticated".

## 6. Wizard-vs-action check

For any `.add` / `.create` / `.setup` that returns a clean doc, do BOTH:

```bash
grep -E "<funcname>" /usr/local/mgr5/var/billmgr.log | tail
#   wizard EXTINFO Wizard 'X' done     -> only step 1 rendered
mysql -u root billmgr -e "SELECT id FROM <table>;"   # zero rows = no action
```

A ~2.6 KB response is a form. A real write returns the created object.

## 7. Pitfalls hit in this run

- **MSYS path mangling**: `wsl ... bash /mnt/d/x.sh` becomes
  `C:/.../git/mnt/d/x.sh`. Always prefix with `MSYS_NO_PATHCONV=1`.
- **CRLF from Python file writes**: `open(p,"w")` on Windows writes `\r\n` and bash then dies with
  `syntax error near unexpected token $'do\r'`. Use `open(p,"w",newline='\n')`.
- **f-string backslash**: `f"{'\"doc\"' in b}"` is a SyntaxError on Python 3.9. Hoist to a
  constant: `DOC = chr(34)+"doc"+chr(34)`.
- **WSL idle drop**: the distro VM dies between commands; re-check
  `systemctl is-active mysqld ihttpd` and retry with backoff.
- **`awk` inside a `wsl -c '...'` heredoc** gets its quotes eaten. Put multi-line shell in a
  `.sh` file written by Python and run that instead.
