"""Repository Skill forwarder; install materializes its registered src implementation."""
from _kit_source_bridge import load_source as _load_source
_implementation = _load_source('workflow_primitives.py')
globals().update({key: value for key, value in vars(_implementation).items() if not key.startswith('__')})
