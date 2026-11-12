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
    "publish_hub_ops.py": _DEMO_REMIX_RENAMES,
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
        (re.compile(r'STATE_PATH = HERE / "channel_state\.json"'),
         'STATE_PATH = HERE.parent / "data" / "channel_state.json"'),
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
    "editkin-workflow-execution.md": (
        (re.compile(r'python scripts/hao_autopilot\.py workflow\b'), 'python src/workflow_contract.py'),
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
    "quality-95-system.md": (
        (re.compile(r'`python scripts/hao_autopilot\.py project95` 會重跑'),
         '維護者工作區的整套專案驗收會重跑'),
        (re.compile(r'(報告寫到 `reports/PROJECT_QUALITY_95\.\{json,md\}`。)'),
         r'\1公開版不附這個驗收入口；公開安裝以 `python src/system_health.py` 與 CI gate 驗收。'),
    ),
    "storage-lifecycle.md": (
        (re.compile(r'python scripts/hao_autopilot\.py dedupe-archive\b'),
         'python src/storage_lifecycle.py dedupe-archive'),
    ),
    "thumbnail-algorithm-score.md": (
        (re.compile(r'python scripts/hao_autopilot\.py thumbnail-score\b'),
         'python src/thumbnail_algorithm_score.py score'),
    ),
}


# Inline links `[t](x.md)`, `[t](./x.md#part "title")` and reference definitions `[id]: ./x.md`.
_SIBLING_MARKDOWN_LINK = re.compile(
    r"\]\((?:\./)?([A-Za-z0-9_.-]+\.md)(?:#[^)\s]*)?(?:\s+\"[^\"]*\")?\)"
    r"|^\s{0,3}\[[^\]]+\]:\s*<?(?:\./)?([A-Za-z0-9_.-]+\.md)(?:#\S*)?>?", re.M)
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s")
_REFERENCE_DEFINITION = re.compile(r"^\s{0,3}\[[^\]]+\]:\s")


def _links_unshipped(text: str, shipped: frozenset[str]) -> bool:
    return any((match.group(1) or match.group(2)) not in shipped
               for match in _SIBLING_MARKDOWN_LINK.finditer(text))


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _filter_text_block(block: list[str], shipped: frozenset[str]) -> list[str]:
    """Keep a block, or drop only its offending table rows, list items or link definitions."""
    if not _links_unshipped("\n".join(block), shipped):
        return block
    if all(line.lstrip().startswith("|") for line in block):
        if len(block) < 3 or _links_unshipped("\n".join(block[:2]), shipped):
            return []
        rows = [row for row in block[2:] if not _links_unshipped(row, shipped)]
        return block[:2] + rows if rows else []
    if all(_REFERENCE_DEFINITION.match(line) for line in block):
        return [line for line in block if not _links_unshipped(line, shipped)]
    if _LIST_ITEM.match(block[0]):
        top = _indent(block[0])
        items: list[list[str]] = []
        for line in block:
            if _LIST_ITEM.match(line) and _indent(line) <= top:
                items.append([line])
            else:
                items[-1].append(line)
        return [line for item in items if not _links_unshipped("\n".join(item), shipped)
                for line in item]
    return []


def drop_unshipped_reference_paragraphs(text: str, shipped: frozenset[str]) -> str:
    """Leave out Markdown that links a sibling reference the public Skill does not ship.

    A canonical reference may point to a sibling file that stays private; in the
    public Skill that pointer would dangle.  The offending paragraph is left out
    (only the offending row, item or link definition of a table, list or
    definition block); fenced code is never changed; text without such a link is
    returned byte-for-byte.  A block is a run of non-blank lines, so a heading or
    intro line written directly above a list goes with the list's paragraph.  Only
    same-folder links (`x.md`, `./x.md`) are recognised; other pointers are left to
    the link check.
    """
    lines = text.split("\n")
    segments: list[list] = []  # [kind, lines]; kind is "blank", "code" or "text"
    index = 0
    while index < len(lines):
        fence = _FENCE.match(lines[index])
        if fence:
            end = index + 1
            while end < len(lines) and not lines[end].lstrip().startswith(fence.group(1)):
                end += 1
            segments.append(["code", lines[index:end + 1]])
            index = end + 1
        elif not lines[index].strip():
            segments.append(["blank", [lines[index]]])
            index += 1
        else:
            end = index
            while end < len(lines) and lines[end].strip() and not _FENCE.match(lines[end]):
                end += 1
            segments.append(["text", lines[index:end]])
            index = end
    changed = False
    for segment in segments:
        if segment[0] == "text":
            kept = _filter_text_block(segment[1], shipped)
            if kept != segment[1]:
                segment[1], changed = kept, True
    if not changed:
        return text
    for position, segment in enumerate(segments):
        if segment[0] == "text" and not segment[1]:
            # One separating blank line goes with the block that was left out.
            for neighbour in (position + 1, position - 1):
                if (0 <= neighbour < len(segments) and segments[neighbour][0] == "blank"
                        and segments[neighbour][1]):
                    segments[neighbour][1] = []
                    break
    return "\n".join(line for segment in segments for line in segment[1])
