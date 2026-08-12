# Architecture Foundation v6.3

## Contents

1. Ground rule
2. Dependency direction
3. Cleanup-first R&D loop
4. Compatibility and rollback
5. What the gate proves

## 1. Ground rule

Architecture changes start from evidence, not folder aesthetics. Preserve the public CLI/import surface, isolate one responsibility at a time, and promote only after correctness, health, architecture, sync, install and upgrade gates pass.

## 2. Dependency direction

The asset subsystem is the first enforced vertical slice:

`asset foundation → asset query → asset application → compatibility facade`

- Foundation: paths, taxonomy, usage persistence, index migration, shared value helpers.
- Query: catalog ingestion and asset selection.
- Application: `AssetRegistry` and write-side orchestration.
- Compatibility: `asset_memory.py`, which preserves historical imports but owns no data logic.

Lower layers cannot import the registry application boundary. New subsystems should adopt the same policy/domain → application → adapter/interface direction without moving files merely for appearances.

## 3. Cleanup-first R&D loop

1. List the failure classes required for the proposed refactor.
2. Run Cleanup self-test plus task-shaped positive and negative fixtures.
3. If Cleanup cannot observe a required failure, improve Cleanup first and add a regression fixture.
4. Freeze evaluator SHA, config SHA and report schema; preserve the raw baseline.
5. Refactor behind a stable facade.
6. Re-run the identical evaluator and functional gates.
7. Record the architecture decision, failures and transferable rule in `.rd/`.

Warning-size functions are `REVIEW`, not automatic failures. Severe findings block unless a bounded exception contains a semantic reason, maximum size and expiry date; even then the debt remains visible as `REVIEW`.

The quality evaluator is itself production infrastructure. Its denominator is the sum of the current checks' maximum points, never a hard-coded historical total. JSON commands emit one document with no trailing human text. A new check must include a regression proving that one failed check lowers the normalized score; otherwise the new metric is not trusted.

## 4. Compatibility and rollback

- Existing imports and commands stay additive until a migration and deprecation window is documented.
- Runtime/user media are never touched by a source refactor.
- A compatibility facade delegates to the new implementation and must not regain business logic.
- Rollback is the previous module set plus the preserved before-report and manifest version.

## 5. What the gate proves

The AST gate proves only parsed Python import edges, configured layer rules, SCC cycles, static hotspots, duplicate bodies and function-size classification. Dynamic imports, plugin registries, subprocess/file protocols, cross-language calls, runtime data ownership and visual quality require separate evidence. A green architecture gate is necessary, never sufficient, for a release.

## 6. Release sequence

The enforced order is: calibrate Cleanup → baseline → refactor → architecture gate → functional and health gates → private/installed sync → public package install/upgrade test → release evidence. If Cleanup changes mid-run, log it as a measurement experiment and do not compare old and new counts as the same metric.
