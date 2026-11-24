---
name: chiper-skill-usage-forensics
description: "Measure and audit which agent skills are actually used, how much context they cost, and which are dead weight. Covers the three telemetry sources (~/.chiper/skills/.usage.json, ~/.chiper/logs/agent.log*, ~/.chiper/state.db), how to parse each, how to reconcile them when they disagree, and how to design skill-history tooling on top. Use when asking 'is this skill being used?', 'which skills are dead?', 'how many tokens do skills cost me?', or when tuning how aggressively an agent loads skills."
origin: chiper
version: "1.0.0"
compatibility:
  - chiper
  - claude-code
  - cursor
  - windsurf
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
metadata:
  domain: meta-observability
  tool_count: 0
  guide_count: 3
  mitre: "N/A (non-attack meta skill)"
  last_reviewed: "2026-11-08"
---

# Skill Usage Forensics

> **Supplementary Files**:
> - `references/telemetry-sources.md` — exact file paths, schemas, and field-by-field semantics of all three telemetry layers
> - `references/query-recipes.md` — copy-paste Python/SQL recipes that produced the audit tables
> - `references/skill-loading-doctrine.md` — what to change when measurement shows skills aren't loading (keyword tables, named anti-patterns, two-strike breaker, cache-safe design rules)
> - `scripts/skill_usage_audit.py` — runnable auditor: timeline, per-skill aggregate, token cost, dead-skill list, error tally
> - `references/fabricated-capability-claims.md` — how a pack's `TOOLS.md` / `MEMORY.md` / `SKILL.md` can carry an inventory that is 100% false, how that poisons agent behaviour, and the `command -v` verification sweep that replaces it
> - `references/agent-md-runtime-loading.md` — which `.md` files the runtime actually loads (only SOUL.md + memories/MEMORY.md + memories/USER.md + one project-context file), proof that `TOOLS.md` is dead, and the frozen-snapshot rule that defers memory edits to the next session

## Summary

Answer "which skills does this agent actually use, and what do they cost?" from real telemetry instead of intuition. Chiper records skill usage in **three places that disagree with each other** — knowing which to trust for which question is the entire skill.

