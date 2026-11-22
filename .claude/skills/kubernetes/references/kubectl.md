# kubectl CLI reference

Concrete command shapes actually used for pod investigation, kept generic -
substitute the real namespace/pod/container from the current task.

## get - locate the resource

```bash
kubectl get pods -A
kubectl get pods -n $NAMESPACE
```

Start with `-A` when the namespace isn't yet known, narrow to `-n $NAMESPACE`
once it is. Sort by age to spot a recently-restarted or newly-scheduled pod:

```bash
kubectl get pods -n $NAMESPACE --sort-by=.metadata.creationTimestamp
```

## describe - inspect the one resource

```bash
kubectl describe pod $POD -n $NAMESPACE
```

Read the `Events:` section at the bottom first - it's the fastest signal for
scheduling failures, image-pull errors, and OOM kills, before reading the full
spec/status above it.

## logs - read the actual failure

```bash
kubectl logs $POD -n $NAMESPACE -c $CONTAINER --tail=$N
```

Tail sizes commonly used range from a few hundred lines up to several
thousand (`--tail=1000`, `--tail=2000`, `--tail=5000`) depending on how far
back the relevant error is - start smaller and widen only if the failure
isn't in view yet, rather than defaulting straight to the largest tail. Add
`--previous` when the container has already restarted and the failure was in
the prior instance, not the current one. Add `-f` only for a live stream with
a clear stop condition.

## events - chronological view across a namespace

```bash
kubectl get events -n $NAMESPACE --sort-by=.lastTimestamp
```

Useful before a specific pod is even identified - scan for the resource that
generated the most recent warning/error events, then drop into
`describe`/`logs` on that one.

## Supplementary checks

```bash
kubectl top pods -n $NAMESPACE --sort-by=cpu
kubectl top pods -n $NAMESPACE --sort-by=memory
kubectl config current-context
```

Check `current-context` before running anything against a namespace whose
environment matters (e.g. before a prod-only action) - don't assume the
active context matches intent.

## Explicit context and reusable flags

Use `--context` for cross-environment comparisons or concurrent sessions so
commands do not depend on another process switching the active context.
For repeated commands in bash or zsh, use an array:

```bash
KUBE_FLAGS=(--context "$CONTEXT_NAME" --namespace "$NAMESPACE")
kubectl "${KUBE_FLAGS[@]}" get pods -l "$SELECTOR" -o wide
```

Do not store several flags in a scalar string and rely on unquoted expansion:
zsh normally passes that string as one argument. Use arrays or repeat the
flags explicitly. If namespace is omitted, the selected context's configured
namespace applies, otherwise `default`; inspect it when scope is surprising:

```bash
kubectl --context "$CONTEXT_NAME" config view --minify \
  -o jsonpath='{.contexts[0].context.namespace}{"\n"}'
```

## Compare replicas and deployed images

Use a label selector rather than hardcoded pod suffixes. This compact view
helps spot an old image, an unready replica, or node-specific differences:

```bash
kubectl "${KUBE_FLAGS[@]}" get pods -l "$SELECTOR" \
  -o custom-columns='NAME:.metadata.name,PHASE:.status.phase,READY:.status.containerStatuses[*].ready,RESTARTS:.status.containerStatuses[*].restartCount,NODE:.spec.nodeName,IMAGE:.spec.containers[*].image'

kubectl "${KUBE_FLAGS[@]}" get deployment "$DEPLOYMENT" \
  -o jsonpath='desired={.spec.replicas} ready={.status.readyReplicas} available={.status.availableReplicas}{"\n"}{range .spec.template.spec.containers[*]}{.name}{" image="}{.image}{"\n"}{end}'
```

`Running` alone does not establish readiness. If the question is whether a
config change reached all replicas, compare the deployment pod template's
checksum/config annotations with each pod's annotations and start time.
A template change does not prove every live pod has been replaced.

## Collect a bounded log window once

When comparing replicas or counting several error patterns, save one bounded
snapshot per pod and analyze that file. Repeated log requests can observe
different windows and add unnecessary calls.

```bash
kubectl "${KUBE_FLAGS[@]}" logs "$POD" -c "$CONTAINER" \
  --since="$LOG_WINDOW" --tail="$N" --timestamps > "$LOG_FILE"
```

Use an explicit window such as `30m`. Check the command's exit status before
interpreting an empty file as no errors. Keep stderr visible, and redact
credentials or tokens before sharing excerpts; truncating lines is not
redaction. Only a time window's upper tail is captured when `--tail` binds.

## Compare resource usage with requests and limits

Use per-container metrics when sidecars could explain a pod-level total:

```bash
kubectl "${KUBE_FLAGS[@]}" top pods -l "$SELECTOR" --containers
kubectl "${KUBE_FLAGS[@]}" get pod "$POD" \
  -o jsonpath='{range .spec.containers[*]}{.name}{" requests="}{.resources.requests}{" limits="}{.resources.limits}{"\n"}{end}'
```

`top` reports recent usage, not configured requests/limits or a historical
peak. Match rows by container name. `-A` adds a namespace column to tabular
output; fixed-position parsers must account for that. Preserve Kubernetes
quantity units when comparing values rather than stripping suffixes.

## Inspect configuration wiring without values

When diagnosing a missing setting, first inspect variable names and their
Secret/ConfigMap references rather than dumping the whole deployment or
Secret contents:

```bash
kubectl "${KUBE_FLAGS[@]}" get deployment "$DEPLOYMENT" \
  -o jsonpath='{range .spec.template.spec.containers[*]}{.name}{"\n"}{range .env[*]}{.name}{" secret="}{.valueFrom.secretKeyRef.name}{" configmap="}{.valueFrom.configMapKeyRef.name}{"\n"}{end}{range .envFrom[*]}{"envFrom secret="}{.secretRef.name}{" configmap="}{.configMapRef.name}{"\n"}{end}{end}'

kubectl "${KUBE_FLAGS[@]}" get secret "$SECRET_NAME" \
  -o go-template='{{range $k,$v := .data}}{{$k}}{{"\n"}}{{end}}'
```

A reference existing is not proof the application loaded it. Inspect only the
specific non-secret runtime setting when that next step is needed.
