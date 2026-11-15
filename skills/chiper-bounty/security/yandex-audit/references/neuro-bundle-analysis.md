# Neuro (Futuris) bundle analysis — where the generative_answer logic lives (2026-11-02)

## Internal naming
- Yandex's generative search is called **"Futuris"** internally, and the SERP tab is
  **`search_neuro`**. Events observed in `main-chunk`: `futuris:mounted`, `futuris:open`,
  `futuris:scrollOver`, `neuro-block:open` / `neuro-block:close`, `HeaderNav:selectNeuro`.

## Bundle layout
- SERP shell: `yastatic.net/s3/web4static/_/v2/main-chunk.0774099cb2adf7d4.js` (513 KB) — hosts
  `window.Ya.createSerpFetch` (the SERP request layer) and `SerpContext`.
- Neuro feature i18n/table: `.../features/Futuris_search_gen_rsr@desktop.2ced7b091b39f887.js`
  (mostly locale strings + a big webpack module-id table — NOT the encoder).
- `createSerpFetch` signature observed: `baseParams:{yu: t.yandexuid}`, `baseOptions:{headers:{}}`,
  `timeout: 2e4, retryCount: 3`. So the endpoint is queried with `yu=<yandexuid>` as a base param.

## The encoder (`coded_request_context`) — STOP LINE
- The `generative_answer` request carries `coded_request_context`, an obfuscated blob (leading `2M`
  prefix, `.`-joined segments; NOT plain base64). The encoder was NOT found in any of the 20 static
  bundles pulled from `nova3` + `web4static`; it lives in a lazily-loaded webpack chunk whose map is
  resolved at runtime (`publicPath` is not statically enumerable in `main-chunk`).
- FORGING `coded_request_context` = deobfuscating their client-side request signing. That is
  **reverse engineering / request tampering**, which sits against Yandex's OOS line ("possibility to
  decompile or use reverse application development") and produces no bounty-scale finding on its own
  (a forged-but-empty `data:""` teaser is not impact).

## What this established (honestly)
1. Concrete AI endpoint + auth model: `POST /search/generative_answer` (cookie-gated, `yu=` param,
   signed `coded_request_context`).
2. The teaser flow (`from=teaser_bsa`) returns `data:""` — no model text flows back on that path.
3. No prompt-injection impact, no cross-user read, no system-prompt/secret leak demonstrated.
4. No OOB callback received.

## Conclusion + recommendation
This is a solid RECON deliverable (endpoint map + auth model + signed-payload identification), not a
finding. The honest terminal state: the generative answer is served behind a signed, cookie-gated,
teaser-only flow; the model-text path and any injection surface live behind the full SERP Neuro panel,
which requires an authenticated session and whose request signing is deliberately opaque. Continue only
if the operator authorizes bundle deobfuscation (arguably OOS) OR wants to flip to the authenticated
Alice WS `TextInput` reflection guardrail test with two own accounts.