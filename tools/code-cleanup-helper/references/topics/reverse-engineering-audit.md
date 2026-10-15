# Reverse analysis and release exposure

- `cleanup.reverse.scope`: identify the authorized target, exact shipped bytes/hash, question, host, provider/version, and static versus runtime activity. A repository URL does not authorize executing or modifying another application.
- `cleanup.reverse.evidence`: source inspection, recovered pseudocode, inferred call edges, and observed runtime behavior are separate evidence classes. Missing native engines, obfuscation, parser errors, exclusions, and truncation remain NOT_CHECKED.
- `cleanup.reverse.exposure`: run `scripts/check_release_exposure.py <delivered-file-or-directory>` for bounded, non-executing triage of private paths, credential-shaped bytes, debug symbols, source maps and PE flag declarations. Findings are candidates for review; compressed/unread payloads remain gaps. No finding is not proof of secrecy.
- `cleanup.reverse.defense`: evaluate server-owned authority/secrets, release-only symbols, source-map access, minimal client data, signed updates, and platform mitigations independently. ASAR, minification, encryption keys shipped with the client, or an anti-debug switch cannot establish resistance to all reverse engineering.
- `cleanup.reverse.privacy`: retain recovered third-party code and raw tool evidence locally. Public learning contains generic contracts and owned regression fixtures, with provenance and license boundaries.

Use R&D's reverse-analysis workflow for optional REA provider discovery and experiments. Cleanup reads evidence; it does not install a provider, launch a target, bypass licensing, or reconstruct a product.
