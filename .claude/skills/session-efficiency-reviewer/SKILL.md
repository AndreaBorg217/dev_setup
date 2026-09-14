---
name: session-efficiency-reviewer
description: Audits Claude Code JSONL sessions for efficiency - context waste, routing and verifier churn. Use for session-cost or agent-efficiency reviews, not code-correctness reviews.
disable-model-invocation: true
---

# Session efficiency reviewer

Treat Claude transcripts as secret-bearing data. Never print, quote, summarize,
or load their prompts, reasoning, commands, or tool results into model context.
Run the local analyzer directly; it emits only counts, redacted paths, byte/token
estimates, and remediation advice.

## Run

List recent main-session transcripts for the current project:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/session_efficiency.py" list --project-root "$PWD"
```

Find sessions whose main or subagent trace mentions a particular file without
printing transcript content:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/session_efficiency.py" list --project-root "$PWD" --mentions-path path/to/file
```

Review the latest substantive main session and its saved subagent traces. Shell-only
fragments created by commands such as `/clear` are ignored:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/session_efficiency.py" review --latest --project-root "$PWD"
```

Review a specific transcript, or add `--json` for machine-readable output:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/session_efficiency.py" review /path/to/session.jsonl
```

The script uses Python's standard library and reads the transcript only inside
the process. Do not pre-process a transcript with `cat`, `jq`, `Read`, or a
general-purpose model. Use `--main-only` when subagent traces must be excluded.

## Interpret and respond

- Report only warnings supported by the analyzer's evidence.
- Treat `toolUseResult.resolvedModel` as authoritative for Agent routing; child
  transcript model labels are only a fallback heuristic.
- Count repeated reads only after successful results and only when ranges are
  broad or substantially overlap. Denied attempts and disjoint targeted ranges
  are not repeat reads.
- For historical sessions, use legacy Shunt receipt totals to distinguish successful offload from denied
  reads followed by paging. Treat a denial without a completed read receipt as
  a routing defect, not proof that Haiku was used.
- Report repeated broad build/test commands and dedicated verifier dispatches
  separately from targeted checks. One final pre-MR full suite is acceptable;
  prefer CI or approved targeted checks during implementation.
- Call character-to-token conversions estimates, not measured billing or
  guaranteed savings. Recorded input/cache token counters are context volume,
  not dollars; model-search suitability is explicitly a heuristic.
- Prioritize the largest repeated context payloads, then incorrect routing and
  avoidable work. A long trace is evidence that a task needs narrowing; do not
  recommend turn caps or continuation messages. Propose narrow changes such as
  Haiku explorer routing, CodeGraph-first source discovery with Context Mode
  sandboxing, `rg`/`jq` with source-side limits,
  targeted reads, compact CLI wrappers, batched inspection scripts, CI
  verification, or progressive skill disclosure.
- Do not automatically edit hooks, skills, model settings, or project files.
  Present fixes first unless the user explicitly asks for implementation.
- If the transcript schema is partially unsupported, disclose the skipped-line
  count and avoid conclusions that depend on missing evidence.

## Provenance

This is a local adaptation of the measurement approach in Uber Engineering's
[Running a Software Factory Efficiently at Uber Scale](https://www.uber.com/gb/en/blog/efficient-software-factory/): measure session cost drivers, use cheaper
models for bounded subagents, batch chatty tool workflows, and pair detected
anti-patterns with targeted remediation. Do not describe this skill as Uber's
internal cost-dashboard skill or as an Uber-published implementation.
