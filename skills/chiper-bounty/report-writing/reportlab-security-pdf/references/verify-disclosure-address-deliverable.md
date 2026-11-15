# Verify the disclosure address is DELIVERABLE — a legal-page address can be decorative

Hit live 2026-10-13 (Arrakis engagement).

## What happened

The target published no `security.txt` and no bug-bounty programme. The only addresses on the site were
`team@arrakis.finance`, printed in the footer/legal pages (`privacy-policy`, `terms-of-service`,
`disclaimer`). A report was staged and sent there.

A day later the mailbox held `Delivery Status Notification (Failure)`:

```
Final-Recipient: rfc822; team@arrakis.finance
Action: failed
Status: 5.1.3
Diagnostic-Code: smtp; The email account that you tried to reach does not exist.
```

So **the address the vendor publishes does not exist.** The send delivered nothing, and because Gmail
deletes a draft on send, the "draft is gone = delivered" heuristic read as success. The same engagement
also sent to `security@arrakis.finance` (guessed, not published) — that one never bounced. MX for the
domain is `smtp.google.com`, i.e. Google Workspace, so a Workspace group/alias accepts mail where the
legal-page address was never provisioned.

## Rules that follow

1. **Do not treat "published on the legal pages" as proof the address receives mail.** A legal-page
   contact is a legal formality; it is frequently an unmonitored or non-existent mailbox.
2. **Collection order for a vendor with no security.txt:** `security.txt` (if present) → security@ /
   psirt@ / security-report@ → an address from `git log` / `CODEOWNERS` / a SECURITY.md → the legal-page
   address LAST. And when the legal-page address is all there is, send to it **and** to the best
   security@ guess, rather than trusting the published one.
3. **Read the bounce window before calling a send delivered.** After any disclosure send, query
   `from:mailer-daemon OR from:postmaster newer_than:3d` and pull
   `Final-Recipient / Action / Status / Diagnostic-Code` from each. `5.1.3` = no such user. A Google
   Groups rejection reads *"the group you tried to contact (X) may not exist, or you may not have
   permission to post messages to the group"* — same practical outcome, different wording, so match on
   both shapes.
4. **Verify delivery in the SENT folder, not the Drafts folder.** Drafts vanish on send; `in:sent`
   with the recipient in the query is the only place that shows what actually left. Assert the
   attachment there too: `/in:sent` → `format=full` → download each part → `sha256` against the local
   PDF. A sent message with a missing or stale attachment is a silent failure that only this check
   catches.
5. If a send bounced, re-send to a working address as a NEW message (do not "fix" the bounced one) and
   say so in the engagement log, so the operator knows the first attempt reached nobody.
