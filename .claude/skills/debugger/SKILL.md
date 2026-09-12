---
name: debugger
description: Diagnoses failures from logs, traces, and metrics — OOMs, crash loops, exceptions, or degraded behaviour. Use when a stack trace, error log, or incident report is provided, or when explicitly asked to find and fix a system or code anomaly.
---

# Debugger

Four phases, strict order. Each phase's output is required input for the next — don't skip ahead.

1. **Gather evidence** — logs, stack traces, pod/container state, metrics, attempt a local reproduction.
2. **Classify** — from that evidence, is this a system/infra failure or a code bug?
3. **Isolate** — for code bugs, trace inputs and dependencies through the real code path to the exact failure point.
4. **Fix the cause** — hand the isolated root cause to the coding skill for a minimal, targeted fix; verify against the Phase 1 repro; add a regression guard.

---

## Phase 1: Gather Evidence (mandatory first step, never skipped)

**Prescribed tooling:** Delegate to `explorer` (Haiku) with Context Mode sandbox. Optionally load the `prometheus` skill for metric windows.

Before writing a single sentence of analysis, before reading any code, before checking commit history — fetch the actual evidence of the failure. Reaching for code archaeology (commit dates, diffs, "this changed recently") before reaching for real evidence is the mistake to avoid: it produces a plausible-sounding story that isn't grounded in what happened, and every downstream conclusion inherits that risk.

Pull everything relevant and available — don't stop at the first thing that returns a result:

- **Logs** — the actual execution record of the failing thing (service, job, pipeline task), via its real API or log store, not a summary of it. Gather with `ctx_batch_execute` (e.g. `kubectl logs --tail 200`, `docker logs --tail 200`, `journalctl -u <unit> -n 100 --since 30m`), follow up with `ctx_search` + `intent` so only error windows enter context.
- **Stack traces / exceptions** — the full trace, not a truncated one-liner. Keep raw trace in the sandbox; return only the failing frame + 20 lines of context via `ctx_search`.
- **Pod / container state** — `kubectl describe pod`, `kubectl get events`, restart counts, exit codes, resource requests/limits vs. actual usage, node conditions. Capped reads via `ctx_batch_execute` + `intent` filter prevent full describe flooding.
- **Metrics** — via the `prometheus` skill (or equivalent) for memory/CPU/latency/error-rate around the failure window. Load the skill once before the first PromQL query. Look for the metric that moved _first_, not just the one that alarmed. Use range queries with bounded windows.
- **Reproduction attempt** — try to reproduce the failure locally or in a sandbox with the same inputs/state (`ctx_execute` with `intent`). A live repro is the strongest evidence available: it lets you inspect real state instead of inferring it, and it doubles as your verification harness in Phase 4. If it reproduces, capture the exact input/state that triggers it. If it doesn't, say so explicitly — that's a signal too (env-specific, race condition, data-dependent).

Keep diagnosis and repair judgement in the main conversation — use `explorer` for the noisy legwork, not for the call on what it means.

Use safe, read-only, capped commands to validate hypotheses as you go: `kubectl describe pod`, `docker logs --tail 200`, `grep -rn -m 50`, `journalctl -u <unit> -n 100 --since 30m`, `curl -Iv`. Cap every command — searches carry `-m 50` or `| head -n 50`, logs carry `--tail`/`-n`. Run these inside `ctx_batch_execute`/`ctx_execute` so caps and `intent` filtering are enforced.

If a piece of evidence requires a tool, credential flow, or API you've been pointed at before (or that obviously exists for this purpose), use it proactively — don't wait to be told. Ask the user for specific missing artifacts (exact env vars, package versions, routing config) only when they're logically required and genuinely unobtainable yourself.

**Fallback only when evidence is genuinely unavailable** (e.g. logs expired/rotated, no metrics, repro impossible): hypothesize from code context, but say explicitly that this is a fallback, not a finding, and label every downstream conclusion as unconfirmed.

---

## Phase 2: Classify — System Failure vs. Code Bug

**Prescribed tooling:** Main thread only. No `explorer`, no CodeGraph, no Context Mode — classification is a judgement call over Phase 1 evidence already in context.

Using the Phase 1 evidence, classify the failure before deciding how to dig further:

- **System / infra failure** — OOM kill, crash loop, node pressure, resource exhaustion, network/DNS/config failure, bad deploy, upstream dependency outage. The evidence itself (pod events, exit codes, metrics) usually points straight at the mechanism; the remaining work is confirming which infra factor caused it, not tracing application logic.
- **Code bug** — the process is healthy and resources are fine, but output/behavior is wrong, an exception is thrown, or state is corrupted. This needs Phase 3.

