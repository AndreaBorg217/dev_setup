# Safety

## Secrets

- Do not run any operation that will expose a secret.
- To use secrets, always use a password manager as instructed by the user.
- Do not hardcode secrets in files.
- Before running any operation, pause and consider whether any secrets will be exposed.
- The only acceptable secret outputs are the secret length or the secret masked with `*` or `[REDACTED]`.

## Conclusive Operations

Do not run conclusive operations without my explicit QA and approval. These include:

- Git commits.
- GitLab merge requests.
- Jira tickets.
- Slack messages.
- Any operation that could trigger an email notification.
