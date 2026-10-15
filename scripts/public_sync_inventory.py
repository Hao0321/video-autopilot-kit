"""Closed-world inventories for canonical-to-public synchronization.

Private canonical filenames and reasons live only in the canonical workspace's
control JSON.  Public source and receipts retain aggregate counts, so the
inventory fails closed without publishing dictionary-attackable name hashes.
"""
from __future__ import annotations

import fnmatch
import os
import stat
import hashlib
import json
import re
from pathlib import Path


def _catalog_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate public sync catalog key")
        result[key] = value
    return result


def _load_public_catalog():
    """Read only the sibling data contract, never an ambient Python module."""
    path = Path(__file__).with_name("public_sync_catalog.json")
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or getattr(before, "st_file_attributes", 0) & 0x400:
        raise ValueError("public sync catalog must be a regular owned file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError("public sync catalog handle does not match its path")
        raw = stream.read(256 * 1024 + 1)
        ended = os.fstat(stream.fileno())
    after = path.lstat()
    def identity(info):
        return (info.st_dev, info.st_ino, stat.S_IFMT(info.st_mode), info.st_size,
                info.st_mtime_ns, getattr(info, "st_file_attributes", 0) & 0x400)
    if (not identity(before) == identity(opened) == identity(ended) == identity(after)
            or before.st_ctime_ns != after.st_ctime_ns or opened.st_ctime_ns != ended.st_ctime_ns
            or len(raw) != before.st_size):
        raise ValueError("public sync catalog changed while reading")
    if not raw or len(raw) > 256 * 1024:
        raise ValueError("public sync catalog exceeds its byte bound")
    data = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_catalog_no_duplicates)
    expected = {'DRAMA_MODULES', 'CANONICAL_DIRECTORY_LABELS', 'SANITIZED_KNOWLEDGE_FILES', 'PRIVATE_CONTROL_SCHEMA', 'PRIVATE_PUBLIC_FILES', 'PRIVATE_CANONICAL_COUNTS', 'CLEANUP_HELPER_FILES', 'REFERENCE_FILES', 'CANONICAL_PUBLIC_OWNED_PINS', 'WORKFLOW_SKILL_FILES', 'SILENT_VLOG_MODULES', 'KNOWLEDGE_FILES', 'SYNC_RECEIPT_PATH', 'ROOT_MODULES', 'PUBLIC_AUDIT_EXCLUDES', 'PRIVATE_CONTROL_FILE', 'LONGFORM_MODULES', 'PUBLIC_OWNED_PATHS'}
    tuples = {'DRAMA_MODULES', 'CANONICAL_DIRECTORY_LABELS', 'WORKFLOW_SKILL_FILES', 'SILENT_VLOG_MODULES', 'KNOWLEDGE_FILES', 'PRIVATE_PUBLIC_FILES', 'ROOT_MODULES', 'PUBLIC_AUDIT_EXCLUDES', 'CLEANUP_HELPER_FILES', 'LONGFORM_MODULES', 'PUBLIC_OWNED_PATHS', 'REFERENCE_FILES'}
    sets = {'SANITIZED_KNOWLEDGE_FILES'}
    if not isinstance(data, dict) or set(data) != expected:
        raise ValueError("public sync catalog key set drifted")
    for key in tuples | sets:
        items = data[key]
        if not isinstance(items, list) or any(not isinstance(item, str) for item in items):
            raise ValueError("public sync catalog list is invalid")
        data[key] = frozenset(items) if key in sets else tuple(items)
    return data


_CATALOG = _load_public_catalog()
ROOT_MODULES = _CATALOG['ROOT_MODULES']
LONGFORM_MODULES = _CATALOG['LONGFORM_MODULES']
SILENT_VLOG_MODULES = _CATALOG['SILENT_VLOG_MODULES']
DRAMA_MODULES = _CATALOG['DRAMA_MODULES']
KNOWLEDGE_FILES = _CATALOG['KNOWLEDGE_FILES']
PRIVATE_PUBLIC_FILES = _CATALOG['PRIVATE_PUBLIC_FILES']
SANITIZED_KNOWLEDGE_FILES = _CATALOG['SANITIZED_KNOWLEDGE_FILES']
REFERENCE_FILES = _CATALOG['REFERENCE_FILES']
WORKFLOW_SKILL_FILES = _CATALOG['WORKFLOW_SKILL_FILES']
CLEANUP_HELPER_FILES = _CATALOG['CLEANUP_HELPER_FILES']
PUBLIC_AUDIT_EXCLUDES = _CATALOG['PUBLIC_AUDIT_EXCLUDES']
SYNC_RECEIPT_PATH = _CATALOG['SYNC_RECEIPT_PATH']
PUBLIC_OWNED_PATHS = _CATALOG['PUBLIC_OWNED_PATHS']
CANONICAL_PUBLIC_OWNED_PINS = _CATALOG['CANONICAL_PUBLIC_OWNED_PINS']
PRIVATE_CONTROL_FILE = _CATALOG['PRIVATE_CONTROL_FILE']
PRIVATE_CONTROL_SCHEMA = _CATALOG['PRIVATE_CONTROL_SCHEMA']
CANONICAL_DIRECTORY_LABELS = _CATALOG['CANONICAL_DIRECTORY_LABELS']
PRIVATE_CANONICAL_COUNTS = _CATALOG['PRIVATE_CANONICAL_COUNTS']
del _CATALOG


