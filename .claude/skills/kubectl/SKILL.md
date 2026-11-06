---
name: kubectl
description: Use when investigating pods, deployments, or services in Kubernetes - the get -> describe -> logs workflow and context switching.
when_to_use: "kubectl get, kubectl describe, kubectl logs, kubectl top, kubectl config current-context, kubectl config use-context, pod CrashLoopBackOff, pod Pending, pod not ready, container restart, --sort-by, --tail, --previous, dry-run manifest"
---

# kubectl

Load this skill once before the first `kubectl` command in a task. Keep its
instructions active for the rest of that task.

## Auth is not this skill's concern

A context's authentication is wired up at `aws eks update-kubeconfig` time -
read [the `aws` skill's EKS reference](../aws/references/eks.md) for that.
This skill only covers switching between already-configured contexts and
investigating what's running.

## Establish the context

Confirm the active context before running anything, especially before a prod
investigation - never assume the current context matches the environment
being investigated:

```bash
kubectl config current-context
```

Switch with:

```bash
kubectl config get-contexts
kubectl config use-context $CONTEXT_NAME
```

Re-check `current-context` after switching, before running the command that
actually matters.

For investigations across environments or concurrent sessions, prefer an
explicit `--context "$CONTEXT_NAME"` on each cluster command. This avoids
changing the shared current context. See the reference for shell arrays
when reusing context and namespace flags.

## The get -> describe -> logs workflow

This is the standard investigation order, narrowing scope at each step:

1. **`get`** - find the resource. Start broad (`kubectl get pods -A` or
   `-n $NAMESPACE`) to locate the pod, then narrow to the one resource once
   identified.
2. **`describe`** - once the pod is known, `kubectl describe pod $POD -n
   $NAMESPACE` for scheduling, restarts, and event history on that one
   resource (`Events:` at the bottom is usually the fastest signal for
   `Pending`/`CrashLoopBackOff`/image-pull failures).
3. **`logs`** - once `describe` points at the failing container,
   `kubectl logs $POD -n $NAMESPACE -c $CONTAINER --tail=$N` for the actual
   error. Add `--previous` if the current container already restarted and the
   failure was in the prior instance. Add `-f` only for a live, ongoing
   stream.

A companion, not a replacement step: `kubectl get events -n $NAMESPACE
--sort-by=.lastTimestamp` for a chronological view across a whole namespace
when the failing resource itself isn't identified yet.

Read [references/kubectl-cli.md](references/kubectl-cli.md) for the concrete
command shapes and flag combinations at each step, plus replica/image
comparison, bounded log collection, resource requests versus usage, and
configuration-reference inspection without dumping secret values.

## Keep it generic

Do not write real namespace names, pod-name prefixes, cluster names, or
internal service names into this skill or its reference file. Use
placeholders (`$NAMESPACE`, `$POD`, `$CONTAINER`) in any example added here.
