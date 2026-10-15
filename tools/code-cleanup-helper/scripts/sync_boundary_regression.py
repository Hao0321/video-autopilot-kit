"""Freeze publication membership and require explicit empty retirement."""
from __future__ import annotations
from pathlib import Path
import tempfile
from sync_public import apply_plan
from sync_safety import plan_sync
from sync_regression import blocked


def tree_bytes(root: Path) -> dict:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def membership_controls(source: Path, dest: Path) -> None:
    config = {"exclude": ["ignored/**"]}
    (source / "kept.md").write_bytes(b"owned original")
    apply_plan(plan_sync(source, dest, config))
    before = tree_bytes(dest)
    frozen = plan_sync(source, dest, config)
    (source / "late.md").write_bytes(b"unplanned addition")
    blocked(lambda: apply_plan(frozen))
    assert tree_bytes(dest) == before, "inventory drift performed a payload write"
    (source / "late.md").unlink()
    frozen = plan_sync(source, dest, config)
    (source / "ignored").mkdir()
    (source / "ignored/raw.txt").write_bytes(b"excluded by frozen configuration")
    config["exclude"].clear()
    apply_plan(frozen)  # Caller mutations and irrelevant private additions cannot change the frozen selection.
    assert tree_bytes(dest) == before
    (source / "kept.md").unlink()
    blocked(lambda: plan_sync(source, dest, {"exclude": ["ignored/**"]}))
    assert tree_bytes(dest) == before
    apply_plan(plan_sync(source, dest, {"exclude": ["ignored/**"]}, allow_empty=True))
    assert not (dest / "kept.md").exists(), "explicit hash-owned retirement failed"


def root_controls(root: Path) -> dict:
    source, dest = root / "source", root / "dest"
    source.mkdir()
    (source / "kept.md").write_bytes(b"owned source")
    (root / "file").write_bytes(b"not a directory")
    blocked(lambda: plan_sync(root / "missing", dest, {}))
    blocked(lambda: plan_sync(root / "file", dest, {}))
    blocked(lambda: plan_sync(source, root / "file", {}))
    apply_plan(plan_sync(source, dest, {}))
    result = {"symlink": "NOT_CHECKED"}
    try:
        (root / "alias").symlink_to(source, target_is_directory=True)
        (root / "dest-alias").symlink_to(dest, target_is_directory=True)
    except OSError:
        return result
    blocked(lambda: plan_sync(root / "alias", dest, {}))
    blocked(lambda: plan_sync(source, root / "dest-alias", {}))
    (source / "nested").mkdir()
    blocked(lambda: plan_sync(root / "alias/nested", dest, {}, allow_empty=True))
    result["symlink"] = "PASS"
    return result


def run_self_test() -> dict:
    with tempfile.TemporaryDirectory(prefix="cleanup-sync-boundary-") as raw:
        root = Path(raw)
        source, dest = root / "private", root / "public"
        source.mkdir()
        dest.mkdir()
        membership_controls(source, dest)
        result = root_controls(root)
    return {"status": "PASS", "optionalNativeControls": result}


if __name__ == "__main__":
    print(run_self_test())
