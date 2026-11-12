"""Static compatibility transforms for redistributable canonical sources."""
from __future__ import annotations

import re
from pathlib import Path

from public_privacy_gate import _RULES as _GATE_RULES


_LOCAL_USER = re.escape(Path.home().name)
_CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af"
# Any non-example drive-rooted path (the repository gate's own rule); maintainer
# workspace names and other private terms come from the private control file.
_DRIVE_ROOT = dict(_GATE_RULES)["nonportable-drive-root"]

PRIVACY_PATTERNS = (
    re.compile(rf"[A-Z]:[\\/]Users[\\/]{_LOCAL_USER}(?=[\\/]|$)", re.I),
    _DRIVE_ROOT,
    re.compile("codex-remote-" + "attachments", re.I),
    re.compile(r"AppData[\\/]Local[\\/]Temp", re.I),
    # A CJK inbox folder name in a path, a pathlib expression or an os.path.join call.
    re.compile(r"_INBOX[\"']?\s*[\\/,]\s*[\"']?[^\\/\"'`\s,)]*[" + _CJK + "]"),
)

REPLACEMENTS = (
    (re.compile(
        r"[A-Z]:[\\/]Users[\\/][^\\/]+[\\/]\.codex[\\/]skills[\\/]"
        r"[^\\/]*voice[^\\/]*[\\/][^\\/]*voice[^\\/]*\.md",
        re.I,
     ), "~/.codex/skills/creator-voice/profile.md"),
    # Any drive-rooted sibling-skill evidence ledger becomes a neutral description.
    (re.compile(r"[A-Z]:[\\/](?:[^\\/\s`'\"]+[\\/])+references[\\/]youtube\.md", re.I),
     "the configured evidence ledger"),
    (re.compile(r"Path\(r?[\"'][A-Z]:[\\/][^\"']*?[\\/]videos[\\/]_INBOX[\\/][^\"']+[\"']\)", re.I),
     'Path("<project-root>/videos/_INBOX/<format>/<content-id>")'),
    (re.compile(r"\b[A-Za-z][A-Za-z0-9]* Visual Master\b"), "Visual Master"),
    (re.compile(r"\b[A-Za-z][A-Za-z0-9]* Aesthetic Standard\b"), "Creator Aesthetic Standard"),
    (re.compile(r"\bHAO_REVIEW_REQUIRED\b"), "CREATOR_REVIEW_REQUIRED"),
    (re.compile(r"\breported_by_hao\b"), "reported_by_creator"),
    # Links into the unpublished algorithm skill point to the shipped Shorts reference.
    (re.compile(r"\[?`?yt-algorithm-mastery/references/([a-z0-9-]+)\.md`?\]?\(\.\./\.\./yt-algorithm-mastery/references/\1\.md\)"),
     "[shorts_reels_2026_best_practices.md](shorts_reels_2026_best_practices.md)"),
)

# The legacy one-off remix entry point is published under a neutral demo name.
_DEMO_REMIX_RENAMES = (
    (re.compile(r"\bcreate_(?!demo_)[a-z]+_remix_plan\b"), "create_demo_remix_plan"),
    (re.compile(r'"legacy_[a-z]+_remix"'), '"demo_remix"'),
)

# Fixed public text for the shot-selection reference.
PUBLIC_SHOT_SELECTION_TEXT = """# 挑選鏡頭的一般規則

這份規則整理挑選鏡頭的一般判斷，屬於剪輯經驗，尚未經作品盲審或觀眾成效證實，不能升格為全域美學分數。

## 用法

1. 先確定本片與每個段落的敘事目的，再挑鏡頭；題材如旅遊、產品、AI 不會自動決定挑法。段落之間改變挑法時，要說明原因。
2. 對每顆候選鏡頭記錄來源時間碼、畫面或音訊觀察、段落用途、使用權與反例。沒有實際素材證據時先不挑，補素材或看片紀錄。
3. 候選排序只當人工挑選的順序，不能寫成已驗證的剪輯品質，也不能直接改 Editkin 時間軸。確定鏡頭後，才編入 Editkin v4 plan 並走 audit → apply → render → 創作者審片。
4. 若與真實性、人物意願、授權、劇情因果或已核准的美感方向衝突，這些條件優先；挑鏡頭的個人偏好可以被覆寫。
"""

