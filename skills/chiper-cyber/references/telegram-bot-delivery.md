# Telegram bot delivery (reference for `chiper-aifaceswap-api`)

How generated artefacts reach the operator through Telegram instead of a browser
download. Companion to the face-swap pipeline (`chiper-faceswap-webapp`).

## Topology

```
client ──HTTPS──► FastAPI :8091 ──► pipeline (ffmpeg → multi-fingerprint → zip)
                                          │
                                          └──► Bot API sendMessage / sendDocument
                                                        │
                                                operator chat on Telegram
```

## Rules of the road

| Rule | Value |
|---|---|
| Chat target | allow-listed chat id only — reject everyone else |
| Max document size | 50 MB via Bot API; larger → chunk or host a signed URL |
| File naming | `<job-id>.zip`, never user-controlled names |
| Retention | delete local artefact after successful delivery |
| Failure mode | retry once, then post a short error message — never silent |

## Minimal send flow

1. Job finishes → artefact path known.
2. `sendDocument` with `chat_id`, `document` (multipart), `caption = job metadata`.
3. On `429 Too Many Requests` → honour `retry_after`, then give up.
4. Record `{job_id, message_id, bytes, delivered_at}` for audit.

## Security notes

- Bot token lives in an env file with `0600`, never in the repo.
- Do not echo artefact contents in the caption (may contain personal data).
- Disable group usage or explicitly allow-list the group id.
- Webhook secret token verified on every update before parsing.