# These files may exist in the private workspace, but are never valid public
# artifacts. Keep this exact so check mode rejects a stale tracked copy.


# Two deliberate packaging mirrors are excluded from whole-repository scoring:
# the workflow runtime is installed in src and the Codex Skill, while Cleanup
# Helper is bundled as an independently audited evaluator.


# Public-kit-owned files have no canonical source and are copied verbatim into
# fresh staging trees.  ``system_health.py`` is the sole analogue of a private
# canonical module; its canonical content is pinned below so a private change
# cannot be silently ignored by a false-green public sync.


# Aggregate counts are not identifying.  They let a public receipt verifier
# validate exact schema shape without retaining filenames, reasons, or hashes.


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_private_control(canonical: Path) -> dict[str, dict[str, str]]:
    path = canonical / PRIVATE_CONTROL_FILE
    if not path.is_file():
        raise ValueError("canonical private inventory control file is missing")
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("canonical private inventory control file is invalid") from exc
    if payload.get("schema") != PRIVATE_CONTROL_SCHEMA:
        raise ValueError("canonical private inventory control schema drifted")
    directories = payload.get("directories")
    if not isinstance(directories, dict) or set(directories) != set(CANONICAL_DIRECTORY_LABELS):
        raise ValueError("canonical private inventory directory shape drifted")
    result: dict[str, dict[str, str]] = {}
    for label in CANONICAL_DIRECTORY_LABELS:
        rows = directories[label]
        if not isinstance(rows, dict):
            raise ValueError(f"canonical private inventory class must be an object: {label}")
        if len(rows) != PRIVATE_CANONICAL_COUNTS[label]:
            raise ValueError(f"canonical private inventory count drifted: {label}")
        normalized: dict[str, str] = {}
        for name, reason in rows.items():
            if (not isinstance(name, str) or not name or Path(name).name != name
                    or name == PRIVATE_CONTROL_FILE):
                raise ValueError(f"canonical private inventory filename is invalid: {label}")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError(f"canonical private inventory reason is missing: {label}")
            normalized[name] = reason.strip()
        result[label] = normalized
    return result


def _canonical_public_classes() -> dict[str, dict[str, tuple[str, ...] | dict[str, str]]]:
    """Return every allowed direct canonical filename exactly once."""
    return {
        "root": {
            "derived": ROOT_MODULES,
            "special": ("SKILL.md", "audit.config.json"),
            "public_owned": CANONICAL_PUBLIC_OWNED_PINS["root"],
        },
        "longform_maker": {"derived": LONGFORM_MODULES, "special": (), "public_owned": {}},
        "silent_vlog_maker": {"derived": SILENT_VLOG_MODULES, "special": (), "public_owned": {}},
        "drama_pipeline": {"derived": DRAMA_MODULES, "special": (), "public_owned": {}},
        "knowledge": {"derived": KNOWLEDGE_FILES, "special": (), "public_owned": {}},
        "agents": {"derived": ("openai.yaml",), "special": (), "public_owned": {}},
        "references": {"derived": REFERENCE_FILES, "special": (), "public_owned": {}},
    }


