#!/usr/bin/env python3
"""Repository-wide semantic privacy gate for redistributable text.

Path-specific sanitizers remove known private structures.  This module is the
second line of defence: every text file selected for the public release is
checked for *shapes* that should never occur in a redistributable kit.  The
patterns intentionally describe categories rather than retaining a person's
private values as deny-list fixtures.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import re
from pathlib import Path


class PublicPrivacyError(ValueError):
    """Raised when release text has a private-data-shaped value."""


_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "local-project-id",
        re.compile(
            r"(?i)(?:\b(?:private|personal|creator|user|local|incident|actual|real|source)\b|"
            r"\u79c1\u4eba|\u500b\u4eba|\u5275\u4f5c\u8005|\u4f7f\u7528\u8005|\u771f\u5be6|\u5be6\u62cd|\u7d20\u6750|\u5c08\u6848)"
            r"[^\r\n]{0,80}(?:\u9577\u7247\s*0[1-9]\b|"
            r"(?:longform|reference[_-]?impl[_-]?longform|project|episode)"
            r"[_ -]?0[1-9]\b|(?<![A-Za-z0-9])#0\d{2}(?![A-Za-z0-9]))|"
            r"(?:\u9577\u7247\s*0[1-9]\b|"
            r"(?:longform|reference[_-]?impl[_-]?longform|project|episode)"
            r"[_ -]?0[1-9]\b|(?<![A-Za-z0-9])#0\d{2}(?![A-Za-z0-9]))"
            r"[^\r\n]{0,80}(?:\b(?:private|personal|creator|user|local|incident|actual|real|source)\b|"
            r"\u79c1\u4eba|\u500b\u4eba|\u5275\u4f5c\u8005|\u4f7f\u7528\u8005|\u771f\u5be6|\u5be6\u62cd|\u7d20\u6750|\u5c08\u6848)"
        ),
    ),
    (
        "creator-performance-metric",
        re.compile(
            r"(?i)(?:\bHao(?:0321)?\b|\b(?:the\s+)?creator(?:'s)?\b|"
            r"\u5275\u4f5c\u8005|\u4f7f\u7528\u8005|\u7528\u6236)"
            r"[^\r\n]{0,100}(?:baseline|actual|outcome|\u5be6\u6e2c|\u771f\u5be6|\u74f6\u9838|\u6210\u6548|\u81ea\u63a8)"
            r"[^\r\n]{0,80}(?:\b(?:CTR|AVP|RPM|views?|retention|subscribers?|revenue)\b|"
            r"\u66dd\u5149|\u7559\u5b58|\u7e8c\u770b|\u89c0\u770b|\u8a02\u95b1|\u7c89\u7d72|\u6536\u76ca)"
            r".{0,48}[+-]?\d+(?:[.,]\d+)*(?:%|\b)|"
            r"(?:\b(?:CTR|AVP|RPM|views?|retention|subscribers?|revenue)\b|"
            r"\u66dd\u5149|\u7559\u5b58|\u7e8c\u770b|\u89c0\u770b|\u8a02\u95b1|\u7c89\u7d72|\u6536\u76ca)"
            r".{0,48}[+-]?\d+(?:[.,]\d+)*(?:%|\b)[^\r\n]{0,80}"
            r"(?:baseline|actual|outcome|\u5be6\u6e2c|\u771f\u5be6|\u74f6\u9838|\u6210\u6548|\u81ea\u63a8)"
            r"[^\r\n]{0,100}"
            r"(?:\bHao(?:0321)?\b|\b(?:the\s+)?creator(?:'s)?\b|\u5275\u4f5c\u8005)"
        ),
    ),
    (
        "dated-creator-verdict",
        re.compile(
            r"(?im)^(?=[^\r\n]*(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2})"
            r"(?=[^\r\n]*(?:\bHao(?:0321)?\b|\b(?:the\s+)?creator(?:'s)?\b|"
            r"\u5275\u4f5c\u8005|\u4f7f\u7528\u8005|\u7528\u6236))"
            r"(?=[^\r\n]*(?:\b(?:verdict|rejected|complained|criticized|criticised|feedback|private\s+reference|no[- ]face)\b|"
            r"\u6293\u5305|\u88c1\u6c7a|\u9ede\u540d|\u6279\u8a55|\u56de\u994b|\u5acc|\u4eba\u5de5\u8a55|"
            r"\u6dd8\u6c70|\u4e0d\u53ca\u683c|\u771f\u6210\u7247|\u79c1\u4eba\u53c3\u8003|\u4e0d\u9732\u81c9))"
            r"[^\r\n]+$"
        ),
    ),
    (
        "raw-user-quote",
        re.compile(
            r"(?i)(?:\bHao(?:0321)?\b|\bcreator\b|\buser\b|\u5275\u4f5c\u8005|\u4f7f\u7528\u8005|\u7528\u6236)"
            r"[^\r\n]{0,35}(?:complained|rejected|criticized|criticised|feedback|challenge|verdict|\u4fee\u6b63|\u6279\u8a55|\u56de\u994b|\u5acc|\u88c1\u6c7a|\u9ede\u540d|\u62b1\u6028)"
            r"[^\r\n]{0,20}[\u300c\u300e].{2,120}[\u300d\u300f]"
        ),
    ),
    (
        "creator-reference-count",
        re.compile(
            r"(?is)(?:\buser\b|\u4f7f\u7528\u8005|\u7528\u6236|\u79c1\u4eba|\bcreator(?:'s)?\b)"
            r".{0,50}(?:supplied|provided|private|personal|\u63d0\u4f9b|\u7d2f\u7a4d|\u9910\u5165|\u79c1\u4eba)"
            r".{0,35}\d+\s*(?:\u5f35|\u652f|\u7bc7|\u500b|\u6bb5|\u7b46|\u4efd|samples?|references?)"
            r".{0,70}(?:\u53c3\u8003|\u6a23\u672c|\u5f71\u7247|\u9010\u5b57\u7a3f|\u7d20\u6750|profile|dataset)"
        ),
    ),
    (
        "sample-performance-result",
        re.compile(
            r"(?is)(?:\b(?:actual|observed|private|outcome|result)\b|\u5be6\u6e2c|\u771f\u5be6|\u79c1\u4eba|\u6210\u6548)"
            r".{0,60}(?:\u6a23\u672c|sample)\s*#?\d+.{0,120}"
            r"(?:\d+(?:[.,]\d+)*%|\d+[\d,]*\s*(?:views?|\u89c0\u770b|\u8a02\u95b1))"
        ),
    ),
    (
        "dated-feedback-quote",
        re.compile(
            r"(?im)^(?=[^\r\n]*(?:19|20)\d{2}[-/.]\d{1,2}[-/.]\d{1,2})"
            r"(?=[^\r\n]*(?:feedback|review|comment|\u56de\u994b|\u610f\u898b|\u4eba\u5de5\u8a55))"
            r"(?=[^\r\n]*[\u300c\u300e].{1,120}[\u300d\u300f])[^\r\n]+$"
        ),
    ),
    (
        "observed-location-coverage",
        re.compile(
            r"(?im)^(?![^\r\n]*(?:PUBLIC_FIXTURE|synthetic|example|sample))"
            r"(?=[^\r\n]*(?:observed|actual|outcome|result|\u5be6\u6e2c|\u5be6\u969b|\u771f\u5be6))"
            r"(?=[^\r\n]*(?:\bGPS\b|geolocation|location|\u5b9a\u4f4d|\u5ea7\u6a19))"
            r"(?=[^\r\n]*\b\d{1,3}(?:\.\d+)?\s*%)[^\r\n]+$"
        ),
    ),
    (
        "nonportable-drive-root",
        re.compile(
            r"(?i)(?<![A-Za-z0-9%?])[A-Z]:[\\/]+"
            r"(?!(?:[AbBdDsSwWZfnrtv])(?:[+*?:'\"\\\s]|$))"
            r"(?!(?:\.{3}|<[^>\r\n]+>|%[A-Z0-9_]+%|\$\{?[A-Z_][A-Z0-9_]*\}?|"
            r"my-videos|assets|episode|sample|example|\u67d0\u8cc7\u6599\u593e|Windows|"
            r"Users[\\/]+(?:<[^>\r\n]+>|%[A-Z0-9_]+%|\$\{?[A-Z_][A-Z0-9_]*\}?|"
            r"example-user|sample-user|\u4f5c\u8005\u540d))"
            r"(?:[\\/]|\b))[^\\/\r\n`<>:\"|?*'()\[\]]+"
            r"(?![:+*?\[\]])"
        ),
    ),
    (
        "user-home-path",
        re.compile(
            r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:[\\/]+Users[\\/]+|/(?:Users|home)/)"
            r"(?!(?:<[^>\r\n]+>|%[A-Z0-9_]+%|\$\{?[A-Z_][A-Z0-9_]*\}?|"
            r"example-user|sample-user|\u4f5c\u8005\u540d)(?:[\\/]|\b))"
            r"[^\\/\r\n]+"
        ),
    ),
    (
        "secret-shaped-token",
        re.compile(
            r"(?i)(?:ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
            r"sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|"
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"
        ),
    ),
    (
        "email-address",
        re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    ),
)

_PRIVACY_IMPLEMENTATION_PREFIXES = (
    "scripts/public_privacy_",
    "scripts/public_sync_",
)
_IMPLEMENTATION_LITERAL_RULES = frozenset({
    "nonportable-drive-root",
    "user-home-path",
    "secret-shaped-token",
    "email-address",
})


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _literal_actor_allowlist(text: str) -> bool:
    """Detect identity checks that bind ``actor`` to inline string literals."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Compare):
            continue
        left = node.left
        for operator, right in zip(node.ops, node.comparators):
            actor_operand = any(
                isinstance(child, ast.Name) and child.id.casefold() == "actor"
                for child in ast.walk(left)
            )
            literal_collection = isinstance(right, (ast.Set, ast.List, ast.Tuple))
            has_string_literal = literal_collection and any(
                isinstance(element, ast.Constant) and isinstance(element.value, str)
                for element in right.elts
            )
            if isinstance(operator, (ast.In, ast.NotIn)) and actor_operand and has_string_literal:
                return True
            left = right
    return False


