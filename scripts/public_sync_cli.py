"""Command and fixture boundary; host globals remain explicitly injected."""
from __future__ import annotations

def _parse_sync_arguments(_host):
    parser = _host['argparse'].ArgumentParser(description=_host['__doc__'])
    parser.add_argument("--canonical", type=_host['Path'])
    parser.add_argument(
        "--repository", type=_host['Path'], default=_host['Path'](_host['__file__']).resolve().parents[1]
    )
    parser.add_argument(
        "--distribution-source", type=_host['Path'],
        help="public-kit source used to seed explicit public-owned files",
    )
    parser.add_argument("--check", "--dry-run", dest="check", action="store_true", help="report drift without writing the target repository")
    parser.add_argument(
        "--verify-receipt", action="store_true",
        help="verify the committed public sync receipt without a private canonical tree",
    )
    parser.add_argument(
        "--self-test", action="store_true", help="run public privacy negative fixtures"
    )
    args = parser.parse_args()
    return args, parser


def _check_sync_drift(_host, canonical, repository, distribution_source) -> int:
    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-sync-") as temp:
        staged = _host['Path'](temp) / "repository"
        expected = _host['sync'](canonical, staged, distribution_source)
        boundary_violations = _host['_output_path_boundary_violations'](
            repository, expected
        )
        drift = [
            name for name in expected
            if name not in boundary_violations
            and (
                not (repository / name).is_file()
                or _host['_text_sha256'](staged / name) != _host['_text_sha256'](repository / name)
            )
        ]
        drift[:0] = [
            _host['_boundary_error'](relative, rule)
            for relative, rule in sorted(boundary_violations.items())
        ]
    if boundary_violations:
        # Avoid reference scans and manifest validation on a tree already
        # proven to contain an escaping alias.
        print("SYNC DRIFT: " + ", ".join(drift[:30]))
        return 1
    stale_references = _host['_unexpected_public_references'](repository)
    private_files = _host['_unexpected_private_public_files'](repository)
    destination_errors: list[str] = []
    destination_manifest = repository / "release-manifest.json"
    if not destination_manifest.is_file():
        destination_manifest = (
            distribution_source or _host['Path'](_host['__file__']).resolve().parents[1]
        ) / "release-manifest.json"
    try:
        _host['validate_public_destination'](repository, destination_manifest)
    except ValueError as exc:
        destination_errors.append(str(exc))
    if drift or stale_references or private_files or destination_errors:
        details = list(drift[:30])
        details.extend("stale-reference:" + name for name in stale_references[:30])
        details.extend("private-public-file:" + name for name in private_files[:30])
        details.extend("destination:" + error for error in destination_errors)
        print("SYNC DRIFT: " + ", ".join(details))
        return 1
    print(f"SYNC GREEN: {len(expected)} redistributable text files")
    return 0


def main(_host) -> int:
    args, parser = _host['_parse_sync_arguments']()
    repository = args.repository.resolve()
    if args.self_test:
        _host['_self_test_public_privacy']()
        _host['_self_test_reserved_public_marker']()
        _host['_self_test_public_owned_lf']()
        _host['_self_test_text_hash_portability']()
        _host['_self_test_output_path_boundaries']()
        _host['self_test_public_renderers'](repository)
        _host['self_test_public_inventory'](repository)
        _host['_self_test_receipt_schema'](repository)
        return 0
    if args.verify_receipt:
        errors = _host['_verify_sync_receipt'](repository)
        if errors:
            print("SYNC RECEIPT RED: " + "; ".join(errors[:30]))
            return 1
        receipt = _host['json'].loads((repository / _host['SYNC_RECEIPT_PATH']).read_text(encoding="utf-8"))
        print(f"SYNC RECEIPT GREEN: {receipt['output_count']} hashed outputs")
        return 0
    if args.canonical is None:
        parser.error("--canonical is required unless --self-test or --verify-receipt is used")
    canonical = args.canonical.resolve()
    distribution_source = (
        args.distribution_source.resolve() if args.distribution_source else None
    )
    _host['_assert_public_workflow_derivation'](canonical, distribution_source or _host['Path'](_host['__file__']).resolve().parents[1])
    if args.check:
        return _check_sync_drift(_host, canonical, repository, distribution_source)
    copied = _host['sync'](canonical, repository, distribution_source)
    print(f"SYNC APPLIED: {len(copied)} files")
    return 0
