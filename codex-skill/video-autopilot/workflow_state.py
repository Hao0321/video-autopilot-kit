"""Repository Skill forwarder; install materializes its registered src implementation."""
from _kit_source_bridge import load_source as _load_source
WORKFLOW_EXECUTABLE_SOURCES = ('workflow_primitives.py', 'workflow_contract_source.py', 'workflow_receipt_store.py', 'public_workflow_sources.py', 'workflow_contract.py', 'workflow_state.py', 'workflow_receipts.py', 'workflow_material_receipts.py', 'workflow_transport.py', 'workflow_audit_binding.py', 'workflow_context_chain.py', 'workflow_json.py', 'workflow_render_retry.py', 'workflow_binding_fixture.py', 'review_policy.py', 'agent_art_review.py', 'engine_continuity.py', 'workflow_contract.json', '_kit_source_bridge.py')
_implementation = _load_source('workflow_state.py')
globals().update({key: value for key, value in vars(_implementation).items() if not key.startswith('__')})
