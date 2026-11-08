---
name: 1password-cli
description: Use when injecting secrets via the op CLI - op run, op read, op item get, account pinning, and vault/item addressing, without ever exposing a secret value.
when_to_use: "op run, --env-file, ~/.env.op, blocked constructs, export, printf, op read, op item get, op://, OP_ACCOUNT, --account, vault, item, 1Password CLI, secret injection, --no-masking, op account list"
---

# 1Password CLI

Load this skill once before the first `op` command in a task. Keep its
instructions active for the rest of that task.

This skill covers this user's actual raw-CLI usage patterns: direct `op`
binary invocations, including `op run --env-file="$HOME/.env.op"`. `OP_ACCOUNT`
setup, Python `op_cache.py`/`op_env.py` helpers, and `1PASSWORD_ERROR`
subcodes are out of scope here.

## Never expose a secret value

No secret value may be printed, echoed, or pasted into the conversation or
terminal output. Only length or a masked/`[REDACTED]` form is an acceptable
secret output. Never disable masking (`--no-masking`,
`OP_RUN_NO_MASKING=true`).

## op run - the default injection pattern

Prefer a single direct-binary invocation over wrapping in `bash -c`:

```bash
op run -- <command>
```

Reference secrets as env vars set to their `op://` path, resolved only inside
the subprocess:

```bash
API_TOKEN='op://<vault>/<item>/credential' op run -- curl -H "Authorization: Bearer $API_TOKEN" ...
```

Use `bash -c '...'` only when multiple commands in the same call need to share
the same resolved env vars (see the `aws` skill's profile-setup section for a
real example: two `aws configure set` calls sharing one `op run` injection).

## ~/.env.op

`~/.env.op` holds `NAME=op://...` references for this user's usual
credentials. Use it through `op run`, never by reading it:

```bash
op --account "$OP_ACCOUNT" run --env-file="$HOME/.env.op" -- python3 <script>
```

Check it only with `stat` or `grep -c KEY`. `cat`/`grep` of its content is
denied by the secret-exposure hook (`**/.env.*`).

## Blocked constructs

Denied by settings permissions or `scripts/block-secret-exposure.py`:

- `export`, `declare`, `env`, `printenv`, `echo $VAR`, `printf` with `$`.
- `$(...)` or backticks around `op`/`sops`/`bw` with read, get, secret or `-d`.
- Any `op` command containing the word `read`, including `op read`.
- `--no-masking` and `OP_RUN_NO_MASKING`.

Replacement: put the whole job in one script file and let `op run` inject
the secrets into that process. The script reads them from the environment
(`os.environ["NAME"]`), uses them (for example to fetch a token and call an
API in the same process), and never prints them. Keep masking on. Do not
capture a token in the outer shell; hand state between calls through a
scratchpad file that holds no secret.

## op read

`op read` is blocked by this user's own tooling in some contexts (a
policy hook denies bare `op read` calls). When blocked, use `op run` instead
rather than working around the block - inject via an env var reference as
above, even for a single value.

## op item get - inspect fields without leaking values

To check what fields an item has before referencing them, list labels only,
never values:

```bash
op item get "<item>" --vault "<vault>" --format json | jq -r '.fields[] | select(.value != null) | .label'
```

Never pipe `.value` through to output.

## Account pinning

Always pass `--account "$OP_ACCOUNT"` explicitly on multi-account machines.
Omitting it can silently resolve against the wrong account's vaults.
`--account` is a global flag; list accounts with `op account list`.
`$OP_ACCOUNT` setup is out of scope for this skill.

## Vault/item addressing

Prefer ID-based `op://` references over name-based ones:

```bash
op://<vault-id>/<item-id>/<field>
```

A vault or item name containing a `/` breaks the `op://` path parser (the
slash gets read as a path separator). IDs don't have this problem and are
stable if the item is later renamed.

Rules for any `op://` reference:

- Always three segments: `op://<vault>/<item>/<field>`. A bare item id fails
  ("too few '/'").
- Quote the reference in the shell (`'op://...'`).
- Names with parentheses or spaces fail to parse (`invalid character '('`).
  Use the ids instead.
- "More than one item matches" means duplicate item names. Use the item id,
  or narrow with `op item get "<item>" --vault "<vault>"`. Find ids with
  `op item list --vault "<vault>" --format json | jq -r '.[] | [.id,.title] | @tsv'`.

## Keep it generic

Do not write real vault IDs, item IDs, item names, or account identifiers
into this skill. Use placeholders (`<vault>`, `<item>`, `$OP_ACCOUNT`) in any
example added here.
