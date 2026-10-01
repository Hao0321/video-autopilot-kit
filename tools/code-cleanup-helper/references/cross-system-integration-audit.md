# Cross-system integration audit

Use this read-only semantic audit when requirements cross a Skill/Agent, MCP/API, product runtime, installer, human review, publishing, or outcome-learning boundary.

## 導航

[False green](#false-green-pattern) · [Mutable Skill](#mutable-skill-boundary) · [Model/context](#model-and-context-boundary) · [Semantic handoff](#semantic-handoff-and-legacy-compatibility) · [Market claims](#market-and-complete-claims) · [Batch](#batch-fan-out-and-editable-re-entry) · [Media workstation](#professional-media-workstation-contract) · [Background jobs](#non-blocking-desktop-background-jobs)

## False-green pattern

The following are component-presence evidence, not end-to-end integration evidence:

- a Skill, module, command or asset library exists;
- a tool appears in an MCP list;
- an installer contains a file;
- unit tests pass inside one subsystem;
- a README says the systems are connected;
- an honest evaluator says the claim is still `unmeasured`.

For each promised flow, require a closed-world list of stages plus one same-revision journey. Evidence should bind planner/Skill revision and hash, handoff schema, executor receipt, atomic product mutation, delivered output, and any claimed review/publish/outcome transition. If any required edge is absent, report `NOT_CHECKED cross-system-integration` even when both endpoint components exist.

## Mutable Skill boundary

When the product must use the newest private Skill on every invocation, inspect whether it loads the canonical current source or consumes a bounded plan with a source revision/hash receipt. Flag these as `REVIEW` or `NOT_CHECKED`:

- private Skill text or full memory copied into a public installer;
- no provenance tying a plan to the Skill bytes that produced it;
- an old project mirror or cached prompt treated as canonical;
- full memory loaded when selected IDs and bounded context are sufficient;
- a product smoke test silently promoting machine review to human certification.

The preferred architecture keeps private decision/memory state outside the shipped product and versions the adapter contract. This is both a freshness and information-boundary check; it does not prove the flow works until the real journey passes.

### Anonymous generalized-memory pack

When the owner explicitly authorizes generalized memory for community use, do not copy the private tree or hand-curate an undocumented subset. Inventory the canonical source directory as a closed world: every source is either included or excluded with a stable reason. For every included module preserve source and content hashes, schema/version, tags and sanitization receipt; gate names, handles, email, private paths, credentials, private raw assets, un-anonymized outcomes and re-identifiable events with positive and negative fixtures. The pack reader must be bounded and paged so an Agent selects only relevant modules. A privacy-green pack still does not replace current-Skill provenance, source-media evidence, human review or rights evidence.

If the orchestrator directly mentions downstream Skills, derive that dependency set from the current canonical bytes and compare it against a stable integration ledger. Require exactly one row per current dependency, no stale rows, installed-source evidence, an explicit mode such as native-plus-dynamic／dynamic-latest／external fallback, and a replayable gate. A static dependency count is not freshness evidence.

Keep a large public knowledge pack out of the browser startup graph. Audit that the full pack is reachable only through a bounded server／MCP reader while the main UI imports a compact summary bound to the full-pack hash. Expanded preset/template registries and heavyweight builders should form on-demand chunks whose real preview/edit journeys are tested. Preserve fixed main JS, gzip and CSS budgets; raising the budget, deleting discoverability, or loading the whole pack merely to compute a summary is not a performance fix.

## Model and context boundary

- Sol／Terra／Luna、reasoning effort、temperature 或 prompt 格式都是 invocation provenance，不能替代 schema、negative gate、executor receipt 或人審。
- Markdown router 可以是 bounded handoff 的可讀層，但執行真相必須是 versioned JSON contract；兩者以 SHA-256／schema 綁定，不能各自漂移。
- 每個 model × effort cell 在 frozen same-provenance benchmark 完成前維持 `unmeasured`。官方產品定位或單次好結果不能關閉品質、Token、延遲或市場優勢宣稱。
- 不論模型等級，current schema、rights、安全、truthfulness 與 semantic audit 都不得 bypass。缺 project-native model matrix／receipt 時，跨模型品質標 `NOT_CHECKED model-quality-evaluation`。

## Semantic handoff and legacy compatibility

Audit the handoff as a semantic contract, not only a parseable command envelope. Build one closed-world list of fields required by the promised workflow and verify positive plus negative fixtures for each risk-bearing family. For an editorial pipeline this may include source/knowledge receipt, brief, promise/stakes/payoff, ordered energy beats, packaging hypotheses, caption/graphics separation, motivated transition evidence, layered audio, quality state, current artifact and outcome checkpoints.

If current and legacy schemas coexist:

- declare both identities and name the current schema explicitly;
- mark legacy execution as compatibility only;
- require every flow claimed current to record the current schema in its receipt;
- reject a gate that closes current parity merely because the legacy plan still parses or edits a file;
- keep missing semantic families visible even when a generic command array succeeds.

A stable capability ledger may use integration levels such as `native_verified`, `contract_enforced`, `orchestrator_handoff`, `unmeasured` and `blocked_external`. Verify the meaning of each level, not just spelling: native needs same-version product evidence, contract needs calibrated rejection fixtures, orchestrator needs a versioned handoff, unmeasured needs a next experiment, and external needs an actionable blocker.

## Market and “complete” claims

Audit market leadership separately from internal product readiness. Require baseline × surface cells, frozen versions, same inputs/brief, independent truth, minimum samples, device/environment receipts, serious-error rate and Token/API cost. Instrument GREEN with zero measured cells proves honest reporting only. It must remain an open parity obligation and cannot be summarized as “won”.

Price does not erase redistribution or security obligations. A free community installer still needs per-item rights for music, SFX, fonts, stock, models and generated/source assets; internal owner-only evidence cannot close that public/community edge.

For licensed or community assets, audit rights metadata as an end-to-end semantic invariant: pack manifest → library listing → verified resolver → UI/MCP import adapter → persisted project asset → render/delivery receipt. A manifest with zero restricted files is still a false green when an adapter drops `license`, `provenance`, `rightsBasis` or `redistributable`; require a delivered journey and a negative fixture that catches the loss.

## Batch fan-out and editable re-entry

Do not treat multi-file selection, repeated function calls or concatenation onto one timeline as batch-product evidence. For a promised batch workflow, audit a closed-world one-to-one mapping from each source or explicit group to a stable durable job, isolated editable project, delivered render and machine-readable receipt. Every receipt should bind source identity/hash before and after processing, current schema, planner/inference provenance, warnings, review state and output hashes.

Require task-shaped negative evidence: one corrupt input does not stop sibling jobs; retry changes only the failed job; an interrupted `running` job recovers safely after restart; unsafe IDs and shared writable output paths are rejected; original media remains byte-identical; machine preview cannot set human approval; and `PUBLISHED` artifacts remain immutable without an explicit correction workflow. Finally, reopen one delivered project in the normal editor, perform an undoable edit and save it. Unit fan-out without delivered UI/runtime re-entry remains `NOT_CHECKED batch-workflow-integration`.

## Professional media workstation contract

Treat professional Timeline, typography, color and director-console claims as four independent end-to-end flows. A module, control or synthetic planner test proves only component presence.

### Creative library previews and native automatic composition

- Audit source pack → closed-world manifest/rights → packaged bytes → runtime resolver → visible preview → apply command → persisted editable graph → Undo/Redo → decoded render. A card count, label, hidden option, generic gradient, or source-only screenshot is a false green for B-roll, music, Look, effect, transition, caption, title/card/tag or text-animation preview claims.
- Audit long-source repurposing as `source hash → evidence-backed editorial-unit map → expected N → N distinct project identities → N distinct decoded outputs → N receipts`. Do not infer N from file count. Reject a one-compilation fallback, duplicated source ranges, a receipt count that only mirrors an array length, and a “recut” whose editorial fingerprint equals its baseline. Prior Skill/product outputs are benchmark-only unless an independent human/evidence protocol labels them.
- Separate preview existence from discoverability. If a beginner must already know which clip／caption to select and then open a generic “more／advanced” disclosure before any preview category is named, record component presence only. Beginner readiness needs a directly visible entry whose copy names the available families, a fresh-profile journey that reaches real preview cards without documentation, and a permanent way to reopen guidance after first-run dismissal.
- For lazy preview surfaces, require the delivered journey to activate every claim-critical chunk and exercise real image/video/audio decode plus animation. Main-bundle shrinkage that hides missing functionality, installer omission, load failure, or unbounded total optional bytes is not optimization.
- Audit one-click editing as one atomic composition contract, not as a bag of available modules. Applicable families—semantic cuts, editable caption design, rhythm, music/ducking, Look/effect/transition, graphics and tracking—must each be selected, explicitly skipped, or blocked with provenance. Require one Undo boundary, save/reopen, a normal manual edit and decoded output. Tracking pipeline presence must not silently promote tracking quality.
- The automatic-editing entry must explain its prerequisite and next action in the default workspace. A disabled button without a reason, a demo asset mistaken for user footage, or instructions available only in external documentation is a beginner-flow failure even when the native planner works.

### Timeline interaction

- A domain-command or interval-query benchmark cannot close editor fluidity. Require a frozen large-project topology, viewport-query latency, materialized DOM/node count, pointer/keyboard input-to-visible-state latency, Undo/Redo latency, scroll/zoom/scrub behavior and a delivered editor journey.
- Record p50 and p95 on the same isolated host with warmup/sample policy. Keep render throughput, planner speed and UI interaction as separate metrics.
- Virtualization is verified only when offscreen clips are not materialized and zoom/scroll preserve selection, playhead, marker and edit semantics. If the UI surface was never activated from the extracted product, mark `NOT_CHECKED professional-timeline-interaction`.
- Audit the whole pointer stream, not one changed coordinate: press → multiple distinct moves → release must keep receiving events, produce visible compositor updates for every sampled move, and create exactly one canonical command on release. Styling that removes hit testing or loses pointer capture after the first frame is a functional failure even when a pure drag calculator is sub-millisecond.
- For edge trim, require start-edge movement to preserve the original Timeline end while updating source and Timeline starts on the same frame grid; end-edge trim preserves Timeline start. Opposite-edge drift, zero-duration output, silent outward extension or a trim-plus-move recorded as two Undo steps is a product-flow failure.
- Prefer transient transform／scroll state during movement and one EditGraph/history commit at release. Re-rendering the canonical graph on every pointer move is a responsibility/performance hotspot; moving gesture plumbing into C++／Rust／GPU does not close a missing-event defect.
- Treat the track header／label column, toolbar, locked lanes, incompatible track kinds and space outside lane content as explicit negative drop regions. The delivered journey must drag a real clip into each applicable boundary, show an invalid affordance, keep the clip visually out of the forbidden region and prove the canonical start／track is unchanged after release. Falling back to the source lane while still committing horizontal movement is a functional failure, not graceful recovery.
- Deletion semantics are part of the editor contract. For ripple delete, remove one middle clip from the primary story track, shift the declared downstream synchronized set by exactly the removed duration, leave unrelated／locked content according to an explicit policy, and require one Undo to restore the complete pre-delete graph. A command named `delete` or an empty-gap cleanup button does not prove automatic gap closure.

### First-source geometry

- Exercise the real delivered file-input／drop path with portrait, landscape and near-square fixtures. Read decoded metadata, choose the declared canvas, fit the preview, persist the project resolution and verify render geometry. A unit-tested aspect-ratio helper cannot close import integration.
- A whole-window drop overlay is discoverability evidence only. On desktop, dropped native paths and picker results must share validation, media probing, durable source identity, cache preparation, starter replacement and editable Timeline insertion. A browser `File`／object URL fallback that cannot survive save/reopen must not be promoted as the native drop workflow; unsupported files also need visible rejection rather than silent disappearance.
- Distinguish a bundled starter placeholder from user content. The first real visual source may replace the starter and establish the canvas at time zero; a later import must not silently override an explicit user canvas choice. If placeholder assets make `project has visual media` true and block first-source inference, report a product-flow failure.

### Bundled typography

- Preserve per-font license, provenance, version/hash and redistribution scope through source pack → build inventory/SBOM/notices → extracted closed-world payload → runtime font resolver → exported frame.
- Do not assume a font engine recursively scans nested directories. Exercise the exact export adapter and retain its font-selection log or equivalent evidence. A successful export that silently falls back to a system font is a negative result, not a pass.
- Require a missing-font/fallback fixture and one actual render whose selected family comes from the delivered pack. Font files merely present in an installer remain `NOT_CHECKED bundled-font-export`.

### Color pipeline

- Verify source color metadata and explicit handling for known SDR, HLG and PQ inputs. Unknown Log footage must fail closed or require an explicit input transform; guessing a camera Log curve is not professional behavior.
- Preserve one documented order such as input normalization → primary grade → one selected look → graphics/output transform. Reject duplicate look/LUT application and preview/export order drift.
- Scopes must sample real source or rendered pixels. A source-frame waveform/vectorscope is useful diagnostic evidence but cannot close decoded-output correctness, HDR delivery or calibrated-reference-display parity. Require actual frame differences, decoded media validation and negative controls for unsupported transforms.

### Director review state

- Persist timecode markers, notes, assignments and review state inside the current project schema; verify save/reopen and Undo/Redo through the normal delivered editor.
- Separate machine states (`draft`, `ready_for_review`, automated warnings) from human assertions (`approved`, `certified`). No automation or smoke test may create human certification without authenticated human action and an audit receipt.
- Multi-user sync, live switching and real control-room latency remain separate obligations; a local notes panel does not close them.

### Decoded overlay visibility and evidence preservation

- Motion-graphic rows, non-empty tracking points, renderer exit 0 and editable graph state are component evidence only. For every claim-critical title/card/tag/HUD, sample decoded output near entrance, middle and exit; require readable pixels, declared safe-area containment and stable visibility while the bound subject moves. A per-sample fade that keeps a tracked label translucent, an anchor that goes off-screen, or a same-color outline that disappears on the footage is an integration failure even when tracking loss is zero.
- Calibrate the artifact evaluator with task-shaped negatives for repeated fade/flicker, off-screen placement and insufficient foreground/background contrast. The negative must operate on decoded frames or renderer output, not merely inspect style properties; a hex color or opacity value cannot prove visibility after composition and encoding.
- Automatic cleanup must carry semantic preserve ranges from the current plan into execution receipts. Silence, low optical flow and long static composition are only features, never universal deletion rules. When a domain uses waiting or decay as evidence—such as a spinning-top endurance result—the applied project and decoded artifact must retain the declared range within frame tolerance, and a missing-range fixture must fail before completion is claimed.
- Final audio acceptance reads the encoded artifact. Source gain, mix-bus settings or a sample-peak limiter do not prove AAC/platform true-peak safety; retain decoded integrated loudness, loudness range and true peak plus a negative fixture that exceeds the declared ceiling.

## Non-blocking desktop background jobs

Treat a long native IPC call as a UI-performance edge, not only a service-integration edge. Update checks, downloads, model setup, analysis and renders must not hold the WebView or main thread until a child process exits. Prefer a small immediate `checking`／`queued`／`downloading` acknowledgement, background execution, and bounded event or polling settlement into an explicit terminal result.

Audit the slow and failed paths, not only a fast localhost response. While the backend is delayed, verify that Timeline input, preview controls and a new UI-state probe still respond within budget. Require duplicate-job coalescing, atomic result publication, a timeout that settles rather than polling forever, and a retry that cannot consume a stale result from a different mode. A service log showing “returned successfully” while the UI cannot accept another command is `NOT_CHECKED non-blocking-desktop-job`, not a pass.

Desktop WebView lifecycle acceptance must use an owned real navigation/close plus dialog handling. Do not call `dispatchEvent(new Event("beforeunload"))` inside a long CDP journey: embedded WebViews may treat it as an actual lifecycle transition and intermittently clear the document. Extract the dirty-state guard into a deterministic unit, retain real Autosave evidence in the delivered journey, and keep true close/navigation behavior `NOT_CHECKED` until exercised through the native lifecycle protocol.

Nested delivered runners must preserve the first journey/build failure. A timeout must terminate and await the exact owned process tree before deleting its extracted workspace; cleanup errors are secondary diagnostics and may not replace the primary stdout/stderr/exit evidence. Retry loops need a wall-clock deadline in addition to per-probe timeouts—`attempts × probe timeout` is the real worst case, so a nominal two-minute loop must not silently run for tens of minutes.

Delivered journeys must isolate recovery files, batch sessions, update caches, trusted-device stores and other persistent test state from the user's real application directories. Replay the same journey twice: a prior Autosave／modal／device credential must not block or change the second run. For CDP／WebDriver controllers, bind each pending command to its owning connection; closing a timed-out socket must not reject requests already issued on a replacement connection. A frozen automation channel is not a product freeze until an independent UI or service probe reproduces it.

Treat configured raw and compressed bundle-byte ceilings as exact hard gates. One byte over is still over: deduplicate or restructure the implementation and rebuild; do not raise the budget solely to erase a regression or cite gzip success as a substitute for an exceeded raw-byte limit.

## Session-native AI tool products

When a desktop product promises that users can control it from their own Codex／Claude session, audit three identities independently: the AI host/session that owns inference and subscription usage, the local MCP process that exposes product tools, and the product runtime that mutates durable state. A local STDIO MCP does not need the editor to collect an AI API key; finding `OPENAI_API_KEY`／`ANTHROPIC_API_KEY` fields, provider tokens or copied subscription credentials in the editor, installer, logs or receipts is a security and responsibility smell.

Tool-list presence is not material understanding. Require one same-source journey:

1. a local analysis packet binds clip／asset identity and source SHA-256;
2. the session receives real keyframes as MCP image content, not paths or prose claiming what the frame contains;
3. transcript access is time-windowed and bounded;
4. semantic segments cite existing frame IDs or transcript cue IDs;
5. the structured edit plan binds the semantic receipt and current source identity;
6. stale source, missing evidence and forged receipt negative fixtures fail before atomic Timeline mutation;
7. the applied project remains editable, Undoable and renderable.

Treat scene detection, tracking and motion analysis that inspect decoded frames locally as separate from the smaller representative keyframe set shown to the model. Do not claim the model viewed every frame merely because the local decoder did. Computer Use is fallback evidence only when no structured product tool exists; stepwise UI clicking cannot close a promised low-latency／low-Token structured flow.

One-click onboarding needs an isolated real host-config fixture, not only a generated command string. Exercise current Codex and Claude CLI shapes with temporary `CODEX_HOME`／`CLAUDE_CONFIG_DIR`, assert STDIO command/args/env identity, and prove no AI secret is written. On Windows, paths containing spaces must survive npm `.cmd` shims; prefer resolving the shim's trusted executable/script and passing an argument array. Claude's variadic `--env` parsing may consume the server name across versions; a validated `mcp add-json` payload is the safer multi-variable adapter. Missing CLI should produce a bounded, inspectable copy-command fallback rather than silent success.