def validate_canonical_inventory(canonical: Path) -> dict[str, dict]:
    """Validate all managed direct canonical directories and return hash evidence."""
    errors: list[str] = []
    evidence: dict[str, dict] = {}
    classes = _canonical_public_classes()
    private_control = _load_private_control(canonical)
    for label, classified in classes.items():
        root = canonical if label == "root" else canonical / label
        if not root.is_dir():
            errors.append(f"missing canonical directory: {label}")
            continue
        derived_seq = tuple(classified["derived"])
        special_seq = tuple(classified["special"])
        owned_pins = dict(classified["public_owned"])
        private = set(private_control[label])
        derived, special, owned = set(derived_seq), set(special_seq), set(owned_pins)
        for class_name, sequence in (("derived", derived_seq), ("special", special_seq)):
            duplicates = sorted(name for name in set(sequence) if sequence.count(name) != 1)
            if duplicates:
                errors.append(f"duplicate {label} {class_name}: " + ", ".join(duplicates))
        overlaps = sorted((derived & special) | (derived & owned) | (special & owned))
        if overlaps:
            errors.append(f"overlapping public classes in {label}: " + ", ".join(overlaps))
        public_names = derived | special | owned
        private_overlap = sorted(public_names & private)
        if private_overlap:
            errors.append(f"public/private overlap in {label}: " + ", ".join(private_overlap))
        actual = {path.name: path for path in root.iterdir() if path.is_file()}
        control_names = {PRIVATE_CONTROL_FILE} if label == "root" else set()
        missing_public = sorted(public_names - set(actual))
        missing_private = sorted(private - set(actual))
        unknown = sorted(
            name for name in actual
            if name not in public_names and name not in private and name not in control_names
        )
        if missing_public:
            errors.append(f"required canonical files missing in {label}: " + ", ".join(missing_public))
        if missing_private:
            errors.append(f"private classifications missing in {label}")
        if label == "root" and PRIVATE_CONTROL_FILE not in actual:
            errors.append("canonical private inventory control file is missing from root")
        if unknown:
            errors.append(f"unclassified canonical file count in {label}: {len(unknown)}")
        for name, expected in owned_pins.items():
            path = actual.get(name)
            if path is not None and _sha256(path) != expected:
                errors.append(
                    f"canonical public-owned analogue changed in {label}/{name}; "
                    "review and update its explicit content pin"
                )
        evidence[label] = {
            "derived": {name: _sha256(actual[name]) for name in sorted(derived) if name in actual},
            "special": {name: _sha256(actual[name]) for name in sorted(special) if name in actual},
            "public_owned_analogue": {
                name: _sha256(actual[name]) for name in sorted(owned) if name in actual
            },
            "private_count": len(private),
            "private_control_count": 1 if label == "root" else 0,
        }
    if errors:
        raise ValueError("canonical direct-file inventory is not closed-world: " + "; ".join(errors))
    return evidence


def public_destination_direct_files() -> dict[str, frozenset[str]]:
    """Exact leaf-file sets grouped by their managed public directory."""
    public_src_owned = {
        Path(relative).name for relative in PUBLIC_OWNED_PATHS
        if Path(relative).parent.as_posix() == "src"
    }
    public_reference_owned = {
        Path(relative).name for relative in PUBLIC_OWNED_PATHS
        if Path(relative).parent.as_posix() == "codex-skill/video-autopilot/references"
    }
    public_skill_owned = {
        Path(relative).name for relative in PUBLIC_OWNED_PATHS
        if Path(relative).parent.as_posix() == "codex-skill/video-autopilot"
    }
    return {
        "src": frozenset((*ROOT_MODULES, *public_src_owned)),
        "src/longform_maker": frozenset((*LONGFORM_MODULES, "__init__.py")),
        "src/silent_vlog_maker": frozenset(SILENT_VLOG_MODULES),
        "src/drama_pipeline": frozenset(DRAMA_MODULES),
        "knowledge/runtime": frozenset(KNOWLEDGE_FILES),
        "codex-skill/video-autopilot": frozenset(("SKILL.md", *public_skill_owned, *WORKFLOW_SKILL_FILES)),
        "codex-skill/video-autopilot/design_runtime/src": frozenset(("aesthetic_score.py", "design_system_v6.py")),
        "codex-skill/video-autopilot/design_runtime/knowledge/runtime": frozenset(("aesthetic_standard.json", "design_reference_dna.json")),
        "codex-skill/video-autopilot/agents": frozenset(("openai.yaml",)),
        "codex-skill/video-autopilot/references": frozenset((*REFERENCE_FILES, *public_reference_owned)),
    }


def public_destination_required_paths() -> list[str]:
    return sorted(
        f"{directory}/{name}"
        for directory, names in public_destination_direct_files().items()
        for name in sorted(names)
    )


def sync_expected_output_paths() -> frozenset[str]:
    """Return the exact non-recursive-receipt output key set for one sync."""
    return frozenset({
        *public_destination_required_paths(),
        *(f"tools/code-cleanup-helper/{relative}" for relative in CLEANUP_HELPER_FILES),
        "tools/code-cleanup-helper/BUNDLE.json",
        "audit.config.json",
        "docs/AUTOPILOT_ARCHITECTURE_V6.md",
        "AUTOPILOT_MANIFEST.json",
    })


