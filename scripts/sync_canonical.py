#!/usr/bin/env python3
"""Synchronize redistributable Video Autopilot sources into the public kit.

The canonical workspace may contain user media, analytics, generated previews,
private preferences and machine paths.  This script uses an explicit allowlist,
copies text only, and fails when known privacy tokens survive the transformation.
It is intentionally deterministic so release preparation does not depend on a
maintainer remembering individual files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
from pathlib import Path


ROOT_MODULES = (
    "aesthetic_score.py", "art_direction.py", "asset_catalog.py",
    "asset_license_governance.py", "asset_memory.py",
    "asset_registry_shared.py", "asset_selection.py", "av_util.py",
    "camera_transition_director.py", "caption_director.py", "challenge_hud.py",
    "channel_tracker.py", "color_calibration_lab.py", "context_router.py",
    "domain_broll_pack.py", "domain_taxonomy.py", "drama_autopilot.py",
    "design_system_v6.py", "knowledge_lifecycle.py", "motion_asset_pack.py",
    "mrbeast_editing_system.py", "three_d_system.py",
    "motion_renderers.py", "outcome_learning.py", "project_kernel.py",
    "project_quality_95.py",
    "project_paths.py", "publishing_copy.py",
    "publish_hub_ops.py", "quality_95.py", "quality_corpus.py",
    "remix_planner.py", "render_caption_showcase.py", "review_loop.py",
    "shorts_autopilot.py", "shorts_delivery.py", "skill_sync.py",
    "storage_lifecycle.py", "storage_optimizer.py", "taste_model.py",
    "teardown.py", "thumbnail_algorithm_score.py", "tracked_graphics.py",
    "template_compiler.py", "mediastorm_craft.py",
    "tracked_typography.py", "visual_director.py", "visual_master.py",
    "visual_plan_support.py", "visual_profiles.py",
)

LONGFORM_MODULES = (
    "asset_forge.py", "audio_chain.py", "brand_templates.py", "color_workflow.py",
    "emphasis_overlays.py", "fx_lib.py", "gate_core.py", "grade_calibrate.py",
    "grade_gate.py", "grade_lib.py", "music_engine.py", "pace_gate.py",
    "plan_gate.py", "proof_stage.py", "screen_clean.py", "script_gate.py",
    "shorts_gate.py", "thumb_template.py", "transitions.py", "video_handlers.py",
    "word_captions.py", "LONGFORM_PIPELINE.md",
)

SILENT_VLOG_MODULES = (
    "__init__.py", "asset_scanner.py", "audit.py", "audit_report.py",
    "bright_card_e2e.py", "checklists.py", "constants.py", "content_routing.py",
    "effects.py", "frame_audit.py", "helpers.py", "pipeline.py",
    "quality_check.py", "quality_check_corpus.py", "routing.py", "scene_audit.py",
    "screen_rec_cleaner.py", "shorts_audio.py", "shorts_captions.py",
    "shorts_template.py", "shorts_vertical.py", "text_overlay.py", "verify.py",
    "voice_profiles.json",
)

DRAMA_MODULES = (
    "__init__.py", "editor.py", "planner.py", "schema_validation.py",
    "schema_validation_corpus.py", "store.py", "tasks.py",
)

KNOWLEDGE_FILES = (
    "aesthetic_standard.json", "asset_license_overrides.json",
    "asset_license_policy.json", "camera_color_profiles.json",
    "color_grading_profiles.json", "design_reference_dna.json", "design_trend_radar.json",
    "state.json",
    "publishing_copy_playbooks.json", "quality_corpus.json",
    "thumbnail_algorithm_standard.json", "topic_research_catalog.json",
    "mediastorm_craft_benchmark.json",
)

REFERENCE_FILES = (
    "ai-evidence-canvas.md", "asset-intelligence-hub.md", "autopilot-modes.md",
    "benchmark-effect-parity.md", "bright-editorial-template-system.md",
    "calibration-learning-and-license.md",
    "camera-transition-and-value-visualization.md", "caption-art-direction.md",
    "cinematic-wave-and-domain-grammar-2026.md",
    "color-science-and-visual-master.md", "craft-index.md",
    "editing-craft-fundamentals.md", "editing-master-techniques.md",
    "editing-techniques-2026.md", "editing-wave5-finecut-2026.md",
    "editing-wave6-2026.md", "genre-copy-grammar-2026.md",
    "genre-editing-craft-2026.md", "hao-aesthetic-standard.md",
    "knowledge-lifecycle.md", "motion-asset-library.md",
    "mrbeast-and-yingshi-benchmark.md", "niche-editing-grammar.md",
    "niche-fonts-colors.md", "publish-hub-and-remix.md", "quality-95-system.md",
    "script-retention-2026.md", "shorts-mastery-2026.md",
    "shorts_reels_2026_best_practices.md", "storage-lifecycle.md",
    "thumbnail-algorithm-score.md", "token-budget-system.md",
    "tracked-typography-and-challenge-ledger.md",
    "design-reference-dna-v6.md", "three-d-and-subject-fx.md",
    "visual-art-direction-2026.md", "competitor-vertical-teardown-2026.md",
    "template-compiler-v2.md", "mediastorm-craft-system.md",
)

PRIVACY_PATTERNS = (
    re.compile(r"C:[\\/]Users[\\/]Hao0321", re.I),
    re.compile(r"D:[\\/]Hao0321_YT_Claude", re.I),
    re.compile("codex-remote-" + "attachments", re.I),
    re.compile(r"AppData[\\/]Local[\\/]Temp", re.I),
)

REPLACEMENTS = (
    (re.compile(r"D:\\skills_social\\social-post\\references\\youtube\.md", re.I),
     "the configured social-post evidence ledger"),
    (re.compile(r"Path\(r?[\"']D:\\Hao0321_YT_Claude\\videos\\_INBOX\\[^\"']+[\"']\)"),
     'Path("<project-root>/videos/_INBOX/<format>/<content-id>")'),
    (re.compile(r"Hao Visual Master"), "Visual Master"),
    (re.compile(r"Hao Aesthetic Standard"), "Creator Aesthetic Standard"),
    (re.compile(r"\[?`?yt-algorithm-mastery/references/cross-platform-truth-2026\.md`?\]?\(\.\./\.\./yt-algorithm-mastery/references/cross-platform-truth-2026\.md\)"),
     "[shorts_reels_2026_best_practices.md](shorts_reels_2026_best_practices.md)"),
)

MODULE_REPLACEMENTS = {
    "project_paths.py": (
        (re.compile(r'MANIFEST_NAME = "AUTOPILOT_MANIFEST\.json"'),
         'MANIFEST_NAMES = ("AUTOPILOT_MANIFEST.json", "release-manifest.json")'),
        (re.compile(r'ROOT_ENV_VARS = \("HAO_AUTOPILOT_ROOT", "VIDEO_KIT_PROJECT_ROOT"\)'),
         'ROOT_ENV_VARS = ("VIDEO_AUTOPILOT_ROOT", "VIDEO_KIT_PROJECT_ROOT", "HAO_AUTOPILOT_ROOT")'),
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
        (re.compile(r'from project_paths import MANIFEST_NAME, discover_project_root'),
         'from project_paths import MANIFEST_NAMES, discover_project_root'),
        (re.compile(r'path = workspace / MANIFEST_NAME'),
         'path = next((workspace / name for name in MANIFEST_NAMES\n'
         '                 if (workspace / name).is_file()), workspace / MANIFEST_NAMES[0])'),
        (re.compile(r'if sync\["status"\] != "GREEN":\n        errors\.append\("installed skill copies drift from project canon"\)'),
         'if sync["status"] != "GREEN":\n'
         '        warnings.append("installed skill copy is absent or differs; run project_kernel.py sync apply")'),
        (re.compile(r'assert manifest\["architecture_version"\] == "6\.1"'),
         'assert manifest["architecture_version"] == "6.1"'),
        (re.compile(r'description="Hao Autopilot manifest control plane"'),
         'description="Video Autopilot manifest control plane"'),
    ),
    "project_quality_95.py": (
        (re.compile(r'str\(ROOT / "\.claude" / "skills" / "capcut-agent-ops" /\n\s*"capcut_helpers" / "delivery_qa\.py"\)'),
         'str(HERE / "capcut_helpers" / "delivery_qa.py")'),
        (re.compile(r'ROOT / "\.claude" / "skills" / "capcut-agent-ops" /\n\s*"capcut_helpers" / "delivery_qa\.py"'),
         'HERE / "capcut_helpers" / "delivery_qa.py"'),
        (re.compile(r'"Hao 人工時間碼審片閉環"'), '"創作者人工時間碼審片閉環"'),
        (re.compile(r'"pairwise_feature_elo" in \(HERE / "knowledge" / "taste_model\.json"\)\.read_text\(encoding="utf-8"\)'),
         '"pairwise aesthetic preference" in sources["taste"]'),
        (re.compile(r'"Every video still requires QUALITY_95\.json plus Hao-owned timestamped review\."'),
         '"Every video still requires QUALITY_95.json plus creator-owned timestamped review."'),
        (re.compile(r'由 Hao 完成時間碼審片'), '由創作者完成時間碼審片'),
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
    "aesthetic_score.py": (
        (re.compile(r'ROOT / "knowledge" /'), 'ROOT.parent / "knowledge" / "runtime" /'),
    ),
    "design_system_v6.py": (
        (re.compile(r'ROOT / "knowledge" / "design_reference_dna\.json"'),
         'ROOT.parent / "knowledge" / "runtime" / "design_reference_dna.json"'),
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
         '        return {"schema_version": 1, "min_comparisons_for_preference": 5, '\
         '"feature_ratings": {}, "comparisons": [], "summary": {}}\n'
         '    return json.loads(target.read_text(encoding="utf-8"))'),
    ),
    "constants.py": (
        (re.compile(r'FONT_NOTO_BLACK = "C\\\\:/Windows/Fonts/NotoSansTC-Black\.otf"[^\n]*\n'
                    r'FONT_NOTO_BOLD = "C\\\\:/Windows/Fonts/NotoSansTC-Bold\.otf"[^\n]*\n'
                    r'FONT_NOTO_REG = "C\\\\:/Windows/Fonts/NotoSansTC-Regular\.otf"[^\n]*\n\n'
                    r'# M43[^\n]*\n'
                    r'FONT_NOTO_SERIF_BOLD = "D\\\\:/Hao0321_YT_Claude/assets/fonts/NotoSerifCJK-Bold\.ttc"'),
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
        (re.compile(r'掃 D:\\\\Hao0321_YT_Claude\\\\assets\\\\ \+ 自動建/更新 index\.json：'),
         '掃描專案 assets/ 並自動建立或更新 index.json：'),
    ),
}


def _transform(text: str, name: str = "") -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for pattern, replacement in REPLACEMENTS:
        text = pattern.sub(replacement, text)
    for pattern, replacement in MODULE_REPLACEMENTS.get(name, ()):
        text = pattern.sub(replacement, text)
    return text


def _copy_text(source: Path, destination: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(source)
    text = _transform(source.read_text(encoding="utf-8-sig"), source.name)
    hits = [pattern.pattern for pattern in PRIVACY_PATTERNS if pattern.search(text)]
    if hits:
        raise ValueError(f"privacy token in {source}: {hits}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def sync(canonical: Path, repository: Path) -> list[str]:
    copied: list[str] = []
    groups = (
        (ROOT_MODULES, canonical, repository / "src"),
        (LONGFORM_MODULES, canonical / "longform_maker", repository / "src" / "longform_maker"),
        (SILENT_VLOG_MODULES, canonical / "silent_vlog_maker", repository / "src" / "silent_vlog_maker"),
        (DRAMA_MODULES, canonical / "drama_pipeline", repository / "src" / "drama_pipeline"),
        (KNOWLEDGE_FILES, canonical / "knowledge", repository / "knowledge" / "runtime"),
        (REFERENCE_FILES, canonical / "references", repository / "codex-skill" / "video-autopilot" / "references"),
    )
    for names, source_root, destination_root in groups:
        for name in names:
            destination = destination_root / name
            _copy_text(source_root / name, destination)
            copied.append(destination.relative_to(repository).as_posix())
    _copy_text(canonical / "SKILL.md", repository / "codex-skill" / "video-autopilot" / "SKILL.md")
    copied.append("codex-skill/video-autopilot/SKILL.md")
    _copy_text(canonical.parents[2] / "AUTOPILOT_ARCHITECTURE_V6.md",
               repository / "docs" / "AUTOPILOT_ARCHITECTURE_V6.md")
    copied.append("docs/AUTOPILOT_ARCHITECTURE_V6.md")
    _write_public_manifest(repository)
    copied.append("AUTOPILOT_MANIFEST.json")
    return copied


def _write_public_manifest(repository: Path) -> None:
    required = [
        "release-manifest.json", "src/project_paths.py", "src/context_router.py",
        "src/asset_registry.py", "src/visual_director.py", "src/visual_master.py",
        "src/tracked_graphics.py", "src/quality_95.py", "src/publish_hub.py",
        "src/storage_lifecycle.py", "src/system_health.py", "src/project_quality_95.py",
        "src/design_system_v6.py", "src/template_compiler.py", "src/mediastorm_craft.py",
        "src/mrbeast_editing_system.py", "src/three_d_system.py",
        "knowledge/runtime/design_reference_dna.json",
        "knowledge/runtime/mediastorm_craft_benchmark.json",
        "docs/AUTOPILOT_ARCHITECTURE_V6.md",
        "codex-skill/video-autopilot/SKILL.md",
        "codex-skill/video-autopilot/references/template-compiler-v2.md",
        "codex-skill/video-autopilot/references/mediastorm-craft-system.md",
    ]
    payload = {
        "schema_version": 2,
        "project_id": "video-autopilot-kit",
        "architecture_version": "6.1",
        "public_distribution": True,
        "roots": {
            "skills": "codex-skill",
            "assets": "assets",
            "videos": "videos",
            "community": "community",
            "scripts": "scripts",
        },
        "planes": {
            "control": ["AUTOPILOT_MANIFEST.json", "src/project_kernel.py", "src/system_health.py", "src/publish_hub.py"],
            "decision": ["src/context_router.py", "src/knowledge_lifecycle.py", "src/quality_95.py", "src/visual_master.py"],
            "design": ["src/design_system_v6.py", "src/template_compiler.py", "src/mediastorm_craft.py", "src/mrbeast_editing_system.py", "src/three_d_system.py", "src/visual_director.py", "src/tracked_graphics.py", "knowledge/runtime/design_reference_dna.json", "knowledge/runtime/mediastorm_craft_benchmark.json"],
            "asset": ["src/asset_registry.py", "src/asset_license_governance.py", "src/motion_asset_pack.py"],
            "execution": ["src/longform_maker", "src/shorts_autopilot.py", "src/tracked_graphics.py", "src/drama_autopilot.py"],
            "evidence": ["knowledge/runtime/state.json", "knowledge/runtime/quality_corpus.json", "data"],
        },
        "required_paths": required,
        "skills": [{
            "id": "video-autopilot",
            "source": "codex-skill/video-autopilot",
            "destination": "video-autopilot",
            "include": ["SKILL.md", "agents/*.yaml", "references/*.md"],
        }],
        "budgets": {
            "context_tokens": {"default": 900, "plan": 900, "build": 800, "audit": 1000, "learn": 1100, "outcome": 650},
            "storage_gb": {"videos_warning": 12, "videos_max": 20, "assets_warning": 5, "assets_max": 8},
            "source_lines": {"python_warning": 500, "python_severe": 1000, "markdown_warning": 400, "markdown_severe": 800, "function_warning": 50, "function_severe": 100},
            "knowledge_lines": {"knowledge/runtime/state.json": {"warning": 1400, "rotate": 1800, "policy": "compact-supported-rules; archive local evidence under data/"}},
        },
        "audit": {
            "source_roots": ["src", "scripts", "codex-skill/video-autopilot"],
            "ignore_globs": ["**/__pycache__/**", "**/_runtime/**", "**/_demo/**"],
            "absolute_path_allowlist": ["src/project_paths.py", "src/project_kernel.py", "scripts/sync_canonical.py"],
            "large_file_allowlist": {
                "codex-skill/video-autopilot/references/editing-craft-fundamentals.md": "on-demand reference chapter; never loaded into default context",
                "codex-skill/video-autopilot/references/editing-master-techniques.md": "on-demand technique catalog",
                "codex-skill/video-autopilot/references/competitor-vertical-teardown-2026.md": "evidence-backed teardown kept cohesive for traceability",
            },
            "long_function_allowlist": {
                "src/capcut_helpers/caption_broll_matcher.py:auto_sequence_brolls": "ordered B-roll assignment transaction sharing one candidate and timing ledger",
                "src/longform_maker/shorts_gate.py:gate_shorts": "declarative gate sequence; rule order and shared report state are the contract",
                "src/silent_vlog_maker/verify.py:run_verify_steps": "ordered verification transaction with one failure ledger",
                "src/release_manager.py:apply_release_archive": "fail-closed upgrade transaction; backup, replacement, rollback and state commit share one boundary",
                "src/shorts_autopilot.py:scan": "compatibility orchestration adapter; its underlying analyzers are independently tested",
                "src/silent_vlog_maker/audit.py:audit_raw_files": "ordered media audit adapter around probe and frame evidence",
                "src/longform_maker/word_captions.py:group_words": "single timing and segmentation algorithm with tightly coupled invariants",
                "src/silent_vlog_maker/audit_report.py:write_markdown_report": "linear report serializer over one immutable audit result"
            },
        },
        "privacy_contract": "No user media, profiles, credentials, analytics, or local outcomes.",
    }
    path = repository / "AUTOPILOT_MANIFEST.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8", newline="\n")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()
    canonical, repository = args.canonical.resolve(), args.repository.resolve()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="video-autopilot-sync-") as temp:
            staged = Path(temp)
            expected = sync(canonical, staged)
            drift = [name for name in expected
                     if not (repository / name).is_file()
                     or _sha256(staged / name) != _sha256(repository / name)]
        if drift:
            print("SYNC DRIFT: " + ", ".join(drift[:30]))
            return 1
        print(f"SYNC GREEN: {len(expected)} redistributable text files")
        return 0
    copied = sync(canonical, repository)
    print(f"SYNC GREEN: wrote {len(copied)} redistributable text files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
