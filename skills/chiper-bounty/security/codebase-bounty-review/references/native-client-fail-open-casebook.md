# Native client / daemon fail-open casebook

Reusable shapes for reviewing an in-scope **client + privileged daemon** (VPN, sync agent, updater,
security tool). Each entry is a code shape, how to find it, how to argue it, and the severity call.
Worked examples are from the nym-vpn-client review (2026-10) — keep them as templates, not as a
checklist to re-report.

---

## Finding A — fail-open client authentication (IPC)

**Shape** — the daemon authenticates connecting local clients by verifying the *client process is
vendor-signed*. A helper decides whether to enforce that:

```rust
fn skip_authentication_checks(cert_serial: &str) -> bool {
    if let Err(err) = own_process.verify_certificate_signature(cert_serial) {
        true          // daemon's OWN signature unverifiable -> skip client verification
    } else { false }
}
// caller
let auth_material = if skip_authentication_checks(..) { None } else { Some(auth_material) };
// downstream
let authorized = if let Some(m) = auth_material { is_authenticated(..).await.is_ok() }
                 else { tracing::debug!("Skipping authentication checks"); true };   // FAIL OPEN
```

**Find it** — grep `skip_auth|skip_authentication|self_is_signed|verify_certificate_signature`
and READ THE FAIL-OPEN BRANCH. The happy path reads fine; the defect is the `else`.

**Second layer to check** — the IPC ACL/DACL. If the pipe grants READ+WRITE to
`WellKnownSid::World` = **Everyone (S-1-1-0)**, the fail-open branch is reachable by any local user
and the ACL gives no defence in depth. Grep `WellKnownSid|AbsoluteSecurityDescriptor|Trustee|0o[0-7]{3}`.

**Argue it with the platform contrast** — Linux (`SO_PEERCRED` → uid + vendor group, else a polkit
prompt) is fail-*closed*. The inconsistency between platforms is the proof it's a bug.

**Severity** — conditional on an unsigned / mis-signed daemon; shipped builds are signed ⇒ LOW/MEDIUM.
State the precondition. Do **not** inflate to "any local user owns the VPN".

---

## Finding B — double fail-open on a privacy-critical config (DNS)

The highest-value shape in a privacy client, because the impact is a **leak**, not a crash.

**Callee is incapable of failing:**

```rust
pub async fn enable_forward(&self, ..) -> Result<(), Error> {
    let (tx, rx) = oneshot::channel();
    if self.tx.send(SetConfig { .., response_tx: tx }).is_ok() {
        rx.await.ok().unwrap_or(Ok(()))     // inner update_config error DISCARDED
    } else {
        Ok(())                              // dead worker -> "success"
    }
}
```

`.ok()` collapses `Result<Result<(),E>, RecvError>` → `Option<Result<(),E>>`; `unwrap_or(Ok(()))`
then discards BOTH a `RecvError` and the inner `Err`. A failed `tx.send` also returns `Ok(())`.
So the function reports success even when the config never applied.

**Caller logs and continues:**

```rust
if let Err(err) = resolver.enable_forward(dns_config).await {
    trace_err_chain!(err, "failed to enable dns forwarding");   // NO return
}
// .. execution continues; system DNS pointed at the resolver below
dns_handler.set(&iface, DnsConfig { addresses: vec![listen_addr.ip()], .. })
    .await.map_err(Error::SetDns)?;      // <- the NEXT step does propagate; this one doesn't
```

**The "live but unconfigured" amplifier** — if the socket is bound at `spawn()` and its address is
returned via `listen_addr()` independently of the config step, the failure leaves the system pointed
at a **live resolver with no forwarding config** → DNS outage, or fallback to a non-tunnelled
resolver = **DNS leak**, with the daemon reporting **Connected** and no error surfaced.

**Find it** — enumerate every swallowed-error site, then diff the branch behaviour:

```bash
rg -n "if let Err\(|inspect_err|trace_err_chain|\.ok\(\)|unwrap_or\(Ok\(\(\)\)\)" <state-machine dir>
```

For each hit record: *does it return / transition state, or only log?* Then state the contrast:

| site | behaviour | verdict |
|---|---|---|
| `connecting_state.rs` | `return ErrorState::enter(..)` | correct |
| `error_state.rs` / `offline_state.rs` | `.inspect_err(..).map_err(Error::SetDns)` | correct |
| `connected_state.rs` | `trace_err_chain!` only, no return | **defect** |

