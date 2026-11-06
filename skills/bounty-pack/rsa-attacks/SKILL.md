---
name: rsa-attacks
author: RESEARCHER_NAME
description: "Offline RSA attack library: small-e, Fermat, Wiener, common-modulus, factordb, auto-dispatch."
category: security
version: 1.0.0
metadata:
  hermes:
    tags: [rsa-attacks]
---

# RSA Attacks Library

## Triggers
- RSA, RSA attack, Wiener attack, Fermat factor, factor N

## Quick Usage
```python
from rsa_attacks import auto, small_e_root, fermat_factor, wiener

# Auto-dispatch (tries cheap attacks in order)
plaintext_int = auto(c=2790, e=3, n=3233)

# Or specific attack
m = small_e_root(c, e=3)
p, q = fermat_factor(n)
d = wiener(e, n)
```

## Core Functions

### small_e_root (e <= 5)
```python
try:
    import gmpy2
    def _iroot(n, e):
        r, exact = gmpy2.iroot(gmpy2.mpz(n), e)
        return int(r), bool(exact)
except ImportError:
    def _iroot(n, e):
        lo, hi = 0, 1 << ((n.bit_length() + e - 1) // e + 1)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if mid ** e <= n: lo = mid
            else: hi = mid - 1
        return lo, lo ** e == n

def small_e_root(c, e=3):
    root, exact = _iroot(c, e)
    return root if exact else None
```

### fermat_factor (p,q close together)
```python
from math import isqrt

def fermat_factor(n, max_iter=1_000_000):
    a = isqrt(n)
    if a * a < n: a += 1
    for _ in range(max_iter):
        b2 = a * a - n
        b = isqrt(b2)
        if b * b == b2: return a - b, a + b
        a += 1
    return None
```

### wiener (small private exponent d)
```python
def wiener(e, n):
    def cf(num, den):
        while den:
            q = num // den; yield q
            num, den = den, num - q * den
    def conv(gen):
        h0,h1,k0,k1 = 0,1,1,0
        for a in gen:
            h0,h1 = h1, a*h1+h0
            k0,k1 = k1, a*k1+k0
            yield h1,k1
    for k,d in conv(cf(e,n)):
        if k==0: continue
        if (e*d-1)%k!=0: continue
        phi = (e*d-1)//k
        s = n-phi+1; disc = s*s-4*n
        if disc>=0:
            r=isqrt(disc)
            if r*r==disc and (s+r)%2==0: return d
    return None
```

## Pitfalls
- gmpy2 optional but 10-100x faster
- factordb may be down — fallback to local attacks
- Fermat only works when p,q are close
- Wiener only works with small d
