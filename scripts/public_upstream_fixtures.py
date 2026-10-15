"""Exact public upstream scanner fixtures, independently pinned to v0.22.1.

Only the listed path-shape heuristic may recognize itself. Other privacy rules
still run; a renamed file or any changed byte loses this recognition.
"""
from __future__ import annotations
import hashlib

_REVIEWED = {'tools/code-cleanup-helper/scripts/exposure_formats.py': ('d1560b3e9449a2b872ffbeace7bc9422a6eb9fe4680280a46272f2e3d7a4a33b', ('user-home-path',)), 'tools/code-cleanup-helper/scripts/exposure_formats_regression.py': ('07dfc4fb8435e72cb3a722e151718b20cd82e68a67b062d74f8d1068f7c6a9da', ('user-home-path',)), 'tools/code-cleanup-helper/scripts/exposure_regression.py': ('b464a6cb3010809a2bf190a98496a2c349d903eb2507fbf25b111dc00cb45227', ('user-home-path',)), 'tools/code-cleanup-helper/scripts/exposure_scope_regression.py': ('7a972c47ae4eb1a52ca34f56e0d83517724b900085e3b11b5f3d193f4133f924', ('user-home-path',)), 'tools/code-cleanup-helper/scripts/sync_regression.py': ('bd43592be21e008333bf0f78457fa3ee5296550253321548baeb3442654f6422', ('nonportable-drive-root',))}


def reviewed_fixture_rules(name: str, text: str) -> frozenset[str]:
    row = _REVIEWED.get(name)
    if row is None:
        return frozenset()
    normalized = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != row[0]:
        return frozenset()
    return frozenset(row[1])
