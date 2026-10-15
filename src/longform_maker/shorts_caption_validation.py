"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


CAPTION_COLOR_KEYS = frozenset({
    "w", "r", "o", "y", "g", "b", "p", "v", "c",
    "white", "gold", "yellow", "red", "coral", "orange", "apricot",
    "green", "mint", "blue", "sky", "pink", "purple", "cream",
})


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


def _validate_caption_render_contract(spec: dict, captions: list, policy: GatePolicy,
                                      fails: list[str], warns: list[str],
                                      nchars, is_official_go_shoot) -> None:
    for _index, blocks, _kind in captions:
        for _text, color in blocks:
            if color.strip().lower() not in CAPTION_COLOR_KEYS:
                fails.append("顏色鍵 %r 非法（可用：%s）"
                             % (color, "/".join(sorted(CAPTION_COLOR_KEYS))))
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
    try:
        captions = expand_caps(spec)
    except AssertionError as exc:
        fails.append("S-F " + str(exc))
        return False, report(fails, warns, dur=timeline.duration)
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
