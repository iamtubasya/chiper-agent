# Octopus Deploy Server API — recipe bank

For the Bugcrowd `octopus-deploy` program (in scope: **Octopus Server + Octopus Tentacle**, C#/.NET,
self-hosted). Run the product locally and drive it entirely over REST. Verified against Server
**2026.3.15882** (ApiVersion 3.0.0) from `octopusdeploy/octopusdeploy:latest`.

Base: `http://localhost:1322`. Header `X-Octopus-ApiKey: API-...`.

## Auth

- **Create an API key without the UI** (the container's admin bootstrap does not need one):
  `docker exec octo-server ./Octopus.Server admin --instance OctopusServer --username admin --apiKey "API-XXXXXXXX"`
- The key **must start with `API-`**. A key without that prefix is rejected with
  `The API key you provided was not valid and doesn't start with "API-" as expected` even though the CLI
  accepted it — so a "wrong key" error right after creation usually means the prefix, not the value.
- Each `Octopus.Server ...` CLI invocation is a full runtime start: ~1–3 min on a weak box. Run it in
  the background and poll, don't block a foreground call.
- **Cookie/session writes need CSRF.** Read the `Octopus-Csrf-Token_<installationId>` cookie from the
  jar and send it as `X-Octopus-Csrf-Token`. Without it every write is
  `403 ... A required anti-forgery token was not supplied or was invalid` — that is CSRF, not RBAC.
  Log in with `POST /api/users/login {"Username":..,"Password":..}`.
- Unauthenticated surface is tiny: only `/api/authentication` and `/api/serverstatus/health` (plus `/`
  and `/app`). Everything else 401s.

## Object model gotchas

- **Scoped user roles are space-scoped**: `POST /api/{space}/scopeduserroles` with
  `{"TeamId":..,"UserRoleId":..,"Scope":{"SpaceId":"Spaces-1"}}`. The top-level `/api/scopeduserroles`
  is *system* scope and rejects space-level roles with
  "You cannot use a role with Space level permissions at the System level".
- Teams need `ExternalSecurityGroups: []` or creation 400s.
- Spaces need `SpaceManagersTeams` (+ `SpaceManagersTeamMembers`) or creation 400s; mirror an existing
  space's fields.
- `GET /api/userroles/{id}` → `GrantedSpacePermissions` / `GrantedSystemPermissions` is the authoritative
  permission list. Read it to prove a user *lacks* a permission before claiming an escalation.
- `GET /api/variables/variableset-<id>` correctly returns `Value: null` for `IsSensitive` variables —
  check this first so you don't report the intended behaviour.

## Project → process → release → deploy (the shortest path to a task log)

1. `POST /api/{space}/environments {"Name":"test-env"}`
2. `GET /api/{space}/projectgroups` → take `ProjectGroups-1`
3. `POST /api/{space}/projects {"Name":..,"ProjectGroupId":"ProjectGroups-1","LifecycleId":"Lifecycles-1"}`
   (`LifecycleId` is required.)
4. Set variables: `PUT /api/{space}/variables/variableset-<projectId>` with the whole object read back
   from the GET, adding
   `{"Name":"S","Value":"...","Type":"String","Scope":{},"IsSensitive":true}`
5. **Deployment process PUT goes to the COLLECTION url**, not an id:
   `PUT /api/{space}/projects/{id}/deploymentprocesses` (with `Id:"deploymentprocess-<projectId>"`).
6. **Step target roles live in the STEP-level `Properties`**, not the action:
   `step["Properties"]["Octopus.Action.TargetRoles"] = "role-name"` — the action's own
   `Octopus.Action.TargetRoles` is ignored and you get
   "Please select one or more target tags that '<step>' step will apply to."
7. Actions nest under `step["Actions"]`; a step with an empty `Actions` array 400s with
   "The step X does not have any actions."
8. Release: `POST /api/{space}/releases {"ProjectId":..,"ChannelId":"Channels-1","Version":"0.0.1","SelectedPackages":[]}`
   (root-level collection, not under the project).
9. Deploy: `POST /api/{space}/deployments {"ReleaseId":..,"EnvironmentId":..,"ProjectId":..,"SpecificMachineIds":[],"ExcludedMachineIds":[]}`
   → response carries `TaskId`.
10. Poll `GET /api/tasks/{id}` until `State` ∈ {Success, Failed, Canceled}, then read the log:
    `GET /api/tasks/{id}/raw` (plain text) or `GET /api/tasks/{id}/details{?verbose}`.

## Runbooks

- Creating a runbook requires `RunRetentionPolicy`, e.g.
  `{"QuantityToKeep":10,"ShouldKeepForever":false}`, plus `EnvironmentScope`.
- Snapshots are created on the **root** collection: `POST /api/{space}/runbookSnapshots`
  (the runbook-scoped path is GET-only → 405).
- Then **publish** by PUTting the runbook with `PublishedRunbookSnapshotId` set, otherwise the run fails
  with "Runbook has no published snapshot".
- Run: `POST /api/{space}/projects/{id}/runbooks/{runbookId}/run`.

## Registering a Tentacle (gives you a real execution target)

`octopusdeploy/tentacle` image, env-driven:

- worker: `-e TargetWorkerPool="Default Worker Pool"`
- deployment target: `-e TargetEnvironment="test-env" -e TargetRole="mask-role"`
- plus `-e ServerUrl=http://octo-server:8080 -e ServerApiKey="API-..." -e Space=Default -e DISABLE_DIND=Y`
- join the server's compose network and set `--hostname` to a DNS-resolvable name (the registered
  `Uri` is `https://<hostname>:10933/`; if the server can't resolve it the deployment fails with
  "Name or service not known").
- The container **exits 143 when its bundled DinD dies** — `DISABLE_DIND=Y` is mandatory unless you
  actually want container workers. Publish `-p 10933:10933` when you want to fuzz the listener from the
  host.

## Manual interventions

`PUT /api/{space}/interruptions/{id}/responsible {"ResponsibleUserId":"Users-1"}` (PUT, not POST; the
link is `/responsible`, not `/responsibility`), then
`POST /api/{space}/interruptions/{id}/submit {"Result":"Proceed", ...}`. Find it with
`GET /api/{space}/interruptions?regarding=<taskId>`.

## Notes for interpreting results in this product

- The masking defects found live in the shared masking classes shipped by **both** Server
  (`Octopus.Core.dll`, `Octopus.Shared.dll`, `Octopus.Server.dll`) and Tentacle
  (`Octopus.Tentacle.Core.dll`) — see
  `references/self-hosted-appliance-audit-and-secret-masking.md`.
- `POST /api/projects` with an incomplete body returns 400 before the permission check; with a valid
  body it is a clean `403 Missing permission: ProjectCreate`.
- Confirming an interruption leaves the deployment/runbook task running; confirm it to keep the lab tidy.
