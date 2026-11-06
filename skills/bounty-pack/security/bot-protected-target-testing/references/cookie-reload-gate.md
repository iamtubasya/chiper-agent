# Cookie reload gate — hosted-storefront "empty page" that is not empty

Measured 2026-10-29 on `insidershop.kohls.com` (Brightsites / `mybrightsites.com` storefront,
Rails backend, support link `support.brightstores.com`).

## Symptom

Every single path — `/`, `/login`, `/robots.txt`, `/sitemap.xml`, even nonsense — returns an
identical tiny page:

```
HTTP/1.1 200 OK
content-length: 110
content-type: text/html; charset=utf-8
set-cookie: pcc_bpc=TPoqnUjhn+riu...<long base64>; Max-Age=2592000; Path=/; Secure; SameSite=None
set-cookie: _bsites.liquid.session=<hex>; Path=/; Secure

<!DOCTYPE html><html><body><script type="text/javascript">window.location.reload()</script></body></html>
```

A HEAD/GET with `curl` or a one-shot `requests.get()` sees 110 bytes and the obvious conclusions are
all wrong: "host is empty", "200 with no body = stub", "every path returns the same thing = soft-404
catch-all, nothing to test". It is none of those — it is a cookie challenge.

## Cause

The edge hands the browser a cookie and asks it to reload. A browser does this transparently, which is
why the site looks completely normal in Chrome while a scripted client sees an empty shell. Only
clients that **discard cookies between requests** are affected.

## Protocol — request twice with a persistent session

```python
import requests
s = requests.Session()                      # the cookie jar IS the fix
s.headers.update({"User-Agent": "<UA the program requires>"})
r1 = s.get(B + "/login", timeout=30)        # 200, 110 bytes, sets pcc_bpc
r2 = s.get(B + "/login", timeout=30)        # 200, ~94 KB — the real page
```

Verify you are through before doing anything else:

```python
assert len(r2.text) > 10_000, "still gated — check the cookie jar is persisting"
```

With `curl`, use `-b jar -c jar` and run the command twice (or `-L` will not help — the reload is
client-side JS, not a 3xx).

## Second gate: Rails CSRF token

Once past the cookie gate, every state-changing form carries a Rails `authenticity_token` that must be
scraped from the page and replayed:

```python
m = re.search(r'<input[^>]*name="authenticity_token"[^>]*>', r.text)
tok = re.search(r'value="([^"]+)"', m.group(0)).group(1)
```

`PUT`/`PATCH` are sent as `POST` with a `_method` field (`_method: "put"`).

**Debounced-input trap:** the token is **not** on the product page for the add-to-cart form. The form
posts to a different endpoint than the page URL:

```html
<form action="/products/<id>/populate" method="post">   <!-- not /products/<id> -->
  <select name="product[options][<optionId>][sub_option]">
  <input  name="product[quantity]" value="1">
  <button name="add_to_cart" value="Add to Cart">
</form>
```

Option selects are nested — `product[options][16124493][sub_option]=42763683` — and price modifiers
appear as `<option data-label="2XL" data-charge="...">2XL (+$2.00)</option>` in the rendered label only.
Posting to the page URL instead of `/populate` silently does nothing and reads as "add to cart broken".

## Generalisation

Cross-check any "empty 200" against the **second request with a cookie jar**. The same shape shows up on
BigCommerce, Salesforce Commerce Cloud and other managed storefronts under names like `*_bpc`,
`*_session_ctx`, `bm_sz`. Rule:

> A uniform tiny `200` body on every path is a challenge page until proven otherwise.
> Re-request with a persistent session before recording the host as dead or as a soft-404 catch-all.
