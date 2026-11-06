# Dangling-CNAME / subdomain-takeover sweep — measured recipe

The highest-yield *manual* technique in the 2026-10-17 Gasunie engagement: it produced the only live
candidates, while ~40 automated tool runs across 5 products produced zero reportable findings. It is cheap,
read-only, and it needs no wordlist.

## Why it works

Automated takeover scanners (`subzy`, `dnsReaper`, `subjack`) key off NXDOMAIN/CNAME fingerprints and mostly
return noise on a modern estate. The signal that actually discriminates is **whether the SaaS backend binds
the tenant to the Host header**. A host that answers identically for its real name and for a random label of
the apex is *unbound* — the classic takeover precondition.

## Step 1 — inventory the CNAMEs (not the subdomains)

```bash
# for every live host, record the CNAME target
nslookup -type=CNAME <host>      # parse "canonical name = ..."
```

Group by target. Measured on 129 live hosts: 44 had CNAMEs across only **14 unique targets** — so the whole
estate reduces to a handful of backends to classify. Save the map (`cname_map.json`); it is the evidence that
you covered the estate rather than sampling it.

Typical groups and their meaning:

| CNAME target pattern | Platform | Takeover-relevant? |
|---|---|---|
| `*.foleon.com`, `*.spgo.io`, `*.flowmailer.net`, `*.kirra.nl` | content/email SaaS, tenant-per-host | **yes** — host-bound tenancy |
| `*.msappproxy.net` (Entra App Proxy), `*.hana.ondemand.com` (SAP BTP), `*.azurefd.net` | cloud app platform | usually configured per-host; verify |
| `*.ondemand.com.cloud.sap.akadns.net` (SAP IAS) | IdP | verify, but auth endpoints are strict |
| `autodiscover.outlook.com`, `*.mail.protection.outlook.com` | Microsoft standard | no |

## Step 2 — host differential (the decisive test)

For each backend, compare the **real host** against a **random label of the apex**, sent to the same backend
IP with the same SNI. Use a raw socket so nothing is normalised:

```python
def raw(dns, hosthdr, sni, path="/"):
    ctx = ssl.create_default_context()
    t = ctx.wrap_socket(socket.create_connection((dns, 443), timeout=12), server_hostname=sni)
    t.sendall(f"GET {path} HTTP/1.1\r\nHost: {hosthdr}\r\nUser-Agent: Mozilla/5.0\r\nConnection: close\r\n\r\n".encode())
    ...
    return status, len(body), sha256(body)[:10], location
```

Verdicts:

- **identical status + identical sha** for real host and random label → the front door is **host-agnostic**.
  The tenant is not bound. → dangling candidate.
- **different** (real host 302 to its own content, random label 404/421/default-site) → **configured**. Safe.
- **random label gets `421 Misdirected Request`** while the real host is served → the edge *does* route on
  Host → configured (this is what Azure Front Door did).

Watch the SNI too: some hosts only present a valid certificate for the platform's shared name
(`startgrid.gasunie.nl` needed SNI `api.cf.eu20.hana.ondemand.com`). A cert-verify failure on the vanity name
is a TLS observation, not a finding — but note it.

## Step 3 — classify the sibling set before claiming "dangling"

Never judge one host in isolation. Sweep **every** host on the same backend and classify each:

- 12 of 13 hosts on `s1.foleon.com` answered `302 → /their-own-page`; one answered `404 "site not found"`
  (1241 B, sha identical to the random-label response) → that one is the dangling candidate, and the 12
  configured siblings are the control that proves the backend *can* bind tenants.
- A backend where **every** host including the real one returns the same generic page is not a per-host
  dangling finding — it is the platform's default front door.

## Step 4 — severity honesty: pattern vs impact

A dangling CNAME proves the *pattern*; it does not prove you can claim the host. Severity stays
**Low–Medium / PARTIAL impact** until claim-ability is demonstrated, and demonstrating it usually requires
creating an account on a third-party platform — a **permanent change** that a "no permanent changes" policy
forbids. Record it as PARTIAL and say why you stopped:

- Foleon: `/signup` → `editor.foleon.com/create-account`; `/pricing` → paid plans. Claiming needs a paid plan.
- Spotler/Flowmailer: signup would bind a real sending domain.
- Also check for a domain-verification record (`TXT` on the host, `_dmarc.<host>`): its absence supports the
  claim that the tenant was never bound.

Do **not** execute the claim to "prove" severity when policy forbids permanent changes. Document the pattern,
the differential evidence, and the exact reason the claim step was not taken.

## Pitfalls

- **Timeouts are not evidence.** A raw-socket timeout on one backend (`integrators.gu-fb.nl`) means nothing;
  retry once, then mark unknown rather than dangling.
- **`nslookup` on this box times out intermittently** for names that resolve fine via `getaddrinfo`. Use
  Python `socket.getaddrinfo` as the resolver of record and treat `nslookup` timeouts as noise.
- **Byte-identical is the bar**, not "similar". Compare sha256 of the body, not length.
- **A 403/404 from a WAF is not a dangling signal** — run the junk-path control first so you can tell a
  catch-all from a real bind.
