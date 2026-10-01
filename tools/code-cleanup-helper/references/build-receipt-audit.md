# Build receipt freshness audit

Use this read-only check when a repository produces installers, desktop binaries, generated frontends, native helpers, model bundles, media packs, or other files that can silently remain stale while source tests pass.

## Boundary

Cleanup verifies only that declared live input and output bytes still match a receipt. It does not claim that an installer contains the right payload, that the delivered executable is the build-directory executable, or that the product launches. Those are delivery-lifecycle claims owned by the product evaluator and the R&D delivery gate.

For two live catalogues that must stay paired by filename identity—such as generated product ads and preserved supplier references—use `artifact_set_assertions` in `audit.config.json`. A receipt protects a build's declared input/output bytes; an artifact-set assertion protects closed-world membership and one-to-one pairing. Neither replaces content review or runtime browser acceptance.

For code-split frontends, output inventory must enumerate the entire emitted directory, including every hashed lazy JavaScript and CSS chunk. Tracking only `index-*` makes a smaller main bundle a false optimization because optional features can silently grow, disappear from the installer, or go stale. A delivered-product journey must activate each claim-critical lazy surface at least once and verify its usable controls, not merely observe that the initial shell launched.

For media-editor catalogues, treat preview chunks and their referenced thumbnails／audio／video／font assets as claim-critical outputs. Activation evidence must exercise real media decode, hover/play or animation behavior, failure UI, one apply action, and persistence into the editable project; counting emitted chunks or DOM cards is insufficient. Track main, compressed main, total lazy, and per-surface bytes separately so code splitting cannot turn a hard startup budget into hidden unbounded download or omit a surface from the delivered payload.

Large immutable resource packs may keep a compact signed／hashed manifest in the build receipt when duplicating hundreds of binary entries would make the receipt impractical, but only if the product delivery evaluator separately compares the extracted pack against the live source pack as a closed world. That comparison must reject missing, unexpected and identity-mismatched files and validate the manifest's count, scope and redistribution flags. Manifest-only freshness never proves payload presence.

Bundled font packs are release inputs, not decorative source assets. Inventory every font and license (or a closed-world manifest covering them), include the pack in SBOM/notices, and compare the extracted installer pack against the source pack. This still does not prove the export stack selects those fonts: retain an actual renderer font-selection trace and a missing-font/fallback negative fixture. Font directories may be non-recursive in native renderers, so a nested layout that only succeeds via system fallback is not a fresh or correct typography delivery.

## Receipt schema

Store a project-relative JSON receipt with schema version 1 and non-empty `inputs` and `outputs` arrays. Every entry has a canonical repo-relative POSIX path, byte count, and lowercase SHA-256:

```json
{
  "schemaVersion": 1,
  "inputs": [{"path": "src/app.ts", "bytes": 123, "sha256": "...64 hex..."}],
  "outputs": [{"path": "dist/app.js", "bytes": 456, "sha256": "...64 hex..."}]
}
```

The checker rejects traversal, absolute or backslash paths, symlinks, missing files, malformed identities, case-insensitive duplicates, input/output overlap, and stale input or output bytes.

```powershell
$env:PYTHONUTF8='1'
python scripts/check_build_receipt.py <project-root> --receipt <repo-relative-receipt.json> --format json
python scripts/check_build_receipt.py --self-test
```

## Promotion semantics

- A green receipt means only that its listed bytes are current.
- The project-native generator remains responsible for closed-world enumeration; a hand-written subset is not completeness evidence.
- Recreate the receipt only through the canonical build. Never refresh hashes after a failure without rebuilding and rerunning correctness gates.
- Restricted or owner-only assets may be valid for an internal delivery while remaining blocked for public redistribution. Keep those two obligations separate and verify the restriction metadata again inside the extracted installer; never let an internal artifact pass promote a public-license claim.
- For release promotion, pass the product evaluator report to `run-benchmark-driven-rd/scripts/delivery_contract_gate.py`. The delivered envelope and extracted payload remain authoritative.
