# Making Skills Actually Load — Doctrine Design

Companion to the measurement half of this skill. Measurement tells you *whether*
skills load; this tells you *what to change when they don't*.

## The failure mode being fixed

Chiper's skill system is lazy by design:

| Tier | Content | When |
|---|---|---|
| 1 | `name: description` in `<available_skills>` | always, in system prompt |
| 2 | full `SKILL.md` | on `skill_view(name)` |
| 3 | `references/`, `scripts/`, `templates/` | on `skill_view(name, file_path=...)` |

Tier 1 is always present. Tiers 2–3 require the model to *decide* to call a tool.
Nothing in the codebase forces that decision — `_skill_view_with_bump` only records
`view_count`. So skill loading is **prompt-level compliance**, not enforcement.

The standard prompt text (in `agent/prompt_builder.py`, emitted ahead of
`<available_skills>`) already says:

> "Before replying, scan the skills below. If a skill matches or is even partially
> relevant to your task, you MUST load it with skill_view(name)..."

Three things defeat it:

1. **Index squash** — 100–400 skill lines drown between system prompt, memory, and history.
2. **Threshold ambiguity** — "even partially relevant" invites the model to rule itself out.
3. **Named rationalisations** — the model skips with a stock excuse ("I already know SQLi", "this is just quick recon") that no rule names explicitly.

## What does NOT work

- **Adding more skill content.** The problem is at the decision point, not in the material.
- **Reordering the index per turn by keyword relevance.** It mutates the system prompt
  mid-conversation and destroys per-conversation prompt caching. Cost multiplies.
  (AGENTS.md in the Chiper repo is explicit: the cached prefix is sacred.)
- **A new core tool that auto-loads skills.** Violates the narrow-waist rule; every tool
  ships on every API call.
- **Repeating "MUST load" louder.** Already there. Volume is not the missing ingredient.

## What works: move the checkpoint to the action boundary

Replace "scan at session start" with **"scan every time the action changes"**.
Session start is the wrong checkpoint — at turn 0 you don't yet know what you'll do.
Actions change 10–50 times per session, so the trigger fires far more often.

Four components carry the load:

### 1. Keyword → domain table

Convert the cognitive task from "find a matching skill among N names" into a
deterministic two-step lookup. Prose descriptions invite interpretation; a keyword
table invites matching. Keep it as a table — this is the single highest-leverage piece.

```markdown
| Domain | Keyword |
|---|---|
| Web | sql, xss, ssrf, xxe, csrf, lfi, upload, deserial, ssti, idor, jwt, oauth |
| Network | nmap, scan, port, ad, ldap, kerberos, smb, dns, mitm, tunnel, vpn |
| Cloud | aws, gcp, azure, kubernetes, docker, terraform, ci/cd, s3, iam |
| ... | ... |
```

### 2. Named anti-patterns

Give every stock excuse a name and a ❌. An unnamed rationalisation passes unnoticed;
a named one must be explicitly rejected, which is cognitively expensive. Same technique
as "known failure modes" in any human playbook.

```markdown
- ❌ "I already know <technique>" → load anyway; the skill holds flags and pitfalls
- ❌ "This is just quick recon" → recon has a skill too
- ❌ "One skill covers everything" → one domain, one skill
- ❌ "The index looked complete" → index is names only, body may contradict
```

### 3. Two-strike circuit breaker

Without it, a failing model retries the same approach with re-rolled parameters —
classic tunnel vision. Force escalation to external knowledge after two failures:
`failed 2x → load a different skill → retry`. This converts a *fail→retry* loop into
a *fail→pivot* loop, and pivoting is where the 100+ unused skills become reachable.

### 4. Tier-3 pointer

Big skills often hold the real commands in `references/`. If `SKILL.md` points at a
reference, load the reference — don't stop at tier 2 and improvise.

## Cost accounting

Doctrine text is added to the system prompt and therefore paid **every turn**.
Budget it explicitly:

| Doctrine size | Extra cost |
|---|---|
| ~2.4 KB (≈600 tokens) | acceptable for a domain-specific agent |
| >5 KB | re-read the pack — most of it is probably decorative |

Static doctrine is cache-safe: the bytes never change across turns, so only the
model's *behaviour* shifts. That is the whole reason this approach is affordable
where dynamic index reordering is not.

## Review-before-apply rule

Doctrine lands in a file that ships on every API call for every session — including
sessions unrelated to the domain. Draft it to a side file (`SOUL.md.preview`), show the
user the diff, get explicit approval, then copy into place and sync to
`~/.chiper/souls/<soul>.md`. Two minutes of review beats weeks of debuggng odd
behaviour that nobody can attribute to a prompt change.

When applying, keep the two copies byte-identical and confirm with `md5sum`:

```bash
md5sum skills/<pack>/SOUL.md ~/.chiper/souls/<soul>.md   # must match
```

## Maintenance obligation

A keyword table goes stale silently. Every time a new skill domain is added, the table
must gain its keywords — otherwise it slowly becomes a lie that actively misroutes.
Put that reminder inside the same file as the table, not in the operator's head.

## Honest limits

- A weak model can still skip a 9-row table. The fix is a better model tier, not more prose.
- This raises compliance from "sometimes" to "almost always" — it does not make it 100%.
- It makes deviation *visible and attributable* ("you skipped §6.1, why?"), which is the
  practical win: drift becomes arguable instead of invisible.
