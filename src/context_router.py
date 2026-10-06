# -*- coding: utf-8 -*-
"""Build one small, stable context packet for each autopilot job.

The router is a budget boundary, not an aesthetic decision engine.  Hard rules
stay in code; creative choices stay in the visual director.  Full research is
only an escalation source when the compact card cannot resolve an exception.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path

from domain_taxonomy import SUPPORTED_DOMAINS, infer_domain

try:
    from knowledge_lifecycle import select_rules
except ImportError:  # installed legacy copy during additive migration
    select_rules = None


ROOT = Path(__file__).resolve().parent
# Skill layout keeps references beside this module; the public kit keeps them
# under codex-skill/.  A release-managed kit has release-manifest.json above src/.
REFS = next((path for path in (ROOT / "references",
                               ROOT.parent / "codex-skill" / "video-autopilot" / "references")
             if path.is_dir()), ROOT / "references")
KIT_LAYOUT = (ROOT.parent / "release-manifest.json").is_file()
PROFILE_DIR = ROOT.parent / "profiles"
PROFILE_NAMES = ("voice", "brand", "style", "show", "your_context")
PACKET_NAME = "current_context_packet.json"
DEFAULT_MAX_TOKENS = 900
MODE_TOKEN_LIMITS = {
    "plan": 900,
    "build": 800,
    "audit": 1000,
    "learn": 1100,
    "outcome": 650,
}

MODE_CARDS = {
    "plan": "只產生可驗證剪輯計畫，不渲染；先盤點素材、缺口、風險與交付規格。",
    "build": "直接建立 current 成片；沿用可重建快取，QA 綠才原子換版。",
    "audit": "唯讀檢查畫面、聲音、節奏、事實與容量；不得順手覆寫成片或原始素材。",
    "learn": "把回饋提煉成可泛化偏好；先回歸舊 corpus，再決定是否進 gate、路由卡或偏好權重。",
    "outcome": "先確認使用者要的成果與現有狀態，只補完成成果所需的最小工作。",
}

FORMAT_CARDS = {
    "shorts": "9:16；前 1 秒先兌現結果，單一主線，高密度但需留 payoff 呼吸；不得由 16:9 中央裁切。",
    "longform": "16:9；用章節、能量波、J/L cut 與鏡頭組句維持長程留存，不把 Shorts 節拍重複貼滿全片。",
    "vlog": "真實時間、地點與現場聲優先；以移動、行動和觀察串場，不替未知食物／歷史編事實。",
    "interview": "No-Face Documentary：最強一句＋真 proof 冷開；H/G 形狀＋文字辨識講者，以操作、手部／環境、文件與圖解承載畫面。禁人物臉、AI 頭像、剪影、reaction face；純波形滿版不超過 3 秒。",
}

# The interview card follows the creator's face policy (profiles/brand.md).
INTERVIEW_CARDS = {
    "no_face": FORMAT_CARDS["interview"],
    "on_camera": "訪談：最強一句＋真 proof 冷開；主持人出鏡依 profiles/brand.md，來賓的臉需本人同意；操作、文件與圖解承載證據，純波形滿版不超過 3 秒。",
    "unset": "訪談：最強一句＋真 proof 冷開；出鏡政策未設定——先讀 profiles/brand.md 或詢問創作者，不預設露臉或不露臉；來賓的臉需本人同意。",
}

DOMAIN_CARDS = {
    "ai": "結果→真操作→局部放大→錯誤修正→證據；畫面跟著操作意圖。",
    "food": "環境→製作→質地極近→入口反應；滋滋、切、脆聲高於裝飾 BGM。",
    "travel": "目的地→地標→人物比例→移動 POV→在地細節；聲音先開下一地點。",
    "product": "結論→情境→關鍵規格→真測試→限制→適合誰；規格不能代替證據。",
    "toy": "成品懸念→拆封手部→零件微距→組裝→清楚揭曉；保留 ASMR。",
    "game": "爆點→最短前因→操作→後果→反應；效果不得遮 HUD。",
    "diy": "after→before→材料→關鍵手勢→失敗修正→proof；縮時只留骨架。",
    "cafe": "空間呼吸→手作儀式→質地→飲用→安靜收尾；氛圍不為速度犧牲。",
    "documentary": "人的後果→環境→觀察→證詞→證據→人的反應；現場聲與事實優先。",
    "interview": "強句＋真 proof 冷開→聲音身份→回答主幹→真操作／手部／環境／文件→停頓→可執行結論；B-roll 只補語境，不冒充成果。",
    "automotive": "引擎／動態→車身→操作→速度→觀察→payoff；運動方向必連續。",
    "fitness": "最好動作→目標→準備→動作分解→疲勞→結果；剪點跟呼吸與落地。",
    "fashion": "完整 look→輪廓→材質→穿著動作→前後對比；以姿勢和形狀接鏡。",
    "architecture": "外部→入口→空間序列→人物比例→材質／光→理由；觀眾必須認得路。",
    "business": "反直覺結論→問題成本→案例→真數字→框架→限制；一張圖只說一個關係。",
    "nature": "行為→環境→目標→等待→轉折→結果；wild track 高於裝飾音效。",
    "music": "最強樂句→全景→主表演者→細節→觀眾反應；跟樂句切，不逐拍亂切。",
    "general": "結果→脈絡→行動→轉折→呼吸→payoff；每顆畫面回答當下語意。",
}

# Ordered preferences; only references that exist in this install are routed,
# so a private or sibling-skill source falls back to its public counterpart.
REFERENCE_ROUTES = {
    "shorts": ("shorts-mastery-2026.md", "competitor-vertical-teardown-2026.md"),
    "longform": ("hao-teaching-longform-method.md", "script-retention-2026.md",
                 "editing-master-techniques.md"),
    "vlog": ("genre-editing-craft-2026.md", "cinematic-wave-and-domain-grammar-2026.md"),
    "interview": ("../../interview-show/references/format-bible.md", "script-retention-2026.md",
                  "genre-editing-craft-2026.md"),
}
ROUTE_SOURCE_LIMIT = 2
REFERENCE_ROUTES_FLAT = frozenset(name for names in REFERENCE_ROUTES.values() for name in names)
LAST_RESORT_SOURCES = ("meta-lessons-canon.md", "craft-index.md")

TOPIC_ROUTES = (
    (
        r"Mr\.?\s*Beast.*(?:Tracking|Roto|3D|VFX|字體|文字|動畫|特效|素材|源頭)|"
        r"(?:Tracking|Roto|3D|VFX|字體|文字|動畫|特效|素材|源頭).*Mr\.?\s*Beast",
        "mrbeast-production-source-map.md",
    ),
    (r"3D|三維|Blender|模型|mesh|相機解算", "three-d-and-subject-fx.md"),
    (r"斜角閃|遮罩高光|物件高光|mask.?sheen|車子|陀螺", "three-d-and-subject-fx.md"),
    (r"設計系統|美感|排版|參考圖|視覺風格", "design-reference-dna-v6.md"),
    (r"Mr\.?\s*Beast|挑戰紀錄|價值階梯|資訊能量", "mrbeast-and-yingshi-benchmark.md"),
)

HARD_GUARDRAILS = (
    "事實、數字、菜名與地點沒有來源就不寫；字幕先對真實畫面。",
    "原始素材唯讀；同片只更新 _out/current，歷史留 metadata，不複製整支 MP4。",
    "畫面先服務語意與證據；效果不得遮人臉、產品、操作、字幕或 proof。",
    "字幕安全區、音訊峰值、缺幀、重複鏡頭與輸出完整性由 gate 強制檢查。",
    "護欄可以硬，創意不能硬編碼；構圖、字卡、節奏和轉場依素材語意動態判斷。",
    "字幕與文字效果分軌：長片逐句字幕乾淨；巨字／數字走獨立 overlay。",
)


def estimate_tokens(value) -> int:
    """Conservative local estimate for mixed Traditional Chinese and JSON."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]", text))
    other = len(text) - cjk
    return cjk + math.ceil(max(0, other) / 4)


