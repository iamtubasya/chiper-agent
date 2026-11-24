# Hunt hypothesis — T1003.001 LSASS access via COMSVCS

**Hunt ID:** `t1003-001-lsass-comsvcs` · **ATT&CK:** T1003.001 · **Status:** active
**Owner:** chiper-cyber · **Opened:** 2026-11-24

## Hypothesis

> An adversary with only user-level access will dump LSASS memory using the
> living-off-the-land route `rundll32.exe comsvcs.dll MiniDump` instead of a
> renamed offensive tool, so it will not match any "mimikatz" filename rule.

If true, we should see `rundll32` command lines containing `comsvcs.dll` together
with an `lsass` process handle — and almost no hits for the same activity under a
tool-name based rule.

## Data required

| Source | Field | Notes |
|---|---|---|
| Sysmon | ProcessCreate (1) | CommandLine, ParentImage |
| Sysmon | ProcessAccess (10) | TargetImage ends with lsass.exe |
| EDR telemetry | module load | comsvcs.dll from rundll32 |
| Windows Security | 4688 (if enabled) | command-line auditing must be on |

## Detection plan

1. Sigma: `sigma/rules/windows/lsass_mem_access.yml` + `rules/comsvcs-minidump.yml`.
2. Splunk SPL:
   ```
   index=sysmon EventCode=1 CommandLine="*comsvcs.dll*" | stats count by user, host, CommandLine
   ```
3. Correlate with EventCode=10 on `lsass.exe` within 60 s.

## Triage checklist

- [ ] Is the parent process expected (edr/IR tooling)?
- [ ] Does the account normally access LSASS (helpdesk, EDR service)?
- [ ] Is there a matching `created time` for a suspicious dump file (`*.dmp`)?
- [ ] Was the binary signed and from System32?

## False positives to expect

- Endpoint agents sampling process memory for crash reporting.
- Forensic acquisitions during an authorised IR engagement.

## Escalation

Confirmed hit → capture the command line, parent chain, and file creation events,
then hand to `chiper-detection-engineering` for rule promotion from `rules/` to
`rules/credential_access/`.