# Maintainer change dates in code comments describe the maintained source's
# history, not the public kit.  Only `#` comment lines are rewritten.
_DATED_COMMENT_NOTES = (
    (re.compile(r"(?m)^(\s*#[^\n]*?) \((?:19|20)\d{2}-\d{2}-\d{2}\)(?=\.)"), r"\1"),
)

MODULE_REPLACEMENTS = {
    "publish_hub.py": _DEMO_REMIX_RENAMES,
    "publish_hub_ops.py": _DEMO_REMIX_RENAMES + (
        (re.compile(r'LEGACY_READY = VIDEOS / "[^"\n]+"'), 'LEGACY_READY = VIDEOS / "_ready-shorts"', True),
    ),
    "rhythm_templates.py": (
        (re.compile(r'\bART_PENDING_CLAUDE\b'), 'ART_PENDING_REVIEW'),
    ),
    "architecture_gate.py": (
        (re.compile(r'str\(HERE\), "--mode", "architecture"'),
         'str(HERE.parent), "--mode", "architecture"'),
        (re.compile(r'cwd=HERE, capture_output'),
         'cwd=HERE.parent, capture_output'),
    ),
    "beyblade_x_rules.py": (
        (re.compile(r'RULES_PATH = Path\(__file__\)\.resolve\(\)\.parent / "knowledge" / "beyblade_x_rules\.json"'),
         'RULES_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "runtime" / "beyblade_x_rules.json"'),
        (re.compile(r'未經\s+[A-Za-z][A-Za-z0-9]*\s+確認時'), '未經創作者確認時'),
    ),
    "project_paths.py": (
        (re.compile(r'MANIFEST_NAME = "AUTOPILOT_MANIFEST\.json"'),
         'MANIFEST_NAMES = ("AUTOPILOT_MANIFEST.json", "release-manifest.json")\n'
         'MANIFEST_NAME = MANIFEST_NAMES[0]'),
        (re.compile(r'ROOT_ENV_VARS = \("HAO_AUTOPILOT_ROOT", "VIDEO_KIT_PROJECT_ROOT"\)'),
         'ROOT_ENV_VARS = ("VIDEO_AUTOPILOT_ROOT", "VIDEO_KIT_PROJECT_ROOT", "HAO_AUTOPILOT_ROOT")'),
        (re.compile(r'def _has_manifest\(path: Path\) -> bool:\n'
                    r'    return \(path / MANIFEST_NAME\)\.is_file\(\)'),
         'def _has_manifest(path: Path) -> bool:\n'
         '    return any((path / name).is_file() for name in MANIFEST_NAMES)'),
        (re.compile(r'def _looks_like_root\(path: Path\) -> bool:\n    return \(path / MANIFEST_NAME\)\.is_file\(\) or \(\n        \(path / "\.claude" / "skills"\)\.is_dir\(\) and \(path / "assets"\)\.is_dir\(\)\n    \)'),
         'def _looks_like_root(path: Path) -> bool:\n    return any((path / name).is_file() for name in MANIFEST_NAMES) or (\n        (path / ".claude" / "skills").is_dir() and (path / "assets").is_dir()\n    )'),
        (re.compile(r'f"Cannot find \{MANIFEST_NAME\}; run inside the workspace or set HAO_AUTOPILOT_ROOT\."'),
         'f"Cannot find a project manifest; run inside the workspace or set VIDEO_AUTOPILOT_ROOT."'),
        (re.compile(r'\(root / MANIFEST_NAME\)\.write_text'),
         '(root / MANIFEST_NAMES[0]).write_text'),
        (re.compile(r'\b[A-Z]+_PATHS_SELFTEST_SKILL\b'), 'VA_PATHS_SELFTEST_SKILL'),
        (re.compile(r'\([^()]*? since (?:19|20)\d{2}-\d{2}-\d{2}\)'),
         '(for example a canonical Skill kept outside\n    the workspace)'),
    ),
    "project_kernel.py": (
        (re.compile(r'Manifest-driven control plane for the Hao video autopilot\.'),
         'Manifest-driven control plane for Video Autopilot.'),
        (re.compile(r'^ABSOLUTE_LITERAL = re\.compile\(r".*"\)$', re.M),
         'ABSOLUTE_LITERAL = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\\\\\\\/]")'),
        (re.compile(r'from project_paths import MANIFEST_NAME, discover_project_root'),
         'from project_paths import MANIFEST_NAMES, discover_project_root'),
        (re.compile(r'path = workspace / MANIFEST_NAME'),
         'path = next((workspace / name for name in MANIFEST_NAMES\n'
         '                 if (workspace / name).is_file()), workspace / MANIFEST_NAMES[0])'),
        (re.compile(r'if sync\["status"\] != "GREEN":\n        errors\.append\("installed skill copies drift from project canon"\)'),
         'if sync["status"] != "GREEN":\n'
         '        warnings.append("installed skill copy is absent or differs; run project_kernel.py sync apply")'),
        (re.compile(r'assert manifest\["architecture_version"\] == "6\.2"'),
         'assert manifest["architecture_version"] == "6.2"'),
    ) + _DATED_COMMENT_NOTES,
    "project_source_metrics.py": (
        (re.compile(r'^ABSOLUTE_LITERAL = re\.compile\(r".*"\)$', re.M),
         'ABSOLUTE_LITERAL = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\\\\\\\/]")'),
    ),
    "publish_hub_cli.py": (
        (re.compile(
            r'withdraw\.add_argument\("--actor", default="[A-Za-z][A-Za-z0-9]*"\)'
        ), 'withdraw.add_argument("--actor", default="creator")'),
        (re.compile(
            r'description="[A-Za-z][A-Za-z0-9]* unified publishing hub"'
        ), 'description="Video Autopilot publishing hub"'),
    ) + _DEMO_REMIX_RENAMES,
    "knowledge_lifecycle.py": (
        (re.compile(r'DEFAULT_STATE = SKILL_ROOT / "knowledge" / "state\.json"'),
         'DEFAULT_STATE = SKILL_ROOT.parent / "knowledge" / "runtime" / "state.json"'),
        (re.compile(r'DEFAULT_VIDEO_LOG = SKILL_ROOT / "video_log\.md"'),
         'DEFAULT_VIDEO_LOG = SKILL_ROOT.parent / "data" / "video_log.md"'),
        (re.compile(r'DEFAULT_VIDEO_ARCHIVE = SKILL_ROOT / "video_log_archive\.md"'),
         'DEFAULT_VIDEO_ARCHIVE = SKILL_ROOT.parent / "data" / "video_log_archive.md"'),
    ),
    "channel_tracker.py": (
        (re.compile(r'STATE_PATH = os\.path\.join\(_DIR, "channel_state\.json"\)'),
         'STATE_PATH = os.path.join(os.path.dirname(_DIR), "data", "channel_state.json")'),
    ),
    "outcome_learning.py": (
        (re.compile(r'OUTPUT_PATH = ROOT / "knowledge" / "outcome_playbook\.json"'),
         'OUTPUT_PATH = ROOT.parent / "data" / "outcome_playbook.json"'),
        (re.compile(r'TASTE_PATH = ROOT / "knowledge" / "taste_model\.json"'),
         'TASTE_PATH = ROOT.parent / "data" / "taste_model.json"'),
    ),
    "domain_broll_pack.py": (
        (re.compile(r'ROOT = Path\(__file__\)\.resolve\(\)\.parents\[3\]'),
         'ROOT = Path(__file__).resolve().parents[1]'),
    ),
    # Central root discovery; the fallback is the public kit root (the parent of
    # src/), not the canonical Skill's grandparent.
    "asset_license_governance.py": (
        (re.compile(r'discover_project_root\(ROOT, required=False\) or ROOT\.parents\[2\]'),
         'discover_project_root(ROOT, required=False) or ROOT.parent'),
        (re.compile(r'ROOT / "knowledge" /'), 'PROJECT_ROOT / "knowledge" / "runtime" /'),
    ),
    "effect_source_map.py": (
        (re.compile(r'discover_project_root\(ROOT, required=False\) or ROOT\.parents\[2\]'),
         'discover_project_root(ROOT, required=False) or ROOT.parent'),
    ),
    "project_kernel_commands.py": (
        (re.compile(r'\b[A-Z]+_KERNEL_SELFTEST_CANONICAL\b'), 'VA_KERNEL_SELFTEST_CANONICAL'),
        (re.compile(r'description="[A-Za-z][A-Za-z0-9]* Autopilot manifest control plane"'),
         'description="Video Autopilot manifest control plane"'),
    ) + _DATED_COMMENT_NOTES,
    # Self-test floor with margin for the public Skill's include set.
    "skill_sync.py": (
        (re.compile(r'assert result\["declared_files"\] >= \d+, '),
         'assert result["declared_files"] >= 60, '),
    ) + _DATED_COMMENT_NOTES,
    # The public shot-selection reference is a fixed public text.
    "shot-selection-language.md": (
        (re.compile(r"\A.*\Z", re.S), lambda _match: PUBLIC_SHOT_SELECTION_TEXT),
    ),
    # Number-splitting examples in a comment use neutral figures.
    "caption_grouping.py": (
        (re.compile(r'(# \u6578\u5b57\u8170\u65ac\uff1a[^\n]*?)\uff08[^\uff09\n]*\uff09'),
         '\\1\uff083|50\u842c\u30011,|234\u300187.|5%\uff09'),
    ),
    # Same state file as channel_tracker.py in the public layout.
    "publish_hub_context.py": (
        (re.compile(r'SHORTS_ROOT = VIDEOS / "_INBOX" / "[^"\n]+"'), 'SHORTS_ROOT = VIDEOS / "_INBOX" / "vertical"', True),
        (re.compile(r'LONGFORM_ROOT = VIDEOS / "_INBOX" / "[^"\n]+"'),
         'LONGFORM_ROOT = VIDEOS / "_INBOX" / "landscape-longform"', True),
        (re.compile(r'LEGACY_READY = VIDEOS / "[^"\n]+"'), 'LEGACY_READY = VIDEOS / "_ready-shorts"', True),
        (re.compile(r'STATE_PATH = HERE / "channel_state\.json"'),
         'STATE_PATH = HERE.parent / "data" / "channel_state.json"'),
        # Only the public defaults stay.
        (re.compile(r'    \w+ = VIDEOS / "_planning" / "[^"\n]+"\n    matches = sorted\(\w+\.glob\([^\n]*\n'
                    r'    if matches:\n        return matches\[0\]\n'), "", True),
    ),
    "aesthetic_score.py": (
        (re.compile(r'ROOT / "knowledge" /'), 'ROOT.parent / "knowledge" / "runtime" /'),
        (re.compile(r'assert travel\["primary_family"\] == "japanese_lifestyle_calm"'),
         'assert travel["primary_family"] == "travel_scrapbook"'),
        (re.compile(r'assert travel\["template_fallback_required"\]\n'
                    r'    assert travel\["primary_family_render_ready"\] is False'),
         'assert not travel["template_fallback_required"]\n'
         '    assert travel["primary_family_render_ready"] is True'),
    ),
    "design_system_v6.py": (
        (re.compile(r'ROOT / "knowledge" / "design_reference_dna\.json"'),
         'ROOT.parent / "knowledge" / "runtime" / "design_reference_dna.json"'),
        (re.compile(r"Compile\s+[A-Za-z][A-Za-z0-9]*'s\s+\d+-reference\s+design\s+DNA"),
         'Compile the redistributable design seed catalog'),
        (re.compile(r'EXPECTED_REFERENCE_COUNT = \d+'),
         'MINIMUM_PUBLIC_REFERENCE_COUNT = 1'),
        (re.compile(
            r'    if data\.get\("reference_count"\) != EXPECTED_REFERENCE_COUNT or len\(rows\) != EXPECTED_REFERENCE_COUNT:\n'
            r'        errors\.append\("design DNA must contain exactly %d anonymized references" % EXPECTED_REFERENCE_COUNT\)'),
         '    if (data.get("reference_count") != len(rows) or\n'
         '            len(rows) < MINIMUM_PUBLIC_REFERENCE_COUNT):\n'
         '        errors.append("design DNA reference_count must match a non-empty public seed catalog")'),
        (re.compile(r'"compiler": "hao-design-system-v6"'),
         '"compiler": "public-design-system-v6"'),
        (re.compile(
            r'    assert short\["source"\]\["learning_partition"\] == \{\n'
            r'        "art_direction": \d+, "full_style": \d+, "layout_only": \d+,\n'
            r'    \}'),
         '    assert sum(short["source"]["learning_partition"].values()) == load_dna()["reference_count"]\n'
         '    assert short["source"]["learning_partition"].get("layout_only", 0) >= 1'),
        (re.compile(r'description="Compile the [A-Za-z][A-Za-z0-9]* v6 design system"'),
         'description="Compile the public v6 design system"'),
        (re.compile(r'assert calm\["route"\]\["primary_family"\] == "japanese_lifestyle_calm"'),
         'assert calm["route"]["primary_family"] == "travel_scrapbook"'),
    ),
    "quality_corpus.py": (
        (re.compile(r'ROOT / "knowledge" /'), 'ROOT.parent / "knowledge" / "runtime" /'),
    ),
    "thumbnail_algorithm_score.py": (
        (re.compile(r'HERE / "knowledge" / "thumbnail_algorithm_standard\.json"'),
         'HERE.parent / "knowledge" / "runtime" / "thumbnail_algorithm_standard.json"'),
    ),
    "publishing_copy.py": (
        (re.compile(r'HERE / "knowledge" / "publishing_copy_playbooks\.json"'),
         'HERE.parent / "knowledge" / "runtime" / "publishing_copy_playbooks.json"'),
        (re.compile(r'HERE / "knowledge" / "topic_research_catalog\.json"'),
         'HERE.parent / "knowledge" / "runtime" / "topic_research_catalog.json"'),
    ),
    "taste_model.py": (
        (re.compile(r'ROOT / "knowledge" / "taste_model\.json"'),
         'ROOT.parent / "data" / "taste_model.json"'),
        (re.compile(r'def load_state\(path: str \| Path = STATE_PATH\) -> dict:\n    return json\.loads\(Path\(path\)\.read_text\(encoding="utf-8"\)\)'),
         'def load_state(path: str | Path = STATE_PATH) -> dict:\n'
         '    target = Path(path)\n'
         '    if not target.is_file():\n'
         '        return {"schema_version": 1, "min_comparisons_for_preference": 5, '
         '"feature_ratings": {}, "comparisons": [], "summary": {}}\n'
         '    return json.loads(target.read_text(encoding="utf-8"))'),
    ),
    "design-reference-dna-v6.md": (
        (re.compile(r'^# [A-Za-z][A-Za-z0-9]* Design System v6：\d+ 張參考圖的可執行 DNA$', re.M),
         '# Design System v6：可公開重用的設計 DNA'),
        (re.compile(
            r'這份文件是 `knowledge/design_reference_dna\.json` 的人類導航，[^\r\n]+`design_system_v6\.py` 編譯成小型 recipe。'),
         '這份文件是公開設計種子目錄的人類導航，不含原圖、私人路徑、維護者偏好或審核結果。種子依 `full_style / layout_only / art_direction` 分軌，實際規劃由 `design_system_v6.py` 編譯成小型 recipe。'),
        (re.compile(r'`design_system_v6\.py selftest` 驗 \d+ 筆、匿名化、\d+ 張 layout-only 不污染表面美術、\d+ 張 art-direction 正確進入家族，以及題材路由。'),
         '`design_system_v6.py selftest` 驗證公開種子非空、識別碼唯一、layout-only 不污染表面美術，以及題材路由。'),
        (re.compile(r'[A-Za-z][A-Za-z0-9]* 人工審片'), '創作者人工審片'),
    ),
    # v0.28.1 rewordings keep a public rule while its pointer goes.  The third item marks a rule as
    # required: if the canonical wording drifts and it stops matching, the sync stops.
    "benchmark-effect-parity.md": (
        (re.compile(r"^(## \d+\. 現有能力矩陣\n)", re.M),
         r"\1\n表中狀態是能力分級參考；實際可用的工具以 Editkin 與本 kit 提供的為準。\n",
         True),
    ),
    "architecture-foundation-v6-3.md": (
        (re.compile(r" `[a-z_]+\.py` owns claim/retry/resume operations\."), "", True),
        (re.compile(r" Planning validation uses `[a-z_]+\.py`, while the planning CLI may call the context router\."),
         "", True),
        (re.compile(r"Both planning and routing use "), "Context routing uses ", True),
    ),
    "asset-intelligence-hub.md": (
        (re.compile(r"（私版 motion）"), "（自備 motion）", True),
        (re.compile(r"\d+ 個程式生成 SFX 已有\n?`assets/sfx/manifest\.json` 與 48 kHz PCM 格式聲明，但授權仍是 `[a-z-]+`。"),
         "程式生成 SFX 須在 `assets/sfx/manifest.json` 宣告 48 kHz PCM 格式與授權；授權未定的素材不得對外散布。", True),
    ),
    "calibration-learning-and-license.md": (
        (re.compile(r"^這份文件是 [A-Za-z ]+ 的證據層；平時由程式讀取，不載入 context packet。$", re.M),
         "這份文件記錄校色、成效學習、授權與封存的規則；相機 profile 與 ColorChecker 規則由你的調色流程執行。",
         True),
        (re.compile(r"^- `[a-z-]+` 只輸出 ([^\n]*?) 建議，", re.M), r"- 鏡頭匹配建議限 \1，", True),
        (re.compile(r"^- `[a-z-]+` 產生來源、waveform、vectorscope 三聯圖；`[a-z-]+` 由", re.M),
         "- 用來源、waveform、vectorscope 三聯圖檢查；A/B 審片由", True),
    ),
    "caption-art-direction.md": (
        (re.compile(r"impact 必存在 `[a-z_]+` 獨立軌"), "impact 必存在獨立 overlay 軌", True),
        # Asset pointers are not part of the kit.
        (re.compile(r"^- 第一個核准素材是 [^\n]*`assets/[^`\n]+`。\n", re.M), "", True),
        (re.compile(r"^- Imagegen 素材索引：`[^`\n]+`\n", re.M), "", True),
    ),
    "camera-transition-and-value-visualization.md": (
        (re.compile(r"^- 母檔：`assets/[^`\n]+`[^\n]*\n", re.M), "", True),
        (re.compile(r"^(## \d+\. 美元粒子資產\n)", re.M),
         r"\1\n以下是美元粒子 overlay 資產的驗收規格（aspect＝landscape／portrait）；資產需自行製作並通過這些驗收。\n", True),
    ),
    "cinematic-wave-and-domain-grammar-2026.md": (
        (re.compile(r"^(## \d+\. )「[^」\n]+」拆成七條可執行規則$", re.M), r"\1流暢節奏拆成七條可執行規則", True),
        (re.compile(r"把「[^」\n]+」翻成可執行"), "把流暢這種模糊目標翻成可執行", True),
        (re.compile(r"`[a-z_]+\.py` 會輸出每段時間、能量、意圖與 shot-duration range。"),
         "節奏規劃要標出每段時間、能量、意圖與 shot-duration range。", True),
        (re.compile(r"^輸出不可只被當成參考文件：", re.M), "這些節奏規則要落到 plan 裡，不可只被當成參考文件：", True),
        (re.compile(r"^- Shorts renderer 會實際插入語意字卡", re.M), "- Shorts 要實際插入語意字卡", True),
    ),
    "color-science-and-visual-master.md": (
        (re.compile(r"^## 強度與「[^」\n]+」素材$", re.M), "## 強度與低對比（霧感）素材", True),
        (re.compile(r"獨立套色會產生 `\.grade\.json`，偵測到既有 sidecar 時預設拒絕重疊。"),
         "獨立套色應保留 `.grade.json` sidecar；已有 sidecar 時不得重疊套色。", True),
        (re.compile(r"^[A-Za-z]+ 的 \d+ 張參考圖所提煉出的", re.M), "[公開設計種子](design-reference-dna-v6.md)所提煉出的", True),
        (re.compile(r"Variant id 不寫死，一律以匯出的 registry 為準：`[^`\n]+`。\n[^\n]*`--check` 驗漂移。"),
         "Variant id 不寫死，一律以當次 `list_editkin_modules` 回傳為準。", True),
        (re.compile(r"。`[a-z_]+\.py analyze` 讀取 primaries、transfer、matrix、range。"), "。", True),
        (re.compile(r"M\d+ 之後正式剪輯都在 Editkin v4 run 裡完成；上面的 `[a-z_]+\.py` FFmpeg Look 只供故障重現。"),
         "上面的 Look 規格是設計規範；正式剪輯與實際套色都在 Editkin v4 run 裡完成。", True),
        (re.compile(r'用 `[a-z_]+\.find_modules\(kind="look", role=<下表 role>\)` 取出 `family` 為 `film_look_v2` 的 variant。'),
         "用 `list_editkin_modules` 取出 role 對應下表、`family` 為 `film_look_v2` 的 `look.color` variant。", True),
        (re.compile(r"這是 \d+ 個 [A-Za-z]+ Film Look v2，"), "這些 Film Look v2 ", True),
    ),
    "editing-wave6-2026.md": (
        # A planned module, not a file: plain words keep the W6C-8 section and its cross-references.
        (re.compile(r"落地\(機械化\): `longform_maker/input_logger\.py`："), "落地(機械化): 新模組 input_logger：", True),
    ),
    "editkin-workflow-execution.md": (
        (re.compile(r"`workflow reject-render "), "`python src/workflow_contract.py reject-render ", True),
        (re.compile(r'python scripts/hao_autopilot\.py workflow\b'), 'python src/workflow_contract.py'),
        (re.compile(r"結果用 `[a-z_]+\.py merge` 平鋪併入 plan（M\d+，見 `references/[a-z0-9-]+\.md`）。"), "結果平鋪併入 plan。",
         True),
        # Count-bearing wording becomes plain wording.
        (re.compile(r'(?:目前)?私有的?\s*\d+\s*[張圖]\s*設計 DNA'), '設計 DNA', True),
        # Public long-form controller (v0.26.0): where the session contract lives,
        # the long-form create command and its offline synthetic selftest.
        (re.compile(r'workflow contract 永遠取該 Skill 同層檔案。'),
         'workflow contract 與長片 session contract（`workflow_longform_contract.json`）永遠取該 Skill 同層檔案。'),
        (re.compile(r'不得在 [A-Z] 槽根目錄另建資料夾'), '不得在磁碟根目錄另建資料夾'),
        (re.compile(r'常用順序是 `create` → `next`'),
         '常用順序是 `create`（長片用 `create-longform --session <session.json>`）→ `next`'),
        (re.compile(r'(SRT 與章節 sidecar 在 render 之後產生。)\n'),
         r'\1' '\n- **離線自測**：`python src/workflow_contract.py selftest` 也會用合成、未簽章的 fixture 跑完整條長片 session'
         '（兩章、一次 set apply、一次 render）。它不是 Editkin 的 audit／apply 收據，也不是美術審片。\n'),
    ),
    "knowledge-lifecycle.md": (
        (re.compile(r'python scripts/hao_autopilot\.py knowledge --rotate-video-log\b'),
         'python src/knowledge_lifecycle.py rotate-video-log'),
        (re.compile(r'python scripts/hao_autopilot\.py knowledge$', re.M),
         'python src/knowledge_lifecycle.py audit'),
        (re.compile(r'python scripts/hao_autopilot\.py learn\b'), 'python src/knowledge_lifecycle.py record'),
    ),
    "mediastorm-craft-system.md": (
        (re.compile(r"轉場「[^」\n]+」不能由機器綠燈代替"), "轉場是否恰當不能由機器綠燈代替", True),
        (re.compile(r"基準從一句「[^」\n]+」改成"), "基準從流暢這種模糊目標改成", True),
        (re.compile(r"3D 先走 `[a-z_]+\.py` 的 capability gate"), "3D 先過 capability gate", True),
    ),
    "three-d-and-subject-fx.md": (
        (re.compile(r"缺前提時 `[a-z_]+\.py` 會輸出 `DOWNGRADED`"), "缺前提時要標 `DOWNGRADED`", True),
    ),
    "token-budget-system.md": (
        (re.compile(r"舊 `[a-z_]+\.md` 不再直接追加，[^\n]*?。"), "", True),
    ),
    "quality-95-system.md": (
        (re.compile(r"(情緒)與「[^」\n]+」。"), r"\1與剪點是否順暢。", True),
        (re.compile(r"^`[a-z_]+\.py build N` 會在技術 QA 後自動建立 provisional 報告與 Hao 審片頁。", re.M),
         "Shorts 技術 QA 通過後，用 `quality_95.py score` 建立 provisional 報告、`review_loop.py create` 建立 Hao 審片頁。",
         True),
        (re.compile(r"預設不會因「[^」\n]+」把技術成片刪除，"), "尚未審片不是刪除技術成片的理由，", True),
        (re.compile(r"^# Quality 95：從「[^」\n]+」到「[^」\n]+」$", re.M), "# Quality 95：從可交付到高品質", True),
        (re.compile(r'videos/_INBOX/[^/"\s]*vertical[^/"\s]*/'), 'videos/_INBOX/vertical/', True),
        (re.compile(r'`python scripts/hao_autopilot\.py project95` 會重跑'),
         '維護者工作區的整套專案驗收會重跑'),
        (re.compile(r'(報告寫到 `reports/PROJECT_QUALITY_95\.\{json,md\}`。)'),
         r'\1公開版不附這個驗收入口；公開安裝以 `python src/system_health.py` 與 CI gate 驗收。'),
        (re.compile(r"^## 整套專案的 9\.5 驗收$", re.M), "## 整套專案驗收", True),
        (re.compile(r"^python review_loop\.py ", re.M), "python src/review_loop.py ", True),
        # The maintained workspace's own acceptance run is not part of the kit.
        (re.compile(r"維護者工作區的整套專案驗收會重跑[\s\S]*?公開版不附這個驗收入口；"), "", True),
    ),
    "storage-lifecycle.md": (
        (re.compile(r"`_[^`\s/]+Shorts`"), "`_ready-shorts`", True),
        (re.compile(r'python scripts/hao_autopilot\.py dedupe-archive\b'),
         'python src/storage_lifecycle.py dedupe-archive'),
    ),
    "thumbnail-algorithm-score.md": (
        (re.compile(r'python scripts/hao_autopilot\.py thumbnail-score\b'),
         'python src/thumbnail_algorithm_score.py score'),
    ),
}