def canonical_receipt_expected_shape() -> dict[str, dict]:
    """Return public class/name expectations without any private filenames."""
    result: dict[str, dict] = {}
    for label, classified in _canonical_public_classes().items():
        result[label] = {
            "derived": tuple(sorted(classified["derived"])),
            "special": tuple(sorted(classified["special"])),
            "public_owned_analogue": tuple(sorted(classified["public_owned"])),
            "private_count": PRIVATE_CANONICAL_COUNTS[label],
            "private_control_count": 1 if label == "root" else 0,
        }
    return result


_SHA256_TEXT = re.compile(r"[0-9a-f]{64}")


def canonical_receipt_shape_errors(inventory) -> list[str]:
    """Validate exact public canonical evidence shape, classes, names, and hashes."""
    expected = canonical_receipt_expected_shape()
    if not isinstance(inventory, dict):
        return ["canonical inventory evidence missing"]
    errors: list[str] = []
    if set(inventory) != set(expected):
        errors.append("canonical inventory root set mismatch")
        return errors
    expected_classes = {
        "derived", "special", "public_owned_analogue",
        "private_count", "private_control_count",
    }
    for label, shape in expected.items():
        row = inventory.get(label)
        if not isinstance(row, dict) or set(row) != expected_classes:
            errors.append(f"canonical inventory class set mismatch: {label}")
            continue
        for class_name in ("derived", "special", "public_owned_analogue"):
            values = row.get(class_name)
            expected_names = set(shape[class_name])
            if not isinstance(values, dict) or set(values) != expected_names:
                errors.append(f"canonical inventory name set mismatch: {label}/{class_name}")
                continue
            if any(not isinstance(value, str) or not _SHA256_TEXT.fullmatch(value)
                   for value in values.values()):
                errors.append(f"canonical inventory hash invalid: {label}/{class_name}")
        if row.get("private_count") != shape["private_count"]:
            errors.append(f"canonical private aggregate count mismatch: {label}")
        if row.get("private_control_count") != shape["private_control_count"]:
            errors.append(f"canonical private-control aggregate mismatch: {label}")
        if label == "root" and isinstance(row.get("public_owned_analogue"), dict):
            for name, expected_hash in CANONICAL_PUBLIC_OWNED_PINS["root"].items():
                if row["public_owned_analogue"].get(name) != expected_hash:
                    errors.append("canonical public-owned analogue pin mismatch")
    return errors


def _matches(relative: str, patterns) -> bool:
    value = relative.replace("\\", "/").lstrip("./")
    for raw in patterns:
        pattern = str(raw).replace("\\", "/").lstrip("./")
        if pattern.endswith("/**") and (
            value == pattern[:-3].rstrip("/") or value.startswith(pattern[:-3])
        ):
            return True
        if fnmatch.fnmatchcase(value, pattern):
            return True
    return False


def validate_public_destination(repository: Path, release_manifest_path: Path | None = None) -> None:
    """Reject every unexpected release-selected file recursively under managed roots."""
    manifest_path = release_manifest_path or repository / "release-manifest.json"
    if not manifest_path.is_file():
        raise ValueError("release manifest is required for public destination inventory")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("release manifest is invalid for public destination inventory") from exc
    includes = manifest.get("managed_include")
    excludes = manifest.get("exclude_globs")
    protected = manifest.get("protected_globs")
    if not all(isinstance(value, list) for value in (includes, excludes, protected)):
        raise ValueError("release manifest selection schema is incomplete")
    expected = set(public_destination_required_paths())
    errors: list[str] = []
    not_selected = sorted(
        relative for relative in expected
        if not _matches(relative, includes) or _matches(relative, excludes)
    )
    if not_selected:
        errors.append("managed public schema contains non-release paths")
    actual: set[str] = set()
    for managed_root in ("src", "knowledge/runtime", "codex-skill/video-autopilot"):
        root = repository / managed_root
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(repository).as_posix()
            if not _matches(relative, includes) or _matches(relative, excludes):
                continue
            if _matches(relative, protected):
                errors.append("protected path entered managed public destination")
            actual.add(relative)
    missing, extra = sorted(expected - actual), sorted(actual - expected)
    if missing:
        errors.append("missing managed public release files: " + ", ".join(missing[:20]))
    if extra:
        errors.append("unclassified managed public release files: " + ", ".join(extra[:20]))
    design_mirrors = (
        ("src/aesthetic_score.py", "codex-skill/video-autopilot/design_runtime/src/aesthetic_score.py"),
        ("src/design_system_v6.py", "codex-skill/video-autopilot/design_runtime/src/design_system_v6.py"),
        ("knowledge/runtime/aesthetic_standard.json", "codex-skill/video-autopilot/design_runtime/knowledge/runtime/aesthetic_standard.json"),
        ("knowledge/runtime/design_reference_dna.json", "codex-skill/video-autopilot/design_runtime/knowledge/runtime/design_reference_dna.json"),
    )
    for source, mirror in design_mirrors:
        if source in actual and mirror in actual:
            if (repository / source).read_bytes().replace(b"\r\n", b"\n") != (repository / mirror).read_bytes().replace(b"\r\n", b"\n"):
                errors.append("public design runtime mirror drift: " + mirror)
    if errors:
        raise ValueError("public destination inventory is not closed-world: " + "; ".join(errors))


