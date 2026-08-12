# -*- coding: utf-8 -*-
"""Hao Motion Asset Pack — 可重用動態素材庫。

產出 12 個功能型模板，橫式／直式各一套：
  backgrounds: urban_collage_signal / perspective_grid_rush /
               halftone_orbit / signal_blueprint
  overlays:    focus_hud / speed_streaks / scan_sweep / kinetic_marks
  transitions: diagonal_slash / grid_shutter / signal_glitch / paper_flash

Overlay 使用黑底 + Screen 混合，而不是巨大 alpha MOV；CapCut/ffmpeg 都能穩定調用。
所有 loop 動畫以週期函數製作，不移動 AI 母版本身，避免生成靜圖 KenBurns 抖動。

CLI:
  python motion_asset_pack.py build --aspect all
  python motion_asset_pack.py pick --role overlay --aspect portrait --energy 0.8
  python motion_asset_pack.py list
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from dataclasses import dataclass
from typing import Callable, Iterable

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

import art_direction as art


ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT_ROOT = os.path.join(ROOT, "assets", "broll", "motion")
SOURCE_MASTER = os.path.join(
    ROOT, "assets", "broll", "generated", "_sources", "hao_urban_collage_master_v1.png"
)
MANIFEST_PATH = os.path.join(OUT_ROOT, "manifest.json")
PREVIEW_PATH = os.path.join(OUT_ROOT, "hao_motion_pack_preview.jpg")
DOMAIN_PACK_ROOT = os.path.join(ROOT, "community", "hao-motion-kit")
DOMAIN_MANIFEST_PATH = os.path.join(DOMAIN_PACK_ROOT, "manifest.json")

FPS = 30
ASPECTS = {
    "landscape": {"render": (960, 540), "output": (1920, 1080)},
    "portrait": {"render": (540, 960), "output": (1080, 1920)},
}
INK = (6, 7, 10)
WHITE = (244, 244, 238)
PURPLE = (102, 52, 255)
CYAN = (39, 211, 238)
YELLOW = (239, 236, 0)
RED = (255, 45, 87)


from motion_renderers import AssetSpec, SPECS

def _encode(frames: Iterable[Image.Image], out_path: str, render_size: tuple[int, int],
            output_size: tuple[int, int]) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    vf = f"scale={output_size[0]}:{output_size[1]}:flags=lanczos"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{render_size[0]}x{render_size[1]}", "-r", str(FPS), "-i", "-",
           "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close()
        err = proc.stderr.read().decode("utf-8", errors="replace")
        code = proc.wait()
    except Exception:
        proc.kill()
        raise
    if code:
        raise RuntimeError("motion encode failed: " + err[-800:])


def _frames(spec: AssetSpec, aspect: str, theme: str) -> Iterable[Image.Image]:
    size = ASPECTS[aspect]["render"]
    count = max(2, round(spec.duration * FPS))
    for i in range(count):
        yield spec.renderer(i / count, size, theme)


def _record(spec: AssetSpec, aspect: str, path: str, theme: str) -> dict:
    return {
        "id": spec.id,
        "role": spec.role,
        "aspect": aspect,
        "path": os.path.relpath(path, ROOT).replace("\\", "/"),
        "duration": spec.duration,
        "fps": FPS,
        "resolution": list(ASPECTS[aspect]["output"]),
        "loop": spec.loop,
        "blend_mode": spec.blend_mode,
        "energy": spec.energy,
        "theme": theme,
        "domains": ["general", "ai", "food", "travel", "toy", "product", "game", "diy",
                    "cafe", "documentary", "interview", "automotive", "fitness", "fashion",
                    "architecture", "business", "nature", "music"],
        "tags": list(spec.tags),
        "usage": spec.usage,
        "guardrail": "screen overlay opacity 20-55%; transition 不可連發；glitch 全片最多一次",
    }


def _preview_frame(spec: AssetSpec, aspect: str, theme: str = "general") -> Image.Image:
    frame = spec.renderer(.34, ASPECTS[aspect]["render"], theme).convert("RGB")
    return ImageOps.fit(frame, (320, 180), method=Image.LANCZOS)


def build_preview(out_path: str = PREVIEW_PATH) -> str:
    cols, tile_w, tile_h = 4, 320, 215
    rows = math.ceil(len(SPECS) / cols)
    sheet = Image.new("RGB", (cols*tile_w, rows*tile_h), (12,12,14))
    for i, spec in enumerate(SPECS):
        frame = _preview_frame(spec, "landscape")
        x, y = (i%cols)*tile_w, (i//cols)*tile_h
        sheet.paste(frame, (x,y))
        d = ImageDraw.Draw(sheet)
        d.rectangle([x,y+180,x+tile_w,y+tile_h], fill=(10,10,12))
        d.text((x+10,y+188), f"{spec.role.upper()}  {spec.id}", fill=WHITE)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    sheet.save(out_path, quality=92)
    return out_path


def build_pack(aspects=("landscape", "portrait"), theme: str = "general",
               only: set[str] | None = None) -> dict:
    records = []
    for aspect in aspects:
        if aspect not in ASPECTS:
            raise ValueError("unknown aspect: " + aspect)
        folder = os.path.join(OUT_ROOT, aspect)
        for spec in SPECS:
            if only and spec.id not in only:
                continue
            out = os.path.join(folder, spec.role + "s", spec.id + ".mp4")
            _encode(_frames(spec, aspect, theme), out,
                    ASPECTS[aspect]["render"], ASPECTS[aspect]["output"])
            records.append(_record(spec, aspect, out, theme))
            print(f"[{aspect}] {spec.id} OK")
    manifest = {
        "version": 1,
        "style": "hao_signal_grid_motion",
        "source_master": os.path.relpath(SOURCE_MASTER, ROOT).replace("\\", "/"),
        "influence_note": "原創都市科技平面語言；高對比黑白、格線、拼貼、斜切與少量題材色，不複製任何遊戲資產",
        "selection_rule": "先依 role/aspect 篩選，再選 energy 最接近；同素材不可連用",
        "assets": records,
    }
    os.makedirs(OUT_ROOT, exist_ok=True)
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    build_preview()
    return manifest


def load_manifest(path: str = MANIFEST_PATH, include_domains: bool = True) -> dict:
    if not os.path.isfile(path):
        manifest = {"version": 1, "style": "procedural_motion_fallback", "generated": False,
                    "build_command": "python src/motion_asset_pack.py build --aspect all",
                    "assets": [{"id": spec.id, "role": spec.role, "aspect": aspect,
                                "path": "procedural://%s/%s" % (aspect, spec.id),
                                "duration": spec.duration, "fps": FPS,
                                "resolution": list(ASPECTS[aspect]["output"]),
                                "loop": spec.loop, "blend_mode": spec.blend_mode,
                                "energy": spec.energy, "theme": "general",
                                "domains": ["general", "ai", "food", "travel", "toy", "product", "game", "diy", "cafe", "documentary", "interview", "automotive", "fitness", "fashion", "architecture", "business", "nature", "music"],
                                "tags": list(spec.tags), "usage": spec.usage,
                                "requires_build": True}
                               for aspect in ASPECTS for spec in SPECS]}
    else:
        with open(path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    if include_domains and os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(MANIFEST_PATH)):
        if not os.path.isfile(DOMAIN_MANIFEST_PATH):
            return manifest
        with open(DOMAIN_MANIFEST_PATH, "r", encoding="utf-8") as f:
            domain_manifest = json.load(f)
        domain_assets = []
        for src in domain_manifest.get("assets", []):
            item = dict(src)
            absolute = os.path.join(DOMAIN_PACK_ROOT, item["package_path"].replace("/", os.sep))
            item["path"] = os.path.relpath(absolute, ROOT).replace("\\", "/")
            item["domains"] = [item["domain"]]
            item["theme"] = item["domain"]
            item["source_pack"] = "hao-motion-kit"
            domain_assets.append(item)
        manifest = dict(manifest)
        manifest["domain_pack_manifest"] = os.path.relpath(DOMAIN_MANIFEST_PATH, ROOT).replace("\\", "/")
        manifest["assets"] = domain_assets + list(manifest.get("assets", []))
    return manifest


def choose_asset(role: str, aspect: str = "landscape", energy: float = .5,
                 domain: str = "general", exclude: Iterable[str] = ()) -> dict:
    manifest = load_manifest()
    banned = set(exclude)
    candidates = [a for a in manifest["assets"]
                  if a["role"] == role and a["aspect"] == aspect and a["id"] not in banned]
    if not candidates:
        raise LookupError(f"no motion asset role={role!r} aspect={aspect!r}")
    candidates.sort(key=lambda a: (
        0 if a.get("domains") == [domain] else (1 if domain in a.get("domains", []) else 2),
        abs(float(a["energy"]) - float(energy)),
        a["id"],
    ))
    return candidates[0]


def _append_asset_cue(cues: list[dict], used: set[str], *, cue_type: str,
                      role: str, t: float, energy: float, reason: str,
                      mode: str, aspect: str, domain: str,
                      max_duration: float | None = None,
                      domain_hint: str | None = None) -> None:
    asset = choose_asset(role, aspect, energy, domain_hint or domain, used)
    used.add(asset["id"])
    cue = {
        "t": round(max(0.0, float(t)), 2), "cue_type": cue_type, "mode": mode,
        "asset_id": asset["id"], "path": asset["path"], "role": role,
        "blend_mode": asset["blend_mode"], "energy": asset["energy"], "reason": reason,
    }
    if max_duration is not None:
        cue["max_duration"] = round(float(max_duration), 2)
    cues.append(cue)


def plan_asset_cues(energy_curve: list[dict], events: list[dict], format_kind: str,
                    domain: str = "general") -> dict:
    """把 Cinematic Wave 轉成少量、可解釋的素材調用點。

    背景只在沒有更好 footage 時補；overlay 最多 2 顆；transition 最多 2 顆。
    這裡刻意不做「每 N 秒塞效果」，避免素材庫愈大影片反而愈吵。
    """
    aspect = "portrait" if format_kind == "short" else "landscape"
    curve = list(energy_curve or [])
    if not curve:
        return {"manifest": os.path.relpath(MANIFEST_PATH, ROOT).replace("\\", "/"),
                "aspect": aspect, "cues": []}
    named = {x.get("name"): x for x in curve}
    cues, used = [], set()

    # Cold opens must first show the strongest footage and promise.  A grid,
    # HUD, frame or domain decoration is never an automatic opener; it may be
    # selected later only when the scene semantics actually call for it.
    breath = named.get("breath")
    if breath:
        _append_asset_cue(
            cues, used, cue_type="breath_bed", role="background",
            t=breath["start"], energy=breath["energy"],
            reason="呼吸段若缺主素材，用低能量設計底承接字卡",
            mode="replace_only_if_no_footage",
            max_duration=min(2.4, float(breath["end"]) - float(breath["start"])),
            aspect=aspect, domain=domain,
        )
    payoff = named.get("payoff")
    if payoff:
        _append_asset_cue(
            cues, used, cue_type="payoff_focus", role="overlay",
            t=payoff["start"], energy=payoff["energy"],
            reason="payoff 只加一層焦點動態，不遮真實證據",
            mode="screen_overlay", max_duration=1.2,
            aspect=aspect, domain=domain,
        )

    # 只取兩個真正的 semantic turn；identity_plate 不另塞 transition。
    payoff_start = float(payoff["start"]) if payoff else -999.0
    turns = [e for e in events or []
             if e.get("type") == "pattern_interrupt"
             and e.get("verified_transition") is True
             and len(e.get("shot_pair") or []) == 2
             and e.get("transition_motivation")
             and abs(float(e.get("t", 0)) - payoff_start) > 1.35][:2]
    for e in turns:
        _append_asset_cue(
            cues, used, cue_type="semantic_stinger", role="transition",
            t=e.get("t", 0), energy=e.get("intensity", .6),
            reason="相鄰鏡頭、動作方向與切點均已驗證後才使用短 stinger",
            mode="full_frame_stinger",
            max_duration=min(.9, float(e.get("duration", .7))),
            aspect=aspect, domain=domain,
        )
    return {
        "manifest": os.path.relpath(MANIFEST_PATH, ROOT).replace("\\", "/"),
        "aspect": aspect,
        "usage_guardrails": [
            "background 只有在沒有更好 footage 時使用",
            "overlay 使用 Screen，建議 opacity 20-55%，不得壓住臉、產品、字幕或 proof",
            "transition 必須有 verified shot pair + 動作或遮擋連續性；沒有證據就 clean cut",
            "同一素材不可連續使用；高能素材後要留乾淨鏡頭",
        ],
        "cues": sorted(cues, key=lambda x: x["t"]),
    }


def _self_test() -> None:
    for aspect, cfg in ASPECTS.items():
        for spec in SPECS:
            frame = spec.renderer(.25, cfg["render"], "ai")
            assert frame.size == cfg["render"] and frame.mode == "RGB", (aspect, spec.id, frame.mode)
        for spec in SPECS:
            if spec.loop:
                a = spec.renderer(0, cfg["render"], "general")
                b = spec.renderer(1, cfg["render"], "general")
                assert a.tobytes() == b.tobytes(), f"loop mismatch: {aspect}/{spec.id}"
    assert len({s.id for s in SPECS}) == len(SPECS)
    cold_only = [{"name": "cold_open", "start": 0.0, "end": 1.0, "energy": .9}]
    for domain in ("toy", "travel", "food", "ai", "general"):
        cold_plan = plan_asset_cues(cold_only, [], "short", domain)
        assert not any(c["cue_type"] == "identity_motion" for c in cold_plan["cues"])
    unverified = [{"type": "pattern_interrupt", "t": 2.0, "duration": .5,
                   "intensity": .8}]
    assert not any(c["role"] == "transition"
                   for c in plan_asset_cues(cold_only, unverified, "short", "toy")["cues"])
    print("motion_asset_pack self-test OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command")
    b = sub.add_parser("build")
    b.add_argument("--aspect", choices=("all", "landscape", "portrait"), default="all")
    b.add_argument("--theme", default="general")
    b.add_argument("--only", default="", help="comma-separated asset ids")
    p = sub.add_parser("pick")
    p.add_argument("--role", choices=("background", "overlay", "transition"), required=True)
    p.add_argument("--aspect", choices=tuple(ASPECTS), default="landscape")
    p.add_argument("--energy", type=float, default=.5)
    p.add_argument("--domain", default="general")
    sub.add_parser("list")
    args = ap.parse_args()
    if args.command == "build":
        aspects = tuple(ASPECTS) if args.aspect == "all" else (args.aspect,)
        only = {x.strip() for x in args.only.split(",") if x.strip()} or None
        _self_test()
        result = build_pack(aspects, args.theme, only)
        print(f"MOTION PACK DONE: {len(result['assets'])} files")
    elif args.command == "pick":
        print(json.dumps(choose_asset(args.role, args.aspect, args.energy, args.domain),
                         ensure_ascii=False, indent=2))
    elif args.command == "list":
        print(json.dumps(load_manifest(), ensure_ascii=False, indent=2))
    else:
        _self_test()
        ap.print_help()


if __name__ == "__main__":
    main()
