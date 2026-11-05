"""Explicit media-only adapters and generated repository Skill entrypoints."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path

ADAPTER_MODULES = (
    "engine_continuity.py", "workflow_contract.py", "workflow_state.py", "workflow_receipts.py",
    "workflow_material_receipts.py", "workflow_transport.py", "workflow_audit_binding.py",
    "workflow_context_chain.py", "workflow_render_retry.py", "workflow_binding_fixture.py",
    "workflow_primitives.py", "workflow_contract_source.py", "workflow_receipt_store.py", "public_workflow_sources.py",
    "workflow_chapter_contract.py", "workflow_longform_runtime.py", "workflow_longform.py",
)
ADAPTER_FILES = (*ADAPTER_MODULES, "workflow_contract.json", "workflow_longform_contract.json")
PUBLIC_ONLY_MODULES = frozenset(("public_workflow_sources.py",))
# Public ports of the canonical long-form session controller (create-longform).
# The canonical inventory keeps these analogues private (sync never copies
# them); each pin records the physical canonical bytes the public port was
# reviewed against, so a changed canonical analogue blocks sync until the port
# is reviewed again. Production pins never overlap CANONICAL_PUBLIC_OWNED_PINS.
REVIEWED_PRIVATE_ANALOGUE_PINS = {
    "workflow_chapter_contract.py": "82841f1e2d07ef10f3f7fa7b1f218ba9a6cbd7fdf6d320736bab0bf38eedcc7d",
    "workflow_longform_runtime.py": "2746bbf7d51af74c5b84b0e5d64763440d0badc5b31c541cee57e15ad220deaf",
    "workflow_longform.py": "32024f835e11bfed1ed9790b1c7ff3b35062b07ea29271e73228dc9ba942dfdb",
    "workflow_longform_contract.json": "195dd0d1a27f4cbed5b982d7704d73c6a7b40f473c517cfbbdd718a72588ffc8",
}


def render_forwarder(name: str, source_names: tuple[str, ...] = ()) -> str:
    if name not in ADAPTER_MODULES:
        raise ValueError("unregistered public workflow forwarder")
    declaration = ""
    if name == "workflow_state.py":
        declaration = "WORKFLOW_EXECUTABLE_SOURCES = " + repr((*source_names, "_kit_source_bridge.py")) + "\n"
    cli = "\nif __name__ == '__main__':\n    raise SystemExit(_implementation.main())\n" if name == "workflow_contract.py" else ""
    return ("\"\"\"Repository Skill forwarder; install materializes its registered src implementation.\"\"\"\n"
            "from _kit_source_bridge import load_source as _load_source\n" + declaration +
            "_implementation = _load_source(" + repr(name) + ")\n"
            "globals().update({key: value for key, value in vars(_implementation).items() if not key.startswith('__')})\n" + cli)


def _public_adapter_sources(distribution: Path, read_source) -> dict[str, str]:
    sources = {}
    for name in ADAPTER_FILES:
        text = sources[name] = read_source(distribution / "src" / name)
        if name.endswith(".py"):
            for node in ast.walk(ast.parse(text)):
                modules = ([node.module or ""] if isinstance(node, ast.ImportFrom) else
                           [a.name for a in node.names] if isinstance(node, ast.Import) else [])
                if any(module.startswith(("workflow_original", "workflow_painted")) for module in modules):
                    raise ValueError("Public media-only adapter imported an undistributed branch: " + name)
    return sources


def validate_adapters(canonical: Path, distribution: Path, read_source) -> None:
    """Preflight the complete public shape, then pin its canonical provenance."""
    from public_sync_inventory import CANONICAL_PUBLIC_OWNED_PINS
    sources = _public_adapter_sources(distribution, read_source)
    state = ast.parse(sources["workflow_state.py"])
    declaration = next(n.value for n in state.body if isinstance(n, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == "WORKFLOW_EXECUTABLE_SOURCES" for t in n.targets))
    names = tuple(ast.literal_eval(declaration))
    for name in ADAPTER_MODULES:
        text = read_source(distribution / "codex-skill/video-autopilot" / name)
        if text != render_forwarder(name, names):
            raise ValueError("Public workflow repository forwarder drift: " + name)
    manifest = json.loads(read_source(distribution / "release-manifest.json"))
    expected = {name: "src/" + name for name in ADAPTER_MODULES}
    if manifest.get("codex_skill", {}).get("materialize_from") != expected:
        raise ValueError("Public standalone Skill materialization contract drift")
    for name in ADAPTER_FILES:
        private_text = None
        if name in PUBLIC_ONLY_MODULES:
            if (canonical / name).exists():
                raise ValueError("New canonical analogue requires explicit adapter review: " + name)
        else:
            private_text = read_source(canonical / name)
            pin = {**REVIEWED_PRIVATE_ANALOGUE_PINS, **CANONICAL_PUBLIC_OWNED_PINS["root"]}.get(name)
            # Inventory pins use original physical bytes, not normalized text hashes.
            if not pin or hashlib.sha256((canonical / name).read_bytes()).hexdigest() != pin:
                raise ValueError("Public workflow canonical analogue changed: " + name)
        if name == "workflow_longform_contract.json":
            if json.loads(private_text) != json.loads(sources[name]):
                raise ValueError("Public long-form session contract differs from its canonical analogue")
        elif not name.endswith(".py"):
            origin, public = json.loads(private_text), json.loads(sources[name])
            for key in ("schema", "contract_revision", "plan_schema", "legacy_plan_policy", "engine_continuity_floor", "limits"):
                if origin.get(key) != public.get(key):
                    raise ValueError("Public adapter contract floor differs: " + key)
