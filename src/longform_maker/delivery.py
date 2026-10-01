# -*- coding: utf-8 -*-
"""Required delivery boundary for long-form builders."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parent.parent
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

try:
    from .. import publish_hub  # type: ignore[import-not-found]  # noqa: E402
    from ..autonomy_standard import assess_and_enqueue  # type: ignore[import-not-found]  # noqa: E402
except ImportError:  # direct-script compatibility
    import publish_hub  # noqa: E402
    from autonomy_standard import assess_and_enqueue  # noqa: E402


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return {}


def register_completed_longform(folder_id: str | int,
                                qa: dict[str, Any]) -> dict[str, Any]:
    """Register a QA-green ``_out/current.mp4`` before reporting success."""
    source = publish_hub.LONGFORM_ROOT / str(int(folder_id)) / "_out" / "current.mp4"
    plan_path = Path(str(qa.get("visual_plan") or source.parent / "current_visual_plan.json"))
    visual_plan = _read_json(plan_path) if plan_path.is_file() else {}
    quality_path = Path(str((qa.get("quality_95") or {}).get("report") or ""))
    quality = _read_json(quality_path) if quality_path.is_file() else None
    qa["autonomy"] = assess_and_enqueue(
        content_id="L%03d" % int(folder_id), format="longform", artifact=source,
        qa=qa, visual_plan=visual_plan, quality_report=quality)
    return publish_hub.register_completed_longform(folder_id, qa)


def selftest() -> None:
    assert callable(register_completed_longform)
    assert callable(assess_and_enqueue)
    print("longform delivery self-test GREEN")


if __name__ == "__main__":
    selftest()
