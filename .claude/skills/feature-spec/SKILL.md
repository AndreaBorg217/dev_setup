---
name: feature-spec
description: Use only when the user explicitly invokes feature-spec or directly asks for a strict written feature specification and review. Collects a structured specification, rejects material gaps, and saves the accepted spec without invoking planner or implementation.
---

# Feature Specification Protocol

Run this protocol only when explicitly invoked. Do not trigger it automatically for an ordinary feature request, task, or `planner` session. Keep it independent from planning and implementation.

Do not write code or propose technical implementation while running this skill.

## Step 1: Provide the Intake Template
Present the following blank template to the user and ask them to fill it out completely:

```markdown
**Feature:** [Explanation of what needs doing]
**Inputs:** [Where any required data or context will originate from]
**Output:** [What I expect the model or product to produce]
**Edge Cases:** [Issues we are aware of that need handling, eg. idempotency]
**Invariants:** [Conditions that always hold true]
**Performance Budget:** [Requirements related to performance such as latency and/or compute]
**Failure Modes:** [Things I will be looking for when I review code that will cause me to revert or not accept the output]
```

Wait for the user to reply with the filled-out template.

## Step 2: Review and Revert
Once the user returns the filled-out template, review it strictly against these criteria:
* **Completeness:** Did they skip any sections or leave them vague?
* **Testability:** Are the *Failure Modes* and *Invariants* specific enough that you can actually write tests or logic against them?
* **Realism:** Is the *Performance Budget* clearly defined (e.g., specific latency limits) and achievable?
* **Robustness:** Are the *Edge Cases* sufficiently detailed?

If the specification fails any of these checks, push back, clearly identify the weak points or missing details, and ask the user to refine those specific sections.

Once the specification is robust and complete, ask for a filename if none was supplied, save the accepted specification as Markdown, reply `Done`, and stop. Do not invoke `planner` or begin implementation automatically.
