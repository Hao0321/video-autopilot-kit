"""Use one current Kit implementation; installed Skills contain materialized code."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import stat
import sys

ALLOWED = frozenset((
    "engine_continuity.py", "workflow_contract.py", "workflow_state.py", "workflow_receipts.py",
    "workflow_material_receipts.py", "workflow_transport.py", "workflow_audit_binding.py",
    "workflow_context_chain.py", "workflow_render_retry.py", "workflow_binding_fixture.py",
    "workflow_primitives.py", "workflow_contract_source.py", "workflow_receipt_store.py", "public_workflow_sources.py",
))


def _regular(path: Path) -> None:
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
            or info.st_nlink != 1 or not 0 < info.st_size <= 1024 * 1024):
        raise RuntimeError("Kit source bridge requires bounded unaliased source")


def load_source(filename: str):
    if filename not in ALLOWED:
        raise RuntimeError("Kit source bridge rejected an unknown module")
    skill = Path(__file__).resolve().parent
    root = skill.parents[1]
    manifest = root / "release-manifest.json"
    _regular(manifest)
    contract = json.loads(manifest.read_text(encoding="utf-8-sig"))
    if (contract.get("project_id") != "video-autopilot-kit"
            or contract.get("codex_skill", {}).get("source") != "codex-skill/video-autopilot"
            or skill != root / "codex-skill/video-autopilot"):
        raise RuntimeError("Kit source bridge does not belong to the current package")
    source_dir = root / "src"
    for folder in (root / "codex-skill", skill, source_dir):
        info = folder.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise RuntimeError("Kit source bridge rejected an aliased directory")
    path = source_dir / filename
    _regular(path)
    name = path.stem
    existing = sys.modules.get(name)
    if existing is not None:
        origin = Path(getattr(existing, "__file__", "")).resolve()
        if origin not in {path, skill / filename}:
            raise RuntimeError("Kit source bridge detected a conflicting imported module")
        if origin == path:
            return existing
    alias = "_video_autopilot_public_" + name
    if alias in sys.modules:
        module = sys.modules[alias]
        if Path(module.__file__).resolve() != path:
            raise RuntimeError("Kit source bridge detected an alias conflict")
        return module
    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Kit source module loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(alias, None)
        raise
    return module
