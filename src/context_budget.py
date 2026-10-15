"""Conservative token estimate shared by routing and planning bindings."""
import json
import math
import re

def estimate_tokens(value) -> int:
    """Conservative local estimate for mixed Traditional Chinese and JSON."""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    cjk = len(re.findall(r"[\u3400-\u9fff\uf900-\ufaff]", text))
    other = len(text) - cjk
    return cjk + math.ceil(max(0, other) / 4)
