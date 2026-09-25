---
name: session-efficiency-reviewer
description: Audits Claude Code JSONL sessions for evidence-backed context waste, file-ownership duplication, skill adherence, and model routing. Use for session-cost or agent-efficiency reviews, not code-correctness reviews.
when_to_use: "session_efficiency.py, JSONL transcript, context waste, file-ownership duplication, skill adherence, model routing, review --latest, review-day, list --mentions-path, mine-preferences, correction marker, preference marker, confidence tier, proposed_artifact, resolvedModel, subagent trace, repeated reads, broad build/test commands, token estimate, Shunt receipt, --main-only, --json, --project-root, --transcript-root"
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

Review every substantive main session across repositories for one local day.
Repeat `--project-root` to restrict the report to selected repositories:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/session_efficiency.py" review-day \
  --date 2026-09-17 --timezone Europe/Malta
```

Mine the last N days (default 7) of your own main-session transcripts for
user-authored correction and preference markers — explicit corrections
("no, not that", "don't do X", "stop doing X", "that's not what I asked"),
explicit preferences ("I prefer X", "always do X", "never do X"), and the
same marker repeated across sessions. Only fixed marker categories, a single
redacted subject word, counts, a confidence tier, and a proposed artifact
type are emitted — never quoted or reconstructable turn text:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/session_efficiency.py" mine-preferences \
  --project-root "$PWD" --days 7
```

Add `--json` for machine-readable output, or `--transcript-root` to point at
a non-default transcript directory. Each finding reports
`category:subtype (subject)`, `occurrences`, `sessions`, a `confidence` tier,
and one `proposed_artifact`:

- `confidence`: `strong` (an explicit workflow-changing correction, or the
  same marker repeated across sessions), `medium` (the same tool/model/
  validation-related preference repeated across sessions), `weak` (a single
  ambiguous instance with no repetition), `contradicted` (conflicting
  `always`/`never`/`i_prefer` evidence for the same subject).
- `proposed_artifact`: `skill` (a recurring multi-step preference), `rule`
  (a broad standing correction or `always`/`never` statement), `hook` (a
  mechanically-enforceable, repeatedly-violated constraint on a named
  tool/model/validation step — a candidate for a new blocking/advisory
  PreToolUse hook, following this repo's `advise-agent-routing.py`,
  `require-coding-skill.py`, and `require-git-skill.py` precedent),
  `workflow doc` (situational context worth recording but not a standing
  rule), or `none` (contradicted or weak evidence — do not force an
  artifact).

This mode remains user-invocation-only, per `disable-model-invocation` above;
present findings and let the user decide whether to draft the proposed
artifact.

The script uses Python's standard library and reads the transcript only inside
the process. Do not pre-process a transcript with `cat`, `jq`, `Read`, or a
general-purpose model. Use `--main-only` when subagent traces must be excluded.

## Interpret and respond

- Report only warnings supported by the analyzer's evidence.
- Treat high subagent volume and continuations to an existing owner as neutral.
  Report subagent waste only when the transcript demonstrates duplicated file
  access, repeated context, incorrect routing, or another measured defect.
- Report sustained direct read-only collection in the main trace with no Agent
  dispatch as missed delegation. Treat Context Mode sandbox calls as successful
  compact extraction, not missed delegation. Tool-name classification remains a
  heuristic; do not infer intent or claim every individual call required a worker.
- A file has one persistent owner for a task. A parent or second worker reading
  or changing the same file is an ownership violation; later questions should
  return to the existing owner and be batched there.
- Report source work without `coding`, Git commands without `git`, and Airflow
  source work without both `coding` and supplemental `airflow` as skill
  adherence failures.
- Treat `toolUseResult.resolvedModel` as authoritative for Agent routing; child
  transcript model labels are only a fallback heuristic.
- Count repeated reads only after successful results and only when ranges are
  broad or substantially overlap. Denied attempts and disjoint targeted ranges
  are not repeat reads.
- For historical sessions, use legacy Shunt receipt totals to distinguish successful offload from denied
  reads followed by paging. Treat a denial without a completed read receipt as
  a routing defect, not proof that Haiku was used.
- Report repeated broad build/test commands separately from targeted checks.
  One final pre-MR full suite is acceptable; prefer CI or approved targeted
  checks during implementation.
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
