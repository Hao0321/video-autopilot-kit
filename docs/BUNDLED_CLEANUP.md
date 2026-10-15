# Bundled Code Cleanup

The Kit includes Code Cleanup v0.22.1, upstream commit
`7097840737035007989dd9fc564dcc65df5e23bb`.

All 70 public upstream files are included, including the complete self-test,
publication safety, state integrity and release exposure dependencies. The Kit
adds portable defaults and `tools/code-cleanup-helper/BUNDLE.json`, which records
the upstream identity and normalized text hashes. Maintainer paths and privacy
settings are removed from the local defaults.

From the Kit directory:

```text
python tools/code-cleanup-helper/scripts/self_test.py
python tools/code-cleanup-helper/scripts/audit.py src --mode all --format json
python scripts/sync_canonical.py --verify-receipt --repository .
```

On macOS, `python src/system_health.py --quick` selects a physical temporary
root for child fixtures. When running the upstream self-test directly, set
`TMPDIR` to a physical path: its publication controls deliberately reject
linked ancestors, including aliases in a system temporary path. Caller-supplied
publication roots retain the same link/reparse checks.

The public synchronization step compares its explicit inventory with the
canonical provider's own publication policy before writing. A newly added
upstream file or changed upstream source blocks synchronization until the
inventory and release pin are refreshed. Cleanup source is copied without the
video-specific text transformations. The receipt verifier also checks the
bundled provider's version and hashes.

Cleanup is a read-only audit provider. A successful source/self-test check does
not certify a rendered video, external service, installer or release.

The full health command includes install, repair, upgrade and rollback fixtures.
Those checks use the existing slow-test category with a 20-minute per-command
timeout; ordinary checks retain seven minutes. Quick health skips slow fixtures.
The longer harness timeout does not change validation rules or claim a measured
installation speed.
