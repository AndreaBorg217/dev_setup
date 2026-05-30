---
name: explain-code
description: Explains code. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
---

When explaining code, always include:

1. **Draw a diagram**: Use ASCII art to show the flow, structure, or relationships
2. **Walk through the code**: Explain step-by-step what happens
3. **Highlight a gotcha**: What's a common mistake or misconception?
4. **Web search**: Search the web for documentation relevant to further educational reading. If it's library code, refer to the documentation anyways. Skip the web search if the explanation is fully derivable from the codebase itself.

## Framework / Library Concepts

When the user asks about a framework or library feature (e.g. Spring annotations, Kafka Streams primitives) as it applies to the codebase:

1. **Explain the concept** first in plain terms — what it is, what problem it solves.
2. **Scan the codebase** for all usages of that feature. Use an Explore agent for broad searches.
3. **For each usage**, explain what it does in context and include a **"with vs. without" comparison**: show a concrete before/after snippet demonstrating how the code would look without the framework, then explain why the framework approach is better. Focus the tradeoff on what it eliminates (manual wiring, boilerplate, error-prone lifecycle management, etc.).
4. **System context**: When explaining a pattern that interacts with an external system (e.g. Kafka Connect, a downstream consumer, an external DB), proactively include a brief section on how that external system connects to the pattern — do not wait for the user to ask.
5. **Export on request**: When the user asks to export, write a `.md` file to `~/Desktop/`. If the user later drills deeper or asks to add context, **update that same file in place** — never create a second file.

## Follow-up Handling

After the initial explanation, the user may ask follow-up questions without re-triggering the skill. Handle these patterns:

- **"give me an example" / "elicit an example"**: Construct a minimal, self-contained code snippet that mirrors the exact codebase pattern. Strip all domain-specific identifiers (use `orders`, `users`, `payments` etc.).

- **"why is X approach not good?" / "what's wrong with Y?"**: Enumerate concrete failure modes, not theoretical concerns. For each failure mode: show what goes wrong, under what condition, and what the observable consequence is. Use a table if comparing multiple cases. Anchor to the actual project context (e.g. what would break in the downstream system).

- **Deepening questions** (e.g. "what happens if the predicate throws?"): Answer directly and concisely — do not re-run the full skill flow. Stay in the explanation context already established.

## Rules

- **Neutral diagrams**: Diagrams must use generic domain names (e.g. `orders`, `customers`, `payments`). Never use internal topic names, service names, or any company-specific identifiers — the user may be exporting diagrams to personal notes or a wiki.
- **Neutral examples**: Code examples must also use generic domain names, never project-specific class names, topic names, or field names.
- **Single file per explanation**: When exporting, one `.md` file per topic on the Desktop. If the user asks follow-up questions or requests additions, update that file in place rather than creating a new one.
