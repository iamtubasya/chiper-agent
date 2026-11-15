# OAuth-gated account handoff (headed browser, user solves once)

When the target's signup is OAuth-only (GitHub/GitLab/Bitbucket/Azure "Sign in with X", no
email+password), the researcher cannot mint an account non-interactively. The working pattern is
a headed-browser handoff: automation drives up to the provider consent screen, the human
completes it once, automation captures the session.

## Recipe (verified 2026-10-21, CodeRabbit app.coderabbit.ai)

1. Fresh profile dir per target (`launch_persistent_context`, `headless=False`,
   `bring_to_front()`).
2. Load the app login page, click the provider button (e.g. "GitHub Cloud") via JS `.click()`.
3. Capture the resulting provider URL — it carries the app's `client_id`, `redirect_uri`,
   `scope`, and `state` (record them; they are reportable surface themselves).
4. Poll `pg.url` every ~3s for up to 8 minutes: success = URL leaves the provider domain and the
   app's `/login` path. On detection, `ctx.storage_state(...)` IMMEDIATELY (see crash-safety).
5. Tell the user exactly what to do in the open window (login provider → Authorize) and wait.

## Pitfalls hit live

- **The provider click is flaky** — the same click redirected to the provider on one run and
  silently no-op'd on the next (stayed on `/login`). If the URL has not left the app after ~15s,
  the script should click again (up to 2-3 attempts), and the user can also click manually.
- **Crash-safe the tail.** A `page.evaluate` AFTER an OAuth navigation throws
  "Execution context was destroyed" — if that happens before `storage_state()`, the session is
  never saved and the whole handoff is lost. Wrap every post-loop evaluate in try/except and save
  the state the moment the URL change is detected, not after diagnostics.
- **Background-process output capture may be empty** (prints with `flush=True` still show
  nothing in `process poll`). Do not rely on it for progress — write progress to a state file
  (`oauth-state.json`) and poll that file from a separate terminal call.
- **Verify the session before declaring success:** reload the app root with the saved profile and
  check for authenticated content (dashboard text, not the login page). A profile that only
  accumulated analytics cookies (`_ga`, `visitor_id`) is NOT authenticated — "Last used GitHub"
  text on the login page only proves an attempt, not a completed OAuth.
- If the app adds a second gate after OAuth (password re-auth to unlock E2E keys, e.g. Proton
  Pass), map it and drive it too — the fork/session alone is not always sufficient.

## Generalization

Same pattern works for any OAuth-gated SaaS trial. The state file + poll + immediate-save shape is
the reusable part; the provider URL fields (`client_id`, `redirect_uri`, `state`) are worth
recording even before auth completes, since redirect_uri/state validation is itself testable
surface.
