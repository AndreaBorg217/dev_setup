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
    - `Animated HTML` - a single self-contained HTML file following the aesthetic below, with step-through animation of the flow.
2. **Walk through**: Explain step-by-step what happens (code path or concept flow)
3. **Highlight a gotcha**: What's a common mistake or misconception?
4. **Web research when needed**: Use `explorer` only when the answer needs
   current or external documentation.
   Skip web research when the explanation is fully grounded in the codebase.

## Code / Framework Explanations

When the user asks about code, a framework or library feature (e.g. Spring annotations, React hooks) as it applies to the codebase:

1. **Explain the concept** first in plain terms - what it is, what problem it solves.
2. **Scan the codebase** for relevant usages, using `explorer` when the search
   is broad or spans multiple files.
3. **For each usage**, explain what it does in context and include a **"with vs. without" comparison**: show a concrete before/after snippet demonstrating how the code would look without the framework, then explain why the framework approach is better. Focus the tradeoff on what it eliminates (manual wiring, boilerplate, error-prone lifecycle management, etc.).
4. **System context**: When explaining a pattern that interacts with an external system (e.g. a message queue, a downstream service, an external DB), proactively include a brief section on how that external system connects to the pattern - do not wait for the user to ask.
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
- **HTML**: write a single self-contained `.html` file (no external deps) to `~/Desktop/` and present it. Clean dark aesthetic with restrained colour, no AI slop:

- **Palette**: dark base — page `#191919`, panels `#202020`, text `#E8E6E3`, secondary `#9B9B9B`, borders `1px solid #2E2E2E`. Plus accents for diagram semantics only, never page chrome — pick as needed per explanation: blue `#4C9AFF` on `#1A2E4A`, orange `#CB7D4A` on `#33231A`, green `#4CAF7D` on `#1A3325`, amber `#C19138` on `#3A2E1A`, purple `#9A6DD7` on `#2A2350`, pink `#D157A0` on `#3A1F33`, red `#E05D5D` on `#3A1F1F`. Assign one meaning per colour per diagram, always show a legend, prefer max ~4 colours per view. No gradients, no glassmorphism, no neon.
- **Type**: system sans (`-apple-system, Inter, SF Pro, Segoe UI, sans-serif`), 15-17px body, node titles ≥15px, labels ≥13px, 12px absolute floor — never 10-11px micro-text. Tight headings. No oversized hero text, no emoji bullets.
- **Layout**: use the screen estate available — full-width responsive doc (max ~1200px, `width: 100%`). Diagram is fully responsive: `grid`/`flex` with `clamp()` sizing and breakpoints at ~860px and ~1080px, no fixed-pixel canvas that overflows the viewport. On desktop show multi-column flow; on narrow screens stack vertically with the same reading order. No `position: absolute` for primary layout (only for transient tokens/overlays). Generous padding (`clamp(12px, 1.5vw, 18px)`) and gaps (`clamp(14px, 2vw, 24px)`), route edges with clearance and offset labels with a solid backdrop so no two elements overlap at any step or viewport. Must remain usable at `390px`, `768px`, and `1200px`. Simple callout blocks, tables and toggles over decoration. Subtle `4-8px` radius, subtle shadow only.
- **Density & vertical fit (binding)**: before writing any code, count every entity the domain needs (brokers × partitions × per-partition fields, consumer groups × members, etc.). If showing all of them with all their fields at once would push the diagram past a reasonable single-screen height (~700-800px of content at 1200px wide, without the page itself scrolling more than one screen-and-a-bit), cut scope — don't shrink padding/fonts to force a fit:
    - Show only the fields relevant to the _current step_ per entity (e.g. a partition shows offset/log only when the narrative touches it; otherwise it collapses to a one-line label). Never render log + ownership + commit state + replica state for every partition at every step simultaneously — that's the default failure mode.
    - If the concept genuinely needs more siblings than fit (e.g. 6 brokers), show 2-3 in full plus a "+N more (same pattern)" chip, not all of them shrunk.
    - If content still can't fit after cutting scope, the _diagram canvas itself_ may scroll independently (`max-height` + `overflow-y:auto` on `#canvas` only) while controls, step list, and caption stay outside it and always visible — the page as a whole should never require scrolling past controls to see the caption.
