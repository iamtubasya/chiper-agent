# Submitting account vs test accounts — regenerate the PoC before it goes out

Measured 2026-10-31 (Scribble Maps). Findings were proven on `RESEARCHER_USERNAME+sm1@gmail.com` and
`RESEARCHER_USERNAME+sm2@gmail.com`; the report was then filed from the operator's main mailbox
`RESEARCHER_EMAIL`. Two edits were mandatory before the PDF could go out, and both are
easy to forget because the finding itself did not change.

## 1. Name the submitting account, not the retired test account

Any example endpoint, `userId`, or "authenticated as account A" line must carry the id the
report is actually filed under. Verify it immediately before submitting:

```
GET /api/account   ->  {"email":"RESEARCHER_EMAIL","userId":"dbVZ4Wz9LP"}
```

If the PoC still shows the old test id, the triager cannot reproduce step 1 and the report
stalls on "cannot reproduce" — which this program explicitly does not pay for.

## 2. State the alias relationship explicitly

Plus-addresses of one mailbox are the same person. Write it in the Notes section:

> "RESEARCHER_USERNAME+sm1@gmail.com and RESEARCHER_USERNAME+sm2@gmail.com are plus-aliases of
> RESEARCHER_EMAIL, the mailbox this report is submitted from, so the caller and the
> target of the foreign userId are the same person."

Without that sentence a differential test across two "accounts" reads as though a third
party's account was used as the victim — and this program's forfeiture rules punish
"using another participant's account or maps as the victim in a proof of concept".

## 3. Re-verify and rebuild the draft

- Re-verify the rebuilt PDF 3x: page count, byte size, and every required string
  (full SHA-256 rather than a 24-char truncation, the submitting userId, the reference id).
- Rebuild the Gmail draft so the attachment is the corrected file. A draft left holding the
  pre-correction PDF is a rejected deliverable — verify with
  `drafts().get(..., format="full")` and read `parts[].filename` + `body.size` against the
  file on disk.
- Put a "SUBMISSION DETAILS" block in the email body (title, date of discovery, attachment
  name + size, PayPal e-mail) so the same content can be pasted straight into a portal form
  if the e-mail channel is not the preferred one.
