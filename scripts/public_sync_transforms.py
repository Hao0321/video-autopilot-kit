"""Static compatibility transforms for redistributable canonical sources."""
from __future__ import annotations

import re
from pathlib import Path


_LOCAL_USER = re.escape(Path.home().name)

PRIVACY_PATTERNS = (
    re.compile(rf"[A-Z]:[\\/]Users[\\/]{_LOCAL_USER}(?=[\\/]|$)", re.I),
    re.compile(r"[A-Z]:[\\/][^\\/\r\n]*_YT_Claude", re.I),
    re.compile("codex-remote-" + "attachments", re.I),
    re.compile(r"AppData[\\/]Local[\\/]Temp", re.I),
)

REPLACEMENTS = (
    (re.compile(
        r"[A-Z]:[\\/]Users[\\/][^\\/]+[\\/]\.codex[\\/]skills[\\/]"
        r"[^\\/]*voice[^\\/]*[\\/][^\\/]*voice[^\\/]*\.md",
        re.I,
     ), "~/.codex/skills/creator-voice/profile.md"),
    (re.compile(r"[A-Z]:[\\/]skills_social[\\/]social-post[\\/]references[\\/]youtube\.md", re.I),
     "the configured social-post evidence ledger"),
    (re.compile(r"Path\(r?[\"'][A-Z]:[\\/][^\"']*?[\\/]videos[\\/]_INBOX[\\/][^\"']+[\"']\)", re.I),
     'Path("<project-root>/videos/_INBOX/<format>/<content-id>")'),
    (re.compile(r"\b[A-Za-z][A-Za-z0-9]* Visual Master\b"), "Visual Master"),
    (re.compile(r"\b[A-Za-z][A-Za-z0-9]* Aesthetic Standard\b"), "Creator Aesthetic Standard"),
    (re.compile(r"\bHAO_REVIEW_REQUIRED\b"), "CREATOR_REVIEW_REQUIRED"),
    (re.compile(r"\breported_by_hao\b"), "reported_by_creator"),
    (re.compile(r"\[?`?yt-algorithm-mastery/references/cross-platform-truth-2026\.md`?\]?\(\.\./\.\./yt-algorithm-mastery/references/cross-platform-truth-2026\.md\)"),
     "[shorts_reels_2026_best_practices.md](shorts_reels_2026_best_practices.md)"),
)

