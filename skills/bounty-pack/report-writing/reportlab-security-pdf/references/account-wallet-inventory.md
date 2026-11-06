# Account & wallet inventory — a report REQUIREMENT on most modern programs

Learned live 2026-10-30 (Bankr engagement). Two lessons, both cost a rebuild of an already
staged draft: the inventory was missing from the PDF, and the first attempt to add it as a
5-column table shredded every e-mail address.

## 1. Why it is a requirement, not a nicety

Many crypto / web3 programs make the inventory part of the mandatory reproduction. Bankr
§7 item 5, verbatim:

> list every Bankr account (email or handle) and wallet address you used while testing, and
> the dates you tested. Activity we can't match to an account or address you listed may be
> treated as unauthorized use.

So a report that omits it is triaged as incomplete even when the bug is real — and the
vendor's anti-abuse process cannot clear the testing burst. Same shape appears in
exchange / custody / agent-platform programs. Read the reproduction section for it before
you build the PDF, not after.

## 2. What the section must contain

- **Every login**, including aliases that resolved to the same account (`+tag`, dot variants).
  Say *why* they collapsed and that no second wallet was created — otherwise a burst of
  logins looks like enumeration.
- **Every wallet on every chain** — EVM and Solana in the same table, full address, lowercase.
- **Disposable mailboxes that never produced a wallet**, with the exact failure the vendor
  returned (e.g. `POST /user/bootstrap` → `500 Failed to set up your Bankr wallet`). This is
  what separates "5 test accounts, 3 of which never got a wallet" from unexplained traffic.
- **Locally generated key pairs** that were created but never linked / never signed / no
  on-chain history — list them for completeness.
- **Exact testing window** — first and last event in UTC plus local time, and the egress IP.
- **The balance the test wallet held** (usually zero). It explains why the finding is about
  entitlement or metering rather than funds and pre-empts a "you moved funds" reading.

## 3. The table that mangles e-mail addresses (and passes the layout checker)

First attempt used one row per account with 5 columns:

```
| # | Account (login) | Bankr wallet - EVM | Bankr wallet - Solana | Role in the test |
```

`pdf_layout_check.py` reported `problems=0` — correctly, nothing left the margin and no cell
overflowed. But the rendered text layer showed:

```
RESEARCHER_USERNAME
@gmail.co
m
```

The e-mail column was narrow enough to break *inside* the token, so `RESEARCHER_EMAIL`
did not exist anywhere in the text layer. That silently defeats the purpose of the section:
a triager greps the PDF for the address they were given and does not find it. The same
mangling hit `bankrtest01snrm@maxxspace.com` and `lyizxuen@guerrillamailblock.com`.

**Fix that worked — a two-column `Field | Value` table**, one row per attribute:

```
| Field | Value |
|---|---|
| Account 1 - login | RESEARCHER_EMAIL |
| Account 1 - EVM wallet | 0xef33...187b |
| Account 1 - Solana wallet | GPKu...1JX |
| Account 1 - role | The account under test. Every request ... belongs to it. |
```

Two columns means the value column gets most of the 170 mm frame and long addresses wrap at
natural boundaries. Same table style as the metadata block, so it reads as one document.

**Verification that actually catches it** — after building, extract the text layer and assert
each *complete* address is present:

```python
txt = "\n".join(p.get_text() for p in pymupdf.open(pdf))
for k in ["RESEARCHER_EMAIL", "RESEARCHER_USERNAME+bankr2@gmail.com", "f.zsusanto@gmail.com",
          "bankrtest01snrm@maxxspace.com", "lyizxuen@guerrillamailblock.com",
          "0xef33e9a9aef3e370951b1a31cf26ddaf9dee187b",
          "GPKuAuR4RgH62GRCSFsTfEbHSe41hFethFFtFwdc61JX", "104.28.226.245"]:
    assert k in txt, "missing or mangled: " + k
```

A `problems=0` from the geometry checker is necessary but NOT sufficient for this section —
the defect is a *substring* failure inside a cell, which the geometry rules cannot see.

## 4. Duplicate it into the e-mail body

The operator reads the draft body first, and some vendors accept only a web form (Bankr: Help
Center, Request Type "Bug Bounty / Vulnerability"; e-mail is for a Critical alert only). A PDF
attachment does not travel into a form field. Keep an aligned plain-text copy of the inventory
in the body, `key : value` per line, so it can be pasted verbatim:

```
Account 1 (the account under test)
  login         : RESEARCHER_EMAIL
  EVM wallet    : 0xef33...
  Solana wallet : GPKu...
  note          : every request in this report belongs to it; balance zero throughout.
```

When the operator asks for the inventory *in the chat* as well ("atau tulis dsni jg boleh biar
sy copi"), hand it over as the same aligned block — not a prose summary.

## 5. Rebuild consequences

Adding the section changes the PDF, so the staged draft is stale. Re-run the full chain:
rebuild → `pdf_layout_check.py --tokens ...` → text-layer assertions above → re-stage the
draft (delete the old one **by subject**, the staging script does this) → verify attachment
`%PDF-` + sha256. The PDF grew 4 → 6 pages and 11 170 → 14 804 B in this session.
