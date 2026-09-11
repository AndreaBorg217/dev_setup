---
name: review-code
description: Review a requested diff, file, symbol, or behaviour for concrete correctness, maintainability, and performance issues. Keep the review interactive unless the user requests an artifact.
---

# Code review

Invoke the `coding` skill before code-facing tools. Keep the review in the main
Sonnet conversation so the user can challenge findings and ask follow-up
questions. Anchor each question to the requested diff, file, symbol, or decision
when one is available.

Use `explorer` only for broad or repeated repository discovery. Do not delegate
review judgement, findings, prose, or follow-up discussion.

Review for concrete memory/resource leaks, bugs against the specification,
maintainability defects, performance problems, and quality issues. Order
findings by severity. For each finding give:

- category and severity;
- exact path and line;
- the observable failure or maintenance cost;
- the smallest correction.

Do not manufacture findings for style preferences, hypothetical callers, or
unreachable misuse. State `PASS` when no in-scope issue remains.

Respond in chat by default. Create or update `REVIEW.md` using
[template.md](template.md) only when the user explicitly asks for a review
artifact.
