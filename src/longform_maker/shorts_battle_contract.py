"""Public workflow component (public distribution).

Configurable workflow component; public fixtures carry no creator data or live proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import re
import os
import sys


def _battle_presentation_failures(auth, fails, motion, names, tracked_rows):
    if motion.get("lock_effects"):
        fails.append("S-W 戰鬥片禁止競技盤／中央鎖定框；請用物件 Tracking 姓名牌")
    if motion.get("hud"):
        fails.append("S-W 戰鬥片禁止框式 HUD；請用無框物件貼附標籤")
    if len(tracked_rows) < 2:
        fails.append("S-W 戰鬥片必須有兩顆陀螺的動態 Tracking 身分標籤")
    mixed_authenticity = set(auth) == {"official", "counterfeit"}
    for side, name, authenticity in zip(("left", "right"), names, auth):
        required_auth = (("正版" if authenticity == "official" else "盜版")
                         if mixed_authenticity else "")
        candidates = [row for row in tracked_rows
                      if name in str(row.get("text", ""))]
        if not candidates:
            fails.append("S-W %s 缺少跟隨主體的名稱標籤：%s" % (side, name))
            continue
        if required_auth and not any(required_auth in str(row.get("text", ""))
                                     for row in candidates):
            fails.append("S-W %s 的 Tracking 標籤缺少真偽：%s｜%s"
                         % (side, required_auth, name))
        if not all(str(row.get("evidence", "")).strip() for row in candidates):
            fails.append("S-W %s 的 Tracking 標籤缺少人工核對證據：%s" % (side, name))
        if any(str(row.get("style", "typography")) not in {"typography", "identity_callout"}
               for row in candidates):
            fails.append("S-W 陀螺身分標籤必須使用無框 typography／identity_callout，不可用面板式 telemetry")

    sheens = list(motion.get("mask_sheens") or [])
    if len(sheens) < 2:
        fails.append("S-W 戰鬥片必須為兩顆陀螺各提供一次主體內黑→彩斜角閃光")
    for index, sheen in enumerate(sheens):
        if str(sheen.get("target_kind", "subject_object")) != "subject_object":
            fails.append("S-W mask_sheens[%d] 只能作用在陀螺主體，不可掃文字／背景" % index)
        if str(sheen.get("subject_class", "")) != "battle_top":
            fails.append("S-W mask_sheens[%d] 必須標記 subject_class=battle_top" % index)
        if str(sheen.get("reveal_mode", "")) != "black_to_color":
            fails.append("S-W mask_sheens[%d] 必須使用 black_to_color 黑→彩斜角閃光" % index)
        if str(sheen.get("shape", "")) not in {"auto_sequence", "sequence", "alpha", "polygon"}:
            fails.append("S-W mask_sheens[%d] 禁止 ellipse／bbox 假遮罩；必須逐幀 matte" % index)
        if not str(sheen.get("evidence", "")).strip():
            fails.append("S-W mask_sheens[%d] 缺少 matte／追蹤人工核對證據" % index)


def _battle_matchup_failures(spec: dict) -> list[str]:
    """驗證戰鬥陀螺對戰的名稱／真偽標示策略。

    `battle_matchup` 是明確資料，不從文案猜正版或盜版：
    official vs official 只顯示名稱；official vs counterfeit 才顯示真偽。
    """
    battle = spec.get("battle_matchup")
    if battle is None:
        return []
    if not isinstance(battle, dict):
        return ["S-T battle_matchup 必須是 dict"]

    left, right = battle.get("left") or {}, battle.get("right") or {}
    names = [str(left.get("name", "")).strip(), str(right.get("name", "")).strip()]
    auth = [str(left.get("authenticity", "")).strip(),
            str(right.get("authenticity", "")).strip()]
    fails = []
    if not all(names):
        fails.append("S-T battle_matchup 左右雙方都必須有 name")
    valid_auth = {"official", "counterfeit", "unknown"}
    if not all(a in valid_auth for a in auth):
        fails.append("S-T authenticity 僅可為 official/counterfeit/unknown")
    if fails:
        return fails

    caps = ["".join(t for t, _c in blocks).strip()
            for _idx, blocks, _kind in spec.get("caps_by_seg", [])]
    tracked = [str(x.get("text", "")).strip()
               for x in (spec.get("tracked_graphics") or {}).get("tracked_labels", [])]
    tracked_rows = list((spec.get("tracked_graphics") or {}).get("tracked_labels", []))
    motion = spec.get("tracked_graphics") or {}
    hud = [str(x.get("label", "")).strip()
           for x in ((spec.get("tracked_graphics") or {}).get("hud") or {}).get("items", [])]
    visible = [x for x in caps + tracked + hud if x]
    visible_joined = "\n".join(visible)

    # S-W：creator 的陀螺視覺語法是「物件貼附姓名牌＋主體 matte 斜角閃光」。
    # 競技盤鎖定框、HUD 卡片與三條線已被人工審核多次否決；對戰成片不得回退。
    _battle_presentation_failures(auth, fails, motion, names, tracked_rows)

    # S-U：BEYBLADE X 官方對戰口號固定為「3・2・1 Go Shoot！」。
    # 「發射」可作一般動作名詞，但不能取代倒數口號。
    slogan_blob = "\n".join(visible + [str(spec.get("what", "")), str(spec.get("place", ""))])
    wrong_slogan = re.compile(r"(?:3\s*[・、，,.]?\s*2\s*[・、，,.]?\s*1|三\s*[、，]?\s*二\s*[、，]?\s*一)\s*(?:發射|发射)", re.I)
    if wrong_slogan.search(slogan_blob):
        fails.append("S-U 戰鬥陀螺倒數口號必須是『3・2・1 Go Shoot！』，禁止寫『3・2・1 發射』")

    if auth == ["official", "official"]:
        redundant = [x for x in visible if "正版" in x]
        if redundant:
            fails.append("S-T 正版對正版只顯示陀螺名稱，禁止真偽冗字：%s"
                         % "/".join(redundant))
        for competitor in names:
            if competitor not in visible_joined:
                fails.append("S-T 正版對正版缺少陀螺名稱：%s" % competitor)
            if any(x == competitor for x in caps):
                fails.append("S-T 名稱已用 Tracking 呈現，不可再用獨立底部字幕重複：%s"
                             % competitor)
    elif set(auth) == {"official", "counterfeit"}:
        for required in ("正版", "盜版"):
            if required not in visible_joined:
                fails.append("S-T 正版對盜版必須清楚標示：%s" % required)
    return fails


def _battle_result_findings(spec: dict) -> tuple[list[str], list[str]]:
    """禁止在沒有逐格證據時，把猜測包裝成官方 Finish 判定。"""
    battle = spec.get("battle_matchup")
    if battle is None:
        return [], []

    caps = ["".join(t for t, _c in blocks).strip()
            for _idx, blocks, _kind in spec.get("caps_by_seg", [])]
    tracked = [str(x.get("text", "")).strip()
               for x in (spec.get("tracked_graphics") or {}).get("tracked_labels", [])]
    hud = [str(x.get("label", "")).strip()
           for x in ((spec.get("tracked_graphics") or {}).get("hud") or {}).get("items", [])]
    visible_text = "\n".join(
        x for x in caps + tracked + hud
        + [str(spec.get("what", "")), str(spec.get("place", ""))] if x
    )

    skill_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if skill_root not in sys.path:
        sys.path.insert(0, skill_root)
    try:
        from beyblade_x_rules import validate_battle_result, visible_finish
    except (ImportError, OSError, ValueError) as exc:
        return [f"S-V BEYBLADE X 規則驗證器無法載入：{exc}"], []

    shown = visible_finish(visible_text)
    result = spec.get("battle_result")
    if result is None:
        if shown:
            return ["S-V 畫面使用官方 Finish 名稱，但缺少 battle_result 逐格判定證據"], []
        return [], []

    verdict = validate_battle_result(
        result,
        matchup=battle,
        visible_text=visible_text,
    )
    failures = [f"S-V {message}" for message in verdict.get("failures", [])]
    warnings = [f"S-V {message}" for message in verdict.get("warnings", [])]
    return failures, warnings
