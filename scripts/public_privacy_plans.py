"""Public privacy plans; canonical implementation."""
from __future__ import annotations

import re
from public_privacy_syntax import _lf, _replace_function, _replace_module_docstring, _replace_function_docstring, _drop_stateful_selftest, _subn_once


def _channel_tracker(text: str) -> str:
    text = _replace_module_docstring(text, '''"""Channel publishing state machine (public distribution).

The JSON state stores D2/D7/D28 scheduling and pending actions.  It does not
ship a maintainer state file or maintainer analytics.  Examples in this module
are synthetic and exist only to exercise the public API.

PUBLIC_FIXTURE: channel metrics examples are synthetic.
"""''')
    text = _replace_function_docstring(text, "record_metrics", '''    """Store only metrics explicitly supplied by the caller.

    Platforms can have different scales, so missing fields remain absent rather
    than being filled or inferred.  The numbers used by the self-test are
    illustrative fixtures, never copied channel analytics.
    """''')
    return _drop_stateful_selftest(text, "_selftest")


PUBLIC_REMIX_KEY_FUNCTION = '''def _key(row: dict) -> list[tuple[str, str]]:
    """Build generic grouping keys without hard-coded maintainer projects."""
    out = []
    niche = str(row.get("niche") or "").lower()
    place = str(row.get("place") or "").strip()
    series = str(row.get("series") or "").strip()
    if place:
        out.append(("place", place))
    if niche and niche not in {"auto", "general"}:
        out.append(("niche", niche))
    if series:
        out.append(("series", series))
    return out'''


PUBLIC_REMIX_SELFTEST = '''def _selftest() -> None:
    rows = [
        {"content_id": "S901", "niche": "travel", "place": "示範城", "series": "public-demo-series"},
        {"content_id": "S902", "niche": "travel", "place": "示範城", "series": "public-demo-series"},
    ]
    groups = defaultdict(list)
    for row in rows:
        for key in _key(row):
            groups[key].append(row)
    assert len(groups[("series", "public-demo-series")]) == 2
    assert len(groups[("place", "示範城")]) == 2
    print("remix_planner self-test GREEN (PUBLIC_FIXTURE)")'''


def _remix_planner(text: str) -> str:
    text = _replace_function(text, "_key", PUBLIC_REMIX_KEY_FUNCTION)
    return _replace_function(text, "_selftest", PUBLIC_REMIX_SELFTEST)


def _asset_registry(text: str) -> str:
    result, count = re.subn(
        r'(?m)^(\s*semantic_target=)"[^"]*"(,\s*)$',
        r'\1"示範城旅行用的精緻紙張地理標籤"\2  # PUBLIC_FIXTURE',
        _lf(text), count=1,
    )
    if count != 1:
        raise ValueError("public sanitizer expected one asset-registry semantic fixture")
    return _subn_once(
        r'(bounded = build_asset_plan\(\n[ \t]*topic=)"[^"\n]*"',
        lambda match: match.group(1) + '"示範老街手作與散步"',
        result, "bounded asset-plan topic fixture",
    )