- **Edge routing against reflow (binding)**: arrows computed from live element positions (`getBoundingClientRect`) are only valid for the exact layout state they're measured in. Any class toggle that changes an element's size or position (`.active`, `.leader`, outline, growing text) must complete and paint _before_ edges are measured — recompute edges inside the same step transition, not from stale rects, and re-measure on breakpoint changes, not just window resize events fired for other reasons. Never route a straight line whose path crosses through a third box's bounding rect — if the layout makes that unavoidable, either reposition the two actors so their connecting arrow is a short direct hop (adjacent panels, not diagonals across the whole canvas), or draw an elbowed/orthogonal path that steps around the intervening box.
- **Timing implementation (binding)**: derive every animation delay from one named duration constant that matches the CSS transition duration exactly (e.g. a single `MOVE_MS` used both in the CSS `transition` and in the JS timeline) — never hardcode independent magic-number `setTimeout` delays (850ms, 700ms, ...) alongside a differently-declared CSS transition (.8s). Drift between the two is what makes hops look sloppy. Prefer one small step-timeline/state-machine driving all moves for a step over chains of nested `setTimeout` calls, which compound drift and are hard to reason about.
- **Animation**: narrative flow, not just a slideshow (vanilla JS/CSS/SVG, no libs). Animate the domain's unit of movement travelling between actors/stages, rendered as the domain object itself (record box with key/id, request card, chunk block — never a generic dot/circle), including failure + recovery stages where relevant to the concept. Controls: play/pause + replay + timeline slider + clickable steps. Motion is linear/ease, 600-1200ms per hop — no bouncy easing, no particles/confetti, no auto-playing carousels (start paused, user presses play).
- **Visual-first (binding)**: the HTML is a diagram, not a note. One persistent canvas/diagram across steps with moving domain objects (same box/card shape as in the static layout, carrying its real key/id/offset — never generic circles/dots), active zone highlighted, and 1-2 sentence caption per stage — never paragraphs-only, never a `pre` dump as the step body. Every transfer between actors must show a labelled directed arrow (SVG/div edge with arrowhead); objects must spawn at the true source actor and travel _along_ those arrows — never appear mid-canvas or out of thin air — and the active arrow highlights per step. Arrows show data direction; if the initiator differs from data flow (e.g. poll vs push), label it explicitly (e.g. `poll: data flows A → B, initiated by B`). When the concept has a logical grouping split into physical shards, show both (grouping container + shard boxes with ownership/replica roles). Text explains the picture; the picture carries the explanation. Code snippets are allowed inside the visual (e.g. snippet beside boxes with arrows into it, with-vs-without panels), but a step must never be text alone.
- **Correctness & domain fidelity (binding)**: every animated step must be state-consistent with the explained system. The token is the domain unit — it spawns at the true source, moves along the labelled arrow, lands at the true destination, and the destination's state updates _after_ arrival (e.g. log append, replica copy, offset advance). Never show a record already in a log before it arrives; never replicate from/to the same actor (e.g. B1→B2/B3, not B1→B1); never show a consumer owning a partition it doesn't own at that step. Offsets, ownership, and replica sets must change only when the narrative says they do, and reverse on replay/reset. Groups that are independent subscribers (e.g. Group B) must visibly fetch too — not sit idle while Group A fetches. Rebalance/replay must explain _what_ replays and _why_ (last committed offset), with the replayed record re-fetched from the broker.
- **Pre-present verification (binding)**: never present a broken visual, and never assume a specific OS, browser, or local app is present — the runtime environment varies and a hardcoded local browser path is not a valid check.
    - If a headless browser is actually available and launchable in the current environment (check first — don't assume), render the file at `1280px`, `900px`, and `390px`, step through every state (each step + Play), take full-page screenshots, and inspect them for: text truncated or covered by tokens, labels on top of boxes or clipped by viewport, edges routed through unrelated zones or showing the wrong direction, tokens spawning mid-canvas or from the wrong source, replica/ack/fetch looping to self, empty tall canvas, horizontal overflow, and the densest step exceeding one screen's height. Fix and re-verify before presenting.
    - If no headless browser can be launched in the current environment, that is not license to skip verification — do a static audit instead, and treat it as mandatory minimum in every case: list every element visible simultaneously in the _densest_ step, estimate its rendered height/width from the actual CSS values used (padding, line-height, font-size, min-height), and sum them against the viewport budget in Density & vertical fit above; trace each defined edge's two endpoints against the layout and confirm no third element's box sits between them; confirm every `setTimeout` value matches the timeline constant from Timing implementation. If the sums don't provably fit or an edge provably crosses another box, cut scope and redo the audit — don't ship on the hope that it renders fine.
- **Content**: naming follows the Rules below — real identifiers for codebase explanations, generic names only for standalone concepts or neutral exports.

## Rules

- **Naming**: when explaining the user's own codebase, use its real identifiers (service, topic, class, field names) — neutrality would make the explanation useless. Use generic domain names (`orders`, `customers`, `payments`) only for standalone concept examples with no codebase anchor, or when the user asks for a neutral/shareable export. If it is not obvious which applies, ask via `AskUserQuestion` (real vs. generic names) before producing the explanation.
- **Single file per explanation**: When exporting, one `.md` file per topic on the Desktop. If the user asks follow-up questions or requests additions, update that file in place rather than creating a new one.
