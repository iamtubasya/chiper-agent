# Submission compliance: the form, the field list, and scope anchoring

Written after an operator challenge on 2026-10-27 (*"sudah sesuai inscopenya y, dan sudah sesuai rules
submitnya, baik dr sisi data yg diminta maupun submit via email?"*) exposed three real gaps in a report
that had already passed the layout gate, the 3x validation gate, and the humanizer check.

The lesson generalises: **a report can be technically flawless, correctly written, properly attached, and
still be non-compliant on delivery.** Compliance is a separate gate with its own evidence.

---

## 1. Enumerate every deliverable the policy names

Policies hide deliverables in prose that reads like boilerplate:

> "Complete the Vulnerability Disclosure Request and send it to security@yarbo.com"

That sentence is a **second document**, not an instruction to write an email. It links to a ~30-field
`.docx`. Sending e-mail + PDF alone skipped it.

### Extraction recipe

```bash
P="$POLICY_URL"
# document links
curl -sS "$P" | grep -oiE 'href="[^"]*\.(docx|doc|pdf|odt|rtf)[^"]*"'
# imperative prose that implies a form
curl -sS "$P" | grep -oiE '(complete|fill|fill in|submit)[^.<]{0,90}(form|request|template|checklist)'
# which mailbox / portal
curl -sS "$P" | grep -oiE '(mailto:[^"]+)|(https://[^"]*(submit|report|intake)[^"]*)'
```

Shopify-hosted docs often 404 on the long path (`/cdn/shop/files/1/0604/5394/5441/files/X.docx?v=...`)
and work on the short one (`/cdn/shop/files/X.docx`). Try both before concluding the form is gone.

### Mine the form for field names

A form template is the most accurate machine-readable statement of what triage reads, because someone had
to enumerate the fields.

```python
import zipfile, re
xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", "ignore")
paras = re.split(r"</w:p>", xml)
text = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", p)).strip() for p in paras]
fields = [t for t in text if t]
# "Label: ____" lines are fields; "(Required)" markers are hard gates
required = [f for f in fields if "(Required" in f or f.endswith("_") or "____" in f]
```

Answer every field, including the ones you are declining: `Vulnerability ID` → `Pending`,
`PGP Key` → `Not provided, available on request`, `Government-issued ID` → `N/A at this stage, will
provide for bounty verification and W-8BEN once validated`. A blank field reads as an incomplete
submission; an explicit "not applicable, because X" reads as competence.

**Never fabricate KYC or a vulnerability ID.** Offer, do not invent.

### Render it with python-docx, not as prose

Vendors ask for Word so they can edit and forward internally (Deeper Network: *"Can you please submit the
BUG Report in a properly formatted word document"*). Build one `build_vdr(out_path, F)` function and pass
different field dicts per finding — sections, headings, `List Number` for steps, `List Bullet` for the
agreement block. Keep it beside the PDF generator so both render from one source.

---

## 2. Reconcile three sources, not one

| source | what it governs |
|---|---|
| VDP / policy page | channel, scope, safe harbour, disclosure timing, prohibited activity |
| programme Terms (a §1.4-style clause) | mandatory *report content* list |
| the submission form | exact field names triage actually reads |

Yarbo's Section 1.4 list, and where each item has to appear:

| required element | where it lives |
|---|---|
| narrative description of root cause | Summary + a `Root cause` subsection |
| linear step-by-step reproduction | `Steps to reproduce`, numbered |
| non-destructive PoC code/demonstration | PoC script as an attachment, described in `Artefacts` |
| full testing environment configuration | `Testing environment` subsection (OS, client, network, source IP, no proxy) |
| affected URLs, app identifiers, code snippets | Affected component |
| exact hardware model + firmware version | explicit **"not applicable"** with the reason — a cloud finding still has to answer it |
| supporting artefacts: screenshots, logs, network capture | Figure + raw JSON capture attachment |
| formal impact assessment + number of affected users | Impact, with a real number |

That last row is where most reports are thin. "Potentially all users" is not a number. Use a published
figure: the app store listing (`10,000+ installs` — read it from the Play Store page, it is in the HTML as
`info 10K+ Downloads`), or the record count you actually observed.

Everything in that table must be assertable against the built artefacts:

```python
need_pdf  = ["Root cause", "Steps to reproduce", "Step 1.", "Testing environment",
             "Artefacts that accompany", "Figure 1", "not applicable", "10,000+"]
need_mail = ["1. Summary", "3. Steps to reproduce", "11. Scope", "12. Submission"]
assert all(n in pdf_text for n in need_pdf)
assert all(n in body for n in need_mail)
```

---

## 3. Scope anchoring

Two failure modes that are invisible while you work and fatal on triage.

### 3a. The asset host does not match the written scope pattern

Policy: assets "under the `target.com` root domain".
Reality: `4zx17x5q7l.execute-api.us-east-1.amazonaws.com` — zero `target.com` in the hostname.

This is normal for any company selling through an API Gateway, and it is **still in scope** when the
programme separately lists cloud/IoT backend APIs and identity services. But the argument must be made in
the report, not assumed:

- state that the published app calls that exact host and stage;
- state that AWS is the hosting provider, not a third party to whom the finding belongs (the policy's
  exclusion for "third-party hosted services" targets vendors the company does not run);
- offer the reparade route: *"if you would rather see this through a target.com front door, name the
  hostname that fronts this gateway and I will re-run it there."*

### 3b. A path segment that reads as a non-production environment

`/Stage/` is the API Gateway **stage name**, not a staging environment. Every policy excludes
"development, staging, test, UAT, pre-release", so a triager skimming the URL can close it without
reading further.

Prove production status, do not assert it. Three proofs that worked:

1. **The distributed build calls that exact host and stage.** Extracted from the store build's AOT
   snapshot — the strongest evidence available short of vendor confirmation.
2. **It holds real data.** Real registered units, warranty records, real accounts created through the
   normal client.
3. **The genuinely non-prod stages are elsewhere and named differently.** In the same estate: `/test` on
   gateway `26akbclmo9`, `/dev` on gateway `oczkojjxh5`. Naming those — and noting they were left
   untouched — is what makes the argument land.

### 3c. Immutable identifiers that look like environment signals

Auth0 tenant `dev-6ubfuqym1d3m0mq1` authenticates the published app and issues tokens for real customer
accounts. Tenant identifiers are fixed at provisioning and cannot be renamed. Raise it proactively so it
is not mistaken for a tell — an unexplained `dev-` in a report is exactly the kind of detail that gets a
report mis-triaged.

### Pre-staging checklist

```
[ ] every host matches the scope pattern literally            -> else: Scope justification bullet
[ ] every path segment free of staging/test/dev vocabulary    -> else: the 3 proofs
[ ] cloud provider named in the host explained as hosting
[ ] look-alike non-prod identifiers (dev-, test-, sandbox-) explained as immutable names
[ ] explicit offer to reproduce through a vendor-preferred front door
```

Put it in the PDF as **Scope justification** (one bullet per risk, one sentence per bullet) and mirror a
condensed version in the e-mail as **11. Scope** + **12. Submission**. That converts "this looks out of
scope" from a silent rejection into a conversation you get to have.

---

## 4. Worked example — Yarbo, 2026-10-27

Two findings, two e-mails, four attachments each:

```
F<n>_<slug>.pdf                      report, 13-section skeleton, layout gate clean
VDR_F<n>_<slug>.docx                 completed Vulnerability Disclosure Request
yarbo_poc_F<n>_<slug>.py             PoC, read-only except the one route, prints request count
poc_capture_F<n>.json                raw request/response with UTC timestamps
```

Verify after staging, per attachment: `sha256` of the fetched attachment == the local file, exactly one
draft per subject, and the body still carries the section markers. A rebuild invalidates the staged PDF —
delete the superseded draft and re-append rather than leaving two generations.

Channel: `security@yarbo.com`, named in the VDP, in the Terms, and on the form itself. No portal. Public
disclosure **not** requested (sections 3 and 4 of the form: "None requested"), consistent with the safe
harbour clause forbidding disclosure of unpatched details without written approval. NDA and W-8BEN are
payment preconditions, so state "will provide once validated" rather than inventing tax or identity data.
