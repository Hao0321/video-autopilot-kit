# Architecture Foundation v7.0

## Contents

1. Ground rule
2. Dependency direction
3. Cleanup-first R&D loop
4. Compatibility and rollback
5. What the gate proves
6. Artifact lifecycle and publishing control plane
7. Public workspace migrations

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

## 6. Artifact lifecycle and publishing control plane

A generated video is not complete merely because a render exists.  The closed-world delivery transaction is:

`canonical current.mp4 → technical QA → human-review state → publishing package → registry/index verification`

- `Build` must call the publishing application boundary after QA; the dependency is a required architecture edge.
- Every completed `current.mp4` must resolve to exactly one publish package with the same SHA-256 and canonical source path.
- A package audit that only validates packages which already exist is insufficient; orphan outputs and stale packages are release blockers.
- Published packages are immutable.  Rebuilding the same content ID with a different hash requires an explicit correction or a new content ID.
- Unpublished packages may move between `review` and `ready`, but status changes must relocate the one package instead of creating another copy.
- `_out/current.mp4` remains the working source.  The human-facing entry is the root shortcut and `videos/_PUBLISH_HUB/START_HERE.md`; package media uses hardlinks when possible, so discoverability does not double storage.

## 7. Public workspace migrations

Managed source updates and user workspace migrations are separate ownership domains:

- the updater may replace only release-manifest-owned code after checksum, compatibility, backup and rollback gates;
- media, profiles, credentials, analytics and unknown files remain protected;
- a versioned workspace migrator may add missing publishing structure and generated indexes, but it never deletes or overwrites user media;
- automatic migrations must be idempotent and pass clean-install, compatible-upgrade, second-run no-op, local-modification protection and rollback fixtures;
- unversioned legacy installs require one explicit adoption before automatic updates take ownership of managed code.

## 8. Release sequence

The enforced order is: calibrate Cleanup → baseline → refactor → architecture gate → functional and health gates → private/installed sync → public package install/upgrade test → release evidence. If Cleanup changes mid-run, log it as a measurement experiment and do not compare old and new counts as the same metric.
