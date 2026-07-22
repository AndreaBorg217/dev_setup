# Claude Code hooks

The safety layer combines Python ports derived from hooks in
[`karanb192/claude-code-hooks`](https://github.com/karanb192/claude-code-hooks)
with local hooks that cover this setup's additional behavior.

## Derived safety hooks

- `block-dangerous-commands.py` blocks catastrophic and high-risk shell commands,
  including local database, infrastructure, cloud, and orchestration rules.
- `git-safety.py` adds protected-branch and destructive GitHub CLI guardrails.
- `protect-secrets.py` protects credential files and secret-bearing commands.
- `protect-tests.py` prevents deleting or disabling tests to manufacture a pass.

## Local hooks

- `policy.py` is the registered fail-closed policy entry point. It composes the
  derived safety checks, adds configuration self-protection and bounded large
  reads, and invokes RTK before returning rewritten Bash input.
- `subagent-routing.py` rewrites missing or mismatched non-Opus Agent routing in
  place, avoiding retry turns. Opus remains unchanged and requires approval.

RTK handles supported Bash command rewriting and noisy-output reduction through
`policy.py`. Unsupported commands and RTK failures pass through unchanged. Set
`CLAUDE_CONFIG_UNLOCK=1` before starting Claude Code when an intentional
configuration-maintenance session needs to modify or hot-reload the protected
settings, hooks, scripts, rules, skills, or global `CLAUDE.md`.

Hook registration and execution order live in `../settings.json`.

Run the local composition tests with:

```sh
python3 -m unittest discover -s ~/.claude/hooks/tests -v
```