def public_privacy_findings(relative_path: str | Path, text: str) -> list[str]:
    """Return rule names only; never echo matching private content."""
    name = str(relative_path).replace("\\", "/")
    normalized = _lf(text)
    rules = _RULES
    if name.endswith(".py") and name.startswith(_PRIVACY_IMPLEMENTATION_PREFIXES):
        # These modules necessarily encode the semantic shapes enforced above.
        # They remain subject to literal path, credential and identity-deny
        # checks here and in release_manager; only rule-definition shapes are
        # exempt from recursively matching themselves.
        rules = tuple(row for row in _RULES if row[0] in _IMPLEMENTATION_LITERAL_RULES)
    # Release paths are public data too. Scan both contents and the exact
    # relative name, but return labels only so a private-shaped filename is
    # never reflected into CI logs or release-manager errors.
    findings = [
        label for label, pattern in rules
        if pattern.search(normalized) or pattern.search(name)
    ]
    if name.endswith(".py") and _literal_actor_allowlist(normalized):
        findings.append("literal-actor-identity-allowlist")
    return findings


def assert_global_public_text_safe(relative_path: str | Path, text: str) -> None:
    findings = public_privacy_findings(relative_path, text)
    if findings:
        joined = ", ".join(findings)
        raise PublicPrivacyError(f"public privacy gate failed: {joined}")


