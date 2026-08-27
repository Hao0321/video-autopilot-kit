# -*- coding: utf-8 -*-
"""Small facade for source color, trend and filter planning.

Keeping this boundary prevents the top-level visual director from becoming an
architecture hotspot while the three lower-level systems remain independently
testable and reusable.
"""
from __future__ import annotations

from filter_runtime import plan_filter_system
from visual_master import plan_color_system, plan_trend_system

__all__ = ["plan_color_system", "plan_trend_system", "plan_filter_system"]
