# The sibling-route gate: same backend, different front door

Learned live 2026-10-30 (Bankr — AI agent platform). This is a distinct entitlement-bypass class
from the field-tampering and webhook-forgery legs already in the parent skill: **nothing is forged
and no field is injected. The product simply exposes a second front door to the same paid backend,
and that door has no gate.**

## The shape of the bug

```
front door A   POST /agent/prompt        -> 403 subscription_required   (gate enforced)
front door B   POST /webhooks/<user>/<x> -> 202, agent runs anyway      (no gate, no metering)
                              both invoke the same agent runtime
```

Paid capability reached on a free account with zero credits, no subscription, and no forged
anything. The vendor's own documentation makes the two doors obvious: A says "Club membership or
Max Mode credits required for AI prompts"; B says "the handler returns a prompt for the agent to
run under your permissions" — and never mentions payment.

## How to find it (do this on every agent / LLM / automation product)

1. **List every surface that can invoke the paid backend.** Documentation sitemaps are the fastest
   map: `/sitemap.xml` gave the whole product tree in one request. Look for the words *agent*,
   *automation*, *webhook*, *scheduler*, *app script*, *cron*, *chat*, *CLI*, *MCP*, *skill*,
   *plugin*, *API*.
2. **Gate-test each surface independently**, not just the one the pricing page sells. The pricing
   page only ever names door A.
3. **Compare error strings.** A gate that fires returns a *specific* string
   (`403 {"error":"subscription_required"}`); a route without the gate returns success. Two
   surfaces, two different answers, same account, same minute — that comparison IS the finding.
4. **Then check the METERING, which is a second independent bug.** A gate can be missing while the
   usage counter still increments, or (as here) both are missing. Read the counter before and after:

   ```
   GET /user   -> bankrClub.dailyMessageLimit 5, dailyMessageCount 0
   ... run the paid capability N times ...
   GET /user   -> dailyMessageCount still 0
   ```

   `count unchanged after N successful paid runs` is the sentence that turns "maybe this is
   intended" into "this capability is unmetered".

## Proving it without touching money

Deploy your own handler so the paid backend does something *observable and harmless* per run —
write a file, echo a marker — then invoke the public URL once per marker:

```js
// handler: read a marker from the request body, ask the agent to write it to a file
export default async function handler(req) {
  let m = 'v0';
  try { const b = await req.json(); if (b.marker) m = b.marker; } catch (e) {}
  return new Response(JSON.stringify({
    prompt: 'Create a plain-text file named run-' + m + '.txt in my file storage whose content is exactly: ' + m
  }), { status: 200, headers: { 'content-type': 'application/json' } });
}
```

Invoke three times with `val1/val2/val3`, then list storage: three files, `createdBy: agent`.
Three markers = three independent agent turns = three units of unmetered inference, with no
purchase. This is a clean, non-destructive PoC that a triager can re-run.

## Read-back channel when the handler cannot return data

If the handler contract is "return `{prompt}`, not a response body", you cannot echo diagnostics
from the function. Two channels work:

- `console.log(...)` inside the handler → the vendor's invocation-log endpoint
  (`GET /webhooks/<name>/logs` → `handlerLogs`). This is the reliable exfil for sandbox
  reconnaissance (runtime, env, filesystem).
- The agent's own tools — have the prompt write a file, then read it back through the normal file
  API. Use this for the PoC because it is the *product* doing the work, not your code.

## Severity framing

- Gate missing + metering missing + free account → **Medium (single-tenant)**: no data crosses an
  account boundary and no funds move, so it is not High. Say that explicitly.
- If the same door also enables *write* tools (transfers, orders), say so as impact context but do
  **not** claim fund risk you did not demonstrate — in this case the recipient allowlist and the
  wallet security settings both held, and recording that as a "guardrail that held" section is what
  keeps the finding credible.
- Quantify the multiplier: per-webhook limits (10/min, 1000/day here) times the number of webhooks a
  wallet can deploy means the unmetered use is not bounded by one endpoint.

## What is usually NOT the bug (checked, held)

- Rate-limit / IP-allowlist enforcement on the second door (it was enforced — XFF, `X-Real-IP`,
  `Forwarded`, `X-Client-IP`, `True-Client-IP` all still 403).
- `readOnly` key flag across the deploy surfaces (enforced on swap, webhook deploy, x402 deploy,
  env write, file upload — even where the vendor's own OpenAPI text says the handler skips it;
  stale docs are not a bug).
- Cross-tenant reads on job/thread/log/file IDs (all correctly scoped).
