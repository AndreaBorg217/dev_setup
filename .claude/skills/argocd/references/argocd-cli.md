# Argo CD CLI reference

This reference reflects the local `argocd` workflow while keeping environment
identifiers generic. Substitute targets established from the current task; do
not hardcode examples from earlier sessions.

## Context and SSO

List saved contexts, identify the active one, and obtain the server host from
the CLI's context table:

```bash
argocd context
```

Prefer that saved server over deriving a host from the current repository or
Kubernetes context. If multiple contexts could match, show the names and ask
which one to use. If none identifies the requested environment, ask for the
server; do not read the Argo CD config file to extract it.

Verify that the session is authenticated while omitting groups and issuer data:

```bash
argocd account get-user-info -o json \
  | jq -r '[.loggedIn, (.username // "unknown")] | @tsv'
```

If the intended server is known and the session is absent or expired, use the
interactive SSO flow:

```bash
argocd login "$ARGOCD_SERVER" --sso --grpc-web
```

The CLI normally opens a browser and listens on local port `8085` for the OAuth2
callback. Wait for the browser flow and CLI command to finish. If the callback
port is demonstrably occupied, stop the failed attempt and retry once with an
available local port:

```bash
argocd login "$ARGOCD_SERVER" --sso --grpc-web \
  --sso-port <available-local-port>
```

The SSO nonce is short-lived. On `Unknown state nonce`, let the failed command
finish, rerun it once, and complete the new browser flow promptly. Do not put the
login process in the background, kill it on a timer, or start overlapping
attempts. Do not compensate for authentication failure with `--insecure`,
`--plaintext`, a password, or a token.

## Discover applications

When the application name is unknown, narrow at the server where possible:

```bash
argocd app list --project "$PROJECT" -o json \
  | jq -r '.[:50][] | [
      .metadata.name,
      (.spec.destination.name // .spec.destination.server // "unknown"),
      (.status.sync.status // "Unknown"),
      (.status.health.status // "Unknown")
    ] | @tsv'
```

Other useful server-side filters are `--cluster`, `--selector`, `--repo`,
`--path`, and `--app-namespace`. If more than 50 applications remain, narrow the
query instead of treating the display cap as a complete result.

## Inspect one application

Return a compact status snapshot:

```bash
argocd app get "$APP" --refresh -o json \
  | jq '{
      application: .metadata.name,
      project: .spec.project,
      destination: (.spec.destination.name // .spec.destination.server),
      namespace: .spec.destination.namespace,
      sync: .status.sync.status,
      health: .status.health.status,
      revision: .status.sync.revision,
      images: (.status.summary.images // []),
      operation: (.status.operationState.phase // null),
      message: (.status.operationState.message // null),
      conditions: [(.status.conditions // [])[] | {type, message}]
    }'
```

Use `--show-operation` when operation details are the subject of the
investigation. Use plain `app get` without `--refresh` when cached status is
sufficient. `--hard-refresh` also invalidates the target-manifest cache and is
not the default diagnostic step.

## Resources and deployed manifests

Inspect the application's resource tree before switching to pod-oriented
Kubernetes commands:

```bash
argocd app get "$APP" -o tree
argocd app resources "$APP" --output tree=detailed
```

Use `app resources` for a lighter inventory or `--orphaned` to inspect only
orphaned resources. If the application name may be hidden by RBAC, include the
known `--project` so the server can distinguish not-found from permission
denied.

Manifest source matters. These commands can return large or sensitive resource
documents, so run them only through a bounded source-side processor that selects
the exact kind/name and excludes Secrets; never send their raw output directly
to model context:

```bash
# Desired manifests rendered from Git/source
argocd app manifests "$APP" --source git

# Resources currently deployed in the cluster
argocd app manifests "$APP" --source live
```

Do not call desired Git manifests “deployed”. Use the refreshed application
status, live manifests, resource tree, sync revision, and reported images as
evidence for what is running. Narrow by kind/name before loading any manifest
content and never expose Secret data.

## Application logs

Start with bounded recent logs:

```bash
argocd app logs "$APP" --tail 200 --since-seconds 1800
```

Then narrow when necessary:

```bash
argocd app logs "$APP" -c "$CONTAINER" --tail 200 --since-seconds 1800
argocd app logs "$APP" --kind Deployment --name "$RESOURCE" --tail 200
argocd app logs "$APP" --filter "$TEXT" --tail 200 --since-seconds 1800
argocd app logs "$APP" -c "$CONTAINER" --previous --tail 200
```

