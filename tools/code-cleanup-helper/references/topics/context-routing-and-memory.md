# Context routing and durable memory

This topic owns the rules that make progressive disclosure smaller without turning it into amnesia.

## Stable rules

- `cleanup.context.canonical-private`: resolve every selected file from the active private Skill root and bind its live SHA-256. A public mirror, copied prompt, chat summary, or old evaluator hash is never runtime authority.
- `cleanup.context.route-bounded`: load only the entrypoint plus the task-selected topic/reference set. Record selected and omitted-but-applicable topic IDs, bytes, Token count, tokenizer identity, and manifest hash.
- `cleanup.context.critical-no-drop`: a Token ceiling may reject or narrow a route, but must never silently omit an applicable critical rule. Budget overflow is `BLOCK` or explicit legacy fallback.
- `cleanup.context.legacy-fallback`: missing, ambiguous, malformed, or unknown routing intent uses the declared legacy-compatible route. It may cost more context; it may not invent a smaller PASS.
- `cleanup.learning.raw-local`: project observations, names, paths, UI details, and raw evidence stay in the target repo `.rd/` and contribute zero default prompt Tokens.
- `cleanup.learning.promotion-receipt`: shared active/core rules require one owner, applicability and exclusions, a live content hash, reciprocal experiment linkage, replayable positive and negative fixtures, and a privacy-safe promotion receipt.
- `cleanup.context.quality-separate`: lower prompt Tokens prove only context efficiency. Compliance recall, verdict parity, false-green detection, and real task quality need separate frozen-corpus evidence.

## Three tiers

1. Tier 0 is the small entrypoint: authority, authorization, status semantics, revision gate, and router contract only.
2. Tier 1 is atomic topic knowledge: normally no more than five selected cards, each with stable rule IDs and bounded cost.
3. Tier 2 is project-local raw evidence: retained, hash-addressable, and retrieved only by explicit experiment/evidence ID.

Demotion changes the active index; it does not delete raw evidence. A user may always request the full legacy route. Any stale content hash, duplicate owner, private marker, missing fixture, or broken reciprocal link blocks shared promotion rather than discarding the learning.

## Required fixtures

- One dense single-line entrypoint must exceed its Token budget even if its line count is small.
- One aggregate route must exceed its budget while every individual file passes.
- Removing a critical topic, duplicating a rule owner, changing topic bytes, or promoting private data must fail.
- New and legacy routes must agree on critical verdicts over the frozen regression corpus.
