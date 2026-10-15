"""Publication preflight regression controls; only temporary fixtures are mutated."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
from sync_public import apply_plan
from sync_safety import MANIFEST, SyncError, ownership, plan_sync, privacy_check, safe_path


def blocked(action) -> None:
    try:
        action()
    except (SyncError, ValueError):
        return
    raise AssertionError("unsafe publication preflight was accepted")


def run_self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="cleanup-sync-") as raw:
        root = Path(raw)
        source, dest = root / "private", root / "public"
        source.mkdir()
        dest.mkdir()
        config = {"sync": {"privacy": {"tokens": ["private-marker"]}}}
        (source / "safe.md").write_text("original\n", encoding="utf-8")
        (source / ".rd").mkdir()
        (source / ".rd/raw.txt").write_text("private-marker", encoding="utf-8")
        (dest / "LICENSE").write_text("public-only\n", encoding="utf-8")
        plan = plan_sync(source, dest, config)
        assert not (dest / "safe.md").exists(), "planning performed a write"
        assert [x["path"] for x in plan["rows"]] == ["safe.md"], "raw learning was selected"
        apply_plan(plan)
        assert ownership(dest)[0]["safe.md"] is not None, "ownership lacks byte identity"
        assert (dest / "LICENSE").read_text() == "public-only\n"

        (source / "safe.md").write_text("updated\n", encoding="utf-8")
        (dest / "safe.md").write_text("user changes\n", encoding="utf-8")
        blocked(lambda: plan_sync(source, dest, config, adopt_existing=True))
        assert (dest / "safe.md").read_text() == "user changes\n"
        (dest / "safe.md").write_text("original\n", encoding="utf-8")
        apply_plan(plan_sync(source, dest, config))
        assert (dest / "safe.md").read_text() == "updated\n"

        frozen = plan_sync(source, dest, config)
        (source / "safe.md").write_text("after-plan mutation\n", encoding="utf-8")
        blocked(lambda: apply_plan(frozen))
        assert (dest / "safe.md").read_text() == "updated\n", "stale plan changed output"
        (source / "safe.md").unlink()
        (dest / "safe.md").write_text("edited stale\n", encoding="utf-8")
        blocked(lambda: plan_sync(source, dest, config))
        (dest / "safe.md").write_text("updated\n", encoding="utf-8")
        apply_plan(plan_sync(source, dest, config, allow_empty=True))
        assert not (dest / "safe.md").exists(), "hash-owned stale file was not retired"
        assert (dest / "LICENSE").is_file(), "public-only packaging was deleted"

        (source / "a.md").write_text("new content\n", encoding="utf-8")
        victim = root / "victim.md"
        victim.write_text("retain\n", encoding="utf-8")
        (dest / MANIFEST).write_text(json.dumps({"schema_version": 1, "managed_paths": ["../victim.md"]}), encoding="utf-8")
        blocked(lambda: plan_sync(source, dest, config))
        assert not (dest / "a.md").exists() and victim.read_text() == "retain\n"
        (dest / MANIFEST).write_text('{"schema_version":1,"managed_paths":[],"managed_paths":[]}', encoding="utf-8")
        blocked(lambda: plan_sync(source, dest, config))
        (dest / MANIFEST).write_text(json.dumps({"schema_version": 1, "managed_paths": ["A.md", "a.md"]}), encoding="utf-8")
        blocked(lambda: plan_sync(source, dest, config))
        (dest / MANIFEST).unlink()
        (dest / "a.md").write_text("legacy\n", encoding="utf-8")
        blocked(lambda: plan_sync(source, dest, config))
        apply_plan(plan_sync(source, dest, config, adopt_existing=True))
        for raw_name in ["../escape", "/root", "C:/escape", "a//b", "a/../b", "a\\b", "CON.txt"]:
            blocked(lambda name=raw_name: safe_path(dest, name))
        for payload in [b"private-marker", b"\x01" + "private-marker".encode("utf-16-le"),
                        ("gh" + "p_" + "a" * 36).encode()]:
            blocked(lambda data=payload: privacy_check(data, "payload.bin", config))
        blocked(lambda: privacy_check(b"safe", "a.md", {"privacy": {"patterns": ["["]}}))
        blocked(lambda: privacy_check(b"safe", ".env", {}))
        blocked(lambda: privacy_check(b"safe", ".env.production", {}))
        privacy_check(b"PORT=8080", ".env.example", {})
        try:
            (source / "linked.md").symlink_to(victim)
        except OSError:
            pass  # Native symlink permission is external to this fixture environment.
        else:
            blocked(lambda: plan_sync(source, dest, config))


if __name__ == "__main__":
    run_self_test()
    print("Publication preflight regression controls passed")
