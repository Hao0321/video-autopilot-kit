"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import subprocess, os
import editorial_templates as editorial


_AUTOPILOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_PROJECT_ROOT = os.path.normpath(os.path.join(_AUTOPILOT, "..", "..", ".."))


def _visual_plan_card_events(visual_plan, total):
    """Return explicitly approved gaps that may use a full-frame card.

    A semantic turn is not permission to cover real footage.  Full-frame cards
    are opt-in only and require both an explicit authoring flag and a verified
    footage gap.  Ordinary pattern interrupts stay on the source footage.
    """
    events = []
    for e in (visual_plan or {}).get("events", []):
        t, dur = float(e.get("t", 0)), float(e.get("duration", 0))
        text = str(e.get("source_text", "")).strip()
        if (e.get("type") == "pattern_interrupt" and text and t >= 1.0
                and e.get("allow_full_frame_card") is True
                and e.get("footage_gap_verified") is True
                and e.get("reason") != "payoff_marker"
                and t + dur <= total - 0.8 and dur >= 0.25):
            events.append((t, min(dur, 0.82), text, str(e.get("card", "NOTE"))))
        if len(events) >= 3:
            break
    return events


def _apply_visual_plan_cards(video_in, visual_plan, theme, base, total):
    """只在明確核准的素材缺口使用全屏 Bright Editorial 字卡。

    片頭、一般語意轉折、片尾與 payoff proof 一律保留真畫面；有真實素材時只能使用不遮
    證據的 overlay，不能用 SHAPE / PLAY、TRAVEL / JOURNAL 等通用模板整頁取代畫面。
    """
    events = _visual_plan_card_events(visual_plan, total)
    if not events:
        return video_in

    card_dir = base + "_cards"
    os.makedirs(card_dir, exist_ok=True)
    card_paths = []
    template_cfg = (visual_plan or {}).get("template_system") or {}
    style_hint = template_cfg.get("style")
    topic = (visual_plan or {}).get("domain", theme)
    role_map = {"price": "stat", "score": "stat", "proof": "stat", "steps": "steps",
                "question": "quote", "quote": "quote", "chapter": "chapter",
                "location": "lower_third", "route": "chapter", "verdict": "chapter"}
    for i, (_t, _dur, text, card_type) in enumerate(events, 1):
        p = os.path.join(card_dir, f"card_{i:02d}.png")
        role = role_map.get(card_type.lower(), "hook")
        editorial.render_template(role, text, card_type.upper(), topic=topic, aspect="portrait",
                                  style_hint=style_hint, value=text, seed=f"{text}:{i}").save(p)
        card_paths.append(p)

    workdir = os.path.dirname(os.path.abspath(video_in)) or "."
    cmd = ['ffmpeg', '-v', 'error', '-y', '-i', os.path.basename(video_in)]
    for p in card_paths:
        cmd += ['-loop', '1', '-i', os.path.relpath(p, workdir)]
    filters, prev = [], '[0:v]'
    for i, ((t, dur, _text, _card_type), _p) in enumerate(zip(events, card_paths), 1):
        # 字卡在語意句首硬切。曾試 80ms crossfade，但卡片與底層字幕同句會短暫疊成雙字；
        # 乾淨硬切反而更像設計好的 pattern interrupt，也不犧牲可讀性。
        filters.append(f'[{i}:v]format=rgba[c{i}]')
        out_label = f'[v{i}]'
        filters.append(
            f"{prev}[c{i}]overlay=enable='between(t,{t:.3f},{t+dur:.3f})':shortest=1{out_label}")
        prev = out_label
    decorated = base + '_cards.mp4'
    cmd += ['-filter_complex', ';'.join(filters), '-map', prev, '-an', '-t', str(total),
            '-c:v', 'libx264', '-crf', '19', '-preset', 'medium', '-pix_fmt', 'yuv420p',
            '-r', '30', os.path.basename(decorated)]
    r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode:
        raise RuntimeError('visual plan cards failed: ' + r.stderr[-700:])
    return decorated


def _apply_motion_asset_cues(video_in, visual_plan, base, total):
    """把 motion_assets cues 疊到 Shorts 成片。

    - overlay：素材本身是黑底 Screen 資產；以 colorkey 去黑再控制 38% opacity，避免巨大 alpha MOV。
    - background：只在 visual plan 明確標成 replace_only_if_no_footage 時使用；目前預設略過，
      因 renderer 無法自行判斷該秒是否真的缺 footage，不能拿設計底蓋掉真素材。
    - transition：全屏短 stinger，依 cue 的時間／長度出現。

    每顆 cue 分開編一次，換素材或壞檔時會大聲失敗，不靜默交付半套效果。
    """
    cues = ((visual_plan or {}).get("motion_assets") or {}).get("cues") or []
    semantic_overlay_contracts = {
        "tracked_label", "proof_highlight", "subject_masked_sheen",
        "particle_payoff", "location_or_price_tag",
    }

    def _eligible(cue):
        role = cue.get("role")
        if role == "transition":
            return True
        if role != "overlay":
            return False
        # 防止舊 visual plan 把無語意題材框線重新帶回成片。真正 overlay
        # 必須說清楚它跟哪個主體／證據綁定，及其功能類型。
        return bool(cue.get("semantic_target")) and cue.get("overlay_contract") in semantic_overlay_contracts

    cues = [c for c in cues if _eligible(c)]
    if not cues:
        return video_in
    current = video_in
    workdir = os.path.dirname(os.path.abspath(video_in)) or "."
    for i, cue in enumerate(cues, 1):
        try:
            t = float(cue.get("t", 0))
            dur = min(float(cue.get("max_duration", .8)), max(0.0, total - t))
        except (TypeError, ValueError):
            continue
        if dur < .12 or t < 0 or t >= total:
            continue
        rel = str(cue.get("path", "")).replace("/", os.sep)
        asset = rel if os.path.isabs(rel) else os.path.join(_PROJECT_ROOT, rel)
        if not os.path.isfile(asset):
            raise FileNotFoundError("motion asset missing: " + asset)
        role = cue.get("role")
        shifted = (f"[1:v]trim=start=0:duration={dur:.3f},"
                   f"setpts=PTS-STARTPTS+{t:.3f}/TB")
        if role == "overlay":
            # 黑底素材轉透明；低 opacity 只留下訊號線／HUD，不蓋字幕與主體。
            prep = shifted + ",colorkey=0x000000:0.045:0.10,format=rgba,colorchannelmixer=aa=0.38[fx]"
        else:
            prep = shifted + "[fx]"
        fc = (prep + ";[0:v][fx]overlay=eof_action=pass:repeatlast=0:shortest=0:"
              f"enable='between(t,{t:.3f},{t+dur:.3f})'[v]")
        out_i = base + f"_motion_{i:02d}.mp4"
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", os.path.abspath(current),
               "-i", os.path.abspath(asset), "-filter_complex", fc, "-map", "[v]", "-an",
               "-t", f"{total:.3f}", "-c:v", "libx264", "-crf", "19", "-preset", "medium",
               "-pix_fmt", "yuv420p", "-r", "30", os.path.abspath(out_i)]
        r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode:
            raise RuntimeError("motion cue failed %s: %s" % (cue.get("asset_id"), r.stderr[-800:]))
        current = out_i
    return current
