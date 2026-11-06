# Web2 candidate evaluation: from pool filter to verified-paying target

Recipe distilled from the 2026-10-21 pivot session (Proton → CodeRabbit → Cloudsmith → Kaartje2go),
where four targets were evaluated before one was committed.

## 1. Pool filter that produced 248 candidates

```python
import json, re
pool = json.load(open(r"D:/data hermes/target-pool/pool.json", encoding="utf-8"))
recs = list(pool["domains"].values())          # values(), not the dict itself
WORKED = {"<domains already audited this session>"}
CRYPTO_KW = re.compile(r"crypto|chain|defi|token|swap|finance|wallet|web3|nft|dao|bitcoin|eth|
solana|blockchain|staking|yield|perpetual|dex|exchange|trading|protocol|labs\.xyz|\.xyz|\.fi|
\.finance|<named web3 programs>", re.I)
cands = [r for r in recs
         if r["domain"].lower() not in WORKED
         and str(r.get("reward","")).lower() == "monetary"
         and str(r.get("live","")).lower() == "true"      # string compare
         and r.get("audit_status","untouched") == "untouched"
         and "platform" not in str(r.get("hosting","")).lower()
         and str(r.get("country","")).lower() not in ("id","in")
         and str(r.get("safe_harbour","")) == "stated"
         and not CRYPTO_KW.search(r["domain"].lower())]
```

`live` is the STRING "True", not a bool. `audit_status` defaults to "untouched" only when the key
is absent — use `.get(...,"untouched")`, never `status` (that is the program's own state).

## 2. Reward-type triage (the pool's "monetary" flag overcounts)

Verified by fetching each live policy:

| Program | Policy says | Verdict |
|---|---|---|
| Kontent.ai | "Amazon vouchers (or another form), amounts determined by Kontent.ai", Bugcrowd VRT | weak EV — voucher discretionary |
| Pokee.ai | "Low 2,000 / Medium 5,000 / Critical 10,000 **Pokee API credits**" | credits, not cash — weak EV |
| Kaartje2go.be | "minimum of a waardebon van €50" gift voucher, severity+quality based | small but real; accessible site |
| Dynamate.be | same Dutch template text, €25 mentioned | low |
| Pepabo (lolipop.jp etc.) | "現在、報奨金制度は設けておりません" — **no bounty at all** | set `no-reward` in pool |

Rule: **grep the policy HTML for the currency/credit noun, not the word "reward"**. "voucher",
"credits", "loot", "swag", "Amazon" next to an amount = non-cash. "bank transfer", "invoice",
CHF/USD/EUR + amount table = cash. Pepabo's policy literally states no bounty system — pool had
it flagged monetary.

## 3. Channel shapes that change the disclosure step

- **Form-based** (Cloudsmith): security.txt `Contact:` is a URL
  (`/vulnerability-disclosure/submit-vulnerability`), no public mailbox. Gmail draft goes with
  **To: unset** and the submission URL in the body; the draft is the copy-paste source for the form.
- **PDF out-of-scope** (Kaartje2go): the out-of-scope list is a PDF at
  `/bestelden/out-of-scope-responsible-disclosure` — download and extract with pymupdf BEFORE
  testing; their list excludes UUID enumeration, open redirects, CSRF forms, subdomain takeover,
  path disclosure, banner grabbing, and names out-of-scope domains (.nl assets/quiz/e/werkenbij).
- **JS-rendered policy** (CodeRabbit): rewards live in the Next.js payload; grep the raw HTML for
  `\$[0-9,]+` / "USD" rather than extracting rendered text.
- **Akamai/CF-blocked policy** (Galaxus, finanzen.net): curl gets "Access Denied"; don't discard
  the target for that (the app itself may still be testable) but expect the bot-protected path.

## 4. Geo reality check (2026-10-21)

Asia-preferred monetary+untouched+self-hosted slice was **8 domains** and all eight were dead ends
(2 AU known-no-cash, 1 JP VDP-only ×3 same owner, 1 JP platform/HackerOne, 2 weak safe-harbour).
Per the operator's standing rule the slice was walked and rejected; the EU/global slice (166
"global" + NL/CH/AT/DE/BE) is where the candidates actually are. Expect to widen on every session.
