"""Public privacy syntax; canonical implementation."""
from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path, PurePosixPath


def _path(value: str | Path) -> str:
    return PurePosixPath(str(value).replace("\\", "/")).as_posix().lstrip("./")


def _lf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _replace_lines(text: str, start: int, end: int, replacement: str) -> str:
    lines = _lf(text).splitlines(keepends=True)
    body = _lf(replacement).rstrip("\n") + "\n"
    lines[start - 1:end] = [body]
    return "".join(lines)


def _tree(text: str) -> ast.Module:
    return ast.parse(_lf(text))


def _function(text: str, name: str) -> ast.FunctionDef:
    for node in _tree(text).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise ValueError(f"public sanitizer expected function {name!r}")


def _replace_function(text: str, name: str, replacement: str) -> str:
    node = _function(text, name)
    return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)


def _replace_module_docstring(text: str, replacement: str) -> str:
    tree = _tree(text)
    if not tree.body or not isinstance(tree.body[0], ast.Expr):
        raise ValueError("public sanitizer expected a module docstring")
    node = tree.body[0]
    if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
        raise ValueError("public sanitizer expected a module docstring")
    return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)


def _replace_function_docstring(text: str, name: str, replacement: str) -> str:
    node = _function(text, name)
    if not node.body or not isinstance(node.body[0], ast.Expr):
        raise ValueError(f"public sanitizer expected a docstring in {name!r}")
    doc = node.body[0]
    if not isinstance(doc.value, ast.Constant) or not isinstance(doc.value.value, str):
        raise ValueError(f"public sanitizer expected a docstring in {name!r}")
    return _replace_lines(text, doc.lineno, doc.end_lineno or doc.lineno, replacement)


def _append_module_docstring_note(text: str, note: str) -> str:
    """Append one public-boundary paragraph inside the existing module docstring."""
    public = _lf(text)
    tree = _tree(public)
    node = tree.body[0] if tree.body else None
    if (not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Constant)
            or not isinstance(node.value.value, str)):
        raise ValueError("public sanitizer expected a module docstring")
    lines = public.splitlines(keepends=True)
    closing = lines[node.end_lineno - 1].rstrip("\n")
    quote = closing[-3:]
    if quote not in ('"""', "'''"):
        raise ValueError("public sanitizer expected a triple-quoted module docstring")
    body = closing[:-3]
    lead = body + "\n\n" if body.strip() else "\n"
    lines[node.end_lineno - 1] = lead + note + "\n" + quote + "\n"
    return "".join(lines)


def _replace_main_block(text: str, replacement: str) -> str:
    """Replace the module's ``if __name__ == "__main__":`` self-test block."""
    public = _lf(text)
    blocks = [
        node for node in _tree(public).body
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__"
    ]
    if len(blocks) != 1:
        raise ValueError("public sanitizer expected one __main__ self-test block")
    node = blocks[0]
    return _replace_lines(public, node.lineno, node.end_lineno or node.lineno, replacement)


def _subn_once(pattern: str, replacement, text: str, label: str, flags: int = 0) -> str:
    """Apply one structural replacement and fail closed when the anchor drifts."""
    if isinstance(replacement, str):
        literal = replacement
        replacement = lambda _match: literal  # noqa: E731 - keep backslashes literal
    public, count = re.subn(pattern, replacement, _lf(text), flags=flags)
    if count != 1:
        raise ValueError(f"public sanitizer expected one {label}, found {count}")
    return public


def _replace_top_assignment(text: str, name: str, replacement: str) -> str:
    for node in _tree(text).body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)
    raise ValueError(f"public sanitizer expected assignment {name!r}")


def _replace_local_assignment(text: str, function: str, name: str, replacement: str) -> str:
    scope = _function(text, function)
    for node in ast.walk(scope):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == name for target in targets):
                return _replace_lines(text, node.lineno, node.end_lineno or node.lineno, replacement)
    raise ValueError(f"public sanitizer expected {function}.{name}")


def _drop_stateful_selftest(text: str, function: str) -> str:
    scope = _function(text, function)
    for node in ast.walk(scope):
        if not isinstance(node, ast.If):
            continue
        segment = ast.get_source_segment(_lf(text), node) or ""
        if "STATE_PATH" in segment and "load_state" in segment:
            return _replace_lines(
                text, node.lineno, node.end_lineno or node.lineno,
                "    # PUBLIC_FIXTURE: no maintainer state file is inspected by public self-tests.",
            )
    raise ValueError("public sanitizer expected the stateful channel self-test block")


def _between(text: str, start_prefix: str, end_prefix: str, replacement: str) -> str:
    text = _lf(text)
    start = re.search(rf"(?m)^{re.escape(start_prefix)}.*$", text)
    if not start:
        raise ValueError(f"public sanitizer expected heading {start_prefix!r}")
    end = re.search(rf"(?m)^{re.escape(end_prefix)}.*$", text[start.end():])
    if not end:
        raise ValueError(f"public sanitizer expected heading {end_prefix!r}")
    end_pos = start.end() + end.start()
    return text[:start.start()] + _lf(replacement).rstrip() + "\n\n" + text[end_pos:]


_PRIVATE_IDENTITY_DIGESTS = frozenset({
    "11c37e60e9124b0c55788eab3faf8955165c4d348fbff040200176e3beaa1778",
    "627f99a6fdfb53953c9edee95c030c33bef3ab488c62a0355e244021c0af10f4",
})


def _token_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _generalize_identity(text: str) -> str:
    """Replace private identity tokens by digest while preserving the public repo URL."""
    protected: list[str] = []

    def protect(match: re.Match[str]) -> str:
        protected.append(match.group(0))
        return f"__PUBLIC_AUTHOR_URL_{len(protected) - 1}__"

    public = re.sub(
        r"https://github\.com/[A-Za-z0-9_.-]+/video-autopilot-kit",
        protect,
        text,
    )

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return "creator" if _token_digest(token) in _PRIVATE_IDENTITY_DIGESTS else token

    public = re.sub(r"\b[A-Za-z][A-Za-z0-9]*\b", replace, public)
    public = re.sub(r"\bcreator\s+Studio\b", "creator brand", public)
    for index, url in enumerate(protected):
        public = public.replace(f"__PUBLIC_AUTHOR_URL_{index}__", url)
    return public


def _generalize_project_ids(text: str) -> str:
    public = re.sub(r"(?i)\breference_impl_longform0[1-9]\b", "reference_impl_demo", text)
    public = re.sub(r"(?i)\blongform0[1-9]\b", "demo_longform", public)
    return re.sub(r"長片0[1-9]", "示範長片", public)
