# -*- coding: utf-8 -*-
"""Required delivery boundary for long-form builders."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

import publish_hub  # noqa: E402


def register_completed_longform(folder_id: str | int,
                                qa: dict[str, Any]) -> dict[str, Any]:
    """Register a QA-green ``_out/current.mp4`` before reporting success."""
    return publish_hub.register_completed_longform(folder_id, qa)


def selftest() -> None:
    assert callable(register_completed_longform)
    print("longform delivery self-test GREEN")


if __name__ == "__main__":
    selftest()
