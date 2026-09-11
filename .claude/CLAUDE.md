# CLAUDE.md

All files under `rules/` are binding for every task in every repository.

# Compact instructions

When compacting, preserve: task goals, decisions made, file changes in progress, test results, error messages under investigation.
Discard: exploratory search results, raw command output, intermediate reasoning, completed subtask details.

Preserve these binding rules during compaction:

@rules/safety.md
@rules/coding.md
@rules/workflow.md
@rules/subagents.md
@rules/interaction.md
@rules/config-management.md

<!-- CODEGRAPH_START -->
## Token-efficient discovery (binding)

Answer from indexes and sandboxes, not from raw reads. This saves
an order of magnitude in tokens (one `codegraph_explore` vs dozens of
grep/Read calls; ~98% reduction via Context Mode sandboxing).

1. CodeGraph first for source: call `codegraph_explore` FIRST for how
   does X work, architecture, flows (how does X reach Y), where/what is
   X, surveying an area, or before editing a symbol. Treat returned
   source as already Read: do NOT re-open those files. One call is
   usually enough; stop there. Non-MCP sessions use
   `codegraph explore "<symbols or question>"`.
2. Context Mode sandbox for data: never let raw output flood context.
   GATHER with `ctx_batch_execute(commands, queries)`; FOLLOW-UP with
   `ctx_search(queries: [...])` (batch all questions in one call);
   PROCESS with `ctx_execute` / `ctx_execute_file` (pass `intent` when
   output may exceed ~5KB so only matching sections return). Fetch URLs
   with `ctx_fetch_and_index`, never `WebFetch`; analyse large
   files/logs with `ctx_execute_file`, never `Read`. `Bash` is only for
   short fixed output (git, mkdir/rm/mv, navigation) and `Read` only
   for exact bytes needed for an edit.
3. Narrow tools only on miss: `rg`/LSP cover exact strings, configs,
   and type diagnostics CodeGraph could not answer. `codegraph affected
   --stdin --quiet` selects targeted-test candidates from changed
   paths; it never replaces required checks.

Do not initialize CodeGraph without the user's approval. If no
`.codegraph/` index answers, fall back to LSP/`rg` (cap with `-m 50` /
`--max-count 50` or `| head -n 50`) and say so. This fallback is exempt
from the `limit-output` strict `-m` deny when the index is absent.
<!-- CODEGRAPH_END -->
