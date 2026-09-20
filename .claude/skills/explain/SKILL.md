---
name: explain
description: Use only when the user explicitly invokes explain via /explain. Generic explainer for understanding code or software concepts - how code works, codebase patterns, framework features, or system concepts.
disable-model-invocation: true
---

Run this protocol only when explicitly invoked. Do not trigger automatically for ordinary questions.

Invoke the `coding` skill before code-facing tools. Keep interpretation,
teaching, and follow-up discussion in the main conversation. Delegate
broad or repeated source discovery to `explorer`.

When explaining, always include:

1. **Ask visualization preference first**: Use `AskUserQuestion` with exactly 2 options before drawing anything:
   - `ASCII diagram` - compact ASCII in the chat, only when flow, hierarchy, or relationships are materially clearer than prose.
   - `Animated HTML` - a single self-contained HTML file following Notion aesthetics (see below), with step-through animation of the flow.
2. **Walk through**: Explain step-by-step what happens (code path or concept flow)
3. **Highlight a gotcha**: What's a common mistake or misconception?
4. **Web research when needed**: Use `explorer` only when the answer needs
   current or external documentation.
   Skip web research when the explanation is fully grounded in the codebase.

## Code / Framework Explanations

When the user asks about code, a framework or library feature (e.g. Spring annotations, Kafka Streams primitives) as it applies to the codebase:

1. **Explain the concept** first in plain terms - what it is, what problem it solves.
2. **Scan the codebase** for relevant usages, using `explorer` when the search
   is broad or spans multiple files.
3. **For each usage**, explain what it does in context and include a **"with vs. without" comparison**: show a concrete before/after snippet demonstrating how the code would look without the framework, then explain why the framework approach is better. Focus the tradeoff on what it eliminates (manual wiring, boilerplate, error-prone lifecycle management, etc.).
4. **System context**: When explaining a pattern that interacts with an external system (e.g. Kafka Connect, a downstream consumer, an external DB), proactively include a brief section on how that external system connects to the pattern - do not wait for the user to ask.
5. **Export on request**: When the user asks to export, write a `.md` file to `~/Desktop/`. If the user later drills deeper or asks to add context, **update that same file in place** - never create a second file.

## Software Concept Explanations

When the user asks about a software concept with no codebase anchor (e.g. how ClickHouse stores data on disk, how LSM trees merge):

1. **Explain the concept** first in plain terms - what it is, what problem it solves.
2. **Walk the flow** end to end with a concrete generic example (`orders`, `users`, `payments`).
3. **Ground with visuals**, not walls of text - the diagram carries the explanation (see Visual-first below).

## Follow-up Handling

After the initial explanation, the user may ask follow-up questions without re-triggering the skill. Handle these patterns:

- **"give me an example" / "elicit an example"**: Construct a minimal, self-contained code snippet that mirrors the exact pattern. Keep real identifiers when anchored to the codebase; use generic ones (`orders`, `users`, `payments`) only for standalone concepts.

- **"why is X approach not good?" / "what's wrong with Y?"**: Enumerate concrete failure modes, not theoretical concerns. For each failure mode: show what goes wrong, under what condition, and what the observable consequence is. Use a table if comparing multiple cases. Anchor to the actual project context (e.g. what would break in the downstream system).

- **Deepening questions** (e.g. "what happens if the predicate throws?"): Answer directly and concisely - do not re-run the full skill flow. Stay in the explanation context already established.

## Animated HTML Visualization

When the user picks `Animated HTML`, split the output: brief explanation in chat, visual explanation in HTML.

- **Chat**: brief only — what it is in 1-2 sentences, a 3-7 step walkthrough, one gotcha. Full detail lives in the HTML file, not the chat.
- **HTML**: write a single self-contained `.html` file (no external deps) to `~/Desktop/` and present it. Follow Notion aesthetics strictly, no AI slop:

- **Palette**: white `#FFFFFF` page, light-gray `#F7F7F5` panels, text `#37352F`, secondary `#787774`, borders `1px solid #E9E9E8`, accent gray-black only. No gradients (especially purple/blue), no glassmorphism, no neon, no dark-mode-by-default.
- **Type**: system sans (`-apple-system, Inter, SF Pro, Segoe UI, sans-serif`), 14-16px body, tight headings. No oversized hero text, no emoji bullets.
- **Layout**: Notion-like doc — narrow centered column (~720px), simple callout blocks, tables and toggles over decoration. Subtle `4-8px` radius, subtle shadow only.
- **Animation**: minimal step-through flow (prev/next + play, vanilla JS/CSS). Highlight active step with a gray background change only — no bouncy easing, no particle/confetti, no auto-playing carousels.
- **Visual-first (binding)**: the HTML is a diagram, not a note. Every step must render a visual (div/SVG boxes, arrows, file blocks, highlighted regions, annotated code snippets when explaining code/frameworks) with 1-2 sentence captions supporting it — never paragraphs-only, never a `pre` dump as the step body. Text explains the picture; the picture carries the explanation. Keep one persistent canvas/diagram across steps when possible and highlight the active element per step. Code snippets are allowed inside the visual (e.g. snippet beside boxes with arrows into it, with-vs-without panels), but a step must never be text alone.
- **Content**: naming follows the Rules below — real identifiers for codebase explanations, generic names only for standalone concepts or neutral exports.

## Rules

- **Naming**: when explaining the user's own codebase, use its real identifiers (service, topic, class, field names) — neutrality would make the explanation useless. Use generic domain names (`orders`, `customers`, `payments`) only for standalone concept examples with no codebase anchor, or when the user asks for a neutral/shareable export. If it is not obvious which applies, ask via `AskUserQuestion` (real vs. generic names) before producing the explanation.
- **Single file per explanation**: When exporting, one `.md` file per topic on the Desktop. If the user asks follow-up questions or requests additions, update that file in place rather than creating a new one.
