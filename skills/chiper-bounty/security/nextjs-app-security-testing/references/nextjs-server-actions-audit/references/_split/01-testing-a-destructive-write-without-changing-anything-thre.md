## Testing a destructive write WITHOUT changing anything — three oracles

Proving an action enforces ownership normally means aiming it at someone else's object — which
mutates state if it fails. Three variants give you the answer with **zero state change**, and the
distinct error strings are the evidence:

1. **Wrong-confirm-name ordering proof (strongest).** Submit the destructive form with a FOREIGN
   `propertyId` *and* a deliberately WRONG `confirmName`. The response tells you where the gate sits:

   ```
   own  object + wrong name  -> "The name you typed does not match this property."   ← control
   foreign object + wrong name -> "Only the property owner can delete a property."   ← authz gate fires FIRST
   ```
   The pair proves the ownership check runs *before* the typed-name check, and nothing is deleted
   either way (the name never matched). Reuse this shape for any action whose later step validates
   an input the attacker controls.
2. **Same-values submit.** For rename / share-percent forms, submit the value the object already
   has (its current name, its current percent). Even if the server wrongly accepts, the visible
   state is identical — so an accepted response here is not a state risk.
3. **Invalid-value-before-validation.** Pass a syntactically invalid value (`percent=abc`) at a
   FOREIGN target. An ownership error = authz first (good). A *validation* error instead means the
   action reached its validator for a non-owned object — that ordering is itself the signal.

Pair these with the UI observation (a view-only share renders **only** the logout form — no save,
delete, share or record buttons), but report the server-side rejection, not the missing button:
"UI hides it" is not enforcement.



- `0:{"a":"$@1","f":"","b":"<buildid>"}` + `1:E{"digest":"..."}` → server error/500.
  Same shape for CSRF-blocked (evil Origin) and cross-tenant replays — by itself not proof
  of which; pair with a legit baseline from the same session.
- `1:{"error":"Only the owner can change these settings."}` → explicit authz message is in
  the `1:` flight segment. Read it; it names the control (owner-only, plan-only, etc).
- `"Server action not found."` on replay with a different cookie → action bound to session.
- Same body + same cookie but `Origin: https://evil.example.com` → 500 == Origin/CSRF
  enforcement active.

**A digest-only `1:E{"digest":"..."}` means YOUR request shape is wrong — it is NOT a
denial.** Verified this session: three different action families (`updateOwnerShare`,
`updateSourceSettings`, `deleteProperty`) each returned a *constant, distinct* digest for
every payload tried. Those constants are the transport/decrypt layer failing, not authz.
If you "prove" a control by collecting such digests you have proven nothing. How to tell
the two apart:

1. **Replay the EXACT captured body** (all `_N_$ACTION_REF_N` / `$ACTION_KEY` hidden
   fields included) with the attacker's cookie — digest → harness; explicit `error`
   string → real server-side check (authoritative).
2. **Do the control test both ways.** Run the same action family from a LEGIT session on a
   resource the account genuinely owns. If the legit one also digests, that family is
   untestable via your harness — say so instead of scoring it as a pass.
3. **Read the resulting state, not the response.** Reload the victim/own view and check
   whether the field actually changed.

**Reachability probe for read-only actions.** A successful write returns an RSC redirect
body (no `error`); a failed one returns `{"error":...}`. Validity probes that always cross
a server-side validator (e.g. `removeShareAction` with a bad `shareId`, `updateSharePercent`
with a wrong MFA/share code) produce a clean `1:{"error":"..."}` — use them as cheap
"does this action reach a real handler" checks, and never as evidence of authorization.

