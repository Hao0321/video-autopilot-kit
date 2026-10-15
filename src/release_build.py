"""Command and fixture boundary; host globals remain explicitly injected."""
from __future__ import annotations
from pathlib import Path
from typing import Optional, Iterable

# Runtime review bundles are local capabilities, not release source.  Keep a
# built-in floor so an accidental manifest edit cannot weaken this boundary.
# Root and nested forms are both listed because ``fnmatch`` does not treat the
# leading ``**/`` as optional for a file at repository root.
_PRIVATE_RELEASE_PATH_GLOBS = (
    "_review/**",
    "**/_review/**",
    "remote_session.json",
    "**/remote_session.json",
    "remote_delivery.json",
    "**/remote_delivery.json",
    "remote_daemon.stdout.log",
    "**/remote_daemon.stdout.log",
    "remote_daemon.stderr.log",
    "**/remote_daemon.stderr.log",
    "remote_tunnel.log",
    "**/remote_tunnel.log",
    ".codex/sessions/**",
    "**/.codex/sessions/**",
    ".codex/session/**",
    "**/.codex/session/**",
    "codex-remote-" "attachments/**",
    "**/codex-remote-" "attachments/**",
    "sessions/*.jsonl",
    "**/sessions/*.jsonl",
)


def _private_release_path_patterns(_host, manifest: dict) -> tuple[str, ...]:
    configured = manifest.get("privacy", {}).get("deny_path_globs", [])
    if not isinstance(configured, list) or not all(
        isinstance(pattern, str) and pattern.strip() for pattern in configured
    ):
        raise RuntimeError("release privacy path policy is invalid")
    return _PRIVATE_RELEASE_PATH_GLOBS + tuple(configured)


def _is_private_release_path(_host, relative: str, patterns: Iterable[str]) -> bool:
    """Match private artifact paths case-insensitively on every platform."""
    return _host['_matches'](relative.casefold(), (pattern.casefold() for pattern in patterns))


def _git_tracked_release_paths(_host, root: Path) -> Optional[set[str]]:
    """Return the checkout's tracked paths, or ``None`` for an exported tree.

    A real Git checkout is closed-world: an untracked file under a broad
    framework include must not silently become release payload.  Exported
    source trees have no ``.git`` metadata, so their fixed path/content privacy
    gates remain authoritative.
    """
    if not (root / ".git").exists():
        return None
    try:
        completed = _host['subprocess'].run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached"],
            capture_output=True,
            timeout=30,
        )
    except (OSError, _host['subprocess'].SubprocessError):
        raise RuntimeError("release tracking inventory is unavailable") from None
    if completed.returncode != 0:
        raise RuntimeError("release tracking inventory is unavailable")
    try:
        decoded = completed.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RuntimeError("release tracking inventory is invalid") from exc
    return {
        value.replace("\\", "/")
        for value in decoded.split("\0")
        if value
    }


def collect_release_files(_host, root: Path, manifest: dict) -> list[Path]:
    root = root.resolve(strict=True)
    includes = manifest["managed_include"]
    excludes = manifest["exclude_globs"]
    protected = manifest["protected_globs"]
    private_paths = _host['_private_release_path_patterns'](manifest)
    tracked_paths = _host['_git_tracked_release_paths'](root)
    found = []
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if not _host['_matches'](relative, includes):
            continue
        _host['_assert_contained_release_path'](root, path)
        if not path.is_file():
            continue
        _host['_assert_contained_release_path'](root, path, require_file=True)
        if _host['_is_private_release_path'](relative, private_paths):
            raise RuntimeError(
                "public privacy gate failed: private-runtime-artifact-path"
            )
        if _host['_matches'](relative, excludes):
            continue
        if tracked_paths is not None and relative not in tracked_paths:
            raise RuntimeError(
                "public privacy gate failed: untracked-release-candidate"
            )
        if _host['_matches'](relative, protected):
            raise RuntimeError("protected path entered release: " + relative)
        found.append(path)
    return sorted(found, key=lambda item: item.relative_to(root).as_posix())


