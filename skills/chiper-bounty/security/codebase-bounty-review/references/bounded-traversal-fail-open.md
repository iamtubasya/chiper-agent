# Bounded traversal fail-open (any stack)

A security decision computed by **walking** attacker-influenced structure — metadata, manifest,
JSON-in-string, header list, ACL entries, pagination — but the walk has a **budget** (node count,
depth, item count, byte length) and ends **silently** when the budget runs out. The attacker pads the
document, puts the payload past the bound, and the control returns "clean".

This is a generalisation of the fail-open family in `native-client-fail-open-casebook.md` (B/D/E):
there the failure was swallowed; here it is *truncated*. Same result — the control reports success
without having decided.

Worked case: bWallet / b-Aware 2026-10, `src/mobile/market/safety.ts`, **validated, Medium**
("defeat the safety filter").

---

## The shape

```ts
const MAX_DEPTH = 10;
const MAX_NODES = 500;

const walkMap = (map, onObject, onString) => {
  let nodes = 0;
  const walk = (v, depth, fromJson) => {
    if (depth > MAX_DEPTH || ++nodes > MAX_NODES) return;      // <-- SILENT STOP
    ...
  };
  walk(map, 0, false);
};

check(s) {
  if (metadataFlagsAdult(s.map)) return { blocked: true, reason: 'metadata' };
  const texts = [...s.texts, ...mapTexts(s.map)];               // <-- same capped walk
  if (texts.some(t => this.matchesText(t))) return { blocked: true, reason: 'keyword' };
  return { blocked: false };                                    // "clean" — but only partly scanned
}
```

Safe shape: budget exhaustion is a **verdict**, not a `return`.

```ts
let budgetExhausted = false;
if (depth > MAX_DEPTH || ++nodes > MAX_NODES) { budgetExhausted = true; return; }
...
if (budgetExhausted) return { blocked: true, reason: 'metadata' };   // fail closed
```

---

## Find it

```bash
# the constants
rg -n 'MAX_(NODES|DEPTH|ITEMS|ENTRIES|KEYS|SIZE|COUNT)|maxDepth|maxNodes|maxItems' <dir>

# the silent stops
rg -n 'if \(.*(depth|nodes|count|len|length).*[<>].*(MAX|max|LIMIT|limit).*\)\s*return' <dir>

# the truncations that do not announce themselves
rg -n '\.slice\(0,\s*[0-9]{2,}\)|\.substring\(0,\s*[0-9]{2,}\)|\.take\([0-9]{2,}\)|\[:[0-9]{2,}\]'
```

Ask of every hit: **does the caller learn that it did not see everything?** If not, it is a candidate.

---

## The trap that wastes a round: the flat-field control hides the bug

First PoC attempt looked "safe": flat `{nsfw: true}` past 600 sibling keys → `blocked: true`.
Reason: a **separate** top-level scan runs before/independent of the walk:

```ts
const objectFlagsAdult = (m) => { for (const [k, v] of Object.entries(m)) ... }  // top level only
```

So the bound only matters for what the flat scan cannot reach. The payload must be **nested and past
the cap**:

```ts
const pastCap = (payload) => {
  const attributes = [];
  for (let i = 0; i < 400; i++) attributes.push({ trait: `v${i}` });  // 400 obj + 400 str + 1 arr = 801 nodes
  attributes.push(payload);                                           // <- the real content
  return { attributes };
};
```

Observed result (real module, 3/3 runs):

| case | payload | result |
|---|---|---|
| A control | flat `nsfw: true` | blocked ✓ |
| B control | `nsfw` at depth 3 | blocked ✓ |
| C | `nsfw` nested, past cap | **blocked=false ✗** |
| D | `contentRating:'explicit'` past cap | **blocked=false ✗** |
| E | banned keyword past cap | **blocked=false ✗** |
| F control | keyword inside a 20 100-char JSON string | blocked ✓ |

**Always ship the controls.** A/B/F passing is what proves the filter works normally and that C/D/E are
the bound, not a broken harness. Without controls the report reads like a mis-written test.

---

## Proving reachability (not just a helper misbehaving)

Trace the call graph to the consumer and quote it:

```ts
// classify.ts:145 — map is the inscription's MAP metadata, creator-controlled
const verdict = safety().check({ ids: [outpoint, origin], collectionId, texts: [name, coll?.name], map: info?.map });
if (verdict.blocked || collVerdict.blocked) return null;     // false verdict => listing is shown
```

Enumerate every sibling consumer (`MarketPage.tsx`, `roomSafety.ts`, …) — it raises the blast radius
and shows you are not reporting an unreachable helper.

---

## Evidence package that triaged cleanly

1. PoC **importing the real module** — no copy, no reimplementation:
   `import { safety } from '.../src/mobile/market/safety'` → `bun run poc-nodecap.ts`
2. Transcript, 3 consecutive identical runs (`poc-nodecap-run.txt`).
3. **The same assertions dropped into the repo's own test tree** so the maintainer runs it with their
   own runner:
   ```
   bun test src/mobile/market/safety.nodecap.test.ts
   -> 1 pass / 2 fail     (fails exactly on the bypass assertions)
   ```
   Then **remove your file from their tree** and show `git status` clean — you demonstrated, you did
   not leave debris in the repo.
4. A findings doc with the blocked/expected table and an honest "limits" paragraph (what is NOT
   affected: id/outpoint blocklists still work).

---

## The argument that kills "by design"

Quote the file's own comment about a **previous fix of the same class**:

> "to MAX_DEPTH levels and at most MAX_NODES nodes (b-Aware report: nesting deeper than the old walk hid terms)"

They already paid for "hidden terms past the walk". The width cap is the same defect, unfixed. That
single sentence removes the reviewer's easiest objection.

Second argument: **the product's own claim**. This filter is documented "ALWAYS ON, with no setting to
turn it off … Apple App Review 1.1.4 / Google Play sexual-content policy". A control that must always
hold is held to a higher bar than one that is advisory.

---

## Severity

Map to the program's own impact table, not to CVSS. bWallet lists "defeat the safety filter" as
**Medium**. State plainly what it is NOT (no funds move, no key read, blocklists by id still work) —
that honesty is what makes the Medium stick instead of drawing a downgrade to Low.

---

## Same shape elsewhere (checklist)

- `parseJsonish` / `JSON.parse` **length caps** — payload just over the cap is never parsed.
- "first N items" allowlists and pagination guards (`items.slice(0, N).every(isAllowed)`).
- Regex-based validators with a step/backtrack budget.
- Recursive `walk`/`visit`/`traverse` in ACL, permission, manifest, or policy evaluators.
- `catch {}` wrapped around a verification walk — error becomes "no finding".
- Truncating log/template scanners (`body.slice(0, 4096)`).
- Anywhere the reviewer's mental model is "we scan the whole document" and the code says "up to N".
