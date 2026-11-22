# Kustomize reference

Generic patterns for editing and verifying overlays. Substitute the real
overlay path (`$OVERLAY`), base path (`$BASE`) and object names.

`yq` is not assumed to be installed. The examples use Python with PyYAML to
pick objects out of a render:

```bash
select_obj() {  # usage: select_obj KIND NAME FILE
  python3 -c 'import sys,yaml; k,n,f=sys.argv[1:4]; print(yaml.safe_dump_all([d for d in yaml.safe_load_all(open(f)) if d and d.get("kind")==k and d["metadata"]["name"]==n]))' "$1" "$2" "$3"
}
```

## Read the overlay before editing

```bash
cat "$OVERLAY/kustomization.yaml"
grep -rn -A4 -E '^\s*-?\s*(path|target):' "$OVERLAY/kustomization.yaml"
```

Find every patch that already targets the object you are changing, in this
overlay and in its bases. Two patches on one field apply in list order and
the later one wins silently.

## Patch style

Avoid JSON patches (`op: add`/`replace`/`remove` with a `path`). Write the
change as a strategic merge patch: a partial manifest that names the object
and holds only the fields that change, in their normal YAML shape.

```yaml
# $OVERLAY/patches/resources.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: $NAME
spec:
  template:
    spec:
      containers:
        - name: $CONTAINER
          resources:
            requests:
              cpu: "2"
              memory: 4Gi
            limits:
              memory: 4Gi
```

```yaml
# $OVERLAY/kustomization.yaml
patches:
  - path: patches/resources.yaml
```

Strategic merge matches list items by their merge key (`name` for
containers, volumes and env). A custom resource has no merge keys, so a
merge patch on one of its lists replaces the whole list. In that case:

1. Stop and say so before writing anything.
2. Offer the options:
   1. A strategic merge patch that repeats the full list.
   2. Moving the value into the base, if every overlay shares it.
   3. A JSON patch.
3. Let the user choose.

When the overlay already patches the object with a JSON patch, ask before
converting it. Do not mix both styles on one field.

When a JSON patch is the chosen option, write one op per object carrying the
complete value (for example `resources` with `requests` and `limits`
together). Do not create an empty object and fill it with later ops. `add`
creates or overwrites a key; `replace` fails when the path does not exist.

## Verify a change by rendering it

Render the overlay at the base ref and at the working tree, then diff only
the objects you changed. Reading the patch alone does not show precedence,
list replacement or a typo in a target name.

```bash
SCRATCH=$(cd "$(mktemp -d)" && pwd -P)
git archive "$BASE_REF" | tar -x -C "$SCRATCH"
kustomize build --enable-helm "$SCRATCH/$OVERLAY" > "$SCRATCH/before.yaml"
kustomize build --enable-helm "$OVERLAY" > "$SCRATCH/after.yaml"
diff <(select_obj "$KIND" "$NAME" "$SCRATCH/before.yaml") \
     <(select_obj "$KIND" "$NAME" "$SCRATCH/after.yaml")
```

`--enable-helm` is needed whenever the overlay has `helmCharts`. It pulls the
pinned chart into the overlay's chart home, so run it from a scratch copy if
the working tree must stay clean.

### Overlays with encrypted secrets

A build that needs KSOPS or another exec plugin fails with
`external plugins disabled`. Do not enable plugins to get past it: that
decrypts secrets. Render only the objects you changed with a scratch
kustomization that pulls in the base and your patch.

Kustomize rejects absolute paths and breaks on the macOS `/var` to
`/private/var` symlink, so resolve the scratch directory and use relative
paths:

```bash
SCRATCH=$(cd "$(mktemp -d)" && pwd -P)
rel() { python3 -c 'import os,sys; print(os.path.relpath(sys.argv[1], sys.argv[2]))' "$1" "$SCRATCH"; }
cat > "$SCRATCH/kustomization.yaml" <<EOF
resources:
  - $(rel "$REPO_ROOT/$BASE")
patches:
  - path: $(rel "$REPO_ROOT/$OVERLAY/$PATCH_FILE")
    target:
      kind: $KIND
      name: $NAME
EOF
kustomize build --load-restrictor LoadRestrictionsNone "$SCRATCH" > "$SCRATCH/out.yaml"
select_obj "$KIND" "$NAME" "$SCRATCH/out.yaml"
```

Copy each patch's `target` from the overlay's `kustomization.yaml`, in the
same order. State in the MR that the full build was not run and why.

### Schema and server-side checks

```bash
kubectl --context "$CONTEXT_NAME" apply --dry-run=server -f "$SCRATCH/out.yaml"
```

A server-side dry run validates against the cluster's schemas, CRDs included,
and changes nothing. Run it against staging unless the user names another
context. If the cluster is managed by Argo CD, prefer `argocd app diff` (see
the `argocd` skill), which compares the render with the live state.

## Common mistakes

1. A patch `target` that matches nothing. Kustomize applies it to zero
   objects without an error. Confirm the change in the rendered output.
2. A list in a merge patch on a custom resource. It replaces the whole list.
3. Editing a base when only one overlay should change.
4. `namePrefix`/`nameSuffix` in the overlay. Patch targets use the
   pre-prefix name.