State which one this is, and the evidence supporting that call, in 1–2 sentences before moving on. If it's ambiguous (a memory leak that surfaces as an OOM, an infra issue that only triggers on one code path), say so and pursue both — don't silently pick one.

For a pure infra failure, skip to Phase 4 once the specific infra fix is identified (raise a limit, fix a config, roll back a bad deploy) — there's no code path to isolate.

---

## Phase 3: Isolate the Failure Point (code bugs only)

**Prescribed tooling:** Delegate broad tracing to `explorer` (Haiku) with CodeGraph first (`codegraph_explore`), then Context Mode for replay. Keep isolation judgement in the main thread.

This is where evidence meets code. Don't guess which function is broken — trace it.

- **Trace inputs and dependencies**: starting from the evidence (the exact input, request, or state that triggered the failure), follow the literal call chain — not an approximation of it — through every function, service call, and dependency involved. `explorer` calls `codegraph_explore "<what the failure trace touches>"` once (treat returned source as already Read; do not re-open those files or re-run the trace in the main thread) — benefits: single token-efficient call replaces dozens of `Read`/`Grep` loops and yields file:line-anchored chain in one receipt. Use a second `explorer` pass only if the chain spans a service boundary not covered by the first call.
- **Re-run the exact failing logic**, not a simplified stand-in, inside Context Mode (`ctx_execute`/`ctx_execute_file` with `intent`). A reduced version can silently behave differently and produce a false confirmation. Exercise the literal logic against real data/state from Phase 1 and inspect actual output — sandbox keeps full output out of the main context, only the diverging assertion returns.
- **Check the check itself**: before trusting any comparison, validation, or test as ground truth, verify it doesn't have its own bug producing false positives/negatives. Test its edge cases directly in the sandbox.
- **Distinguish correlation from causation explicitly**: if two things changed around the same time, name it as a candidate explanation, then verify against the real failure evidence — don't write it up as confirmed causation until it is.
- **Never present a hypothesis as a finding.** A diff, a commit date, or a timing correlation is a hypothesis until checked against the real evidence.
- If the trace is ambiguous or the evidence incomplete, list 2–3 prioritized, testable hypotheses rather than committing early — then test them in priority order until one is confirmed (one `ctx_execute` per hypothesis, `intent`-filtered).
- If it's a silent failure with no stack trace, immediately identify where state inspection or telemetry is missing — that gap is itself part of the diagnosis.
- **State what remains unconfirmed.** If part of the chain can't be verified against real evidence, say so plainly instead of substituting a plausible narrative.

Close this phase with a definitive root cause: the exact file:line/condition where behavior diverges from what's expected, cited with a snippet. When reporting a divergence between two things that should agree (two implementations, or a spec vs. an implementation), quote the relevant snippet from each side with a file:line reference — not just a prose description.

---

## Phase 4: Fix the Cause, Not the Symptom

**Prescribed tooling:** Delegate the edit to the `coding` skill via `builder` (Sonnet); verify in Context Mode.

Only make a change once Phase 2 or 3 has produced a definitive cause.

- **Target the root cause, not the point where the symptom became visible.** If a null check would just swallow bad state rather than explaining why the state is bad, that's a symptom fix — find out why the value is wrong and fix that, unless a defensive check is genuinely the correct architectural boundary (say explicitly which case this is).
- **Delegate the actual code change to the coding skill via `builder`.** Hand it the isolated root cause from Phase 3 — file:line, the divergence, expected vs. actual behavior — and let it produce the minimal, targeted modification per the coding skill's Discovery and context (CodeGraph first, Context Mode for noisy output, LSP for diagnostics) and verification rules. Don't freehand the edit in this skill. Don't refactor surrounding code unless the surrounding architecture is the direct cause of the bug.
- **Verify against the Phase 1 reproduction.** Re-run the same repro case (or give the exact test/`curl` command) that demonstrated the failure inside `ctx_execute` with an `intent` filter, and confirm it now passes against the real logic — not a mock.
- **Prevention**: suggest one minimal unit test or specific logging/metric addition that would have caught this exact issue earlier, tied directly to the gap surfaced in Phase 1 or 3 (missing telemetry, an untested edge case, an alert threshold that didn't fire).

---

## Output Format

- Open with the classification (Phase 2) and the definitive root cause (Phase 3, or the infra cause) — 1–2 sentences, no filler or sympathetic text.
- If genuinely ambiguous, open with the prioritized hypotheses instead and say so explicitly.
- Then: evidence gathered, the trace that isolated the cause, the fix (produced via the coding skill), the verification command, and the prevention suggestion.
- Every claim about what happened must trace back to evidence gathered in Phase 1 — flag anything that doesn't.