def _path_label(path: Path) -> str:
    """Return a stable packet path; never charge tokens for a machine path."""
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return resolved.name


def _fingerprint(path: Path) -> dict:
    resolved = path.resolve()
    if not resolved.is_file():
        return {"path": _path_label(path), "missing": True}
    data = resolved.read_bytes()
    return {"path": _path_label(path), "bytes": len(data),
            "sha256_12": hashlib.sha256(data).hexdigest()[:12]}


def creator_face_policy(profile: Path | None = None) -> str:
    """Return no_face / on_camera / unset from the brand profile checkbox."""
    path = profile or PROFILE_DIR / "brand.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        text = ""
    match = re.search(r"露臉嗎？\s*`?\[([ xX])\]\s*會\s*\[([ xX])\]\s*不會", text)
    if match and (match.group(1) != " ") != (match.group(2) != " "):
        return "on_camera" if match.group(1) != " " else "no_face"
    # Private skill installs keep their established no-face card; a public kit
    # must not inherit a maintainer default it never configured.
    return "unset" if KIT_LAYOUT else "no_face"


def _route_paths(route_names: list) -> tuple:
    """Existing sources only, most relevant first, capped per format route."""
    topic_first = [name for name in route_names if name not in REFERENCE_ROUTES_FLAT]
    route = [name for name in route_names if name in REFERENCE_ROUTES_FLAT]
    existing = [(REFS / name).resolve() for name in route if (REFS / name).resolve().is_file()]
    topical = [(REFS / name).resolve() for name in topic_first if (REFS / name).resolve().is_file()]
    return tuple(dict.fromkeys([*topical, *existing[:ROUTE_SOURCE_LIMIT]]))


