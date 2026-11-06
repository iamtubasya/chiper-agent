## Rate-limit headers that are not enforced

`x-ratelimit-remaining: 120` in every response does NOT mean the limit is enforced. A SLOW
loop never triggers the limiter (the window refills between requests) — 120 requests over
50s (~143/min) produced zero 429s and looked "fine". The decisive test is a FAST burst:
140 parallel requests in 3.9s (~2,163/min) → still 200 ×140, no 429, no Retry-After, while
the header value lagged (99–107 mid-burst, 37 after 5s, 119 after 15s). Report the header
as informational and the documented 429 as never observed; do not confuse "no limits" with
"Cloudflare eventually IP-blocked me" (Error 1010) — a blunt edge block is not the
documented per-key quota, and it also hits legitimate script traffic.

