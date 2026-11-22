---
name: kubernetes
description: Use when investigating live Kubernetes workloads with kubectl, editing or verifying Kustomize overlays and patches, or reading Helm charts and their values.
when_to_use: "kubectl get, kubectl describe, kubectl logs, kubectl top, kubectl config current-context, kubectl config use-context, pod CrashLoopBackOff, pod Pending, pod not ready, container restart, --sort-by, --tail, --previous, dry-run manifest, kustomize build, kustomization.yaml, overlay, patches, strategic merge patch, JSON patch, op: add, helmCharts, valuesFile, valuesInline, resources requests limits, helm show values, helm template, helm pull, chart version, values.schema.json"
---

# Kubernetes

Load this skill once before the first `kubectl`, `kustomize` or `helm` command
in a task, or before editing a Kustomize overlay. Keep its instructions active
for the rest of that task.

## Pick the reference

| Task | Read |
|---|---|
| Inspect what is running: pods, events, logs, usage, config wiring | [references/kubectl.md](references/kubectl.md) |
| Edit an overlay or patch, or verify what an overlay renders | [references/kustomize.md](references/kustomize.md) |
| Find a chart's version, its available values, or how a value is used | [references/helm.md](references/helm.md) |

## Auth is not this skill's concern

A context's authentication is wired up at `aws eks update-kubeconfig` time -
read [the `aws` skill's EKS reference](../aws/references/eks.md) for that.

## Establish the context

Confirm the target context before any cluster command, especially before a
prod investigation. Never assume the current context matches the environment
being investigated:

```bash
kubectl config current-context
kubectl config get-contexts
```

Prefer an explicit `--context "$CONTEXT_NAME"` on each cluster command over
`kubectl config use-context`, so concurrent sessions do not change each
other's target. Server-side checks (`--dry-run=server`) go to staging unless
the user names another context.

## Rules that apply to every task

1. Avoid JSON patches in Kustomize overlays. Use a strategic merge patch, or
   stop and say why one cannot express the change. Details in
   [references/kustomize.md](references/kustomize.md).
2. Verify an overlay change by rendering it and comparing it with the render
   of the base ref, never by reading the patch alone.
3. Never decrypt secrets to render an overlay. Do not enable KSOPS or exec
   plugins for a verification build.
4. Read a chart's values from the exact chart version the overlay pins, not
   from the chart's latest release.

## Keep it generic

Do not write real namespace names, pod-name prefixes, cluster names, chart
repository hosts or internal service names into this skill or its references.
Use placeholders (`$NAMESPACE`, `$POD`, `$CONTAINER`, `$OVERLAY`, `$CHART`).
