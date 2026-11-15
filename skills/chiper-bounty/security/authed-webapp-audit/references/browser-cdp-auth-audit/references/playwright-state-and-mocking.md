# Playwright/CDP runtime state, mocking, and capture

> Clean-room re-expression of technique from ARTEX's `playwright-cli` (AGPL-3.0). Our own wording,
> mapped onto our browser tooling. Load when an authed audit needs a session that survives many
> steps, request interception, or a recorded PoC.

## Why this matters to an audit

Four capabilities turn a browser from "I can see the page" into a real instrument:

1. **State capture/reuse** — log in once, export storage state, reuse it across every later request.
   Without this, long audits drown in re-authentication.
2. **Request mocking/interception** — modify, block, or synthesise responses to test client-side trust
   (UI shows data the server never sent; a "disabled" control is only disabled in JS).
3. **Tracing** — a full timeline (actions, network, console, errors) for a reproduction that reviewers
   can replay.
4. **Video/screenshot capture** — the PoC artefact.

## State (the highest-value habit)

Persist and reuse, per identity:

- **cookies** and **localStorage**/**sessionStorage** (export after login; re-import next run);
- a **named storage-state file per identity** (`state-<role>.json`) so a multi-role test does not
  cross-contaminate;
- note that some apps bind the session to a device/IP — if reuse fails, re-auth rather than fight it.

Export immediately after login, before you have mutated anything: a clean baseline is reusable; a
post-test state is not.

## Mocking / interception

Reason about the **client's trust boundaries**, not just "change a response":

- does the UI gate a control by a role flag returned from the server? Mock it and see whether the
  *server* enforces it — if only the client does, that is a real finding, not a mock artefact.
- does a "read-only" field become editable when its response is altered? Confirm the write path also
  accepts it; otherwise it is cosmetic.
- block a third-party script and confirm whether the app fails closed or open.

Always record the **unmocked** request/response next to the mocked one — the report needs the real
server behaviour, not the fabricated one.

## Tracing and capture for the PoC

- Start a trace at the beginning of the reproduction, stop it at the end — a partial trace is a
  liability.
- Capture the network log alongside UI actions so the reviewer sees cause and effect.
- For video, record one clean continuous take; do not stitch, and do not include unrelated tabs.
- Keep the artefact small and labelled (`poc-<finding>.zip` / `.webm`) and store it under the target's
  evidence directory, not the desktop.

## Discipline

- Authorised targets only; this is a testing instrument, not a scraping tool.
- Never leave a mocked state running for later phases — a stale mock silently invalidates results.
- A video/screenshot is *evidence*, not proof of impact: pair it with the raw request and response.
