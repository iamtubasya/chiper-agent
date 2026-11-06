# Submitting through a vendor's own portal (not e-mail)

Measured 2026-10-31 (Scribble Maps, `api.scribblemaps.com/vulnerabilities`). The program
requires login to submit, so the portal is the primary channel. What actually worked, and
what to avoid.

## The human form can be captcha-walled — check for a documented programmatic path first

`POST /api/vulnerability/submit` (multipart: `title`, `description`, `date`, `attachments`,
plus a `captcha` field holding `turnstile.getResponse('#turnstile-widget')`) is the form
endpoint. When Turnstile stops auto-solving, the portal page itself documents an
alternative for AI/agent submission that needs **no captcha**:

```
POST /api/vulnerability/aisubmit?userId=<the session's own userId>
multipart: title, description, attachments
```

Before using it, verify the session identity and that the parameter matches
(`GET /api/account` → `userId`). Sending a *foreign* userId is itself the bug class being
reported elsewhere — never do it as a convenience.

## aisubmit returns pendingConfirmation — the report is NOT in review yet

```
200 {"success":true,"pendingConfirmation":true,"referenceId":"FF3179",
     "message":"...emailed fz*****@gmail.com a link to approve this submission...
                will not be reviewed until you open that email, click the approval link..."}
```

Consequences to plan for:
- `GET /api/vulnerability/list` stays `[]` until the owner clicks the approval link, so an
  empty list is **not** proof the submission failed.
- The approval e-mail can be delayed (measured: not in the inbox 12 minutes after a 200).
  Tell the operator to watch spam and to click within the stated expiry (48 h here).
- The operator, not the agent, should click the approval link — it is their identity and
  their mailbox.

## Dry-run probes against the submit endpoint trip a per-IP throttle

Six deliberately-incomplete payloads (all rejected by validation, none created a report)
were enough to make `/api/vulnerability/submit` answer
`429 "You've submitted too many reports recently"`. Rules:

- Validate the payload shape with **one** incomplete probe, not six. The useful signal is
  the field name in the error (`"Description is required"` → the field is `description`).
- Distinguish throttle from validation before concluding anything:
  `400 {"error":"..."}` = throttle clear and payload wrong;
  `429` = back off, do not keep probing.
- Space probes out; the throttle is per network, so it also blocks the operator's own
  manual submit from the same IP. Say so when handing the browser over.

## One report per day per account

Programs that cap submissions make the **strongest** finding the one that goes through the
portal today; the rest wait or go by e-mail. Sequence them by severity, and record in the
coverage doc which finding consumed the daily slot so the next session does not re-send it.

## Handing the form to the operator

- Fill the form in a headed browser on a persistent profile, verify the fields 3x
  (title length, description length, date, attachment name **and byte size** against the
  file on disk, prefilled payment e-mail), then leave the window open.
- Run it with `terminal background=true` so the browser survives the turn, and tell the
  operator the keep-open duration — a script that exits closes the window.
- Screenshot after the checks pass; a larger screenshot than the empty-form one is cheap
  evidence the fields really rendered.
