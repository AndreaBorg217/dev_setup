# EKS auth reference

## Discover the cluster

If the cluster name isn't already known, list what the profile can see rather
than guessing:

```bash
aws eks list-clusters --profile $AWS_PROFILE --region $AWS_REGION
```

An account can have more than one cluster. If more than one comes back, use
`AskUserQuestion` to confirm which one is meant before wiring it into
kubectl - do not assume a cluster name matches the profile name.

## Wire the cluster into kubectl

```bash
aws eks update-kubeconfig \
  --profile $AWS_PROFILE \
  --region $AWS_REGION \
  --name $CLUSTER_NAME \
  --alias $CONTEXT_NAME
```

- `--name` is the real EKS cluster name from `list-clusters`.
- `--alias` sets the kubectl context name. Without it, the context defaults to
  the long `arn:aws:eks:...` form - always set it so context switching (see
  the `kubectl` skill) can use a short name.
- Repeat once per environment/profile. Each call only adds/updates that one
  context in `~/.kube/config`; it does not touch other contexts already there.

## What this actually authenticates

`update-kubeconfig` does not embed a static token. It writes an `exec`-based
user entry into `~/.kube/config` that shells out to
`aws eks get-token --cluster-name $CLUSTER_NAME --profile $AWS_PROFILE` on
every kubectl call. That means:

- Credentials are short-lived and always freshly signed by that profile's live
  IAM identity - nothing to rotate or expire manually.
- The binding between a kubectl context and an AWS identity is fixed at
  `update-kubeconfig` time. To point a context at a different profile, rerun
  `update-kubeconfig` with the new `--profile` (same `--alias` overwrites the
  existing context's auth) rather than hand-editing `~/.kube/config`.
- Verify the binding worked with `aws sts get-caller-identity --profile
  $AWS_PROFILE` (confirms the AWS side) and `kubectl config get-contexts`
  (confirms the context exists) - a mismatch between the two means the wrong
  profile was passed to `update-kubeconfig`.

Switching the active context (see the `kubectl` skill) only flips which
context is active. It does not create auth - that only happens here.