MODULE_REPLACEMENTS = {
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
        (re.compile(r'description="Hao Autopilot manifest control plane"'),
         'description="Video Autopilot manifest control plane"'),
    ),
    "publish_hub_cli.py": (
        (re.compile(
            r'withdraw\.add_argument\("--actor", default="[A-Za-z][A-Za-z0-9]*"\)'
        ), 'withdraw.add_argument("--actor", default="creator")'),
        (re.compile(
            r'description="[A-Za-z][A-Za-z0-9]* unified publishing hub"'
        ), 'description="Video Autopilot publishing hub"'),
    ),
    "project_quality_95.py": (
        (re.compile(r'"[A-Za-z][A-Za-z0-9]* 人工時間碼審片閉環"'), '"創作者人工時間碼審片閉環"'),
        (re.compile(r'"pairwise_feature_elo" in \(HERE / "knowledge" / "taste_model\.json"\)\.read_text\(encoding="utf-8"\)'),
         '"pairwise aesthetic preference" in sources["taste"]'),
        (re.compile(r'"Every video still requires QUALITY_95\.json plus [A-Za-z][A-Za-z0-9]*-owned timestamped review\."'),
         '"Every video still requires QUALITY_95.json plus creator-owned timestamped review."'),
        (re.compile(r'由\s+[A-Za-z][A-Za-z0-9]*\s+完成時間碼審片'), '由創作者完成時間碼審片'),
        (re.compile(r'commands\["longform"\]\["ok"\] and\n\s*all\(token in sources\["long"\] for token in \("longform_evidence", "create_review_bundle"\)\)'),
         'commands["longform"]["ok"] and "final_delivery_qa" in sources["long"]'),
        (re.compile(r'"pairwise aesthetic preference" in sources\["taste"\]'),
         '"add_comparison" in sources["taste"]'),
        (re.compile(r'doctor\.get\("sync"\), critical=True\),'),
         'doctor.get("sync")),'),
    ),
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
    "tracked_typography.py": (
        (re.compile(r'from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont'),
         'from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont\n\nfrom platform_compat import find_cjk_font'),
        (re.compile(
            r'def font\(text: str, size: int\) -> ImageFont\.FreeTypeFont:\n'
            r'    path = FONT_DIR / \("Huninn-Regular\.ttf" if CJK_RE\.search\(text\) else "Fredoka-SemiBold\.ttf"\)\n'
            r'    if not path\.is_file\(\):\n'
            r'        raise FileNotFoundError\("missing tracked-graphics font: %s" % path\)\n'
            r'    return ImageFont\.truetype\(str\(path\), max\(12, int\(size\)\)\)'),
         'def font(text: str, size: int) -> ImageFont.FreeTypeFont:\n'
         '    preferred = FONT_DIR / ("Huninn-Regular.ttf" if CJK_RE.search(text) else "Fredoka-SemiBold.ttf")\n'
         '    path = str(preferred) if preferred.is_file() else find_cjk_font(\n'
         '        ["Black", "Bold", "Semibold"] if not CJK_RE.search(text) else ["Bold", "TC", "CJK"]\n'
         '    )\n'
         '    if not path:\n'
         '        raise FileNotFoundError(\n'
         '            "missing redistributable/system CJK font; install Noto Sans CJK/TC or add a licensed font under assets/fonts/_active"\n'
         '        )\n'
         '    return ImageFont.truetype(str(path), max(12, int(size)))'),
    ),
    "art_direction.py": (
        (re.compile(r'ROOT = os\.path\.normpath\(os\.path\.join\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\), "\.\.", "\.\.", "\.\."\)\)'),
         'ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))'),
    ),
    "motion_asset_pack.py": (
        (re.compile(r'ROOT = os\.path\.normpath\(os\.path\.join\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\), "\.\.", "\.\.", "\.\."\)\)'),
         'ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))'),
        (re.compile(
            r'    if not os\.path\.isfile\(path\):\n'
            r'        raise FileNotFoundError\("motion asset manifest missing; run: python motion_asset_pack\.py build"\)\n'
            r'    with open\(path, "r", encoding="utf-8"\) as f:\n'
            r'        manifest = json\.load\(f\)'),
         '    if not os.path.isfile(path):\n'
         '        manifest = {"version": 1, "style": "procedural_motion_fallback", "generated": False,\n'
         '                    "build_command": "python src/motion_asset_pack.py build --aspect all",\n'
         '                    "assets": [{"id": spec.id, "role": spec.role, "aspect": aspect,\n'
         '                                "path": "procedural://%s/%s" % (aspect, spec.id),\n'
         '                                "duration": spec.duration, "fps": FPS,\n'
         '                                "resolution": list(ASPECTS[aspect]["output"]),\n'
         '                                "loop": spec.loop, "blend_mode": spec.blend_mode,\n'
         '                                "energy": spec.energy, "theme": "general",\n'
         '                                "domains": ["general", "ai", "food", "travel", "toy", "product", "game", "diy", "cafe", "documentary", "interview", "automotive", "fitness", "fashion", "architecture", "business", "nature", "music"],\n'
         '                                "tags": list(spec.tags), "usage": spec.usage,\n'
         '                                "requires_build": True}\n'
         '                               for aspect in ASPECTS for spec in SPECS]}\n'
         '    else:\n'
         '        with open(path, "r", encoding="utf-8") as f:\n'
         '            manifest = json.load(f)'),
        (re.compile(
            r'        if not os\.path\.isfile\(DOMAIN_MANIFEST_PATH\):\n'
            r'            raise FileNotFoundError\("domain motion manifest missing: " \+ DOMAIN_MANIFEST_PATH\)'),
         '        if not os.path.isfile(DOMAIN_MANIFEST_PATH):\n'
         '            return manifest'),
    ),
    "motion_renderers.py": (
        (re.compile(r'ROOT = os\.path\.normpath\(os\.path\.join\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\), "\.\.", "\.\.", "\.\."\)\)'),
         'ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))'),
        (re.compile(
            r'    if not os\.path\.isfile\(SOURCE_MASTER\):\n'
            r'        raise FileNotFoundError\("missing imagegen master: " \+ SOURCE_MASTER\)'),
         '    if not os.path.isfile(SOURCE_MASTER):\n'
         '        im = _base(size)\n'
         '        draw = ImageDraw.Draw(im, "RGBA")\n'
         '        w, h = size\n'
         '        blocks = ((0.00,0.00,0.34,0.22,PURPLE),(0.66,0.00,1.00,0.18,CYAN),(0.00,0.74,0.28,1.00,YELLOW),(0.72,0.72,1.00,1.00,RED))\n'
         '        for x0, y0, x1, y1, color in blocks:\n'
         '            draw.polygon([(int(w*x0),int(h*y0)),(int(w*x1),int(h*y0)),(int(w*(x1-.06)),int(h*y1)),(int(w*x0),int(h*y1))], fill=color+(185,))\n'
         '        _corner_marks(draw, size, WHITE, 150)\n'
         '        return im'),
    ),
    "editorial_templates.py": (
        (re.compile(r'PROJECT_ROOT = os\.path\.normpath\(os\.path\.join\(os\.path\.dirname\(os\.path\.abspath\(__file__\)\), "\.\.", "\.\.", "\.\."\)\)'),
         'PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))'),
    ),
    "domain_broll_pack.py": (
        (re.compile(r'ROOT = Path\(__file__\)\.resolve\(\)\.parents\[3\]'),
         'ROOT = Path(__file__).resolve().parents[1]'),
    ),
    "asset_license_governance.py": (
        (re.compile(r'PROJECT_ROOT = ROOT\.parents\[2\]'), 'PROJECT_ROOT = ROOT.parent'),
        (re.compile(r'ROOT / "knowledge" /'), 'PROJECT_ROOT / "knowledge" / "runtime" /'),
    ),
    "color_calibration_lab.py": (
        (re.compile(r'PROJECT_ROOT = ROOT\.parents\[2\]'), 'PROJECT_ROOT = ROOT.parent'),
        (re.compile(r'ROOT / "knowledge" /'), 'PROJECT_ROOT / "knowledge" / "runtime" /'),
    ),
    "visual_master.py": (
        (re.compile(r'PROJECT_ROOT = ROOT\.parents\[2\]'), 'PROJECT_ROOT = ROOT.parent'),
        (re.compile(r'PROFILE_PATH = ROOT / "knowledge" / "color_grading_profiles\.json"'),
         'PROFILE_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "color_grading_profiles.json"'),
        (re.compile(r'TREND_PATH = ROOT / "knowledge" / "design_trend_radar\.json"'),
         'TREND_PATH = PROJECT_ROOT / "knowledge" / "runtime" / "design_trend_radar.json"'),
    ),
    "visual_director.py": (
        (re.compile(
            r'system\.get\("standard_id"\) != "[A-Za-z][A-Za-z0-9_-]*-aesthetic-standard"'
        ), 'system.get("standard_id") != "public-aesthetic-standard"'),
        (re.compile(
            r'compiled\.get\("compiler"\) != "[A-Za-z][A-Za-z0-9_-]*-design-system-v6"'
        ), 'compiled.get("compiler") != "public-design-system-v6"'),
        (re.compile(
            r'    if \(compiled\.get\("source"\) or \{\}\)\.get\("reference_count"\) != \d+:\n'
            r'        bad\.append\("v6 design DNA must route all \d+ abstract references"\)'
        ),
         '    source = compiled.get("source") or {}\n'
         '    partition = source.get("learning_partition") or {}\n'
         '    if not source.get("reference_count") or source.get("reference_count") != sum(partition.values()):\n'
         '        bad.append("v6 design DNA source count must match its public learning partition")'),
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
    "constants.py": (
        (re.compile(r'FONT_NOTO_BLACK = "C\\\\:/Windows/Fonts/NotoSansTC-Black\.otf"[^\n]*\n'
                    r'FONT_NOTO_BOLD = "C\\\\:/Windows/Fonts/NotoSansTC-Bold\.otf"[^\n]*\n'
                    r'FONT_NOTO_REG = "C\\\\:/Windows/Fonts/NotoSansTC-Regular\.otf"[^\n]*\n\n'
                    r'# M43[^\n]*\n'
                    r'FONT_NOTO_SERIF_BOLD = "[^"\r\n]*NotoSerifCJK-Bold\.ttc"'),
         'try:\n'
         '    from platform_compat import find_cjk_font\n'
         'except ImportError:  # package execution fallback\n'
         '    find_cjk_font = lambda prefer=None: None\n\n'
         'def _ffmpeg_font(prefer=None) -> str:\n'
         '    path = find_cjk_font(prefer=prefer)\n'
         '    return str(path).replace(":", r"\\:") if path else "sans-serif"\n\n'
         'FONT_NOTO_BLACK = _ffmpeg_font(["Black", "Heavy", "Bold"])\n'
         'FONT_NOTO_BOLD = _ffmpeg_font(["Bold", "Black", "bd"])\n'
         'FONT_NOTO_REG = _ffmpeg_font(["Regular", "Noto", "PingFang"])\n'
         'FONT_NOTO_SERIF_BOLD = _ffmpeg_font(["Serif", "Song", "Ming"])'),
    ),
    "asset_scanner.py": (
        (re.compile(r'掃 [^\r\n]*assets[^\r\n]*自動建/更新 index\.json：'),
         '掃描專案 assets/ 並自動建立或更新 index.json：'),
    ),
    "delivery.py": (
        (re.compile(r'import publish_hub  # noqa: E402\n'
                    r'from autonomy_standard import assess_and_enqueue  # noqa: E402'),
         'try:\n'
         '    from .. import publish_hub  # type: ignore[import-not-found]  # noqa: E402\n'
         '    from ..autonomy_standard import assess_and_enqueue  # type: ignore[import-not-found]  # noqa: E402\n'
         'except ImportError:  # direct-script compatibility\n'
         '    import publish_hub  # noqa: E402\n'
         '    from autonomy_standard import assess_and_enqueue  # noqa: E402'),
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
}