The sibling set is what makes it a *bug* rather than a style choice — cite it. And note when the
callee makes the guard **dead code** (Finding B's callee above) — that is a stronger statement than
"the caller forgot to return".

**Severity** — low/medium: conditional on the config step failing, but the product's own bar is that
a leak must be impossible, and here it is silently possible and undetectable. Say which.

---

## Finding C — runtime toggle that weakens a control

**Shape** — a blocking/safety rule that can be disabled at runtime by configuration or an env var:

```rust
if !env_flag("NYM_FIREWALL_BLOCK_HYPERV") { add_blocking_hyperv_rules(wmi)?; }
```

Pair with the vendor's own in-code admission (`const HYPERV_LEAK_WARNING_MSG: &str =
"Hyper-V (e.g. WSL machines) may leak in blocked states.";`) — the code *documents* the leak class
consistent pattern. Same shape as Finding A: a security control
with an off switch. Low/Informational, but list it beside the fail-open findings — triagers value the
consistent pattern.

---

## Finding D — failure is UNREPRESENTABLE in the signature (unit return)

A distinct shape from B: here the callee does not *discard* an error — its **return type cannot
express one**. Check the *signature*, not just the call site.

```rust
fn apply_desired_state(&mut self, store: &SCDynamicStore,
                       actual_state: &HashMap<ServicePath, Option<DnsSettings>>) {   // -> ()
    for (path, settings) in actual_state {
        _ => {
            if let Err(e) = desired_settings.save(store, path_cf) {
                tracing::error!("Failed changing DNS for {}: {}", path, e);   // logged only
            }
        }
    }
}
```

…called from a `Result`-returning function which then **returns `Ok(())` unconditionally**:

```rust
fn apply_new_config(..) -> Result<()> {
    match &self.dns_settings {
        None => {                                   // the FIRST/normal set on connect
            self.dns_settings = Some(new_settings);
            self.update_and_apply_state(store);     // -> () ; all failures swallowed
        }
        Some(old) => {                              // the RE-apply path
            for p in self.backup.keys() { new_settings.save(store, p)?; }   // <= this one propagates!
        }
    };
    Ok(())
}
```

**Why it is a defect, not a style choice** — the *same function* propagates on one branch
(`save(..)?`) and cannot report on the other. That intra-function asymmetry is the proof; cite both
branches side by side. (Observed: `nym-dns/src/macos.rs` — `apply_desired_state` returns `()`;
`apply_new_config`'s `None` branch returns `Ok(())` while its `Some` branch uses `?`.)

**Also check the sibling `reset()`** — if it *does* accumulate a `first_error` across the same
multi-path loop, the codebase demonstrably knows the pattern and omitted it here. Naming that makes
the report much harder to wave away as "by design".

**Find it** — grep the apply/set steps for unit returns:
`rg -n "fn (apply|set|write|update|configure)[a-z_]*\([^)]*\)\s*\{" <dir>` and read the return type.
`-> ()` on a security-critical apply step is the smell. Cross-check the caller for an unconditional
`Ok(())` after the call.

**Severity** — same as B: the control silently does not take effect, the daemon reports Connected,
and the impact is a leak. Conditional on the save failing, but undetectable when it does.

---

## Finding E — swallowed-error asymmetry: classify the swallowed steps by SECURITY ROLE

The strongest version of B/D, and the one that reads as deliberately wrong to a triager. When a
config step makes several calls, do not ask "are they propagated?" — ask **which** ones are not.

```rust
pub async fn set_dns(&mut self, ..) -> Result<()> {
    if let Err(e) = self.dbus.disable_dot(self.tunnel_index).await {
        trace_err_chain!(e, "Failed to disable DoT");          // SWALLOWED  <- anti-leak
    }
    if let Err(e) = self.dbus
        .set_domains(tunnel_index, &[(".", true)])             // SWALLOWED  <- THE anti-leak rule
        .await
    {
        trace_err_chain!(e, "Failed to set search domains");
    }
    let _ = self.dbus.set_dns(self.tunnel_index, servers.to_vec()).await?;  // PROPAGATED <- benign
    Ok(())
}
```

The pattern to look for: **the calls that PREVENT the leak are swallowed; the harmless one
propagates.** That asymmetry is simultaneously the proof and the impact analysis — you do not have
to argue severity separately, you read it off the diff.

**Know the semantics of the swallowed call before writing it up** — the impact claim depends on it,
and the vendor's reviewers know these APIs better than you:

| platform | call | what losing it means |
|---|---|---|
| systemd-resolved | `SetDomains(link, &[(".", true)])` | `("." , true)` = route **every** domain to this link + **default-route** flag. Without it resolution keeps consulting other (physical) links ⇒ DNS leaves the tunnel |
| systemd-resolved | `SetLinkDNSOverTLS` / `disable_dot` | link left in a resolver configuration the client did not intend |
| macOS SCDynamicStore | `DnsSettings::save(store, path)` | system resolver never re-pointed ⇒ queries still go to the pre-VPN resolver |

**Severity** — this is the highest of the fail-open family: an ordinary error path (D-Bus failure,
permission/policy error, transient bus error) on the *common* desktop configuration produces a real
DNS leak while the UI shows Connected. Call it Medium and say why, rather than hiding behind "the
config step must fail first".

---

## Review order for this target class

1. IPC auth (Finding A) + the ACL layer.
2. Kill-switch / firewall: does the error path land in `Blocked` (fail closed) or continue?
3. Swallowed-error enumeration across the tunnel state machine (Finding B). For every hit record
   *does it return/transition, or only log?* — the sibling set is the proof.
4. **Check the apply/set step SIGNATURES** (Finding D): a unit-returning (`-> ()`) helper on a
   security-critical config path cannot report failure. Cross-check the caller for an unconditional
   `Ok(())` after the call, and read the *other* branches of the same function — an intra-function
   asymmetry (`save(..)?` on one branch, log-only on the other) is the fix-it argument.
5. **Classify the swallowed calls by security role** (Finding E): if the calls that *prevent* the
   leak are swallowed while a benign one propagates, the diff IS the impact analysis. Learn the
   platform semantics of the lost call (`SetDomains((".", true))`, `disable_dot`, `DnsSettings::save`)
   before writing the impact paragraph.
6. Dual-stack default-deny — all three platforms now verified, use as the checklist:
   - Linux: nft table family `inet` (v4+v6) + `Policy::Drop` on in/out/forward.
   - macOS: pf `block drop all` with **no family qualifier** (matches inet+inet6).
   - Windows: match-all (`libwfp NullConditionBuilder`) filters at `FilterBuilder::WeightClass::Max`
     on all four ALE layers — `ALE_AUTH_CONNECT_V4`, `ALE_AUTH_RECV_ACCEPT_V4`, `ALE_AUTH_CONNECT_V6`,
     `ALE_AUTH_RECV_ACCEPT_V6` — in BOTH session and persistent variants
     (`nym-vpn-windows/winfw/src/winfw/rules/persistent/blockall.cpp`). v4-only = IPv6 leak.
7. Store layer: on-disk secret modes (`0600`), parent dir (`0700`), keyring vs plaintext.
8. Config/env toggles that disable a control (Finding C).

Enumerate **every** platform backend of the DNS/config layer — Linux has (at least) `systemd-resolved`
*and* `resolvconf`, and each is a separate fail-open candidate with its own semantics. Do not stop at
the first backend you read.

**Honest negatives are deliverables.** "Kill switch fails closed", "dual-stack covered on Linux and
macOS", "store layer clean" are all worth writing down — they stop the next session re-deriving them.

**"Opaque" is a claim — verify it before you write it down.** Corrected 2026-10: an earlier version
of this casebook used `winfw` as the worked example of an unverifiable FFI gap ("the Rust repo only
binds to it, so Windows can't be checked from source"). **That was wrong**, and it caused a real
retraction. The `winfw` C++ source ships in the *same repository* at `nym-vpn-windows/winfw/`
(`winfw.cpp`, `rules/persistent/blockall.cpp`), and reading it converted "Windows untested" into a
verified **PASS** in a single pass.

So the rule is the inverse of the old advice: **before labelling a native/FFI component untested,
hunt its source.**
- Look for a **sibling top-level directory** — a Rust core commonly sits beside `*-windows/`,
  `*-macos/`, `*-android/` app dirs that hold the platform layer.
- Search for `.cpp`/`.h`/`.vcxproj`/`CMakeLists.txt`; `build.rs` names the library
  (`println!("cargo:rustc-link-lib=…")`) and usually points at its source dir.
- Only if that search comes up **empty** may you record **untested** — and then say *why*
  (e.g. "shipped as a prebuilt binary"), not merely "native".
- When the component is a **fork, name the upstream** — `winfw` is a **Mullvad** WFP fork
  (`mullvadguids.cpp`, `mullvadobjects.cpp`), which moves the prior from "unaudited" to "a widely
  deployed kill switch with its own audit history".

Same discipline for **crate/package names**: never list a "remaining surface" from memory. Enumerate
with `ls -d */` at the workspace root (an invented crate name — `nym-exports` — was listed as
unexamined here and does not exist). Both errors bias toward *understating* coverage, which the next
session then inherits as a false negative.
