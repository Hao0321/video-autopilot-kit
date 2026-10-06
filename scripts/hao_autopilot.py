#!/usr/bin/env python3
"""Public command hub for the Video Autopilot kit.

The README, TROUBLESHOOTING and the Codex Skill references document commands as
``python scripts/hao_autopilot.py <command> ...``.  Each command forwards to the
public module that owns it, so behavior, exit codes and JSON output are the same
as calling that module directly.  The hub adds no state, network access or file
writes of its own.

    python scripts/hao_autopilot.py                 # list commands
    python scripts/hao_autopilot.py workflow next <run>
    python scripts/hao_autopilot.py learn --scope shorts/food --rule "..." --evidence "..."
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# command -> (module relative to the kit root, leading arguments, summary)
COMMANDS = {
    "workflow": ("src/workflow_contract.py", (),
                 "Editkin v4 run: create/status/next/claim/complete/fail/resume/verify/reject-render"),
    "thumbnail-score": ("src/thumbnail_algorithm_score.py", ("score",),
                        "score long-form thumbnail evidence (+ 168x94 preview)"),
    "dedupe-archive": ("src/storage_lifecycle.py", ("dedupe-archive",),
                       "preview, then --apply, verified archive deduplication"),
    "storage": ("src/storage_lifecycle.py", (),
                "storage audit/check/prune/deliver/snapshot"),
    "knowledge": ("src/knowledge_lifecycle.py", ("audit",),
                  "audit learning memory; --digest prints the runtime card; "
                  "--rotate-video-log [--apply] rotates the video log"),
    "learn": ("src/knowledge_lifecycle.py", ("record",),
              "record one feedback rule with its evidence (soft until repeated)"),
    "project95": ("src/project_quality_95.py", ("audit",),
                  "whole-project quality-95 acceptance report"),
    "health": ("src/system_health.py", (),
               "kit health (--quick for the fast subset)"),
}
KNOWLEDGE_FLAGS = {"--rotate-video-log": "rotate-video-log", "--digest": "digest"}


def resolve(argv: list) -> list:
    """Translate hub arguments into the module command line (no execution)."""
    if not argv or argv[0] not in COMMANDS:
        raise KeyError(argv[0] if argv else "")
    module, lead, _summary = COMMANDS[argv[0]]
    rest = list(argv[1:])
    if argv[0] == "knowledge":
        flags = [flag for flag in KNOWLEDGE_FLAGS if flag in rest]
        if len(flags) > 1:
            raise ValueError("choose one of " + ", ".join(KNOWLEDGE_FLAGS))
        if flags:
            rest.remove(flags[0])
            lead = (KNOWLEDGE_FLAGS[flags[0]],)
    return [sys.executable, str(ROOT / module), *lead, *rest]


def usage() -> str:
    rows = ["usage: python scripts/hao_autopilot.py <command> [args...]", "", "commands:"]
    rows += ["  %-16s %s" % (name, spec[2]) for name, spec in COMMANDS.items()]
    rows += ["  %-16s %s" % ("selftest", "verify every command maps to a shipped module")]
    return "\n".join(rows)


def self_test() -> int:
    missing = [spec[0] for spec in COMMANDS.values() if not (ROOT / spec[0]).is_file()]
    assert not missing, "hub points at missing modules: %s" % missing
    assert resolve(["knowledge"])[2:] == ["audit"]
    assert resolve(["knowledge", "--rotate-video-log", "--apply"])[2:] == ["rotate-video-log", "--apply"]
    assert resolve(["learn", "--rule", "r", "--evidence", "e"])[2:] == ["record", "--rule", "r", "--evidence", "e"]
    assert resolve(["thumbnail-score", "e.json", "--output-dir", "o"])[2:] == ["score", "e.json", "--output-dir", "o"]
    assert resolve(["workflow", "next", "run"])[1].endswith("workflow_contract.py")
    for bad in ([], ["unknown"]):
        try:
            resolve(bad)
        except KeyError:
            pass
        else:
            raise AssertionError("unknown hub command accepted: %r" % bad)
    try:
        resolve(["knowledge", "--digest", "--rotate-video-log"])
    except ValueError:
        pass
    else:
        raise AssertionError("conflicting knowledge flags accepted")
    print("hao_autopilot command hub self-test GREEN")
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help", "help"}:
        print(usage())
        return 0
    if args[0] == "selftest":
        return self_test()
    try:
        command = resolve(args)
    except KeyError:
        print("unknown command: %s\n\n%s" % (args[0], usage()), file=sys.stderr)
        return 2
    except ValueError as exc:
        print("invalid arguments: %s" % exc, file=sys.stderr)
        return 2
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
