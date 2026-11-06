# Unverified ownership claims → authoritative DNS (hosting/panel class)

Class-level recipe. Trigger: any product where a tenant can "add" a name they should own —
custom domain onboarding, vanity hostnames, subdomain claim-before-owner, org slugs, BYO-cert.

Worked instance: **djangoeurope.com / wservices GmbH** (2026-10-25, DRF hosting panel, no formal
program; findings F1 Medium + F2 Low). Read this before concluding "the domain surface is gated" on a
hosting target — the previous pass on the same target had marked the whole paid product surface gated
and missed this.

## 1. The bug is the ORDER of trust, not a missing format check

Two endpoints, each individually plausible:

```
POST /domain/   {"name": "<anything>"}          -> 201, zone published authoritatively
POST /website/  {"systemuser": .., "hostnames": ["www.<same name>"]}
                -> 400 "Domain does not exist. Add the domain and make sure you have access to it."
```

The error message tells you to do exactly the thing that has **no access check**. `/website/` validates
against a row (`domain`) that the caller created seconds earlier, so the composite path is wide open
while each individual message reads correct.

Probe rule: for every child resource ask **"what am I validating against, and who wrote that row?"**
If the answer is "a row the same caller created in the previous request", you have found the class.

Generalises to `websitedomain`, `domainrecord`, `ssl.domains`, `mailuser.domain`,
`mailforwarding`/`mailtransport`, monitoring jobs — all inherited the same unverified parent.

## 2. Proof ladder — do not stop at "accepted"

Stopping at `201` gives you a Low at best. The ladder that makes it a Medium:

1. **Claim a real third-party name** to prove there is no registrant check (`kernel.org` → 201), then a
   synthetic name to prove nothing is validated at all.
2. **Query the provider's own nameserver directly**, not a public resolver (cache and non-AA answers
   muddy the evidence):
   ```python
   import dns.resolver, dns.query, dns.message
   ns_ip = str(dns.resolver.resolve("ns1.wservices.ch", "A")[0])
   for rt in ("SOA", "NS", "MX", "TXT"):
       resp = dns.query.udp(dns.message.make_query(name, rt), ns_ip, timeout=6)
       aa = (int(resp.flags) // 1024) % 2          # AA bit, without importing dns.flags
       print(rt, "AA=%d" % aa, [str(x) for x in resp.answer])
   ```
   `AA=1` on SOA/NS/MX/TXT = the platform declares itself authoritative for a name it does not own.
   The MX answer matters most: `MX 10 mail.<provider>` means mail routing is claimable too.
3. **Run the control query.** Same nameserver, a name nobody ever claimed → `REFUSED`, no AA. Without
   this row the vendor answers "that is just the server's default behaviour". With it, AA=1 is provably
   produced by the attacker's own record. This single row is what makes the report survive triage.
4. **Do not stop at DNS**: attach the website object and show what is auto-created (shared IP,
   `websitedomain` with `auto_dns=true`, an HTTP monitor polling `http://victim/` every 600 s). Objects
   created *against a third party* are the concrete harm.

### 2b. Prove you can WRITE into the claimed zone (and never say "immediately")

Two upgrades that turn tier 3 from "argued" into "partly proven" without touching a third party's mail:

1. **Publish your own record and resolve it.** After the claim, `POST /domainrecord/` with your own label:

   ```
   POST /domainrecord/ {"domain":<id>,"subdomain":"proof","type":"A","data":"203.0.113.7","ttl":60}
     -> 201
   dig @<provider-ns-ip> proof.<claimed-name> A   ->  AA=1  60 IN A 203.0.113.7
   ```

   That is attacker-chosen data answered authoritatively for a name the attacker does not own — much
   stronger than quoting the provider's own auto-generated MX/SPF. (Keep it to a documentation-range
   IP like `203.0.113.7`; never point a record at real infrastructure.)

