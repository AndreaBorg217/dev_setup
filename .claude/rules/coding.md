# Coding skill requirement

For programming work, load the mandatory `coding` skill before reading or
changing source code, using code-oriented LSP operations, or running builds,
tests, linters, or type checkers. The skill is the canonical coding and code
review policy.

Discovery precedence is CodeGraph, then Context Mode sandbox, then LSP, then
`rg`/native tools: `codegraph_explore` first for source questions (treat its
source as already Read), Context Mode (`ctx_batch_execute` gather,
`ctx_search` follow-up, `ctx_execute`/`ctx_execute_file` process,
`ctx_fetch_and_index` for URLs) for anything noisy, LSP for type-aware
navigation/diagnostics, `rg` only for exact strings or configs.
