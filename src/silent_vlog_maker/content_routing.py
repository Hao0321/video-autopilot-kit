"""
silent_vlog_maker.content_routing — BACKWARD-COMPAT SHIM (2026-06-20 rank6 拆分).

原 859 行單檔拆成三個聚焦模組（純內部重構，行為不變）：
  - routing.py    : RoutingDecision + detect/recommend/route_content + print_routing_decision
  - checklists.py : PRE_BUILD_CHECKLIST_* + get/print
  - verify.py     : run_verify_steps + validate_checklist_answers

本檔保留為 re-export shim：既有 `from .content_routing import X` 全部零改動。
"""
from .routing import (
    RoutingDecision,
    detect_layout, detect_content_type, recommend_path, recommend_bgm,
    should_use_flower_text, recommend_caption_style,
    route_content, print_routing_decision,
)
from .checklists import (
    PRE_BUILD_CHECKLIST_TEACHING_LONGFORM,
    PRE_BUILD_CHECKLIST_FOOD_VLOG,
    PRE_BUILD_CHECKLIST_TRAVEL_VLOG,
    PRE_BUILD_CHECKLIST_SCREEN_RECORDING_TEACHING,
    PRE_BUILD_CHECKLISTS,
    get_pre_build_checklist, print_pre_build_checklist,
)
from .verify import run_verify_steps, validate_checklist_answers

__all__ = [
    "RoutingDecision", "detect_layout", "detect_content_type", "recommend_path",
    "recommend_bgm", "should_use_flower_text", "recommend_caption_style",
    "route_content", "print_routing_decision",
    "PRE_BUILD_CHECKLIST_TEACHING_LONGFORM", "PRE_BUILD_CHECKLIST_FOOD_VLOG",
    "PRE_BUILD_CHECKLIST_TRAVEL_VLOG", "PRE_BUILD_CHECKLIST_SCREEN_RECORDING_TEACHING",
    "PRE_BUILD_CHECKLISTS", "get_pre_build_checklist", "print_pre_build_checklist",
    "run_verify_steps", "validate_checklist_answers",
]