_TEXT_SUFFIXES = {
    ".css", ".csv", ".html", ".ini", ".js", ".json", ".md", ".mjs",
    ".py", ".svg", ".toml", ".ts", ".txt", ".yaml", ".yml",
}


def _release_files(root: Path) -> list[Path]:
    """Use the release builder's exact include/exclude contract."""
    module_path = root / "src" / "release_manager.py"
    spec = importlib.util.spec_from_file_location(
        "_video_autopilot_release_manager", module_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load release manager: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = module.read_json(root / "release-manifest.json")
    return module.collect_release_files(root, manifest)


def scan_repository(root: Path) -> list[list[str]]:
    """Scan every release path plus decodable text, returning labels only."""
    findings: list[list[str]] = []
    for path in _release_files(root):
        relative = path.relative_to(root).as_posix()
        text = ""
        if path.suffix.lower() in _TEXT_SUFFIXES or path.name == "LICENSE":
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                text = ""
        labels = public_privacy_findings(relative, text)
        if labels:
            findings.append(labels)
    return findings


def _selftest() -> None:
    safe = (
        "Hao Video Autopilot is maintained at "
        "https://github.com/Hao0321/video-autopilot-kit.\n"
        "Use D:/my-videos or D:/.../assets for a generic example.\n"
        "PUBLIC_FIXTURE metrics are synthetic and contain no creator result.\n"
        "Video Autopilot feedback ingestion uses hao.video-autopilot.edit-plan/v4.\n"
        "## 2099-03-04 public research update\n"
        "The user requests a generic cleanup example.\n"
    )
    assert not public_privacy_findings("README.md", safe)
    approved_license = "MIT License\n\nCopyright (c) 2026 Hao0321 Studio\n"
    assert not public_privacy_findings("LICENSE", approved_license)
    public_placeholders = (
        "Use E:/<project-root>/assets, /Users/<name>/Videos, or "
        "/home/<user>/project in portable documentation.\n"
    )
    assert not public_privacy_findings(
        "examples/<project>/README.md", public_placeholders
    )

    joined = lambda *parts: "".join(parts)
    fixtures = {
        "local-project-id": joined("Local example long", "form", "03 incident"),
        "creator-performance-metric": joined(
            "The creator actual outcome A", "VP was 41", ".2% in a local run"
        ),
        "dated-creator-verdict": joined(
            "Creator review on 2099-", "02-03 rejected this batch"
        ),
        "raw-user-quote": joined(
            "User rejected with ", chr(0x300C), "synthetic private correction", chr(0x300D)
        ),
        "creator-reference-count": joined(
            "User supplied 29 refe", "rence samples in a private dataset"
        ),
        "sample-performance-result": joined(
            "Actual sam", "ple 17 reached 81", ".4% retention"
        ),
        "dated-feedback-quote": joined(
            "2099-03-04 ", chr(0x300c), "private correction", chr(0x300d), " feedback"
        ),
        "observed-location-coverage": joined(
            "Observed G", "PS coverage reached 87", "% in the private run"
        ),
        "nonportable-drive-root": joined(
            "E", ":/", "private-workspace/source.mov"
        ),
        "user-home-path": joined(
            "C", ":/", "Users/private-user/project/file.txt"
        ),
        "secret-shaped-token": joined(
            "github_", "pat_", "abcdefghijklmnopqrstuvwxyz123456"
        ),
        "email-address": joined("private.person", "@", "example.test"),
    }
    for expected, fixture in fixtures.items():
        findings = public_privacy_findings("synthetic.txt", fixture)
        assert expected in findings, (expected, findings)
    actor_fixture = joined(
        "if str(actor).lower() not in {", repr("owner-one"), ", ",
        repr("owner-two"), "}:\n    raise PermissionError()\n"
    )
    actor_findings = public_privacy_findings("synthetic.py", actor_fixture)
    assert "literal-actor-identity-allowlist" in actor_findings, actor_findings

    license_fixtures = {
        "secret-shaped-token": joined(
            "github_", "pat_", "abcdefghijklmnopqrstuvwxyz123456"
        ),
        "email-address": joined("private.person", "@", "example.test"),
        "nonportable-drive-root": joined("F", ":/", "private/license.txt"),
    }
    for expected, fixture in license_fixtures.items():
        findings = public_privacy_findings("LICENSE", approved_license + fixture)
        assert expected in findings, (expected, findings)

    for fixture in (
        joined("/", "Users/private-user/project/file.txt"),
        joined("/", "home/private-user/project/file.txt"),
    ):
        findings = public_privacy_findings("synthetic.txt", fixture)
        assert "user-home-path" in findings, findings

    private_relative = joined("exports/private.person", "@", "example.test.txt")
    relative_findings = public_privacy_findings(private_relative, "safe public text")
    assert "email-address" in relative_findings, relative_findings
    try:
        assert_global_public_text_safe(private_relative, "safe public text")
    except PublicPrivacyError as exc:
        message = str(exc)
        assert "email-address" in message
        assert private_relative not in message
    else:
        raise AssertionError("private-shaped relative filename was accepted")
    total_rules = len(_RULES) + 1
    print(f"PUBLIC GLOBAL PRIVACY SELFTEST GREEN: {total_rules} rules")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run global public privacy fixtures")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--repository",
        type=Path,
        help="repository root; only files selected by release-manifest.json are scanned",
    )
    args = parser.parse_args()
    if not args.self_test and args.repository is None:
        parser.error("use --self-test and/or --repository ROOT")
    if args.self_test:
        _selftest()
    if args.repository is not None:
        root = args.repository.resolve()
        findings = scan_repository(root)
        for labels in findings:
            print(f"[BLOCK] {', '.join(labels)}")
        if findings:
            print(f"PUBLIC GLOBAL PRIVACY RED: {len(findings)} files")
            return 1
        print("PUBLIC GLOBAL PRIVACY GREEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
