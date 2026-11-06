# security.txt as the SCOPE TEST (not just the contact card)

Most programs define scope by asset list. A growing number define it by protocol:

> "Only domains/subdomains which have a security.txt file in their root (i.e.
> https://shop.orf.at/security.txt) are in scope. Currently, the scope is limited https://orf.at"

When you see wording like that, the security.txt file **is** the authorisation boundary, and you can
compute the in-scope set objectively instead of guessing from the apex domain.

## Recipe

1. Get the live host list first (`subfinder` → `httpx`). Do not try to resolve this from the apex.
2. For every live host, fetch `https://<host>/.well-known/security.txt` **following redirects**.
3. Classify by CONTENT, not status code:

   | Observation | Verdict |
   |---|---|
   | body matches the canonical file (`Contact: mailto:<same address>`) | IN SCOPE |
   | `302` → `https://<apex>/.well-known/security.txt` → 200, same body | IN SCOPE — the host is part of the same estate |
   | `200` but the body is an HTML error/SPA page | **OUT** — false positive (see below) |
   | `404` / no canonical body | OUT |
   | redirect to a third-party/VPN login | OUT |

4. Record the result as `<host> :: IN-SCOPE (canonical)` / `:: out` in `recon/securitytxt_map.txt`,
   and the IN-SCOPE subset in `recon/in_scope_hosts.txt`. Those two files become the scope ledger you
   cite in the report.
5. Hosts discovered LATER (from a JS bundle, a CSP header, a redirect) are not automatically in
   scope — run the same test on them before touching them.

## Worked examples (2026-10)

**orf.at** — 150 live hosts → **41** served the canonical file. In scope: `orf.at` plus
`www der on sport news oe1 fm4 topos help bits assets aurora bernard bert bianca billy boa bolek
brava brain bglv1 bewusstgesund bachmannpreis bildung burgenland clyde collector files mediendaten
oekastatic pipe oe3 ooe oesterreich radio sendungen soph-assets sagsmulti termine teletext text tube
tubestatic tirol wetter` and later `websys tv cookiedispenser`. OUT: `tvthek` (404), `shop.orf.at`
(discovered via a page, but `/security.txt` returned a **Shopware "Sales Channel Not Found" HTML
page at HTTP 200** — the classic soft-200 false positive), `admin.contentsales`, `api-*-tvthek`,
`anmeldung`, `adinsights`, `beschaffung`. The host that turned out to matter most (`websys.orf.at`)
was not in the sweep at all — it came from a `Location:` header on an in-scope host.

**valiant.ch** — the policy wording is the opposite case: "Any products and services owned, operated
or maintained by Valiant Bank", including third-party-operated services. There the security.txt test
does NOT constrain scope, so scope = the whole estate, and the boundary comes from the PROHIBITED
list instead (no brute force, no DoS, no social engineering). Read which of the two shapes you have
before building the host list.

## Why this matters more than a normal scope read

- It converts a judgement call into a test you can re-run and cite. When a host is tempting but
  out of scope you can say exactly why you left it alone.
- It protects the safe harbour. Getting this wrong is the difference between authorised research and
  unauthorised access, and programs do revoke safe harbour for scope breaches.
- The sweep itself is cheap and non-invasive: one GET per host, no payloads. It is nothing like a
  scan, so it stays inside "no noticeable load" rules.

## Pitfalls

- **Soft-200 false positives.** Always inspect the body, never trust the status code. Appliance and
  e-commerce error pages (Shopware, Cloudflare Access, SPA shells) return 200 with HTML.
- **Do not treat a redirect as out of scope automatically** — a 302 to the canonical file is exactly
  how RFC 9116's `Canonical:` is meant to work, and it is the operator saying "this host is covered".
- **The apex-only sentence can contradict the rule above it.** When a policy says both, treat the
  written rule as the test, note the contradiction in the log, and stay conservative on anything
  ambiguous (test only the hosts that clearly pass).
- **New hosts found mid-engagement need the test too** — a host appearing in a CSP or a JS bundle is
  a lead, not an authorisation.
