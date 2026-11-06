# security.txt-driven scope mapping — the ONE reference for policies that define scope by presence

For policies that scope by **the presence of `/.well-known/security.txt`** rather than by a host list.
The file's presence IS the authorisation boundary, so measure it empirically — never infer scope from
"that hostname looks like their infrastructure".

Supersedes the short-lived `securitytxt-defined-scope.md`.

---

## 1. Why status codes lie

Four outcomes look alike if you only read `%{http_code}`:

| What you get | What it means | In scope? |
|---|---|---|
| `200` + `Contact: mailto:<their address>` | the real canonical file | **IN** |
| `302` → an in-scope host's canonical file, final `200` | their infra deliberately redirects it here | **IN** (state the reading you took) |
| `200` + an HTML error page | soft-200 — e.g. a Shopware *"Sales Channel Not Found"* page, a branded 404 template | **OUT** |
| `404`, or `302` somewhere unrelated | host sits on different infrastructure | **OUT** |

Fetch with `-L` and **match the canonical content string**, never the status code alone.

## 2. Recipe (one GET per host — not volumetric)

```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
CANON="Contact: mailto:security@<target>"          # copied from the canonical file you already fetched

: > recon/securitytxt_map.txt
while read -r line; do
  h=$(echo "$line" | awk '{print $1}' | sed 's#https\?://##' | cut -d/ -f1)
  [ -z "$h" ] && continue
  out=$(curl -s -A "$UA" -L --max-time 12 "https://$h/.well-known/security.txt" 2>/dev/null)
  if echo "$out" | grep -q "$CANON"; then echo "$h :: IN-SCOPE"; else echo "$h :: out"; fi
done < recon/httpx.txt >> recon/securitytxt_map.txt

grep "IN-SCOPE" recon/securitytxt_map.txt | tee recon/in_scope_hosts.txt
cp recon/subs_raw.txt subs.txt                      # the 0B checkpoint expects this exact name
```

Sleep ~0.3–0.5 s between hosts. 150 hosts finishes in minutes and stays inside a "no DoS / no brute
force" rule because it is one GET per host.

## 3. Rule-vs-summary ambiguity is normal — record which reading you applied

Policies frequently say two contradictory things at once, e.g. *"only domains/subdomains which have a
security.txt file in their root are in scope"* **and** *"currently, the scope is limited to
https://orf.at"*. Apply the **written rule** (the file test, which has an explicit subdomain example),
stay conservative on anything genuinely ambiguous, and state the reading in the report. Do not let a
tempting hostname pull you across a line the policy draws.

## 4. Re-check hosts discovered LATER — this is the step that gets skipped

Subdomains found in a JS bundle or a CSP (`connect-src` / `frame-src`) were never in the passive sweep.
Fetch their security.txt **before** the first test request, not after.

ORF 2026-10 case: an in-scope SPA referenced `konto.orf.at`, `konto-api.orf.at`, `anmeldung.orf.at`,
`on-newsletter.orf.at`, `data-<hash>.orf.at`. None published a security.txt → **all OUT**; testing
stopped immediately. One incidental `/health` read on `konto-api` happened before the scope check —
that kind of slip gets **disclosed in the report**, not buried.

## 5. The pivot a completed scope map enables: `303 Location` → internal admin portal

The single highest-yield thing to do *after* the map exists is follow the redirects served by the
in-scope legacy hosts. ORF:

```
https://bits.orf.at/filehandler/   ->  303  Location: https://websys.orf.at/admincenter/
https://aurora.orf.at/             ->  303  Location: https://websys.orf.at/admincenter/
```

That surfaced `websys.orf.at` — an internal ORF AdminCenter — which then had to be scope-tested itself
(it *did* serve the canonical file, so it was IN). Chasing `Location:` headers on in-scope 3xx
responses is cheap, legal, and finds the app nobody linked to.

## 6. Validate a header-reflection finding 3× with the SAME payload — and prove the negatives

Found on the same legacy estate: an untrusted `X-Forwarded-For` reflected into `Set-Cookie`.

- **3× with the identical payload.** A reflection can be payload-dependent. ORF's
  `X-Forwarded-For: 1.2.3.4; Domain=evil.example` reproduced 3/3 as
  `Set-Cookie: Vietnam2Session=127.0.0.1.2.3.4; Domain=evil.<rand>; Path=/; Domain=.orf.at`,
  while `; Path=`, `; Max-Age=`, `; SameSite=`, `; secure` and `; expires=` did **not** survive.
  Report only the form that reproduces; say you have not reverse-engineered the parser. A finding that
  evaporates on run 2 is a not-a-finding, and this rule exists to kill those.
- **curl strips CRLF from header values**, so `X-Forwarded-For: x\r\nInjected: 1` cannot be sent with
  `-H`. Use a raw socket (Python `ssl.wrap_socket` + a hand-built request) to test response splitting.
  ORF truncated at the CR → no splitting; that negative belongs in the report because it is what caps
  the severity.
- **Prove the negatives explicitly** and list them: CRLF/response splitting (raw socket, marker absent),
  cache poisoning (`X-Cache` stayed MISS on the Set-Cookie endpoint), session fixation (server mints a
  fresh token, supplied cookie ignored), and XFF-based ACL bypass. Then run the decisive sweep —
  `scripts/xff_authz_diff.py` fetches every host × path twice (clean vs `X-Forwarded-For: 127.0.0.1`)
  and diffs status + body sha256 + length; **zero diffs** is what lets you report the whole family as
  Low honestly instead of hoping.

## 7. Reporting the boundary

Put a **"Scope and handling note"** section in the deliverable: (a) the rule you applied, (b) the
out-of-scope hosts you *identified but deliberately did not test*, (c) confirmation that no record was
accessed, no data modified, no scanner used, no volumetric/DoS testing. That paragraph is the first
thing a bank's security team reads, because it is what makes the safe harbour unambiguous.

## 8. Pitfall — the tempting internal hostname

Enumeration surfaces names that look like a jackpot: `confluence.`, `bitbucket.`, `easyhypopricer.`,
`api.`, `businessnet.`, `adfs01.`, `dialin.`, `*.intra.`. **Check they resolve publicly before writing
a sentence about them** (`dnsx -silent -a -resp -d HOST`, or one curl expecting a real banner). A host
that hangs or returns HTTP 000 is DNS-only/internal: **information at best, not a finding**, and outside
the boundary anyway. The Valiant 2026-10 engagement produced 12 such names and zero testable surface —
the source-control, wiki and mortgage-pricer hosts were all internal while the public estate was a
Liferay portal plus a stack of branded 403s.