2. **Record API shape quirks, they cost runs:** a blank `subdomain` is rejected (`"This field may not be
   blank."`) — use a label or `"@"`; MX needs `priority` **and** `data` as a bare label
   (`{"subdomain":"@","type":"MX","data":"mail.example","priority":5}` → 201, while
   `"data":"10 mail.example"` → `"Data must be a valid DNS label."`); `GET /domainrecord/` may be
   `501 Not implemented`, so read existing/auto rows through `GET /domain/<id>/ -> .records[]`
   (they carry `"auto": true`).

3. **⛔ Do not write "immediately publishes" unless you timestamped it.** Zone publication is
   asynchronous and inconsistent between runs: one claim answered `AA=1` after ~2 s, a later claim was
   still `REFUSED` at +10 s, +25 s and +45 s. Poll with timestamps, report the observed latency, or write
   "publishes". This is the one adverb that turns a correct report into a claim the vendor can rebut —
   the same applies in reverse to revocation (§6).

## 3. Impact tiers — write them separately, never merged into one claim

| tier | claim | how it is proven |
|---|---|---|
| proven | squatting / onboarding denial | uniqueness is global: pre-claim `example.org`, the real owner later gets `"domain with this Domain name already exists."` and can never onboard; only the attacker can DELETE |
| proven | objects issued for a name the tenant does not own | `POST /website/` → 201 + IP + auto_dns + auto monitor |
| **argued only** | mail/traffic interception | requires the victim domain to be (or become) delegated to the platform NS. Say plainly you did not do it and why — it would require taking over a real third party's mail |

Mixing tier 3 into tier 2 is how a clean Medium gets downgraded to Info. Keep an explicit impact-boundary
section; it is also your appeal basis if they under-rate tier 1.

## 4. Usually NOT the bug (test, then record as verified negative)

- **Normalisation** is often correct and burns a probe cycle: `SECTEST.COM`, `" sectest.com"`,
  `sectest.com.`, `sectest.com..`, IDN `xn--…` were all handled properly here. The table is your proof
  that the missing control is *authorisation*, not syntax.
- **`token.permissions`** (DRF multi-token) is a **restriction** only: a view-only token got `403` on
  `POST /domain/`. Self-issued tokens cannot escalate.
- **`sshkey.user`** forced to the authed user — sent `user: 8551` and `user: 999999`, both stored as
  8503. (Still worth re-testing elsewhere; a real BOLA when broken.)
- **Paywall/activation gate**: an unpaid `systemgroup` order yields `productinfo.is_active=false`,
  status `"Waiting for activation"`, and an OS account that cannot SSH in. `PATCH /productinfo/`
  silently ignores `price`/`is_active`/`paid_until`. All holds — log it to stop re-litigation.

## 5. Remediation shape to recommend

1. Pending row + proof of control before the zone publishes: `_<vendor>-verify.<name>` TXT holding a
   per-request token, or a code to the domain's SOA RNAME / registrant address. Expire pending rows (72 h).
2. Never treat "the row exists" as ownership anywhere else — child endpoints must validate against the
   *verified* state. The auto-created monitor is the urgent one (it starts polling a third party).
3. Abuse review for high-value names / many apex domains claimed in a short window.
4. A legitimate-owner dispute path, otherwise first-come-first-served makes the bug a durable DoS.

## 6. Cleanup discipline (this class creates real state)

- Delete child→parent: monitoring → location → website → ssl → domain.
- **Revocation is not instant.** After `DELETE /domain/` → 204 the nameserver still answered `AA=1` for
  ~15–20 s before flipping to `REFUSED`. Poll until REFUSED and paste that poll into the report —
  otherwise the vendor re-checks five seconds later, sees a live zone, and accuses you of leaving it up.
- Deleting a claimed *third-party* zone is the one action to verify twice.

## 7. Adjacent findings on the same surface (separate drafts — RULE 0)

- `GET /backup/` returning **server-level** backup metadata (24 rows, dates predating the account,
  `systemuser: null`, `bserver`/`server` UUIDs). Low. Check `OPTIONS` for actions — none means
  metadata-only; say that explicitly.
- Unauthenticated `GET /server/` leaking hostnames, OS/package versions, hardware, DB-admin URLs.
  Recon enabler; often already reported — check the prior report first.
