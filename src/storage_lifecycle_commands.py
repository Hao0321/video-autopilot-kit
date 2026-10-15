"""CLI and owned fixtures; application globals stay with the compatibility host."""
from __future__ import annotations

def _selftest(_module_globals) -> None:
    with _module_globals['tempfile'].TemporaryDirectory(prefix="storage_lifecycle_") as td:
        job = _module_globals['Path'](td) / "job"
        out = job / "_out"
        work = out / "_work"
        out.mkdir(parents=True)
        work.mkdir()

        legacy = out / "old_v7.mp4"
        legacy.write_bytes(b"legacy")
        state = _module_globals['activate_policy'](out)
        assert state["legacy_files"] == ["old_v7.mp4"]
        assert _module_globals['is_version_like']("movie_v12_FINAL.mp4")
        assert not _module_globals['is_version_like']("current.mp4")

        candidate = work / "current_candidate.mp4"
        candidate.write_bytes(b"revision-one")
        current = _module_globals['atomic_publish'](candidate, _module_globals['canonical_output_path'](out))
        delivered = _module_globals['Path'](td) / "published.mp4"
        info = _module_globals['link_or_copy'](current, delivered)
        assert info["method"] in ("hardlink", "copy") and delivered.read_bytes() == b"revision-one"

        # 原子換 current 後，先前 hard link/copy 必須仍是上一版內容。
        candidate.write_bytes(b"revision-two")
        _module_globals['atomic_publish'](candidate, current)
        assert current.read_bytes() == b"revision-two"
        assert delivered.read_bytes() == b"revision-one"

        one = _module_globals['create_milestone'](current, job, "approved")
        two = _module_globals['create_milestone'](current, job, "published")
        assert one["milestones"] == 1 and two["milestones"] == 2
        try:
            _module_globals['create_milestone'](current, job, "approved")
        except RuntimeError:
            pass
        else:
            raise AssertionError("third binary milestone was not blocked")

        (work / "current_vis.mp4").write_bytes(b"cache")
        (work / "current_vis.json").write_text("{}", encoding="utf-8")
        (work / "current_cap.mp4").write_bytes(b"throwaway")
        (work / "burned.mp4").write_bytes(b"longform-throwaway")
        cards = work / "current_cards"
        cards.mkdir()
        (cards / "a.png").write_bytes(b"png")
        dry = _module_globals['prune_transients'](work)
        assert dry["count"] == 2 and (work / "current_cap.mp4").exists()
        qa = {"all_green": True}
        final = _module_globals['finalize_success'](job, current, work, qa,
                                 registered_transients=[work / "burned.mp4"])
        assert final["finalized"] and not (work / "current_cap.mp4").exists()
        assert not (work / "burned.mp4").exists()
        assert (work / "current_vis.mp4").exists() and legacy.exists()

        # baseline 之後的新 vN 不能進來。
        bad = out / "movie_v8.mp4"
        bad.write_bytes(b"bad")
        try:
            _module_globals['assert_output_policy'](out, state)
        except AssertionError:
            pass
        else:
            raise AssertionError("new versioned output was not blocked")

        archive = job / "_archive"
        archive.mkdir()
        survivor = job / "source.mp4"
        archived = archive / "source.mp4"
        survivor.write_bytes(b"same-content")
        archived.write_bytes(b"same-content")
        dry_dedupe = _module_globals['deduplicate_archive_copies'](job, min_hash_bytes=1)
        assert dry_dedupe["candidate_count"] == 1 and not _module_globals['os'].path.samefile(survivor, archived)
        applied_dedupe = _module_globals['deduplicate_archive_copies'](job, apply=True, min_hash_bytes=1)
        assert applied_dedupe["status"] == "GREEN" and _module_globals['os'].path.samefile(survivor, archived)
        after_dedupe = _module_globals['audit_tree'](job, hash_duplicates=True, min_hash_bytes=1)
        assert after_dedupe["reclaimable_bytes"] == 0 and after_dedupe["hardlink_groups"]
    print("storage_lifecycle self-test GREEN")

def _cli_contract_selftest(_module_globals) -> None:
    """Keep machine output parseable when human display fields evolve."""
    sample = {"bytes": 1024, "display_size": _module_globals['_human_bytes'](1024)}
    assert _module_globals['json'].loads(_module_globals['json'].dumps(sample, ensure_ascii=False)) == sample

def main(_module_globals, argv: list[str] | None = None) -> int:
    ap = _module_globals['argparse'].ArgumentParser(description="M115 auto-edit storage lifecycle")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("audit")
    a.add_argument("root")
    a.add_argument("--hash-duplicates", action="store_true")
    a.add_argument("--min-size-mb", type=float, default=20.0)
    dupe = sub.add_parser("dedupe-archive")
    dupe.add_argument("root")
    dupe.add_argument("--apply", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("out_dir")
    p = sub.add_parser("prune")
    p.add_argument("work_dir")
    p.add_argument("--apply", action="store_true")
    d = sub.add_parser("deliver")
    d.add_argument("current")
    d.add_argument("destination")
    s = sub.add_parser("snapshot")
    s.add_argument("current")
    s.add_argument("job_root")
    s.add_argument("--label", choices=["approved", "published"], required=True)
    sub.add_parser("selftest")
    ns = ap.parse_args(argv)

    if ns.cmd == "selftest":
        _module_globals['_selftest']()
        _module_globals['_cli_contract_selftest']()
        return 0
    if ns.cmd == "audit":
        result = _module_globals['audit_tree'](ns.root, hash_duplicates=ns.hash_duplicates,
                            min_hash_bytes=int(ns.min_size_mb * 1024 ** 2))
    elif ns.cmd == "dedupe-archive":
        result = _module_globals['deduplicate_archive_copies'](ns.root, apply=ns.apply)
    elif ns.cmd == "check":
        result = _module_globals['assert_output_policy'](ns.out_dir)
    elif ns.cmd == "prune":
        result = _module_globals['prune_transients'](ns.work_dir, apply=ns.apply)
    elif ns.cmd == "snapshot":
        result = _module_globals['create_milestone'](ns.current, ns.job_root, ns.label)
    else:
        result = _module_globals['link_or_copy'](ns.current, ns.destination)
    if ns.cmd in ("audit", "prune", "dedupe-archive"):
        display_bytes = result.get("bytes", result.get("reclaimed_bytes", 0))
        result["display_size"] = _module_globals['_human_bytes'](display_bytes)
    # A CLI advertised as JSON must emit one parseable JSON document.  Human
    # display text belongs inside the document instead of trailing after it.
    print(_module_globals['json'].dumps(result, ensure_ascii=False, indent=2))
    return 0