def self_test_public_inventory(repository: Path) -> None:
    """Negative fixtures for recursive destination and receipt schema closure."""
    import copy
    import tempfile

    expected_shape = canonical_receipt_expected_shape()
    valid = {
        label: {
            "derived": {name: "0" * 64 for name in shape["derived"]},
            "special": {name: "0" * 64 for name in shape["special"]},
            "public_owned_analogue": {
                name: CANONICAL_PUBLIC_OWNED_PINS["root"][name]
                for name in shape["public_owned_analogue"]
            },
            "private_count": shape["private_count"],
            "private_control_count": shape["private_control_count"],
        }
        for label, shape in expected_shape.items()
    }
    assert not canonical_receipt_shape_errors(valid)
    assert canonical_receipt_shape_errors({})
    missing_name = copy.deepcopy(valid)
    missing_name["root"]["derived"].pop(next(iter(missing_name["root"]["derived"])))
    assert canonical_receipt_shape_errors(missing_name)
    injected_private_class = copy.deepcopy(valid)
    injected_private_class["root"]["forbidden_private_inventory"] = {"opaque": 1}
    assert canonical_receipt_shape_errors(injected_private_class)
    manifest_path = repository / "release-manifest.json"
    with tempfile.TemporaryDirectory(prefix="video-autopilot-inventory-test-") as temp:
        staged = Path(temp)
        for relative in public_destination_required_paths():
            path = staged / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture\n", encoding="utf-8")
        validate_public_destination(staged, manifest_path)
        extra = staged / "src" / "extra_dir" / "extra.py"
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("unexpected = True\n", encoding="utf-8")
        try:
            validate_public_destination(staged, manifest_path)
        except ValueError as exc:
            assert "unclassified managed public release files" in str(exc)
        else:
            raise AssertionError("recursive public destination accepted an extra release file")
        extra.unlink()
        cache = staged / "src" / "__pycache__" / "ignored.pyc"
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(b"generated cache fixture")
        validate_public_destination(staged, manifest_path)
        mirror = staged / "codex-skill/video-autopilot/design_runtime/src/design_system_v6.py"
        mirror.write_text("stale copy\n", encoding="utf-8")
        try:
            validate_public_destination(staged, manifest_path)
        except ValueError as exc:
            assert "public design runtime mirror drift" in str(exc)
        else:
            raise AssertionError("public design runtime accepted a stale mirror")
    assert len(sync_expected_output_paths()) == 419
    required_extractions = {
        "src/review_auth.py", "src/review_page.py", "src/review_bundle.py",
        "src/review_http.py", "src/review_pairing.py", "src/review_remote.py",
        "src/review_loop_selftest.py", "src/asset_usage_history.py", "src/context_budget.py",
        "src/release_archive.py", "src/release_test_support.py", "src/release_mutation_selftest.py",
    }
    assert required_extractions <= sync_expected_output_paths()
    # Sync tooling is repository-owned, like sync_canonical.py itself; it is
    # required by the release manifest and is not a generated sync output.
    for name in ("public_sync_paths.py", "public_sync_receipts.py"):
        assert (repository / "scripts" / name).is_file()
    required_review = {"src/agent_art_review.py", "src/review_policy.py", "codex-skill/video-autopilot/agent_art_review.py", "codex-skill/video-autopilot/review_policy.py"}
    assert required_review <= set(sync_expected_output_paths())
    assert "codex-skill/video-autopilot/references/native-reel-scenes.md" not in PUBLIC_OWNED_PATHS
    print("public sync inventory negative fixtures GREEN")