def _creator_profiles() -> dict:
    present = [name for name in PROFILE_NAMES if (PROFILE_DIR / (name + ".md")).is_file()]
    return {"present": ["profiles/%s.md" % name for name in present],
            "missing": [name for name in PROFILE_NAMES if name not in present]}


def _all_reference_cost() -> dict:
    paths = sorted(REFS.glob("*.md"))
    total_bytes = sum(p.stat().st_size for p in paths)
    total_tokens = sum(estimate_tokens(p.read_text(encoding="utf-8")) for p in paths)
    return {"files": len(paths), "bytes": total_bytes, "estimated_tokens": total_tokens}


def build_context_packet(mode: str = "build", format: str = "shorts", domain: str = "general",
                         topic: str = "", max_tokens: int | None = None) -> dict:
    mode = mode if mode in MODE_CARDS else "build"
    format = format if format in FORMAT_CARDS else "shorts"
    domain = infer_domain(topic, domain, SUPPORTED_DOMAINS)
    max_tokens = int(max_tokens if max_tokens is not None else MODE_TOKEN_LIMITS[mode])
    route_names = list(REFERENCE_ROUTES[format])
    format_card = INTERVIEW_CARDS[creator_face_policy()] if format == "interview" else FORMAT_CARDS[format]
    if re.search(r"字幕|字卡|文字效果|浮空字|巨字|caption|kinetic|Mr\.?\s*Beast", str(topic), re.I):
        route_names.insert(0, "caption-art-direction.md")
    for pattern, reference in TOPIC_ROUTES:
        if re.search(pattern, str(topic), re.I):
            route_names.insert(0, reference)
    # 同一來源只保留一次，並維持「本題最相關」在第一順位；不存在的來源不路由。
    route_paths = _route_paths(route_names)
    last_resort = next((REFS / name for name in LAST_RESORT_SOURCES if (REFS / name).is_file()),
                       REFS / LAST_RESORT_SOURCES[-1])
    # Four is the normal runtime cap; the memory layer itself supports up to six
    # for explicit deep/learn escalation without pushing build packets over 800.
    rule_limit = 6 if mode == "learn" else 4
    knowledge_card = select_rules(mode, format, domain, topic, limit=rule_limit) if select_rules else []
    # Build packets carry the topic only as a routing hint; 64 mixed-language
    # characters are enough and preserve headroom for pinned safety rules.
    topic_limit = 160 if mode in {"learn", "plan"} else 64
    packet = {
        "schema_version": 1,
        "route": {"mode": mode, "format": format, "domain": domain,
                  "topic": str(topic or "")[:topic_limit]},
        "instruction": "只讀這個 packet 執行；遇到列出的 escalation trigger 才加讀一份 source。",
        "mode_card": MODE_CARDS[mode],
        "format_card": format_card,
        "domain_card": DOMAIN_CARDS[domain],
        "knowledge_card": knowledge_card,
        "hard_guardrails": list(HARD_GUARDRAILS),
        "creative_policy": {
            "hard": "只鎖安全、真實、檔案生命週期、技術品質與 Token 上限。",
            "soft": "美感使用偏好權重與素材語意；允許變奏、覆寫與新訓練融合。",
        },
        "quality_95": {
            "target": 95,
            "rule": "已知負面案例可機械封鎖；審美必須由創作者（或其指定審片者）完成時間碼審片才可認證，裝置不限。",
            "artifacts": ["_qa/QUALITY_95.json", "_review/review.html"],
        },
        "escalation": {
            "triggers": ["規則衝突", "新題材沒有 domain card", "QA 連續失敗", "使用者要求深度研究／學習"],
            "read_at_most_one_first": True,
            "sources": [_path_label(p) for p in route_paths],
            "full_canon_last_resort": _path_label(last_resort),
        },
        "source_fingerprints": [_fingerprint(p) for p in route_paths],
        "budget": {"max_tokens": max_tokens},
    }
    if KIT_LAYOUT:
        packet["creator_profiles"] = _creator_profiles()
        packet["instruction"] = ("先讀 creator_profiles.present（聲音、品牌、風格）再執行；缺少的不得自行假設。"
                                 "其餘只讀這個 packet；遇到 escalation trigger 才加讀一份 source。")
    selected_rules = len(packet["knowledge_card"])
    # 不讓新增記憶把固定 packet 撐爆；依排序只從尾端移除全域低優先規則，
    # 任務精確 scoped memory 位於前端，因此不會再次「明明 pinned 卻載不到」。
    while True:
        packet["budget"]["knowledge_rules_selected"] = len(packet["knowledge_card"])
        packet["budget"]["knowledge_rules_trimmed"] = selected_rules - len(packet["knowledge_card"])
        if estimate_tokens(packet) <= max_tokens:
            break
        if packet["knowledge_card"]:
            packet["knowledge_card"].pop()
        elif len(packet["escalation"]["sources"]) > 1:
            # Multi-route topics may not crash a small packet: drop the least
            # relevant escalation source (with its fingerprint) before failing.
            packet["escalation"]["sources"].pop()
            packet["source_fingerprints"].pop()
        else:
            break
    packet["budget"]["estimated_tokens"] = estimate_tokens(packet)
    packet["budget"]["within_budget"] = packet["budget"]["estimated_tokens"] <= max_tokens
    if not packet["budget"]["within_budget"]:
        raise ValueError(f"context packet exceeds budget: {packet['budget']}")
    return packet


