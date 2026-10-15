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
)
ADAPTER_FILES = (*ADAPTER_MODULES, "workflow_contract.json")
PUBLIC_ONLY_MODULES = frozenset(("public_workflow_sources.py",))


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
                if any(module.startswith(("workflow_original", "workflow_painted", "workflow_longform")) for module in modules):
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
            pin = CANONICAL_PUBLIC_OWNED_PINS["root"].get(name)
            # Inventory pins use original physical bytes, not normalized text hashes.
            if not pin or hashlib.sha256((canonical / name).read_bytes()).hexdigest() != pin:
                raise ValueError("Public workflow canonical analogue changed: " + name)
        if not name.endswith(".py"):
            origin, public = json.loads(private_text), json.loads(sources[name])
            for key in ("schema", "contract_revision", "plan_schema", "legacy_plan_policy", "engine_continuity_floor", "limits"):
                if origin.get(key) != public.get(key):
                    raise ValueError("Public adapter contract floor differs: " + key)
