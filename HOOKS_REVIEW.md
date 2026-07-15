# Hooks Review - `.claude/hooks/`

**Date:** 2026-07-15
**Audience:** codex onboarding / maintenance

---

## Overview

Three local `PreToolUse` hooks plus one external `rtk` hook guard and reshape Claude Code tool calls. They execute in the order registered in `.claude/settings.json`:

| Order | File | Scope | Effect |
|-------|------|-------|--------|
| 1 | `block-destructive-commands.py` | Bash | deny on destructive patterns |
| 2 | (external: `rtk hook claude`) | Bash | may rewrite supported commands, e.g. `pytest` -> `rtk pytest` |
| 3 | `filter-noisy-output.sh` | Bash | rewrite: pipe through grep/head |
| 4 | `subagent-routing.py` | Agent | ask on suboptimal routing |

All local hooks handle stdin parse failure gracefully (exit 0 / return `{}`).

---

## `block-destructive-commands.py`

**Purpose:** Safety gate — blocks destructive CLI commands before they execute.

**Coverage:** 10 domains — filesystem, git, SQL, Docker, Kubernetes, ArgoCD, Helm, Terraform, AWS, Airflow.

**Mechanism:** Regex match against stdin command. On match, returns `permissionDecision: deny` with the matched pattern in the reason string.

**Verified behavior:**

| Issue | Location | Severity |
|-------|----------|----------|
| `DELETE\s+FROM` blocks any SQL delete, including scoped deletes (`DELETE FROM users WHERE id=5`) | L31 | accepted strict policy |
| `airflow tasks clear` is blocked because it can trigger reruns | L64 | accepted strict policy |
| AWS pattern can false-positive when a harmless command argument contains a destructive word (`delete`, `terminate`, etc.) | L59 | accepted strict policy |
| No bypass mechanism exists for intentional destructive ops | - | accepted strict policy |

**Design note:** Self-described "speed bump, not a guarantee" - quoting, variable expansion, or wrapper scripts can bypass it. The strict false-positive posture is intentional: destructive-looking commands should stop and require a safer path or manual execution.

---

## `filter-noisy-output.sh`

**Purpose:** Quiet-mode filter — rewrites Bash commands to append grep/head pipes, keeping Claude's output focused on errors and warnings.

**Coverage:** Six command categories — test, lint, build, install, log, ops. Each has a specific grep pattern for "signal" lines and a `head -N` truncation.

**File naming:** Named `.sh`, shebang is `python3` (documented in docstring). Works fine.

**Findings and changes:**

| Issue | Location | Severity |
|-------|----------|----------|
| `rtk hook claude` rewrites commands such as `pytest` and `npm run build` with an `rtk ` prefix; anchored filter regexes missed those rewritten commands | L14+ | fixed |
| Install noise grep stripped legitimate summary lines (`found 0 vulnerabilities`, `added 1200 packages`) | L79-83 | fixed |
| macOS vs GNU grep runtime nuances remain untested at shell-pipeline level | L99+ | low |
| No `--help`/`--version` short-circuit for harmless commands | - | low |
| `head -150/200` may truncate useful context in very large outputs, especially logs | L99-114 | low |

**Implementation note:** Command-category regexes now accept an optional `rtk ` prefix so filtering still applies after the external hook rewrites supported commands. Install summaries are preserved by no longer treating `added`, `updated`, and `found` lines as noise.

---

## `subagent-routing.py`

**Purpose:** Cost optimization — intercepts Agent tool calls and nudges toward cheaper subagents/models using `permissionDecision: ask`.

**Model hierarchy:** haiku (search/read/triage) → sonnet (implementation/edit) → opus (planning).

**Mechanism:** Pattern-matches subagent type + description + prompt text, then compares actual model against expected model. Asks for confirmation on mismatch or missing model.

**Verified behavior:**

| Issue | Location | Severity |
|-------|----------|----------|
| Always asks when model is unset | L147-151 | accepted strict policy |
| `HAIKU_PATTERNS` overlap with `IMPLEMENTATION_PATTERNS`; implementation is checked first, so edits route to `sonnet` | L49-55, L89-104 | accepted behavior |
| `model_family()` uses substring match | L71-79 | low |
| No quiet/suppress mode for focused sessions | - | accepted strict policy |

**Implementation note:** No opt-out was added. Explicit Agent model selection remains enforced by default.

---

## Cross-cutting Issues

1. **Execution order matters:** `rtk hook claude` rewrites supported commands. The destructive blocker now runs before `rtk` so it sees the original command, and the output filter accepts `rtk`-prefixed rewritten commands.

2. **No PostToolUse hooks:** All hooks are PreToolUse. No mechanism to filter secrets, API keys, or sensitive data from tool outputs.

3. **No committed integration tests:** Hook behavior was manually sampled during review, but no test harness is kept in the repo.

4. **macOS-specific gap:** The generated grep/head pipelines still are not executed across BSD/GNU tool variants.

---

## Recommendations

### Completed
- Run `block-destructive-commands.py` before `rtk hook claude`.
- Make `filter-noisy-output.sh` recognize `rtk`-prefixed commands.
- Preserve package-manager summary lines in install output.

### Explicitly Not Changed
- Keep `DELETE\s+FROM` as a hard deny, including scoped deletes.
- Keep broad AWS destructive-word matching as a hard deny, including known false positives.
- Keep `airflow tasks clear` as a hard deny.
- Keep `subagent-routing.py` always-on; do not add an environment opt-out.

### Short-term
- If the strict false-positive posture becomes too disruptive, revisit AWS and Airflow policy with explicit examples from real use.
- Add shell-level tests for the generated grep/head pipelines if cross-platform behavior starts to matter.

### Longer-term
- Add PostToolUse hook(s) for output sanitization (secrets, keys, tokens).
