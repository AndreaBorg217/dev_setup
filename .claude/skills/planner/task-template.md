# Task file schema

Create exactly one file at `tasks/<full-id>.md` for each task indexed by
`PLAN.md`. The heading, filename stem, task-index ID, and every `Blocks:`
reference must use the same full ID. Planning-time Status is `PENDING` and
Results is empty.

```markdown
# t1-concise-task-title

Status: PENDING
Model: sonnet
Model reason: <Name the implementation or required semantic judgement.>
Skills: <Comma-separated known applicable invocation names, or None.>
Skill context: <Resolved inputs/persona required by those skills, or None.>
Goal: <One-sentence outcome.>
Writes: <Comma-separated paths/globs, or None.>
How: <Self-contained implementation steps, task-specific evidence, exact paths and commands, and important function/type/interface signatures.>
Materialization: <None, or Local — exact implementation-time build/install/code-generation command and observable ready state.>
Handoff: <Exact artifact/state later tasks may consume, or None.>
Verification: <CI | Manual | Local> — <Exact command/action and observable result.>
Results:
```

When execution checkpoints a task, append only these fields under `Results:`:

```text
Outcome:
Files changed:
Skills used:
Materialization:
Verification:
Handoff:
Notes:
```

`Local` must name one targeted check and must not contain a full build, module,
repository, or integration suite. Put exhaustive commands under `CI`.

`Materialization` is not verification. Use it only when execution must build,
install, publish, generate, migrate, or otherwise make an artifact available to
a later task. It must name the exact locally approved command and the observable
ready state. Include every repository path that command can change in `Writes`.
Prefix a broad Maven/Gradle artifact build with
`CLAUDE_PLAN_MATERIALIZATION=1` and disable its tests (for example,
`CLAUDE_PLAN_MATERIALIZATION=1 ./mvnw install -DskipTests`); tests remain owned
by Verification. Do not use the marker when a test goal is present or tests are
not explicitly skipped.
Use `Handoff` to name the exact version, generated API, schema, file, endpoint,
or other state a later block consumes. A task with no downstream artifact uses
`Handoff: None`.

Use the exact callable name of each known applicable skill; plugin skills retain
their namespace, for example `streaming:kafka`. Catalogue discovery is manual
and on demand. `Skill context` records resolved answers or operating mode that a
skill requires. It is not permission to leave a skill decision unresolved.

Use `Model: sonnet` for every implementation task and for read-only work needing
semantic judgement or elevated-risk handling. The template above is the
default. Use Haiku only for bounded noisy or menial read-only work; when changing
to `Model: haiku`, remove the `Model reason` line.
