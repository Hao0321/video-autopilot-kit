# Maintainer-only operations

Read this file only when modifying, releasing, or diagnosing Code Cleanup Helper itself.

## Dedicated checks

```powershell
python scripts/check_links.py <target>
python scripts/check_drift.py <target>
python scripts/check_sync.py <target>
python scripts/check_build_receipt.py <target> --receipt <repo-relative-receipt.json> --format json
python scripts/check_audit_snapshot.py <before-report.json> <after-report.json> --format json
python scripts/check_skill_revision.py capture --root <active-private-skill-root> --output <revision.json> --quiet
python scripts/check_skill_revision.py verify --evidence <revision.json>
python scripts/check_context_budget.py <skill-root> --manifest <skill-root>/profiles/context-budget.json
python scripts/self_test.py
```

New deterministic checks start with calibrated positive and negative fixtures. Context manifests gate both each file and aggregate route in UTF-8 bytes plus exact `o200k_base` Tokens; an unavailable tokenizer is blocking `NOT_CHECKED`, never PASS. JSON CLIs emit one parseable document; score denominators derive from live maximum points. Project-specific thresholds, expected counts, and paths belong in the target repo `audit.config.json`, not the shared engine.

For concurrent edits, re-read canonical private bytes and apply context-sensitive patches. Public sync is private → public only, requires a managed manifest/privacy preflight, strict promotion, sync check, and same-revision replay of dependent product promotions. Cleanup never commits, pushes, publishes, signs, or deletes releases; an explicitly authorized R&D external-change gate owns those mutations.

After metadata changes, run skill-creator `quick_validate.py`. Keep source and packaged artifacts separated; generated evidence directories must not pollute the audited inventory.
