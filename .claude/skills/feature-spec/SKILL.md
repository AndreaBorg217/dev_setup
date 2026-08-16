---
name: feature-spec
description: Use when the user wants to build, plan, or scope a new feature, or when the `planner` skill requires an accepted spec before planning starts.
---

# Feature Specification Protocol

Produces `FEATURE_SPEC.md` inside the feature's plan directory. This is a precondition for `planner`, which will not proceed past its own Step 2 until the spec here is accepted. No code or technical implementation is proposed under this skill.

## Step 0: Classify thin vs. substantive

Read the user's request as given, before asking anything.

- **Thin** = a short sentence or two, with detail toward at most 1-2 of the 12 sections below (e.g. "add a retry button to the export screen").
- **Substantive** = anything else: multiple sentences, several sections implied, existing context pasted in, prior discussion to draw from.

If **thin**: skip prefill entirely. No Haiku call, no Sonnet call, zero dispatch cost. Go straight to Step 2 and present the blank template.

If **substantive**: proceed to Step 1.

## Step 1: Prefill draft (substantive requests only)

Dispatch a Haiku subagent (`model: "haiku"`, per `rules/subagents.md`) to extract and organize what the user already said into the 12 sections below. It must not add, infer, or complete anything the user did not state. Sections with no supporting statement are left blank, not guessed.

The 12 required sections, in this exact order:

```
Objective
Inputs and existing context
Outputs
In scope
Non-goals
Invariants
Edge cases
Failure modes
Performance budget or measurement plan
Validation policy
Deployment boundary
Existing pattern to mirror
Prohibited abstractions or changes
```

## Step 2: Present template

Present the 12 sections to the user:
- Thin path: all sections blank.
- Substantive path: prefilled from Step 1's draft, with any unsupported section left explicitly blank rather than filled.

Ask the user to complete or correct it. Wait for their reply.

## Step 3: Completeness and adversarial review

Dispatch a Sonnet subagent (`model: "sonnet"`, per `rules/subagents.md`) to review the returned template. This check applies to every sentence, not only blank sections - a prefilled or user-written sentence can still be a filled gap rather than a genuine decision. The reviewer must distinguish:
- A genuine user decision (specific, testable, intentional), from
- A filled gap (vague, generic, or assumed) that reads as complete but is not.

Check for:
* **Completeness** - no section skipped or left vague.
* **Testability** - *Failure Modes* and *Invariants* are specific enough to write tests or logic against.
* **Realism** - *Performance Budget or Measurement Plan* has concrete, achievable numbers or a concrete measurement method.
* **Robustness** - *Edge Cases* are sufficiently detailed.
* **Boundary clarity** - *Deployment Boundary* and *Prohibited Abstractions or Changes* are unambiguous about what must not happen.

If a flagged gap is itself ambiguous or architecturally loaded (i.e. the Sonnet reviewer cannot characterize what's missing well enough to phrase a precise question), dispatch Opus (`model: "opus"`, per `rules/subagents.md`) to characterize the gap before it goes to the user. Do not dispatch Opus by default just because this determination is hard, or because other skills in this flow use Opus elsewhere - it is an escape valve for genuinely ambiguous gaps only.

## Step 4: Halt on material gaps

If any check in Step 3 finds a material missing decision, halt via `AskUserQuestion`: state which section is incomplete, what specifically is missing, and what is needed to proceed. Do not plan around a guess, do not silently fill the gap yourself, and do not proceed to Step 5 until the user answers.

Repeat Steps 2-4 until the spec passes review with no material gaps.

## Step 5: Save and record revision

Once accepted:

1. Determine the plan directory: if `planner` invoked this skill and supplied a `$plandir` (its already-resolved `plans/<slug>/` path), use that path exactly - do not derive a separate slug. Only when run standalone with no caller-supplied directory, derive `plans/<kebab-case-slug>/` from the feature name and create it.
2. Write the accepted spec to `<plandir>/FEATURE_SPEC.md`.
3. Compute a revision hash: the SHA-256 of the file's exact byte content at acceptance time, truncated to the first 8 hex characters. If `PLAN.md` already exists for this feature, increment its existing revision counter; otherwise this is revision 1. Record the hash and revision number alongside the acceptance.
4. Report the hash/revision back so `planner` can write it into `PLAN.md` and so `plan-execute` can compare against it before dispatching affected tasks.

If `FEATURE_SPEC.md` is later edited after `PLAN.md` already references a revision, recompute the hash the same way. A hash mismatch means the spec changed since planning: any pending task whose scope touches the changed section(s) must be amended before it executes.

## Halt conditions

- Material gap in any of the 12 sections after review -> `AskUserQuestion`, do not proceed.
- Ambiguous/architecturally-loaded flagged gap that Sonnet cannot phrase precisely -> escalate to Opus for characterization only, then still halt via `AskUserQuestion` to get the user's decision.
- Never invent requirements, never silently fill a blank or vague section, never plan around an assumption.
