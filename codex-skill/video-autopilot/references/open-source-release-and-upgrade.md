# Open-source release and upgrade contract

Read this file completely before building, publishing, installing, upgrading or rolling back the
public kit.

## Ownership boundary

`release-manifest.json` is the sole allowlist. A release contains executable framework code,
documentation, empty templates, synthetic examples and separately licensed public assets. It does
not contain user media, credentials, analytics, profiles, local outcome memory, generated projects,
private assets or machine-specific paths.

The updater owns only paths in the prior `release-index.json`. It may replace these paths or retire
them in a later release after backup. It must leave every unknown path untouched.

Protected paths include `config.py`, `profiles/`, `projects/`, `data/`, `videos/`, `assets/`,
`channel_state.json`, `outcomes/`, `.video-autopilot/` and `*.local.*`. A package containing one of
these paths is invalid.

## Build a release

1. Update `release-manifest.json` version and compatibility window.
2. Add the release notes to `CHANGELOG.md`.
3. Run `python src/system_health.py --quick` and relevant full media tests.
4. Run `python src/release_manager.py selftest`.
5. Build with the immutable release URL:

   `python src/release_manager.py build --base-url https://github.com/Hao0321/video-autopilot-kit/releases/download/vX.Y.Z`

6. Verify the generated archive, `.sha256` file and `release-channel.json`.
7. Upload all three as release assets. `release-channel.json` must also be attached so the stable
   `releases/latest/download/release-channel.json` URL resolves.
8. Do not publish until privacy, licensing, portability and migration checks are green.

The builder creates a deterministic zip, a per-file SHA-256 index and a channel manifest. The
updater verifies both the archive hash and every indexed file before touching an installation.

## Install or upgrade

- New or legacy copy:
  `python install_or_upgrade.py --install-root <folder> --apply --install-skill`
- Pre-updater folder without the bootstrap: download
  `https://github.com/Hao0321/video-autopilot-kit/releases/latest/download/install_or_upgrade.py`,
  run `--check`, then explicitly run `--apply`. Automatic mode never adopts a non-empty unmanaged
  folder.
- Preview only:
  `python install_or_upgrade.py --install-root <folder> --check`
- Normal managed copy:
  `python src/release_manager.py update --install-root <folder> --apply`
- Non-blocking compatible auto-update:
  `python src/release_manager.py auto --install-root <folder>`

Automatic updates are limited to the declared compatibility window and an explicit idempotent
migration row. Unknown/unversioned legacy copies are allowed only through one confirmed bootstrap.
Major or incompatible versions return `CONFIRM_REQUIRED`.

## Transaction and rollback

Before replacement, managed files are copied to:

`.video-autopilot/backups/<UTC transaction>/files/`

The transaction ledger records created, replaced and retired files. Any exception during apply
triggers immediate rollback. Manual rollback uses:

`python src/release_manager.py rollback --install-root <folder>`

Unknown custom files and protected paths are not part of the transaction.

## Codex Skill synchronization

`python src/release_manager.py install-skill` synchronizes the public Skill to
`~/.codex/skills/video-autopilot`. It writes `.video-autopilot-skill.json` and may retire only paths
listed as managed by that marker. If an existing destination has no marker, the command returns
`ADOPT_REQUIRED`; use `--adopt` only after reviewing that destination.

## Failure policy

- Network/channel check failure is non-blocking and cached.
- Hash mismatch, unsafe zip path, protected path, wrong project ID or incompatible automatic update
  is fail-closed.
- Editing work must continue when only the update channel is unavailable.
- Never weaken integrity checks to make a release install.