**Domain**: meta-observability (auditing the agent's own behaviour)

## When to Use

- User asks whether skills are being loaded / why skills seem unused
- Deciding whether to rewrite a SOUL skill-loading section — **measure first**, a prompt tweak aimed at "skills never load" is wasted if the real problem is 141 skills with 11 ever touched
- Auditing context/token cost attributable to skills
- Deciding what to prune, split, or consolidate in a 100+ skill pack
- Verifying a change to skill loading actually changed behaviour

## The Three Telemetry Sources

| Source | Path | Grain | Strength | Weakness |
|---|---|---|---|---|
| Lifetime counters | `~/.chiper/skills/.usage.json` | per-skill aggregate, forever | survives session pruning | no timeline, no context, no success/fail, **names can fork** |
| Executor log | `~/.chiper/logs/agent.log*` (4 rotated files) | per tool call | duration + payload size + error text | rotation drops history |
| Session store | `~/.chiper/state.db` (`messages` table) | per message, with args | full argument JSON, session_id, timestamp | pruned by `chiper sessions prune`; large |

**Rule of thumb:**
- "How many times, ever?" → `.usage.json`
- "How much did each load cost?" → `agent.log`
- "Which session, what was the skill called with?" → `state.db`

## Methodology

### Phase 1: Establish the baseline before theorising

Never reason about skill usage from the visible `available_skills` index — that is *availability*, not *usage*. Pull all three sources first, then reconcile.

### Phase 2: Extract events from `agent.log`

Executor log lines are the richest single source. Two regexes cover almost everything:

```python
LINE = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ (\w+) \[([^\]]*)\] (.*)$')
OK   = re.compile(r'tool (\w+) completed \(([\d.]+)s, (\d+) chars\)')
FAIL = re.compile(r'Tool (\w+) returned error \(([\d.]+)s\): (.*)')
```

Group 3 of `LINE` is the session id, so every call keeps its session attribution for free. `chars` is the payload that entered context — **this is the token-cost metric, and it is invisible everywhere else**.

### Phase 3: Extract events from `state.db`

`skill_view` calls live in assistant messages as a `tool_calls` JSON array:

```sql
SELECT id, session_id, tool_calls, timestamp FROM messages
WHERE tool_calls LIKE '%"skill_view"%' AND role = 'assistant';
```

Note there is **no `sqlite3` binary** on a stock Chiper host — use Python's `sqlite3` module. `~/.chiper/sessions/sessions.db` exists but is an empty stub; the real store is `~/.chiper/state.db`.

### Phase 4: Decide what "used" means

`skill_view` succeeding is **not** usage — it can be a browse, a failed patch preamble, or a curator review pass. Use the follow-up heuristics, in order of trustworthiness:

| Definition | Rule | Notes |
|---|---|---|
| Loaded | `skill_view` returned `success: true` | over-counts |
| **Worked** (recommended) | ≥1 non-`skill_view` tool call in the same session within 300s | cheap, deterministic, tracks real work |
| Cited | skill name appears in the assistant's text reply | brittle, model may paraphrase |

## 4. Two hosts, one question — always ask which install

Chiper runs on more than one surface, and **their telemetry is disjoint**. Before quoting any
number, establish which install you are measuring:

```bash
hostname                                        # which machine am I actually on
docker ps -a                                    # is there a Chiper container alongside?
docker exec <ctr> bash -lc 'hostname; ls ~/.chiper/logs'
```

A container `chiper-install-test` and the host VPS both have a full `~/.chiper`, with
different users, different histories, and different `.usage.json` files. Mixing them produces
a "the numbers moved" bug that does not exist. Pull logs out for analysis rather than reading
them in-place through `docker exec` on every query:

```bash
for f in agent.log agent.log.1 agent.log.2 agent.log.3; do
  docker exec <ctr> cat ~/.chiper/logs/$f 2>/dev/null
done > /tmp/ctr_agent.log
```

Container installs skew differently from host installs and the skew is itself the finding:

| Metric | Host (operator use) | Container (installer/build use) |
|---|---|---|
| `skill_manage` : `skill_view` | ≈ 1:1 | **≈ 2:1** (pack still being written) |
| Avg `skill_view` payload | ~13 KB | **~22 KB** |
| Error rate | ~5% | **~8%** |
| Ambiguous-name failures | rare | **common** (duplicate mirrors installed twice) |

A `skill_manage`-dominant profile means the pack is under construction, not in use — do not
conclude "skills are well maintained" from it.

## 5. Reconcile the sources

Expect disagreement and treat it as signal, not a bug to average away:

- `.usage.json` counts **cumulative lifetime**; `state.db` only knows surviving sessions → `.usage.json` will read higher. That gap is how much history you already lost to pruning.
- `.usage.json` keys can **fork** on qualified names: `chiper-security-bounty-hunter` and `chiper-cyber:chiper-security-bounty-hunter` are the same skill with two counters. Always normalise with `name.split(":")[-1]` before aggregating.

### Phase 6: Derive the four findings that actually matter

1. **Coverage ratio** — distinct skills used ÷ skills installed. Below ~15% means the pack is mostly dead weight and the problem is curation, not loading.
2. **Concentration** — top skill's share of all loads. One aggregator/router skill at 35–40% means the agent wants a map, not more procedures.
3. **Token cost** — sum of `chars` ÷ 4 ≈ tokens. Report total and top-10 payloads; one 100 KB skill load is ~26 k tokens.
4. **Error rate** — failed calls ÷ total. Non-zero usually means stale `old_string` patches or skills referenced under wrong names.

## 6. Domain-hit rate — the metric that predicts non-loading

Coverage ratio (Phase 6) tells you how much of the pack is dead. **Domain-hit rate** tells you
whether the model fails to route *even when the skill exists*. This is the number to quote when
someone says "skills aren't being called for task X".

Procedure:

1. Build a keyword→domain map for the domains you care about (reuse the table from
   `references/skill-loading-doctrine.md`).
2. Pull every user turn from `agent.log` — `grep 'conversation turn:'` — and drop the curator's
   own `Review the conversation above…` turns, they are not user tasks.
3. Keep turns whose text hits ≥1 domain keyword.
4. For each, ask: did a `skill_view` happen in the same session within ~900 s **after** the turn?
5. `hit_rate = hits_with_skill_view / hits`

Worked example (host, 19 domain-bearing user turns over 5 days):

```
domain-relevant tasks:          19
followed by skill_view ≤15min:   7   (37%)
missed entirely:                12   (63%)
```

Cross-check against the pack itself before blaming the prompt: if the domain's dedicated skills
have `view_count == 0` in `.usage.json`, the skill genuinely never fired. An OSINT drill-down
found 9 OSINT/recon skills installed, **2 ever loaded**, and 19 of 20 skills containing
recon capability never touched once. That is routing failure, not "the model is busy".

Also check model tier — the session with 94 `skill_view` calls was running a different model
than the sessions with zero. Compliance is partly a model-quality signal; say so instead of
only rewriting prompt text.

## 7. Interpreting the Results

| Symptom | Real cause | Action |
|---|---|---|
| Few skills ever load | Pack too big / descriptions don't match user vocabulary | Curate and prune; do **not** add more prompt text |
| One skill dominates | It is a router/aggregator doing the real work | Keep it small and sharp; consider splitting referenced sub-skills |
| Skills exist but never fire | Domain-hit rate low; pack inventory claims tools the host lacks (`command -v` sweep) | Verify inventory first, then doctrine — see `references/fabricated-capability-claims.md` |
| Entry-point `SKILL.md` is huge | It is an archive, not a routing doc | Split to `SKILL.md` + `references/`, add a task→skill table |
| Huge payload per load | Skill body too long | Split into `SKILL.md` + `references/`, load references on demand |
| Token spend high but loads low | A few giant skills | Attack the top-10 payloads, not the call count |
| Counter names forked | Qualified vs bare name | Normalise; do not "fix" by deleting records |

## Pitfalls

- **Repair scope discipline.** When the operator names specific fields to fix, fix *only* those.
  Rewriting surrounding prose, "improving" phrasing, or correcting other defects in the same
  write gets you corrected. Byte-delta check after every write; see
  `references/fabricated-capability-claims.md` → "Repair doctrine".
- **`scripts/skill_usage_audit.py` only ran live once** (2026-11-08, host profile `default`) — its individual recipes are all verified separately, but treat a re-run on a new host/adapter as a test until its numbers reconcile.
- **Never conclude "skills aren't loading" without checking `.usage.json` first.** It is cumulative and often proves they load plenty.
- **`skill_manage` ≈ `skill_view` in count is a red flag**, not a healthy sign — it means skills are being rewritten as often as they are read, i.e. the pack never stabilises.
- **`skills_list` output is large** (~50 KB for 140 skills). Counting those calls as cheap is wrong; multiply calls × payload size.
- `agent.log` rotates (`.1`–`.3`), so always glob `agent.log*` and sort by timestamp — per-file order is not chronological.
- Do **not** propose reordering the `available_skills` index per turn to boost relevance: it mutates the system prompt mid-conversation and destroys prompt caching.
- Report the gap between `.usage.json` and `state.db` counts honestly rather than picking one number.

## Verification

- Distinct-skill count from `.usage.json` and from the log parse should be within a few names of each other; a large gap means heavy pruning or forked keys.
- Sum of per-skill counts must equal the number of extracted events (allow for duplicates across rotated files).
- Any skill appearing in logs but absent from `.usage.json` is a real telemetry bug worth reporting, not silently dropped.

## Acting on the Result

Measurement alone changes nothing. When the audit shows skills not loading or the pack
mostly dead, the remedy is doctrine design, not more skill content — see
`references/skill-loading-doctrine.md` for the cache-safe pattern (per-action keyword
table, named anti-patterns, two-strike circuit breaker) plus the review-before-apply
rule that keeps a 12 KB system prompt honest.

Cross-check before rewriting a SOUL: a coverage ratio under ~15% means the real problem
is pack curation, and no amount of prompt doctrine will make 141 skills load. Prune first.

Before either step, run the **inventory truth check** in
`references/fabricated-capability-claims.md`. A pack that claims "518 tools mastered" while the
host has 11 of 50 present will keep producing wrong commands no matter how well skills route;
the agent is answering from a false map.