def write_context_packet(output_dir: str | os.PathLike, **kwargs) -> dict:
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / PACKET_NAME
    packet = build_context_packet(**kwargs)
    payload = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
    cache_hit = target.is_file() and target.read_text(encoding="utf-8") == payload
    if not cache_hit:
        fd, temp_name = tempfile.mkstemp(prefix=".context-", suffix=".tmp", dir=target_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            os.replace(temp_name, target)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    packet["runtime"] = {"path": str(target), "cache_hit": cache_hit}
    return packet


def audit() -> dict:
    sample = build_context_packet("build", "shorts", "food", "拉麵實測")
    baseline = _all_reference_cost()
    return {
        "reference_library_worst_case": baseline,
        "routed_packet": sample["budget"],
        "estimated_reduction_vs_bulk_load_pct": round(
            100 * (1 - sample["budget"]["estimated_tokens"] / max(1, baseline["estimated_tokens"])), 1
        ),
        "note": "比較值是『把 references 整批載入』的最壞情況，不宣稱過去每次都實際花掉這些 tokens。",
    }


def self_test() -> None:
    short = build_context_packet("build", "shorts", "auto", "拉麵價格實測")
    long = build_context_packet("plan", "longform", "ai", "Claude 教學")
    assert short["route"]["domain"] == "food"
    assert long["route"] == {"mode": "plan", "format": "longform", "domain": "ai", "topic": "Claude 教學"}
    assert short["budget"]["within_budget"] and long["budget"]["within_budget"]
    assert "偏好權重" in short["creative_policy"]["soft"]
    caption = build_context_packet("learn", "longform", "ai", "MrBeast 巨字與數字字幕效果")
    assert any(source.endswith("caption-art-direction.md") for source in caption["escalation"]["sources"])
    assert any(source.endswith("mrbeast-and-yingshi-benchmark.md") for source in caption["escalation"]["sources"])
    interview = build_context_packet("build", "interview", "interview", "全程不露臉創業訪談")
    assert interview["route"]["format"] == "interview"
    assert interview["format_card"] == INTERVIEW_CARDS[creator_face_policy()]
    assert interview["budget"]["within_budget"]
    verbose = build_context_packet("build", "shorts", "toy", "戰鬥陀螺對戰與完整字幕規劃" * 40)
    assert len(verbose["route"]["topic"]) <= 64 and verbose["budget"]["within_budget"]
    for fmt in FORMAT_CARDS:
        routed = build_context_packet("plan", fmt, "general", "")
        assert routed["escalation"]["sources"], "every format must route at least one real source"
        assert not any(item.get("missing") for item in routed["source_fingerprints"]), fmt
    crowded = build_context_packet("outcome", "longform", "ai", "MrBeast 字幕 3D 設計系統 美感")
    assert crowded["budget"]["within_budget"] and crowded["escalation"]["sources"]
    assert "Hao" not in json.dumps(crowded, ensure_ascii=False)
    _self_test_face_policy()
    print("context_router self-test GREEN")


def _self_test_face_policy() -> None:
    with tempfile.TemporaryDirectory(prefix="context-profile-") as temp:
        brand = Path(temp) / "brand.md"
        brand.write_text("- 你會錄 talking-head / 露臉嗎？ `[ ] 會  [x] 不會`\n", encoding="utf-8")
        assert creator_face_policy(brand) == "no_face"
        brand.write_text("- 你會錄 talking-head / 露臉嗎？ `[x] 會  [ ] 不會`\n", encoding="utf-8")
        assert creator_face_policy(brand) == "on_camera"
        brand.write_text("- 你會錄 talking-head / 露臉嗎？ `[ ] 會  [ ] 不會`\n", encoding="utf-8")
        assert creator_face_policy(brand) == ("unset" if KIT_LAYOUT else "no_face")


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    route = sub.add_parser("route")
    route.add_argument("--mode", choices=MODE_CARDS, default="build")
    route.add_argument("--format", choices=FORMAT_CARDS, default="shorts")
    route.add_argument("--domain", default="general")
    route.add_argument("--topic", default="")
    route.add_argument("--max-tokens", type=int, default=None,
                       help="override the mode-specific token ceiling")
    route.add_argument("--output-dir", default=str(ROOT / "_runtime"))
    sub.add_parser("audit")
    sub.add_parser("selftest")
    args = parser.parse_args()
    if args.command == "route":
        result = write_context_packet(args.output_dir, mode=args.mode, format=args.format,
                                      domain=args.domain, topic=args.topic, max_tokens=args.max_tokens)
    elif args.command == "audit":
        result = audit()
    else:
        self_test()
        return 0
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
