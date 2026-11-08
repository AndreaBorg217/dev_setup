# EC2 reference

## Never call describe-instances unfiltered

Always scope with `--filters` and project only the needed fields with
`--query`. Don't dump the full instance list on a shared account.

## Pattern: resolve a pod's node to EC2 instance detail

When a workload behaves differently across otherwise-identical pod replicas,
checking whether they landed on different underlying instance hardware is a
useful early step.

1. **Find which node a pod is running on.** `kubectl get pods -n $NAMESPACE -o
   wide` shows the `NODE` column directly - an EC2 private DNS name
   (`ip-<private-ip-with-dashes>.<region>.compute.internal`) that encodes the
   node's private IP. `kubectl get nodes -o wide` cross-checks that name
   against the node's `INTERNAL-IP` column, or gives the full node list when
   several pods need mapping at once.
2. **Resolve the node(s) to EC2 instance detail**, filtered by the private
   IPs collected in step 1:

```bash
aws ec2 describe-instances \
  --profile $AWS_PROFILE \
  --region $AWS_REGION \
  --filters "Name=private-ip-address,Values=$IP_1,$IP_2,$IP_3" \
  --query "Reservations[*].Instances[*].[PrivateIpAddress,InstanceId,InstanceType,CpuOptions.CoreCount,CpuOptions.ThreadsPerCore,Placement.AvailabilityZone]" \
  --output table
```

3. **Compare the projected fields across instances.** `InstanceType` and
   `CpuOptions` differences explain hardware-driven behaviour differences
   between replicas - check these before assuming an application-level cause.

`Name=private-ip-address` is the filter to use when the investigation starts
from pod/node IPs. Other useful filter keys: `instance-id`, `tag:<key>`,
`instance-state-name`. Pick the filter that matches what's already known -
never filter after the fact by piping the full unfiltered result through
`grep`/`jq`.
