# Helm reference

Reading charts: which version an overlay pins, which values it accepts, and
how a value ends up in a manifest. Substitute `$CHART`, `$REPO_URL`,
`$VERSION` and `$RELEASE` from the overlay. Set `SCRATCH=$(cd "$(mktemp -d)" && pwd -P)`
first.

## Find the pinned chart

For Kustomize-managed charts the pin is in the overlay:

```bash
grep -n -A10 '^helmCharts:' "$OVERLAY/kustomization.yaml"
```

Read `name`, `repo`, `version`, `releaseName`, `valuesFile` and `valuesInline`
for each entry.

For an Argo CD Helm source, read `spec.source.chart`, `repoURL` and
`targetRevision` from the Application (see the `argocd` skill). Always use
the pinned version; values change between chart versions.

## List the values a chart accepts

```bash
helm repo add "$REPO_NAME" "$REPO_URL"   # once; skip for oci:// charts
helm show values "$REPO_NAME/$CHART" --version "$VERSION" > "$SCRATCH/values.yaml"
helm show chart  "$REPO_NAME/$CHART" --version "$VERSION"
helm show readme "$REPO_NAME/$CHART" --version "$VERSION"
helm search repo "$REPO_NAME/$CHART" --versions | head
```

OCI charts take the full reference: `helm show values oci://$REGISTRY/$CHART --version "$VERSION"`.

`values.yaml` lists defaults and usually their comments. When the chart ships
`values.schema.json`, it is the authoritative list of keys and types:

```bash
helm pull "$REPO_NAME/$CHART" --version "$VERSION" --untar --untardir "$SCRATCH"
python3 -c 'import json,sys; print(sorted(json.load(open(sys.argv[1]))["properties"]))' "$SCRATCH/$CHART/values.schema.json"
```

Query a nested default instead of reading the whole file:

```bash
python3 -c 'import sys,yaml; v=yaml.safe_load(open(sys.argv[1])); print(yaml.safe_dump({k: v.get(k) for k in sys.argv[2:]}))' "$SCRATCH/values.yaml" resources persistence ingress
```

## Find how a value is used

A key in `values.yaml` does not show where it lands. Search the templates:

```bash
grep -rn "\.Values\.$KEY" "$SCRATCH/$CHART/templates"
grep -rn 'include "' "$SCRATCH/$CHART/templates/_helpers.tpl" | head
```

Check subcharts in `$SCRATCH/$CHART/charts/` and the dependency list in
`Chart.yaml`. Subchart values sit under the subchart's name in the parent's
values.

## Render with the overlay's values

```bash
helm template "$RELEASE" "$REPO_NAME/$CHART" --version "$VERSION" \
  --namespace "$NAMESPACE" -f "$OVERLAY/values.yaml" > "$SCRATCH/render.yaml"
select_obj "$KIND" "$NAME" "$SCRATCH/render.yaml"   # helper in kustomize.md
```

Add `--show-only templates/$FILE.yaml` to render one template. `helm template`
does not contact the cluster, so `lookup` calls return empty and
`.Capabilities` uses defaults; pass `--api-versions` or `--kube-version` when
a template branches on them.

To check a values change, render before and after and diff only the objects
that change, as in the Kustomize reference.

## Rules

1. Never pass secret values with `--set` on the command line. Use a values
   file that is SOPS-managed, or leave the secret to the deployed overlay.
2. Pull and untar charts into a scratch directory, not into the repository.
3. `helm install`, `upgrade`, `uninstall` and `rollback` change a cluster.
   They need explicit user approval, and GitOps-managed releases change
   through Git instead.
