# API-Gateway webhook receiver: auth-inconsistency across provider routes

Trigger: a `webhooks.` / `hooks.` / callback host is AWS API Gateway behind CloudFront. Symptoms: most
routes return `403 {"message":"Missing Authentication Token"}` (classic API Gateway error for a route that
requires an API key or IAM auth), and response headers carry `x-amz-apigw-id:` / `x-amzn-RequestId:` /
`X-Amzn-Trace-Id:`.

## Technique — enumerate provider webhook routes and diff their auth

```python
providers = ["trello","asana","jira","github","gitlab","wrike","clickup","zendesk",
             "monday","notion","hubspot","salesforce","confluence","jotform","typeform",
             "google","sheets","excel","slack"]
for p in providers:
    r = requests.post(f"https://webhooks.<apex>/{p}/webhook", json={"test":1}, timeout=10)
    print(p, r.status_code, r.text[:80])
```

The signal is the **asymmetry**: some routes return `403 "Missing Authentication Token"` (auth enforced)
while others return `200 "Webhook received successfully."` with no key, no `Authorization` header, no
signature. That split is the evidence of an oversight, not by-design — if it were a uniform "fast ACK then
async-validate" design, every route would 200 and drop bad payloads async.

Also probe the sibling path shapes: `/{p}/webhook`, `/{p}/hooks`, `/webhook/{p}`, `/notify`,
`/api/{p}/webhook`, and both GET + POST on each.

## Verify it's really no-signature

Send deliberately wrong HMAC/signature headers and confirm the endpoint still 200s:

```python
for hdr in [{"X-Trello-Webhook":"invalid"}, {"X-Hub-Signature-256":"sha256=invalid"},
            {"X-Gitlab-Token":"invalid"}]:
    r = requests.post(url, json={"a":1}, headers=hdr)
    # still 200 -> no signature validation before the ACK
```

Reproduce 3× (unique body each time) and check prod AND staging (the `staging-webhooks.` host usually
mirrors it).

## Honest framing (avoid over-claim)

These are ACK endpoints: fixed string response, no observable processing, no reflection. The real impact
(webhook forgery driving a sync / data change, or replay against a synced object) needs a connected
provider account to prove. Report as **Medium** missing-authentication (CWE-306) with an explicit
"could not show end-to-end effect without a connected tool" caveat — do not inflate to High.