def validate_release_tree(_host, root: Path, manifest: dict, files: list[Path]) -> list[str]:
    root = root.resolve(strict=True)
    errors = []
    if not _host['re'].fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", str(manifest.get("release_date", ""))):
        errors.append("release_date must be a deterministic UTC timestamp")
    if not manifest.get("migrations"):
        errors.append("at least one explicit migration declaration is required")
    included = {path.relative_to(root).as_posix() for path in files}
    for relative in manifest.get("required_paths", []):
        if relative not in included:
            errors.append("required release file missing: " + relative)
    deny_patterns = [
        _host['re'].compile(pattern, _host['re'].I)
        for pattern in manifest.get("privacy", {}).get("deny_text_patterns", [])
    ]
    privacy_gate = None
    privacy_gate_relative = manifest.get("privacy", {}).get(
        "semantic_gate", "scripts/public_privacy_gate.py"
    )
    try:
        privacy_gate_path = root / _host['_canonical_portable_relative'](
            privacy_gate_relative
        )
        _host['_assert_contained_release_path'](root, privacy_gate_path, require_file=True)
    except (TypeError, ValueError, RuntimeError):
        errors.append("public privacy gate path is unsafe or unavailable")
        privacy_gate_path = None
    if privacy_gate_path is not None:
        try:
            spec = _host['importlib'].util.spec_from_file_location(
                "_video_autopilot_public_privacy_gate", privacy_gate_path
            )
            if spec is None or spec.loader is None:
                raise RuntimeError("module loader unavailable")
            module = _host['importlib'].util.module_from_spec(spec)
            spec.loader.exec_module(module)
            privacy_gate = module.assert_global_public_text_safe
        except Exception as exc:
            errors.append("public privacy gate unavailable: %s" % type(exc).__name__)
    for path in files:
        try:
            _host['_assert_contained_release_path'](root, path, require_file=True)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        relative = path.relative_to(root).as_posix()
        text = ""
        is_text = path.suffix.lower() in _host['TEXT_EXTENSIONS'] or path.name == "LICENSE"
        if is_text:
            text = path.read_text(encoding="utf-8", errors="replace")
            if path == root / "release-manifest.json":
                # The manifest intentionally contains exclusion and deny-rule
                # declarations. Remove those policy fields before scanning so
                # a rule cannot recursively report its own pattern as leaked
                # data; the remaining manifest values are still inspected.
                sanitized_manifest = _host['read_json'](path)
                sanitized_manifest.pop("exclude_globs", None)
                sanitized_manifest.pop("protected_globs", None)
                sanitized_privacy = sanitized_manifest.get("privacy", {})
                sanitized_privacy.pop("deny_path_globs", None)
                sanitized_privacy.pop("deny_text_patterns", None)
                text = _host['json'].dumps(sanitized_manifest, ensure_ascii=False)
            for pattern in deny_patterns:
                if pattern.search(text):
                    errors.append("public privacy gate failed: manifest-deny-text-pattern")
        if privacy_gate is not None:
            try:
                privacy_gate(relative, text)
            except ValueError as exc:
                errors.append(str(exc))
    return errors


def _release_payload(_host, path: Path) -> bytes:
    payload = path.read_bytes()
    if path.suffix.lower() in _host['TEXT_EXTENSIONS'] or path.name in {"LICENSE", ".gitignore"}:
        text = payload.decode("utf-8-sig")
        return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    return payload


def _deterministic_zip(_host, source: Path, archive: Path) -> None:
    source = source.resolve(strict=True)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with _host['zipfile'].ZipFile(archive, "w", compression=_host['zipfile'].ZIP_DEFLATED, compresslevel=9) as out:
        for path in sorted(source.rglob("*")):
            _host['_assert_contained_release_path'](source, path)
            if not path.is_file():
                continue
            _host['_assert_contained_release_path'](source, path, require_file=True)
            relative = path.relative_to(source).as_posix()
            info = _host['zipfile'].ZipInfo(relative, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = _host['zipfile'].ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, _host['_release_payload'](path))


def build_release(_host,
    root: Path = None,
    dist: Optional[Path] = None,
    base_url: Optional[str] = None,
) -> dict:
    root = root.resolve(strict=True)
    manifest_path = root / "release-manifest.json"
    _host['_assert_contained_release_path'](root, manifest_path, require_file=True)
    manifest = _host['read_json'](manifest_path)
    version = manifest["version"]
    files = _host['collect_release_files'](root, manifest)
    errors = _host['validate_release_tree'](root, manifest, files)
    if errors:
        raise RuntimeError("release validation failed:\n- " + "\n- ".join(errors))
    sync_inventory_contract = _host['_load_sync_inventory_contract'](root)
    dist = (dist or root / "dist").resolve()
    archive_name = "video-autopilot-kit-v%s.zip" % version
    archive = dist / archive_name
    with _host['tempfile'].TemporaryDirectory(prefix="video-autopilot-release-") as temporary:
        stage = _host['Path'](temporary) / "release"
        for source in files:
            relative = source.relative_to(root)
            target = stage / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Canonicalize public text before per-file hashes are computed.
            target.write_bytes(_host['_release_payload'](source))
        receipt_errors = _host['_staged_sync_receipt_errors'](stage, sync_inventory_contract)
        if receipt_errors:
            raise RuntimeError(
                "release sync-receipt parity failed:\n- "
                + "\n- ".join(receipt_errors)
            )
        indexed = []
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                indexed.append(
                    {
                        "path": path.relative_to(stage).as_posix(),
                        "sha256": _host['sha256_path'](path),
                        "size": path.stat().st_size,
                    }
                )
        index = {
            "schema_version": 1,
            "project_id": manifest["project_id"],
            "version": version,
            "generated_at": manifest["release_date"],
            "files": indexed,
        }
        _host['atomic_json'](stage / "release-index.json", index)
        _host['_deterministic_zip'](stage, archive)
    archive_hash = _host['sha256_path'](archive)
    channel = {
        "schema_version": 1,
        "project_id": manifest["project_id"],
        "latest": {
            "version": version,
            "url": (base_url.rstrip("/") + "/" + archive_name) if base_url else archive_name,
            "sha256": archive_hash,
            "release_notes": "https://github.com/Hao0321/video-autopilot-kit/releases/tag/v%s" % version,
        },
    }
    _host['atomic_json'](dist / "release-channel.json", channel)
    (dist / (archive_name + ".sha256")).write_text(
        archive_hash + "  " + archive_name + "\n", encoding="ascii"
    )
    return {
        "status": "GREEN",
        "version": version,
        "archive": str(archive),
        "sha256": archive_hash,
        "managed_files": len(files),
        "channel": str(dist / "release-channel.json"),
    }
