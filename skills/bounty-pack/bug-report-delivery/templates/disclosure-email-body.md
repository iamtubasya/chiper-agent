# Disclosure e-mail body — the fixed shape (rule 0c)

Copy this file per finding, fill the `<>` slots, run the `humanizer` skill, then

```
python scripts/stage_finding_draft.py report.md Out.pdf "<subject>" \
  --to security@vendor.com --body body_Fn.txt
```

`stage_finding_draft.py` now **refuses to stage** a body that is missing the shape or that asks for a
reward, so a copy-paste forgetting the intro fails loudly instead of shipping.

---

## Skeleton

```
Hello <Vendor> Security Team,

My name is RESEARCHER_NAME. I am an independent security researcher, and I am sending this report through
your responsible disclosure programme at <policy URL>.

<One or two sentences: where the issue is, in plain language.>

<The exact command, then the exact value it returned. Keep both verbatim — the reader must be able to
re-run them.>

<One sentence on what that result proves, stated no stronger than the evidence supports.>

I made no change to any system or data, and I have not shared this with anyone else. If it is useful I
can send the raw evidence, walk through the reproduction, or test a fix once it is in place.

Thank you for taking the time to look at this.

Best regards,
RESEARCHER_NAME
RESEARCHER_EMAIL
```

## Rules that are not negotiable

- **Introduction first.** Who is writing, that they are an independent researcher, and the channel.
  A body that opens on the technical content was rejected verbatim: *"draft email nya tidak ada
  perkenalan, lengkapi dulu"*.
- **The finding, with the real command and the real returned value.** No paraphrase of the output.
- **No reward ask.** No "bounty", "reward", "credit", "Hall of Fame", "swag". Say nothing about
  compensation; the vendor's programme handles that. This was an explicit operator correction
  (*"tanpa tanya reward"*).
- **Do not characterise the vendor's policy either.** Declining compensation by saying the policy
  offers none (*"I understand from your policy that none is offered"*) is a false statement on any
  programme that does offer one — read the policy text first, or leave compensation out entirely.
  Shapes copied from other disclosure skills carry that sentence; strip it.
- **Signed with the operator's real name** — RESEARCHER_NAME — not a handle, not "the researcher".
- **One finding = one body = one PDF.** Never merge two findings into one draft; never reuse a body
  across findings (the finding paragraph is always per-finding).
- **Humanizer, then assert.** `[t for t in ["\u2014","\u2013","delve","pivotal","leverage","seamless",
  "I hope this helps"] if t in body] == []`.
- **The PDF must be complete and tidy.** Wrap long curl lines in the markdown before building, then
  `qa_pdf_layout.py <pdf> --margin-mm <m>` must report `clean` for every finding. An overflowing code
  line is the usual offender; re-stage the affected drafts after the rebuild.

---

## Worked example (shipped, Nordnet VDP 2026-10-12)

```
Hello Nordnet Security Team,

My name is RESEARCHER_NAME. I am an independent security researcher, and I am sending this report through
your responsible disclosure programme at https://www.nordnet.se/security-disclosure.

nordnetab.com runs WordPress with Gravity Forms, and the plugin's testing endpoint is reachable without
authentication on the production site.

    curl -s https://nordnetab.com/wp-json/gravityforms/v2/tests/mock-data | grep -o 'gravity.loc'

The request returns about 30 KB of plugin configuration, and inside it is an internal development
hostname:

    "embed_form": {"urls": {"edit_post": "https://gravity.loc/wp-admin/post.php..."}}

The same payload also lists your forms, including "Capital Markets Day - ENG" and "Capital Markets
Day - SE". I did not authenticate against anything and did not modify anything; I am reporting that a
test route is live in production and is leaking a development hostname.

I made no change to any system or data, and I have not shared this with anyone else. If it is useful I
can send the raw evidence, walk through the reproduction, or test a fix once it is in place.

Thank you for taking the time to look at this.

Best regards,
RESEARCHER_NAME
RESEARCHER_EMAIL
```

Why it works: the reader can triage from the first screen, the two commands are copy-paste runnable,
the claim stops exactly where the evidence stops ("leaking a development hostname" — not "RCE"), and
nothing anywhere hints at compensation.
