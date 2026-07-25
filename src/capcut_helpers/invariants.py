"""
capcut_helpers.invariants — AP12 落地 (2026-05-26).

Helper code mutate data 必同步所有 dependent metadata fields. 通用 decorator pattern：
1. Pre-snapshot: list invariants that mutation may violate
2. Mutate
3. Post-check: re-assert each invariant; auto-fix or warn

Born from M69b bug (subtitle_corrections.py 改 text 沒同步 styles[].range → 12 caption GIANT 字).

Usage:
    from capcut_helpers import validate_invariants

    @validate_invariants(
        invariants={
            "styles_range_match_text_len": lambda data: all(
                s.get('range', [0,0])[1] == len(data.get('text', ''))
                for s in data.get('styles', [])
            ),
            "text_non_empty": lambda data: bool(data.get('text')),
        },
        auto_fix={
            "styles_range_match_text_len": lambda data: _fix_styles_range(data),
        },
        on_violation="warn",  # "raise" | "warn" | "silent"
    )
    def apply_some_text_mutation(data, ...):
        # mutation logic
        return data

Available auto-fixes:
    - _fix_styles_range: sets styles[i].range[1] = len(text) for any full-coverage style
"""
import functools
import warnings
from typing import Callable, Optional


def validate_invariants(
    invariants: dict,
    auto_fix: Optional[dict] = None,
    on_violation: str = "warn",
):
    """Decorator: enforce data invariants before+after mutation.

    Args:
        invariants: dict of {invariant_name: check_fn(data) -> bool}
        auto_fix: optional dict of {invariant_name: fix_fn(data) -> data}
        on_violation: "raise" / "warn" / "silent"

    The decorated function must take `data` as first arg and mutate it (in-place OK)
    or return modified data.

    Behavior:
        - PRE: snapshot which invariants currently hold (some may be False already; we don't fix those)
        - MUTATE: run wrapped function
        - POST: re-check each invariant. If was True before and now False → violation.
        - VIOLATION HANDLING: if auto_fix exists, attempt fix; if still violated, apply on_violation policy
    """
    auto_fix = auto_fix or {}
    if on_violation not in ("raise", "warn", "silent"):
        raise ValueError(f"on_violation must be raise/warn/silent, got {on_violation}")

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(data, *args, **kwargs):
            # Pre-snapshot
            pre_states = {}
            for name, check_fn in invariants.items():
                try:
                    pre_states[name] = bool(check_fn(data))
                except Exception:
                    pre_states[name] = None  # check failed — skip

            # 🆕 2026-05-27: auto-snapshot text length for _fix_styles_range
            # (without this, _fix_styles_range can't tell which styles were full-coverage)
            if isinstance(data, dict) and "text" in data:
                data["_prev_text_len"] = len(data.get("text", ""))

            # Run mutation
            result = func(data, *args, **kwargs)
            mutated = result if result is not None else data

            # Post-check
            violations = []
            for name, check_fn in invariants.items():
                if pre_states.get(name) is not True:
                    continue  # was already False or unknown, not our job to fix
                try:
                    if not check_fn(mutated):
                        violations.append(name)
                except Exception as e:
                    violations.append(f"{name} (check raised: {e})")

            # Try auto-fix
            still_violated = []
            for v in violations:
                if v in auto_fix:
                    try:
                        auto_fix[v](mutated)
                        # Re-check
                        if not invariants[v](mutated):
                            still_violated.append(f"{v} (auto-fix failed)")
                    except Exception as e:
                        still_violated.append(f"{v} (auto-fix raised: {e})")
                else:
                    still_violated.append(v)

            # Handle remaining violations per policy
            if still_violated:
                msg = f"[validate_invariants] {func.__name__}() violated: {still_violated}"
                if on_violation == "raise":
                    raise RuntimeError(msg)
                elif on_violation == "warn":
                    warnings.warn(msg, RuntimeWarning, stacklevel=2)

            # snapshot key 絕不能流進 draft JSON — 乾淨路徑也要清 (2026-06-10 audit:
            # 之前只有 _fix_styles_range 觸發時才 pop → 無違規的 mutation 把
            # _prev_text_len 序列化進 CapCut content)
            if isinstance(mutated, dict):
                mutated.pop("_prev_text_len", None)
            if isinstance(data, dict) and data is not mutated:
                data.pop("_prev_text_len", None)

            return result
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────
# Common auto-fixes for CapCut text materials
# ─────────────────────────────────────────────────────────────────────


def _fix_styles_range(co: dict) -> dict:
    """M73 fix — sync styles[].range[1] after text mutation.

    Logic (matches M69b inline fix in subtitle_corrections.py):
        - If style covered FULL old text (r[1] >= old_len) → extend to new_len
        - Else if r[1] > new_len → cap at new_len
        - Else (partial slice still valid) → leave alone

    Requires `co["_prev_text_len"]` snapshot set before mutation (see
    @validate_invariants wrapper auto-snapshot behavior).
    """
    text = co.get("text", "")
    new_len = len(text)
    old_len = co.get("_prev_text_len", new_len)  # fallback no-op
    for s in co.get("styles", []):
        r = s.get("range", [0, 0])
        if not isinstance(r, list) or len(r) != 2:
            continue
        if r[1] >= old_len:  # was full coverage → extend
            s["range"] = [r[0], new_len]
        elif r[1] > new_len:  # partial but now overshoots → cap
            s["range"] = [r[0], new_len]
    # Don't leak the snapshot key into output
    co.pop("_prev_text_len", None)
    return co


# ─────────────────────────────────────────────────────────────────────
# Predefined invariant sets
# ─────────────────────────────────────────────────────────────────────


TEXT_MATERIAL_INVARIANTS = {
    "styles_range_match_text_len": lambda co: all(
        s.get("range", [0, 0])[1] == len(co.get("text", ""))
        for s in co.get("styles", [])
        if isinstance(s.get("range"), list) and len(s["range"]) == 2
    ),
    "text_non_empty": lambda co: bool(co.get("text")),
}

TEXT_MATERIAL_AUTO_FIX = {
    "styles_range_match_text_len": _fix_styles_range,
}


# ─────────────────────────────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────────────────────────────


def _self_test():
    """Self-test the decorator pattern with simulated M69b bug."""

    @validate_invariants(
        invariants=TEXT_MATERIAL_INVARIANTS,
        auto_fix=TEXT_MATERIAL_AUTO_FIX,
        on_violation="warn",
    )
    def buggy_replace(co, old, new):
        """Simulates M69 bug: replace text without syncing styles range."""
        co["text"] = co["text"].replace(old, new)
        # BUG: doesn't update styles[].range[1]
        return co

    # Setup
    co = {
        "text": "hello cloud world",
        "styles": [{"range": [0, 17]}],  # full coverage of "hello cloud world"
    }
    assert TEXT_MATERIAL_INVARIANTS["styles_range_match_text_len"](co), "pre-condition"

    # Buggy mutation (cloud → Claude, +1 char)
    buggy_replace(co, "cloud", "Claude")

    # Decorator should have auto-fixed it
    assert co["text"] == "hello Claude world"
    assert co["styles"][0]["range"] == [0, len(co["text"])], (
        f"auto-fix should have synced range, got {co['styles'][0]['range']}"
    )
    print("[OK] self-test passed: text=%r range=%s" % (co["text"], co["styles"][0]["range"]))


if __name__ == "__main__":
    _self_test()
