---
name: feature-spec
description: Use whenever the user wants to build, plan, or scope a new feature. Prompts the user to fill out a strict specification template, then reviews their submission and pushes back (reverts) if it lacks necessary detail.
---

# Feature Specification Protocol

When the user indicates they want to start a new feature or task, you must enforce a strict two-step intake and review process. **Do not write any code or propose technical implementations until this protocol is satisfied and you are 99% confident on what the user is saying.**

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
Once the user returns the filled-out template, you must act as a strict reviewer. Carefully analyze their submission against these criteria:
* **Completeness:** Did they skip any sections or leave them vague?
* **Testability:** Are the *Failure Modes* and *Invariants* specific enough that you can actually write tests or logic against them?
* **Realism:** Is the *Performance Budget* clearly defined (e.g., specific latency limits) and achievable?
* **Robustness:** Are the *Edge Cases* sufficiently detailed?

If the specification fails any of these checks, push back, clearly identify the weak points or missing details, and ask the user to refine those specific sections. 

Only proceed to the implementation phase once the specification is robust, complete, and you have explicitly approved it. Ask me for a filename and save it as a markdown file before proceeding.