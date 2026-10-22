"""Exact reviewed upstream scanner fixtures.

The bundled Cleanup scanner fixtures were retired with the bundled tool in
v0.25.0, so no release file currently has a reviewed exemption.  A future entry
must pin one exact path, its normalized SHA-256 and the path-shape heuristic
that may recognize itself; other privacy rules still run, and a renamed file
or any changed byte loses this recognition.
"""
from __future__ import annotations
import hashlib

_REVIEWED: dict[str, tuple[str, tuple[str, ...]]] = {}


def reviewed_fixture_rules(name: str, text: str) -> frozenset[str]:
    row = _REVIEWED.get(name)
    if row is None:
        return frozenset()
    normalized = text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != row[0]:
        return frozenset()
    return frozenset(row[1])