`-c`/`--container` selects a container. `--filter` filters log text. Do not use
one in place of the other. Avoid `-f` unless live streaming is explicitly
needed; if used, make the stop condition clear. When `app logs` returns nothing,
inspect `app get -o tree` or `app resources --output tree=detailed` to identify
the actual workload and container before retrying.

## Diff semantics

`argocd app diff "$APP"` compares target and live state. Its default exit codes
are significant:

- `0`: no difference;
- `1`: a difference exists;
- `2`: a general error.

Therefore, exit code `1` is evidence of drift, not a failed CLI call. For
interactive inspection where the shell wrapper would otherwise treat drift as
an error, keep genuine errors non-zero but disable the difference exit code:

```bash
argocd app diff "$APP" --exit-code=false | sed -n '1,240p'
```

If output is truncated, summarize which resources changed and run a narrower
resource-specific inspection instead of paging the entire diff into model
context. Argo CD ignores Kubernetes Secrets in this diff, so a clean result is
not evidence that live and target Secret values are equal.

## Approved sync

Before execution, record the current revision and deployment history, then
restate the active context, application, target revision, and exact scope. A dry
run can validate the operation shape but is not permission for the real sync:

```bash
argocd app sync "$APP" --resource 'GROUP:KIND:NAME' --dry-run
```

After explicit approval, remove `--dry-run`. Add `--prune` only when the user
approved deletion of the unexpected resource identified by the diff:

```bash
argocd app sync "$APP" --resource 'GROUP:KIND:NAME'
argocd app sync "$APP" --resource 'GROUP:KIND:NAME' --prune
```

Avoid broad selectors, projects, wildcards, and negated resource filters unless
their resolved target set was shown and approved. Do not add `--force`,
`--replace`, `--assumeYes`, or `--async` as retry strategies. Do not perform
routine manual sync/prune merely because a generic guide recommends it; first
inspect the application's sync policy and actual drift. This CLI exposes prune
through mutation flags such as `app sync --prune`, not a separate workflow that
bypasses the same approval and deletion checks.

After the operation completes, rerun the compact refreshed `app get` projection
and report observed status. Do not claim success solely because the sync command
was accepted.

## Deployment history and approved rollback

History is read-only. Use the wide output to associate history IDs with deployed
revisions and timestamps; use `id` only when IDs alone are sufficient:

```bash
argocd app history "$APP"
argocd app history "$APP" -o id
```

Do not use a `--max` flag copied from generic guides unless the installed
`argocd app history --help` supports it. The current CLI supports `wide` and
`id` output but not `--max`.

Before rollback:

1. Capture the current refreshed revision, images, sync/health state, and
   operation state.
2. Show the relevant history rows and resolve the exact target history ID and
   revision with the user.
3. Inspect `.spec.syncPolicy.automated`. Argo CD cannot roll back an application
   while automated sync is enabled. Do not disable automated sync implicitly.
4. Explain that rollback deploys a historical state but does not make the
   current Git source agree with it. Establish how Git will be corrected or how
   re-reconciliation will be controlled.
5. Show whether `--prune` is proposed and which resources it could delete, then
   obtain explicit approval.

Always supply the selected ID; omitting it silently chooses the previous
history entry:

```bash
argocd app rollback "$APP" "$HISTORY_ID"
```

Add `--prune` only when the deletion set was explicitly approved. After the
rollback, rerun the compact refreshed application projection and `app history`.
Report the observed revision, health, sync state, and operation result, and do
not claim durable recovery until the Git desired state is reconciled.

## Approved live-resource patch

`patch-resource` is an out-of-band live mutation. It can create GitOps drift and
may be reverted by automated reconciliation. There is no dry-run flag, so show
the complete patch and exact target before requesting approval.

For an explicitly approved merge patch:

```bash
argocd app patch-resource "$APP" \
  --group apps \
  --kind Deployment \
  --namespace "$NAMESPACE" \
  --resource-name "$RESOURCE" \
  --patch '{"spec":{"replicas":0}}' \
  --patch-type application/merge-patch+json
```

Use the patch type that matches the supplied document. Do not use `--all`, do
not include credentials or secret values, and do not improvise a live patch
when the desired change belongs in Git. After an approved patch, inspect the
resource tree and refreshed application state; report whether reconciliation
retained or reverted the change.
