# -*- coding: utf-8 -*-
"""Grouped validators used by the stable :mod:`shorts_gate` facade.

This module owns generic Shorts structure, caption-plan, and post-expansion
checks. Battle-specific truth rules and the public API remain in
``shorts_gate.py``.
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class GatePolicy:
    """Immutable thresholds supplied by the compatibility facade."""

    platform_rules: dict
    default_platform: str
    first_cut_max: float
    loop_tolerance: float
    tail_clear: float
    caption_kinds: frozenset
    kinetic_kinds: frozenset
    kind_char_limit: dict
    kinetic_max_ratio: float
    nonwhite_max_ratio: float
    nonwhite_max_colors: int
    risky_patterns: tuple
    reading_warn: float
    reading_fail: float
    caption_dwell_warn: float
    caption_rate_warn: float
    first_frame_ratio: float


@dataclass(frozen=True)
class GateTimeline:
    """Validated timing facts shared by later rule groups."""

    segs: list
    duration: float
    loop_policy: str


def validate_required_fields(spec: dict, fails: list[str]) -> None:
    """S-A/S-E: validate the explicit persistent-label policy and fields."""
    persistent_policy = str(spec.get("persistent_label_policy", "required"))
    if persistent_policy not in {"required", "intro", "omit"}:
        fails.append("S-E persistent_label_policy 僅可為 required/intro/omit")
    required_fields = ["place", "what"] + ([] if persistent_policy == "omit" else ["addr"])
    for key in required_fields:
        if not spec.get(key):
            fails.append("S-A/E 缺 %s（開場識別/地址常駐是鐵則）" % key)


def _validate_duration(spec: dict, duration: float, policy: GatePolicy,
                       fails: list[str]) -> None:
    platform = spec.get("platform", policy.default_platform)
    if platform not in policy.platform_rules:
        fails.append("S-B 未知平台 %r（可用：%s）"
                     % (platform, "/".join(policy.platform_rules)))
        platform_rule = policy.platform_rules[policy.default_platform]
    else:
        platform_rule = policy.platform_rules[platform]
    deadzone = platform_rule["deadzone"]
    if platform_rule["dur_min"] - 0.01 <= duration <= platform_rule["dur_max"] + 0.5:
        return
    if deadzone and deadzone[0] <= duration <= deadzone[1]:
        fails.append("S-B 片長 %.1fs 落在 %d-%ds 死區（兩頭不沾；平台=%s）"
                     % (duration, math.ceil(deadzone[0]), math.floor(deadzone[1]), platform))
    else:
        fails.append("S-B 片長 %.1fs 不在 %.0f-%.0fs 帶（平台=%s）"
                     % (duration, platform_rule["dur_min"], platform_rule["dur_max"], platform))


def _validate_nonloop_battle_contract(spec: dict, segs: list,
                                        fails: list[str]) -> None:
    for left_index, (left_src, left_in, left_duration) in enumerate(segs):
        for right_index in range(left_index + 1, len(segs)):
            right_src, right_in, right_duration = segs[right_index]
            if os.path.normcase(os.path.abspath(left_src)) != \
                    os.path.normcase(os.path.abspath(right_src)):
                continue
            overlap = min(left_in + left_duration, right_in + right_duration) \
                - max(left_in, right_in)
            if overlap > 0.12:
                fails.append(
                    "S-D 禁止 loop 但 seg%d/seg%d 來源重疊 %.2fs（疑似重播或補時）"
                    % (left_index, right_index, overlap)
                )

    if not spec.get("battle_matchup"):
        return
    contract = spec.get("battle_edit_contract") or {}
    if not contract:
        fails.append("S-D 戰鬥片必須提供 battle_edit_contract（展示→戰鬥→單次退場）")
        return
    showcase = list(contract.get("showcase_segments") or [])
    result = list(contract.get("result_segments") or [])
    invalid = [index for index in showcase + result
               if not isinstance(index, int) or index < 0 or index >= len(segs)]
    if invalid:
        fails.append("S-D battle_edit_contract 含無效段落索引：%s" % invalid)
    if not showcase:
        fails.append("S-D 戰鬥片缺手持展示段 showcase_segments")
    elif min(showcase) > 1:
        fails.append("S-D 戰鬥片開場兩段內必須出現手持展示，不得直接從戰鬥開始")
    if not result:
        fails.append("S-D 戰鬥片缺結果／終局段 result_segments")
    elif showcase and min(result) <= min(showcase):
        fails.append("S-D 結果段必須在手持展示之後")
    if contract.get("result_once") and len(result) != 1:
        fails.append("S-D result_once=true 時 result_segments 必須恰好一段")
    if result and result[0] == 0:
        fails.append("S-D 結果段不得放在開頭爆雷")
    if str(contract.get("ending", "")) != "single_pass":
        fails.append("S-D 戰鬥片 ending 必須為 single_pass，禁止重播式片尾")


def _validate_loop(spec: dict, segs: list, loop_policy: str,
                   policy: GatePolicy, fails: list[str]) -> None:
    if loop_policy not in {"required", "forbidden"}:
        fails.append("S-D loop_policy 僅可為 required/forbidden")
    elif spec.get("battle_matchup") and loop_policy != "forbidden":
        fails.append("S-D 戰鬥片禁止無縫 loop；賽果不得拿到開頭或於片尾重播")
    elif loop_policy == "required":
        if segs[-1][0] != segs[0][0]:
            fails.append("S-D 末段未回首段 clip（loop 不成立）")
        else:
            loop_end = segs[-1][1] + segs[-1][2]
            if abs(loop_end - segs[0][1]) > policy.loop_tolerance:
                fails.append("S-D loop 未對齊：末段收在 %.1fs、首段起於 %.1fs"
                             "（運鏡片必須對齊末幀==首幀）" % (loop_end, segs[0][1]))
    else:
        _validate_nonloop_battle_contract(spec, segs, fails)


def validate_timeline(spec: dict, policy: GatePolicy,
                      fails: list[str]) -> GateTimeline:
    """S-B/S-C/S-D plus source existence, preserving legacy fail order."""
    segs = spec["segs"]
    duration = round(sum(segment[2] for segment in segs), 3)
    _validate_duration(spec, duration, policy, fails)
    if segs[0][2] > policy.first_cut_max:
        fails.append("S-C 首刀 %.1fs > 2.0s（2 秒內要有變化）" % segs[0][2])
    loop_policy = str(spec.get("loop_policy", "required"))
    _validate_loop(spec, segs, loop_policy, policy, fails)
    for source, _in_point, _duration in segs:
        if not os.path.isfile(source):
            fails.append("素材不存在：%s" % os.path.basename(source))
    return GateTimeline(segs=segs, duration=duration, loop_policy=loop_policy)


def validate_opening_and_battle(spec: dict, fails: list[str], warns: list[str],
                                matchup_failures, result_findings) -> list:
    """S-A identity and the delegated S-T/S-V battle truth checks."""
    captions = spec["caps_by_seg"]
    segment_zero = [caption for caption in captions if caption[0] == 0]
    segment_one = [caption for caption in captions if caption[0] == 1]
    tracked_identity = [
        str(row.get("text", "")).strip()
        for row in (spec.get("tracked_graphics") or {}).get("tracked_labels", [])
        if str(row.get("text", "")).strip() and str(row.get("evidence", "")).strip()
    ]
    has_verified_battle_identity = bool(spec.get("battle_matchup") and len(tracked_identity) >= 2)
    if not segment_zero:
        fails.append("S-A 開場段沒有任何字幕（首條必須是地名/店名大字）")
    else:
        first_text = "".join(text for text, _color in segment_zero[0][1])
        if spec["place"] not in first_text:
            fails.append("S-A 首條字幕 %r 不含 place=%r" % (first_text, spec["place"]))
        if spec["what"] not in first_text:
            candidates = []
            if len(segment_zero) > 1:
                candidates.append("".join(text for text, _color in segment_zero[1][1]))
            if segment_one:
                candidates.append("".join(text for text, _color in segment_one[0][1]))
            if not candidates and not has_verified_battle_identity:
                fails.append("S-A 缺「一句這是什麼」（seg0 第二條或 seg1 首條）")
            elif not has_verified_battle_identity and not any(
                    spec["what"] in candidate for candidate in candidates):
                warns.append("S-A 開場前兩段找不到 what=%r（有識別句即可，僅提醒）" % spec["what"])

    fails.extend(matchup_failures(spec))
    result_fails, result_warns = result_findings(spec)
    fails.extend(result_fails)
    warns.extend(result_warns)
    return captions


def _color_resolver():
    try:
        from silent_vlog_maker.shorts_vertical import resolve_color
        return resolve_color
    except ImportError:
        try:
            parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
            sys.path.insert(0, parent)
            from silent_vlog_maker.shorts_vertical import resolve_color
            return resolve_color
        except ImportError:
            return None


def _validate_caption_render_contract(spec: dict, captions: list, policy: GatePolicy,
                                      fails: list[str], warns: list[str],
                                      nchars, is_official_go_shoot) -> None:
    resolve_color = _color_resolver()
    if resolve_color:
        for _index, blocks, _kind in captions:
            for _text, color in blocks:
                try:
                    resolve_color(color)
                except AssertionError as exc:
                    fails.append("顏色鍵 %r 非法（%s）" % (color, exc))
                    break

    kinetic = []
    for _index, blocks, kind in captions:
        if kind not in policy.caption_kinds:
            fails.append("S-S 未知字幕模式 %r（可用：%s）"
                         % (kind, "/".join(sorted(policy.caption_kinds))))
            continue
        text = "".join(part for part, _color in blocks)
        official = bool(spec.get("battle_matchup")) and is_official_go_shoot(text)
        if kind in policy.kind_char_limit and not official \
                and nchars(text) > policy.kind_char_limit[kind]:
            fails.append("S-S %s 字幕 %d 字 > %d 字；強效果必須短"
                         % (kind, nchars(text), policy.kind_char_limit[kind]))
        if kind in policy.kinetic_kinds:
            kinetic.append(kind)
    content_count = sum(kind != "addr" for _index, _blocks, kind in captions)
    kinetic_max = max(2, math.ceil(content_count * policy.kinetic_max_ratio))
    if len(kinetic) > kinetic_max:
        fails.append("S-S 動態字幕 %d 條 > %d 條；巨字／浮空字只給 hook、轉折、proof、payoff"
                     % (len(kinetic), kinetic_max))
    for previous, current in zip(kinetic, kinetic[1:]):
        if previous == current:
            warns.append("S-S 連續使用 %s；建議 clean hold 或換另一種語法避免模板感" % current)


def _validate_caption_color_and_claims(spec: dict, captions: list,
                                       policy: GatePolicy, fails: list[str]) -> None:
    tokens = [token for _index, blocks, _kind in captions for token in blocks]
    if tokens:
        nonwhite = [token for token in tokens if token[1] not in ("white", "w")]
        ratio = len(nonwhite) / len(tokens)
        colors = set(token[1] for token in nonwhite)
        if ratio > policy.nonwhite_max_ratio:
            fails.append("S-I 非白字比例 %.0f%% > 35%%" % (ratio * 100))
        if len(colors) > policy.nonwhite_max_colors:
            fails.append("S-I 非白色數 %d > 2 種：%s" % (len(colors), sorted(colors)))

    evidence = spec.get("evidence") or {}
    for _index, blocks, _kind in captions:
        for text, _color in blocks:
            hits = [category for category, pattern in policy.risky_patterns if pattern.search(text)]
            if hits and not str(evidence.get(text, "")).strip():
                fails.append('S-P 高風險宣稱無佐證（%s）：%r —— 在 SPEC["evidence"] '
                             "補「怎麼驗過的」或改寫成畫面撐得住的說法"
                             % ("/".join(hits), text.replace("\n", "/")))


def validate_caption_plan(spec: dict, timeline: GateTimeline, captions: list,
                          policy: GatePolicy, fails: list[str], warns: list[str],
                          nchars, is_official_go_shoot) -> None:
    """S-G/S-S/S-I/S-P checks before caption expansion."""
    last_index = len(timeline.segs) - 1
    if timeline.loop_policy == "required" and any(
            index == last_index for index, _blocks, _kind in captions):
        fails.append("S-G 有字幕綁在 loop 段（接點要乾淨）")
    _validate_caption_render_contract(
        spec, captions, policy, fails, warns, nchars, is_official_go_shoot,
    )
    _validate_caption_color_and_claims(spec, captions, policy, fails)


def _validate_reading_speed(spec: dict, content: list, policy: GatePolicy,
                            fails: list[str], warns: list[str],
                            nchars, is_official_go_shoot) -> None:
    for start, end, blocks, _kind in content:
        chars = sum(nchars(text) for text, _color in blocks)
        dwell = max(end - start, 0.01)
        chars_per_second = chars / dwell
        full_text = "".join(text for text, _color in blocks)
        if bool(spec.get("battle_matchup")) and is_official_go_shoot(full_text):
            continue
        if chars_per_second > policy.reading_fail:
            fails.append("S-R 讀不完：%r %d 字只停 %.2fs = %.1f 字/秒（上限 %.0f）"
                         % (blocks[0][0].replace("\n", "/")[:12], chars, dwell,
                            chars_per_second, policy.reading_fail))
        elif chars_per_second > policy.reading_warn:
            warns.append("S-R 偏快：%r %.1f 字/秒（舒適 <%.0f）——縮短字句或拉長該段"
                         % (blocks[0][0].replace("\n", "/")[:12], chars_per_second,
                            policy.reading_warn))


def _caption_rhythm(content: list, duration: float, policy: GatePolicy,
                    warns: list[str]) -> tuple[float | None, float | None]:
    if not content:
        return None, None
    dwells = sorted(round(caption[1] - caption[0], 3) for caption in content)
    middle = len(dwells) // 2
    median_dwell = dwells[middle] if len(dwells) % 2 else \
        round((dwells[middle - 1] + dwells[middle]) / 2, 3)
    caption_rate = round(len(content) / duration * 60, 1)
    if median_dwell > policy.caption_dwell_warn:
        warns.append("S-O 字幕中位停留 %.2fs > %.1fs —— 直式的節奏主體是換句不是剪點，"
                     "市面樣本 0.63-1.43s（competitor-vertical-teardown §2）"
                     % (median_dwell, policy.caption_dwell_warn))
    if caption_rate < policy.caption_rate_warn:
        warns.append("S-O 換句 %.1f 句/分 < %.0f —— 市面樣本 39.7-75.4，字幕偏稀"
                     % (caption_rate, policy.caption_rate_warn))
    return caption_rate, median_dwell


def _warn_soft_first_frame(spec: dict, policy: GatePolicy, warns: list[str],
                           first_frame_quality) -> None:
    quality = first_frame_quality(spec)
    if not quality or quality["chosen"][0] >= policy.first_frame_ratio * quality["best"][0]:
        return
    warns.append("S-Q 首幀銳利度 %.1f（%s@%.1fs）不到全素材池最高 %.1f 的 60%% —— "
                 "看 FIRSTFRAME.jpg 時比對更銳的候選：%s"
                 % (quality["chosen"][0], quality["chosen"][1], quality["chosen"][2],
                    quality["best"][0], ", ".join("%s@%.1fs=%.1f" % (name, time, sharp)
                                                   for sharp, name, time in quality["top"])))


def finalize_expanded_report(spec: dict, timeline: GateTimeline, policy: GatePolicy,
                             fails: list[str], warns: list[str], *, expand_caps,
                             seg_bounds, report, first_frame_quality, nchars,
                             is_official_go_shoot):
    """Expand captions, run S-D/S-R/S-O/S-Q, and build the legacy report."""
    captions = expand_caps(spec)
    content = [caption for caption in captions if caption[3] != "addr"]
    if content and content[-1][1] > timeline.duration - policy.tail_clear:
        reason = "loop 接點要乾淨" if timeline.loop_policy == "required" else "結果後需保留乾淨退場"
        fails.append("S-D 末字幕距片尾 <%.1fs（%s）" % (policy.tail_clear, reason))
    _validate_reading_speed(
        spec, content, policy, fails, warns, nchars, is_official_go_shoot,
    )
    caption_rate, caption_dwell = _caption_rhythm(content, timeline.duration, policy, warns)
    _warn_soft_first_frame(spec, policy, warns, first_frame_quality)
    result = report(
        fails, warns, dur=timeline.duration, caps=captions, bounds=seg_bounds(spec),
        cap_rate=caption_rate, cap_dwell=caption_dwell,
    )
    return result["ok"], result
