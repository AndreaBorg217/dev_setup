# Safety

## Secrets

- Do not run any operation that will expose a secret.
- To use secrets, always use a password manager as instructed by the user.
- Do not hardcode secrets in files.
- Before running any operation, pause and consider whether any secrets will be exposed.
- The only acceptable secret outputs are the secret length or the secret masked with `*` or `[REDACTED]`.
- Treat password manager values, credential files, decrypted SOPS/KSOPS content, environment dumps, private keys, kubeconfigs, Terraform state, and other plaintext secret stores as secrets. Do not print, paste, copy, summarize, or echo them into the conversation.
- Never print secrets with `echo`, `printf`, `cat`, `env`, `printenv`, `set`, `op read`, `bw get`, `bws secret get`, or `sops -d`.
- Use `op run` for 1Password-backed subprocesses and keep output masking enabled. Never use `op run --no-masking` or `OP_RUN_NO_MASKING=true`.
- Use `bws run` only for trusted subprocesses that do not print their environment or secret variables.
- Treat SOPS/KSOPS files as secrets even when they are encrypted in git. Never decrypt-and-print; only decrypt-and-pipe directly into a consuming process such as `kubectl apply -f -` or `kubectl diff -f -`.
- Use `sops exec-env` or `sops exec-file` for subprocesses that need decrypted values. If decrypting to a temp file is unavoidable, use `TMPFILE=$(mktemp /tmp/sops_XXXXXX)`, install `trap 'rm -f "$TMPFILE"' EXIT INT TERM` immediately, and redirect decrypt output to `"$TMPFILE"` only.
- Never read, cat, echo, copy, paste, or summarize decrypted temp-file values. If inspection is needed, show key names only, for example `grep -E '^\s+[A-Za-z0-9_.-]+:' "$TMPFILE" | sed 's/:.*/:/'`.
- For SOPS edits, decrypt to `TMPFILE`, edit the temp file only as a handoff artifact, encrypt to `OUTFILE=$(mktemp /tmp/sops_out_XXXXXX)`, then atomically `mv "$OUTFILE" "$TARGET"`.
- When encrypting a temp file back to a target, always use `sops encrypt --filename-override "$TARGET" --input-type yaml --output-type yaml "$TMPFILE" > "$OUTFILE"` so `.sops.yaml` rules match the real path instead of `/tmp`.
- Before encrypting, check `grep -q '^sops:' "$TARGET"` when the target exists to avoid double-encrypting an already encrypted file.
- After successful SOPS work, explicitly `rm -f "$TMPFILE" "$OUTFILE"` and clear the trap with `trap - EXIT INT TERM`.
- Files under `~/.aws`, `~/.ssh`, `~/.kube`, `~/.config/gcloud`, `.netrc`, `.npmrc`, `*.pem`, `*.key`, `terraform.tfstate`, decrypted temp files, password-manager exports, Claude transcripts, and other plaintext secret stores are off-limits for direct reads. Use existence/count checks only, such as `stat`, `wc -l`, or `grep -c KEYNAME`.
- Kubernetes Secret manifests must be SOPS-encrypted before being written to tracked paths.

## Conclusive Operations

Do not run conclusive operations without my explicit QA and approval. These include:

- Git commits and pushes.
- Merge/pull requests (GitLab or GitHub).
- Jira tickets.
- Slack messages.
- Notion writes (see interaction.md for scope).
- Any operation that could trigger an email notification.
