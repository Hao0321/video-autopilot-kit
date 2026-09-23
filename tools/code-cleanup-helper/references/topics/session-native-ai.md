# Session-native AI tool product audit

- `cleanup.ai.identity-separation`: distinguish the user's Codex/Claude host, the local MCP process, and the durable product runtime. The product must not request or retain provider API keys/subscription credentials merely to expose local tools.
- `cleanup.ai.same-source-evidence`: bind source hash, bounded keyframes/transcript cues, semantic receipt, structured plan, atomic editable mutation, Undo, and render output. Local decoding is not proof that the model viewed every frame.
- `cleanup.ai.forgery-stale-negative`: stale source, missing frame/cue evidence, forged receipt, and incompatible schema must fail before mutation.
- `cleanup.ai.onboarding-real-host`: exercise supported host CLI/config shapes in isolated homes, verify command/args/env/server identity and protocol health, and write no AI secret. `configured` and `connected` are separate states.
- `cleanup.ai.human-fallback`: missing CLI or health failure yields a bounded inspectable copy-command and next-session instruction, never silent success.

Computer Use is fallback evidence when no structured tool exists; stepwise clicking cannot close a promised low-latency/low-Token structured flow.
