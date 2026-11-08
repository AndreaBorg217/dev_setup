---
name: aws
description: Use when configuring AWS CLI profiles, authenticating kubectl against EKS, investigating EC2 instances behind a workload, inspecting S3 storage classes, lifecycle rules, and storage costs, or querying RDS, CloudWatch metrics and log groups, and Cost Explorer cost and usage.
when_to_use: "RDS, aws rds describe-db-clusters, CloudWatch, get-metric-statistics, log groups, aws logs tail, Cost Explorer, cost and usage, aws ce get-cost-and-usage, aws configure, AWS profile, aws sts get-caller-identity, aws eks update-kubeconfig, aws eks list-clusters, aws ec2 describe-instances, --filters, --query, 1Password AWS credentials, op run, stg profile, prod profile, kubectl auth via AWS, EKS auth, node instance type, CPU skew, instance hardware, aws s3api, S3 prefixes, S3 storage classes, S3 lifecycle, Glacier billing, BucketSizeBytes"
---

# AWS CLI

Load this skill once before the first `aws` command in a task. Keep its
instructions active for the rest of that task.

## Establish the profile

Never assume a default profile or region. Confirm which named profile
(`$AWS_PROFILE`) and region (`$AWS_REGION`) the task targets before running
anything, and pass both explicitly on every command rather than relying on
`~/.aws/config` defaults.

## Profile setup

Discover existing profiles with `aws configure list-profiles` before
creating or guessing one. Reuse the verified profile during the task;
recheck after credentials, target environment, or authentication state change.

Credentials come from a password manager. Never print or echo a raw key value - inject
via `op run` so the value only ever lives inside the subprocess environment:

```bash
AWS_ACCESS_KEY_ID='op://<vault>/<item>/username' \
AWS_SECRET_ACCESS_KEY='op://<vault>/<item>/credential' \
op run -- bash -c 'aws configure set aws_access_key_id "$AWS_ACCESS_KEY_ID" --profile $AWS_PROFILE \
  && aws configure set aws_secret_access_key "$AWS_SECRET_ACCESS_KEY" --profile $AWS_PROFILE'

aws configure set region "$AWS_REGION" --profile $AWS_PROFILE
aws configure set output json --profile $AWS_PROFILE
```

`bash -c` here is deliberate: two `aws configure set` calls need to share the
same resolved env vars from one `op run` invocation. For a single command, use
`op run -- <command>` directly instead (see the `1password-cli` skill).

Verify with `aws sts get-caller-identity --profile "$AWS_PROFILE" --region
"$AWS_REGION"` and compare `Account` and `Arn` with the intended identity.
Different environments may use different accounts; profiles within the same
account can still have different permissions.

## EKS auth and EC2 investigation

Read [references/eks.md](references/eks.md) before running `aws eks`
commands - it covers cluster discovery and exactly how `update-kubeconfig`
hands kubectl its auth. Switching contexts (see the `kubectl` skill) does not
authenticate them - `update-kubeconfig` is what actually does.

Read [references/ec2.md](references/ec2.md) before running
`aws ec2 describe-instances` - it covers scoping the call with `--filters`
and projecting fields with `--query` instead of dumping the full instance
list, plus the pattern for resolving a pod's node to EC2 instance detail.

## S3 storage and lifecycle investigation

Read [references/s3.md](references/s3.md) when checking S3 prefixes, object
storage classes, lifecycle rules, CloudWatch storage totals, or Glacier
minimum-duration charges. It distinguishes samples from complete listings
and delayed bucket metrics from current object-level evidence.

## RDS, CloudWatch and Cost Explorer discovery

Read-only shapes; pass `--profile "$AWS_PROFILE" --region "$AWS_REGION"` on each.

```bash
# RDS: clusters, then their member instances
aws rds describe-db-clusters \
  --query 'DBClusters[].{Id:DBClusterIdentifier,Engine:Engine,Version:EngineVersion,Status:Status}'
aws rds describe-db-instances --filters Name=db-cluster-id,Values=<cluster-id> \
  --query 'DBInstances[].{Id:DBInstanceIdentifier,Class:DBInstanceClass,Status:DBInstanceStatus}'

# CloudWatch Logs: find groups, then read a bounded window
aws logs describe-log-groups --log-group-name-prefix <prefix> \
  --query 'logGroups[].{Name:logGroupName,Days:retentionInDays,Bytes:storedBytes}'
aws logs tail <log-group> --since 1h --filter-pattern '<pattern>'
aws logs filter-log-events --log-group-name <log-group> \
  --start-time <epoch-ms> --end-time <epoch-ms> --filter-pattern '<pattern>'

# CloudWatch metrics (any namespace; see references/s3.md for the S3 case)
aws cloudwatch get-metric-statistics --namespace <namespace> --metric-name <metric> \
  --dimensions Name=<name>,Value=<value> \
  --start-time <iso> --end-time <iso> --period 300 --statistics Average

# Cost Explorer: --region us-east-1
aws ce get-cost-and-usage --time-period Start=<yyyy-mm-dd>,End=<yyyy-mm-dd> \
  --granularity MONTHLY --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

- RDS `describe-db-instances` also returns Neptune and DocumentDB instances;
  `--filters` on `engine` narrows them.
- `logs tail` takes `--since` as `5m`, `2h`, `1d` or an ISO timestamp (default
  10 minutes) and exits when drained unless `--follow` is set, so omit
  `--follow`. `filter-log-events` times are epoch milliseconds; always set
  `--start-time`, and prefer `--max-items` to bound output.
- `get-metric-statistics` `--end-time` is exclusive and `--period` must be a
  multiple of 60 (300 for starts 15 to 63 days ago, 3600 beyond 63 days), or
  no datapoints return. Dimensions must match the published set exactly.
- Cost Explorer has a single endpoint (`ce.us-east-1.amazonaws.com`), so use
  `--region us-east-1`. Each API request costs about $0.01 (per source for
  custom billing views), pagination included: keep queries few and coarse.
  `End` is exclusive; `HOURLY` granularity must be enabled separately and
  covers 14 days.

## Keep it generic

Do not write real vault/item IDs, account IDs, cluster names, instance IDs, bucket names, or object keys
into this skill or its reference files. Use placeholders (`$AWS_PROFILE`,
`$AWS_REGION`, `<vault>/<item>`) in any example added here.
