---
name: sops
description: Use when encrypting, editing, rotating or applying SOPS-encrypted files (Kubernetes Secrets, KSOPS) with AWS KMS - without ever exposing decrypted values.
when_to_use: "sops, sops exec-env, sops exec-file, sops encrypt, sops decrypt, sops rotate, sops updatekeys, --filename-override, .sops.yaml, *.enc.yaml, KSOPS, kustomize build, AWS_PROFILE, KMS decrypt, Failed to get the data key, TMPFILE, trap, Kubernetes Secret manifest"
---

# SOPS

Load this skill once before the first `sops` command in a task. Keep its
instructions active for the rest of that task. The binding rules are in
`rules/safety.md` (Secrets section); this skill adds the command shapes.
Never decrypt-and-print: decrypted content goes only into a consuming
process, or a `mktemp` file with an immediate cleanup trap.

## AWS profile

KMS decrypt and encrypt need the right AWS profile. Set it explicitly on
every `sops` command; never rely on a default. Pick the profile whose
`aws sts get-caller-identity --profile "$AWS_PROFILE"` Account matches the
KMS key ARN in `.sops.yaml`. A wrong or missing profile fails with "Failed to
get the data key". See the `aws` skill for profiles and the `1password-cli`
skill for obtaining credentials.

```bash
AWS_PROFILE="$AWS_PROFILE" AWS_REGION="$AWS_REGION" sops ...
```

`sops encrypt` also accepts `--aws-profile`; decrypt, edit and rotate use
`AWS_PROFILE`.

## Use decrypted values

Pipe straight into the consumer:

```bash
AWS_PROFILE="$AWS_PROFILE" sops decrypt "$TARGET" | kubectl apply -f -
```

`kubectl diff -f -` works the same. Or run a process that receives the
values:

```bash
AWS_PROFILE="$AWS_PROFILE" sops exec-env "$TARGET" './consumer.sh'
AWS_PROFILE="$AWS_PROFILE" sops exec-file "$TARGET" './consumer.sh {}'
```

The consumer must not print: a consumer containing env, set, export,
declare, echo, printf, cat, less, more, head, tail, tee or pbcopy is denied.
Put the logic in a script file.

## Encrypt, edit, rotate

```bash
TMPFILE=$(mktemp /tmp/sops_XXXXXX)
trap 'rm -f "$TMPFILE"' EXIT INT TERM
AWS_PROFILE="$AWS_PROFILE" sops decrypt "$TARGET" > "$TMPFILE"
# edit "$TMPFILE" as a handoff artefact only; never read or print it
OUTFILE=$(mktemp /tmp/sops_out_XXXXXX)
AWS_PROFILE="$AWS_PROFILE" sops encrypt --filename-override "$TARGET" \
  --input-type yaml --output-type yaml "$TMPFILE" > "$OUTFILE"
mv "$OUTFILE" "$TARGET"
rm -f "$TMPFILE" "$OUTFILE"; trap - EXIT INT TERM
```

- `--filename-override` makes `.sops.yaml` rules match the real path, not `/tmp`.
- When the target already exists, `grep -q '^sops:' "$TARGET"` tells you it
  is already encrypted; do not encrypt an encrypted file again. For a new
  file, encrypt the plaintext temp file the same way.
- Edit in place with `sops edit "$TARGET"` only when the editor is
  non-interactive for you; otherwise use the temp-file flow.
- Rotate the data key: `sops rotate --in-place "$TARGET"`. Change recipients
  with `sops updatekeys --yes "$TARGET"` after editing `.sops.yaml`.
- Inspect key names only:
  `grep -E '^\s+[A-Za-z0-9_.-]+:' "$TMPFILE" | sed 's/:.*/:/'`.
- Kubernetes Secret manifests must be SOPS-encrypted before being written to
  tracked paths.

## KSOPS and kustomize

`scripts/block-secret-exposure.py` denies any command containing the word
`ksops`, and any `kustomize build`, `kubectl kustomize` or `kubectl apply -k`
whose target uses a KSOPS generator, unless the output is piped directly into
`kubectl apply -f -` or `kubectl diff -f -`. Do not run these bare, redirect
them to a file, or add `| head`/`| grep`.

```bash
AWS_PROFILE="$AWS_PROFILE" kustomize build <overlay> | kubectl diff -f -
```

Also denied: `Read`/`Grep` on `*.enc.yaml|yml|json` or any file containing
`sops:` or `ENC[AES256_GCM`. Use `stat`, `wc -l` or `grep -c KEY`.

## Keep it generic

Do not write real ARNs, account ids, profile names or secret key names into
this skill. Use placeholders (`$TARGET`, `$AWS_PROFILE`, `<overlay>`).
