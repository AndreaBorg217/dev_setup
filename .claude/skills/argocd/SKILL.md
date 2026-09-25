---
name: argocd
description: Use when accessing Argo CD through the argocd CLI — finding the server, using SSO, inspecting deployed applications/resources/manifests/logs/history, diffing, syncing, rolling back, or patching live resources.
when_to_use: "argocd CLI, argocd context, argocd login, --sso, --grpc-web, account get-user-info, app list, app get, --refresh, --hard-refresh, --show-operation, app history, app resources, --output tree=detailed, app manifests, --source git, --source live, app logs, --filter, app diff, patch-resource, --prune, rollback, sync, GROUP:KIND:NAME, --force, --replace, --assumeYes, ARGOCD_SERVER, GitOps reconciliation"
---

# Argo CD CLI

Load this skill once before the first `argocd` command in a task. Keep its
instructions active for the rest of that task.

## Establish the target and identity

Never infer the Argo CD server, context, application, project, cluster, or
revision from the current repository or Kubernetes context.

1. Run `argocd context` to identify saved server hosts, contexts, and the active
   context. Use the intended saved server as `$ARGOCD_SERVER`; do not ask the
   user for a host that the CLI already reports.
2. Run `argocd account get-user-info -o json` with a narrow `jq` projection to
   verify the active identity without printing groups, tokens, or configuration.
3. If no saved context identifies the intended server, or the intended
   application remains ambiguous, ask the user rather than guessing.

Do not read or print the Argo CD config file. It can contain authentication
material.

## Authentication

The established interactive login method is browser SSO:

```bash
argocd login "$ARGOCD_SERVER" --sso --grpc-web
```

Use it only when the current session is absent or expired and Argo CD access is
part of the user's request. Tell the user that browser completion is required,
wait for that attempt to finish, then verify with `account get-user-info`. Do
not start concurrent login attempts.

Never ask for or place a password, auth token, cookie, or client secret on the
command line. Do not add `--insecure`, `--plaintext`, or `--core` to work around
an authentication failure. Read
[references/argocd-cli.md](references/argocd-cli.md) for SSO nonce recovery.

## Inspect applications

Prefer structured output and project only the fields required for the question.
Do not paste full application JSON, rendered manifests, or a fleet-wide list
into the conversation.

- Use `argocd app list -o json` only for discovery; filter by project, cluster,
  selector, repository, path, or a bounded `jq` projection.
- Use `argocd app get "$APP" -o json` for saved status.
- Add `--refresh` when current controller state is required. It requests a
  status refresh; do not add it to unrelated metadata questions.
- Use `--show-operation` only when investigating an active or failed operation.
- Use `argocd app history "$APP"` to identify deployment history IDs and
  revisions before a rollback or when reconstructing what was deployed.
- Do not use `--hard-refresh` without a specific reason to invalidate the
  target-manifest cache.
- Use `argocd app get "$APP" -o tree` or `argocd app resources "$APP"
  --output tree=detailed` to inspect the resources under an application before
  dropping down to Kubernetes commands.
- Distinguish desired and deployed manifests: `app manifests --source git`
  renders the desired source; `--source live` reads deployed resources.

For logs, prefer `argocd app logs` over locating pods with `kubectl`. Start with
a bounded tail and time window. Use `-c` to select a container; `--filter`
matches log text and is not a container selector. Use `-f` only when the user
asked for a live stream. If logs are empty, inspect the resource tree first.

Read [references/argocd-cli.md](references/argocd-cli.md) for bounded commands,
field projections, and diff exit-code handling.

## Mutations and approval

Skill invocation and read-only inspection do not authorize a sync, rollback,
`patch-resource`, or any other Argo CD mutation. Present the exact context,
application, current and target revisions, resource scope, expected change, and
whether pruning is involved; obtain explicit user approval immediately before
executing it.

- Run and interpret `argocd app diff` before proposing a sync.
- Prefer one exact application and, when requested, exact
  `GROUP:KIND:NAME` resources.
- `--prune` authorizes deletion. Add it only when deletion was explicitly
  approved and the diff identifies the resources to remove.
- `app patch-resource` changes the live resource outside Git. Show the exact
  resource and patch, explain that GitOps reconciliation may revert it, and do
  not use `--all`. Never put secret values in the patch.
- Before rollback, show deployment history and require an explicit history ID;
  never rely on the CLI's implicit “previous” entry. Rollback is unavailable
  while automated sync is enabled, and it does not replace correcting Git.
- Do not use `--force`, `--replace`, `--assumeYes`, project/selector bulk sync,
  or wildcard/negated resource filters unless the user explicitly approved that
  mechanism and resolved target set.
- After an approved mutation, refresh and report the resulting sync, health,
  revision, and operation state with a bounded projection.

## Keep it generic

Do not write internal hosts, application names, project names, cluster names,
usernames, repository URLs, or credentials into this skill. Use placeholders
such as `$ARGOCD_SERVER`, `$APP`, and `argocd.example.com` in examples.
