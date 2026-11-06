# Origin WAF + PATH allowlist — read before re-attempting City-Data / hand-rolled anti-bot gates

Worked case: `city-data.com` (whole-estate self-hosted VDP, 2026-10-09). A gate that at first glance
"is Cloudflare Turnstile" turned out to be the **origin's own WAF** whose allowlist, not any
fingerprint, decided what you could reach. Four attempts to "get past Turnstile" were the wrong project.

## 1. Classify the block FIRST — three axes, not one

Before building any harness, settle which of these you are looking at. The skill already covers
**fingerprint-scoped** (§1–2, §3a UA matrix) and **egress-scoped** (§3a-0). This session added the
third axis: **path/allowlist-scoped**.

| Axis | Test | Result shape | Action |
|------|------|--------------|--------|
| Fingerprint | same request via curl vs real Chrome | one works | fix client (§1) |
| Egress / IP | same request from a different exit IP | one works | rotate exit (§3c) |
| **Path / allowlist** | **benign** path vs **attack-signature** path, same client | benign 200, signature 403 | map the allowlist — do not fight it |

The dead giveaway for axis 3: a **non-existent, benign** path answers with a *normal app response*
(`403 Forbidden` from the app, or a real `404`), while the same client with a payload (`<script>`,
`../`, `%00`, `SLEEP(`) gets the **challenge page in ~0.39 s** instead of ~1.15 s. Uniform ~0.38 s
responses on every signature variant = a signature list, not a heuristic.

## 2. Confirm it is the origin, not Cloudflare

- `Server: nginx` plus a **custom header** (`X-Server: cdn1`) — Cloudflare would show `server: cloudflare`.
- Resolve the host: the A record was in the **host's own ASN** (OVH, `51.81.5.187`), **not** a Cloudflare
  range (104.x / 172.6x / 173.x). If the IP is the origin, there is no CF proxy in the path to bypass.
- The challenge page **brands itself** with `challenges.cloudflare.com/turnstile/v0/api.js` and a
  `data-sitekey` — a widget the origin embedded. Embedding the widget does not make the block a CF
  block; the *decision* is still the origin's.

Consequence: "bypass Turnstile" is the wrong goal. Nothing to bypass — you need to find which paths the
allowlist serves without a challenge.

## 3. Map the allowlist (this is the actual work)

Request only **benign, non-existent** paths and read the status — never an attack signature:

```bash
for p in / /index.html /.git/config /probe-nonexistent-xyz.css /nope-123; do
  printf "%-28s " "$p"
  curl -sk -m 12 -o /dev/null -w "%{http_code} %{size_download}b\n" "https://TARGET$p"
done
```

- `403` **real app page** on a non-existent benign path → path-allowlist WAF (benign unknown = app 403).
- `200` on a path you didn't expect → it is on the static allowlist.
- `429`/challenge only on `/.env`, `/.git/config`, `<script>`, `../` → signature rule.

**Static paths that answered 200 behind the gate** (typical allowlist members — try the whole set on any
such target, they are the cheapest way to get a target's *policy* without passing the challenge):
`/robots.txt`, `/.well-known/security.txt`, `/favicon.ico`, `/ads.txt`, `/BingSiteAuth.xml`, `/css/style.css`.

**`robots.txt` is an attack-surface map.** City-Data's `Disallow:` list named the live dynamic endpoints
(`/city/js/getBoxes.php*`, `/county/js/getBoxes.php*`, `/restaurants/afd.class.php*`,
`/forum/reputation.php*`, `/cityname.php*`, `/mtc.cl…`). Cross-check each against the allowlist.

## 4. The gate usually guards the SUBMIT action, not the invitation page

A recurring shape: the *informational* page is served, the *action* is gated.

| Path | Result | Meaning |
|------|--------|---------|
| `/forum/misc.php?do=register` | **200 (38 KB, real vBulletin page)** | invitation page — open |
| `/forum/register.php`, `/forum/registeradv.php` (the actual form) | **403** | the action — gated |

So "the register page loads" does not mean signup is reachable. Check the concrete form/action URL, not
the marketing page that links to it. Same pattern for `.well-known/security.txt` (reachable) vs the
policy it references (gated) — recover the policy text from the **Wayback Machine**
(`https://web.archive.org/web/<ts>id_/<url>`) rather than fighting the live gate.

## 5. Registration classification — do NOT misapply the identity rule

**A public forum signup is not KYC/KYB.** When the user says "register yourself using my data", using
their real supplied details on a public forum registration is **authorised** — the standing
"don't fabricate identity" rule is scoped to KYC/KYB into **regulated** entities (bank, exchange, tax
SaaS), where a false declaration risks the account being banned. Do not cite that rule to refuse a
public signup; apply it only where identity verification actually happens.

Also do not claim a blocker that is actually the target's: if the WAF blocks the form, say **"the WAF
blocked the form"** — never wrap it as a self-imposed rule.

## 6. Honest outcome shape

If the WAF genuinely blocks every proof payload, the correct result is a **NEGATIVE report with the
allowlist map as coverage evidence**, not a "hardened target" claim and not a scanner dump. Record:
reachable paths + statuses, the signature probes that returned the challenge (with timing), and the
explicit gap ("no authenticated surface reached"). The `finding_gate` / `triage_gate` pair will correctly
hold this at 0 REPORT findings.
