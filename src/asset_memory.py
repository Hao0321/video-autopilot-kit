# -*- coding: utf-8 -*-
"""Compatibility façade for asset usage and index migration.

New code should import ``asset_usage`` or ``asset_index_migration`` directly.
This module preserves the established public API without making lower layers
construct the application-level registry.
"""
from __future__ import annotations

import os
from typing import Iterable

from asset_index_migration import migrate_index_paths
from asset_usage import asset_fatigue_report, load_usage_snapshot, record_plan_usage


def record_asset_paths(
    paths: Iterable[str | os.PathLike],
    content_id: str,
    feedback: str = "",
    project_root: str | os.PathLike | None = None,
) -> int:
    """Delegate the legacy path API to the registry application boundary."""
    from asset_registry import record_asset_paths as record_with_registry

    return record_with_registry(paths, content_id, feedback, project_root)


__all__ = [
    "asset_fatigue_report",
    "load_usage_snapshot",
    "migrate_index_paths",
    "record_asset_paths",
    "record_plan_usage",
]
