"""Leave pointers to things the public kit does not have out of the shipped references."""
from __future__ import annotations

import ast
import re
import textwrap

# Inline links `[t](x.md)`, `[t](<./x.md#part> "title")` and reference definitions `[id]: ./x.md`.
_SIBLING_MARKDOWN_LINK = re.compile(
    r"\]\(<?(?:\./)?([A-Za-z0-9_.-]+\.md)(?:#[^)\s>]*)?>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\)"
    r"|^\s{0,3}\[[^\]]+\]:\s*<?(?:\./)?([A-Za-z0-9_.-]+\.md)(?:#\S*)?>?", re.M)
_FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_LIST_ITEM = re.compile(r"^\s{0,3}(?:[-*+]|\d+[.)])\s")
_ANY_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_ORDERED_ITEM = re.compile(r"^(\s*)(\d+)[.)]\s")
_REFERENCE_DEFINITION = re.compile(r"^\s{0,3}\[[^\]]+\]:\s")
_HEADING = re.compile(r"^(#{1,6})\s")
_INLINE_CODE = re.compile(r"`([^`\n]+)`")
_DOTTED = re.compile(r"[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)+")
_FILE_SUFFIXES = frozenset(("py", "md", "json", "jsonl", "yaml", "yml", "txt", "csv", "srt", "ass", "html", "css",
                            "js", "ts", "tsx", "png", "jpg", "jpeg", "webp", "mp4", "mov", "wav", "mp3", "zip", "log"))
# Packages of the maintained source whose submodules can be named through the package.
PACKAGES = frozenset(("longform_maker", "silent_vlog_maker", "drama_pipeline"))
_PLACEHOLDER = re.compile(r"[*?\[\]{}<>$%]")
_LOCATION_SUFFIX = re.compile(r"(?:#.*|::.*|:\d+(?::\d+)?|:[A-Za-z_]\w*)$")
# Any relative link target, for example `[t](../src/x.py)` or `[t](私人.md)`.
_RELATIVE_LINK = re.compile(r"\]\(<?(?!(?:[a-z][a-z0-9+.-]*:|#|/))([^)\s>]+)>?"
                            r"|^\s{0,3}\[[^\]]+\]:\s*<?(?!(?:[a-z][a-z0-9+.-]*:|#|/))([^\s>]+)>?", re.M)
_ANCHOR_LINK = re.compile(r"\]\(#([^)\s]+)\)")
_PYTHON_INFO = frozenset(("", "python", "py", "python3", "pycon"))
_SETUP_LINE = re.compile(r"^\s*(?:\$\s+)?(?:cd|pushd|popd|Set-Location)\b", re.I)
# Anchors of headings the filter removed; consulted while it re-filters links to them.
_GONE_ANCHORS: set[str] = set()
_DASH_C = re.compile(r"(?:^|\s)-c\s+([\"'])(.*?)\1")
_SENTENCE_BREAK = re.compile(r"[。！？]|(?<!\be\.g)(?<!\bi\.e)(?<!\betc)(?<!\bvs)(?<!\bcf)[.!?](?=\s|$)")
_DOTTED_HEAD = re.compile(r"([A-Za-z_]\w*)((?:\.[A-Za-z_]\w*)*)(\.?)")
_IMPORT_LINE = re.compile(r"^\s*(?:(?:>>>|\.\.\.)\s*)?(?:from\s+([A-Za-z_][\w.]*)\s+import\s+([^#\n]*)"
                          r"|import\s+([A-Za-z_][\w.,\s]*))", re.M)
_PYTHON_CALL = re.compile(r"(?<![\w.])(?:python(?:3(?:\.\d+)?)?(?:\.exe)?|py(?:\s+-3(?:\.\d+)?)?|uv\s+run)\s")
_DIRECT_SCRIPT = re.compile(r"^\s*(?:\$\s+)?\.{1,2}[\\/]([\w./\\-]+\.py)\b")
_PY_TOKEN = re.compile(r"[^\s\"'=]+\.py\b")
_RUN_MODULE = re.compile(r"(?:^|\s)-m\s+([A-Za-z_][\w.]*)")
_PROMPT = re.compile(r"^\s*(?:>>>|\.\.\.)\s?")
_CONTINUATION = ("\\", "^", "`", "&&", "||", "|")
_HERE_DOCUMENT = re.compile(r"<<-?\s*['\"]?\w+|@['\"]\s*$")
_INTRO_END = (":", "：")


def imported_names(tree: ast.AST) -> set[str]:
    """Module names an AST can import: dotted parts, submodules named from a package, import_module() targets."""
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            parts = (node.module or "").split(".")
            found.update(parts)
            if node.level or parts[-1] in PACKAGES:
                found.update(alias.name for alias in node.names)
        elif (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
              and isinstance(node.args[0].value, str)
              and getattr(node.func, "attr", getattr(node.func, "id", None)) in ("import_module", "__import__")):
            found.update(node.args[0].value.split("."))
    return found - {""}


def _unshipped_module(name: str, modules: frozenset[str] | None) -> bool:
    return modules is not None and name.endswith(".py") and name not in modules


def _private_module_path(dotted: str, private: frozenset[str]) -> bool:
    """`module.attr`, `package.module` or `package.module.attr` naming a private module."""
    parts = dotted.split(".")
    if parts[-1].lower() in _FILE_SUFFIXES and len(parts) == 2:
        return False  # a file name such as `plan.json`
    if parts[0] + ".py" in private:
        return True
    return parts[0] in PACKAGES and len(parts) > 1 and parts[1] + ".py" in private


def _dotted_head_private(target: str, private: frozenset[str]) -> bool:
    head = _DOTTED_HEAD.match(target)
    if not head or not (head.group(2) or head.group(3)):
        return False  # no dot after the first name
    return _private_module_path(head.group(1) + (head.group(2) or ".x"), private)


def _points_unshipped(token: str, shipped: frozenset[str], private: frozenset[str],
                      modules: frozenset[str] | None) -> bool:
    target = _LOCATION_SUFFIX.sub("", token.strip("\"'(),;")).rstrip(".:/")
    parts = [part for part in re.split(r"[\\/]", target) if part]
    if not parts:
        return False
    name = parts[-1]
    if len(parts) == 1 and _dotted_head_private(target, private):
        return True  # `module.attr(...)`, `module.<name>` or `package.module` of a private module
    if _PLACEHOLDER.search(name) or name.startswith("."):
        return False  # a glob, placeholder, variable or bare suffix, not a pointer
    if parts[0] == "references" and len(parts) > 1 and name not in shipped:
        return True  # a sibling reference the public Skill does not ship
    if name.endswith(".md") and name in private:
        return True  # a private document of the maintained source
    if name.endswith(".tsx") or (name.endswith(".ts") and len(parts) > 1):
        return True  # a TypeScript source path of another program (a bare `x.ts` may be a video file)
    if _unshipped_module(name, modules):
        return True  # a module the public kit does not ship
    dotted = _DOTTED.fullmatch(target.split("(")[0])
    return bool(dotted and _private_module_path(dotted.group(0), private))


def _code_imports_private(code: str, private: frozenset[str]) -> bool:
    """Python source (prompts allowed, one line or many) that imports a private module."""
    source = "\n".join(_PROMPT.sub("", line) for line in code.split("\n"))
    try:
        tree = ast.parse(textwrap.dedent(source).strip())
    except SyntaxError:
        return any(_import_line_private(match, private) for match in _IMPORT_LINE.finditer(source))
    return any(name + ".py" in private for name in imported_names(tree))


def _import_line_private(match: re.Match, private: frozenset[str]) -> bool:
    if match.group(1):
        parts = match.group(1).split(".")
        names = re.findall(r"[A-Za-z_]\w*", match.group(2)) if parts[-1] in PACKAGES else []
        return any(part + ".py" in private for part in parts + names)
    if re.search(r"\bfrom\b", match.group(3)):
        return False  # JavaScript `import x from '...'`, not Python
    modules = [item.split()[0] for item in match.group(3).split(",") if item.strip()]
    return any(part + ".py" in private for module in modules for part in module.split("."))


def _relative_link_unshipped(target: str, shipped: frozenset[str], private: frozenset[str],
                             modules: frozenset[str] | None) -> bool:
    parts = [part for part in re.split(r"[\\/]", target.split("#")[0]) if part not in ("", ".")]
    if not parts:
        return False
    name = parts[-1]
    if len(parts) == 1 and name.endswith(".md"):
        return name not in shipped  # a same-folder sibling
    return (name in private or name.endswith(".tsx") or (name.endswith(".ts") and len(parts) > 1)
            or _unshipped_module(name, modules))


def _links_unshipped(text: str, shipped: frozenset[str], private: frozenset[str] = frozenset(),
                     modules: frozenset[str] | None = None) -> bool:
    if any((match.group(1) or match.group(2)) not in shipped
           for match in _SIBLING_MARKDOWN_LINK.finditer(text)):
        return True
    if any(_relative_link_unshipped(match.group(1) or match.group(2), shipped, private, modules)
           for match in _RELATIVE_LINK.finditer(text)):
        return True
    if _GONE_ANCHORS and any(match.group(1) in _GONE_ANCHORS for match in _ANCHOR_LINK.finditer(text)):
        return True  # a table-of-contents link to a section that was left out
    for match in _INLINE_CODE.finditer(text):
        span = match.group(1)
        if (any(_points_unshipped(token, shipped, private, modules) for token in span.split())
                or _code_imports_private(span, private) or _runs_unshipped_module(span + " ", private, modules)):
            return True
    return False


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _strip_trailing_blanks(lines: list[str]) -> list[str]:
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def _cut_after_last_sentence(line: str) -> str | None:
    """The part of a line up to its last sentence end, or None when it has none."""
    breaks = list(_SENTENCE_BREAK.finditer(line))
    return line[:breaks[-1].end()].rstrip() if breaks else None


def _without_trailing_intro(lines: list[str]) -> list[str]:
    """Drop a trailing sentence that ends in a colon, also across wrapped lines: it introduced something that went."""
    lines = _strip_trailing_blanks(list(lines))
    while lines and lines[-1].rstrip().endswith(_INTRO_END):
        last = lines.pop().rstrip()
        kept = _cut_after_last_sentence(last[:-1])
        if kept is not None:
            lines.append(kept)  # an earlier sentence on the same line stays
        else:
            while lines and lines[-1].strip():
                kept = _cut_after_last_sentence(lines[-1].rstrip())
                if kept == lines[-1].rstrip():
                    break  # the previous line ends a sentence
                lines.pop()
                if kept is not None:
                    lines.append(kept)
                    break
        lines = _strip_trailing_blanks(lines)
    return lines


def _filter_table(rows: list[str], shipped: frozenset[str], private: frozenset[str],
                  modules: frozenset[str] | None) -> list[str]:
    if len(rows) < 3 or _links_unshipped("\n".join(rows[:2]), shipped, private, modules):
        return []
    kept = [row for row in rows[2:] if not _links_unshipped(row, shipped, private, modules)]
    return rows[:2] + kept if kept else []


def _filter_text_block(block: list[str], shipped: frozenset[str],
                       private: frozenset[str] = frozenset(),
                       modules: frozenset[str] | None = None) -> list[str]:
    """Keep a block, or drop it, or only its offending table rows, list items or link definitions."""
    if not _links_unshipped("\n".join(block), shipped, private, modules):
        return block
    if all(line.lstrip().startswith("|") for line in block):
        return _filter_table(block, shipped, private, modules)
    if all(_REFERENCE_DEFINITION.match(line) for line in block):
        return [line for line in block if not _links_unshipped(line, shipped, private, modules)]
    if _LIST_ITEM.match(block[0]):
        return _strip_trailing_blanks(_filter_list(block, shipped, private, modules))
    start = next((index for index, line in enumerate(block)
                  if _LIST_ITEM.match(line) or line.lstrip().startswith("|")), None)
    if start is None or _links_unshipped("\n".join(block[:start]), shipped, private, modules):
        return []  # the pointer is in the text itself: the whole block goes
    # Text directly above a list or table stays while any of its items or rows stays.
    rest = block[start:]
    if all(line.lstrip().startswith("|") for line in rest):
        kept = _filter_table(rest, shipped, private, modules)
    elif _LIST_ITEM.match(rest[0]):
        kept = _strip_trailing_blanks(_filter_list(rest, shipped, private, modules))
    else:
        kept = []
    return block[:start] + kept if kept else _without_trailing_intro(block[:start])


def _filter_list(lines: list[str], shipped: frozenset[str], private: frozenset[str],
                 modules: frozenset[str] | None) -> list[str]:
    """Drop offending list items; an item whose own text is clean keeps it and loses only nested items."""
    top = _indent(lines[0])
    items: list[list[str]] = []
    for line in lines:
        if line.strip() and _ANY_LIST_ITEM.match(line) and _indent(line) <= top:
            items.append([line])
        else:
            items[-1].append(line)
    kept: list[list[str]] = []
    for item in items:
        if not _links_unshipped("\n".join(item), shipped, private, modules):
            kept.append(list(item))
            continue
        nested = next((index for index, line in enumerate(item[1:], 1)
                       if line.strip() and _ANY_LIST_ITEM.match(line) and _indent(line) > top), None)
        if nested is not None and not _links_unshipped("\n".join(item[:nested]), shipped, private, modules):
            head, rest = item[:nested], _filter_list(item[nested:], shipped, private, modules)
            if not any(line.strip() for line in rest) and _strip_trailing_blanks(head)[-1].rstrip().endswith(_INTRO_END):
                kept.append([])  # an item that only introduced its nested items goes with them
            else:
                kept.append(head + rest)
        else:
            kept.append([])  # dropped; the empty marker keeps the numbering below in step
    _renumber(items, kept)
    return [line for item in kept for line in item]


def _renumber(items: list[list[str]], kept: list[list[str]]) -> None:
    """Close the gaps a dropped item leaves in an ordered sequence (a list restarting at its own number stays)."""
    shift, previous = 0, None
    for original, item in zip(items, kept):
        match = _ORDERED_ITEM.match(original[0])
        if not match:
            continue
        number = int(match.group(2))
        if previous is None or number != previous + 1:
            shift = 0  # a new sequence
        previous = number
        if not item:
            shift += 1
        elif shift:
            item[0] = match.group(1) + str(number - shift) + item[0][match.end(2):]


def _runs_unshipped_module(line: str, private: frozenset[str], modules: frozenset[str] | None) -> bool:
    direct = _DIRECT_SCRIPT.match(line)
    if direct and _unshipped_module(re.split(r"[\\/]", direct.group(1))[-1], modules):
        return True  # a script run directly, such as `./tool.py`
    call = _PYTHON_CALL.search(line)
    if not call:
        return False
    rest = line[call.end():]
    if any(_unshipped_module(re.split(r"[\\/]", token)[-1], modules) for token in _PY_TOKEN.findall(rest)):
        return True
    module = _RUN_MODULE.search(rest)
    return bool(module and _private_module_path(module.group(1) + ".x", private))


def _imports_private(lines: list[str], private: frozenset[str]) -> bool:
    """Whole Python body first (multi-line imports), then each line and each `-c` argument (any language)."""
    if _code_imports_private("\n".join(lines), private):
        return True
    return any(_code_imports_private(line, private)
               or any(_code_imports_private(match.group(2), private) for match in _DASH_C.finditer(line))
               for line in lines)


def _is_python_fence(lines: list[str]) -> bool:
    info = lines[0].strip().lstrip("`~").strip().lower().split()
    return (info[0] if info else "") in _PYTHON_INFO


def _python_uses_private(lines: list[str], private: frozenset[str]) -> bool:
    """Python code that calls into a private module, for example `module.function(...)`."""
    return any(_dotted_head_private(match.group(0), private) for line in lines for match in _DOTTED.finditer(line))


def _filter_code_block(lines: list[str], private: frozenset[str], modules: frozenset[str] | None) -> list[str]:
    """Drop the commands that run a module the kit does not ship, each with its own comment right above it.

    The whole block goes when a Python example imports a private module, when such a
    command is continued over several lines or feeds a here-document, or when no command is left.
    """
    closed = len(lines) > 1 and _FENCE.match(lines[-1]) is not None
    body = lines[1:-1] if closed else lines[1:]
    if _imports_private(body, private) or (_is_python_fence(lines) and _python_uses_private(body, private)):
        return []  # an example that imports or calls a private module (also through `python -c` or a here-document)
    hits = {index for index, line in enumerate(body) if _runs_unshipped_module(line, private, modules)}
    if not hits:
        return lines
    if any(body[index].rstrip().endswith(_CONTINUATION) or _HERE_DOCUMENT.search(body[index])
           or (index > 0 and (body[index - 1].rstrip().endswith(_CONTINUATION)
                              or _HERE_DOCUMENT.search(body[index - 1])))
           or (index + 1 < len(body) and body[index + 1].lstrip().startswith(("|", "&&", "||")))
           for index in hits):
        return []
    for index in sorted(hits):
        after = index + 1
        shared = (after < len(body) and body[after].strip() and not body[after].lstrip().startswith("#")
                  and after not in hits)
        above = index - 1
        while not shared and above >= 0 and body[above].lstrip().startswith("#") and above not in hits:
            hits.add(above)
            above -= 1
    kept: list[str] = []
    for index, line in enumerate(body):
        if index in hits or (not line.strip() and index - 1 in hits and (not kept or not kept[-1].strip())):
            continue  # a removed command group takes one separating blank line with it
        kept.append(line)
    if not any(line.strip() and not line.lstrip().startswith("#") and not _SETUP_LINE.match(line) for line in kept):
        return []  # nothing but comments or directory changes is left
    return lines[:1] + kept + (lines[-1:] if closed else [])


def _segments(text: str) -> list[list]:
    """Split Markdown into [kind, lines]: "blank", "code" or "text".

    Every heading is its own segment; a loose list stays one text block.
    """
    lines = text.split("\n")
    segments: list[list] = []
    index = 0
    while index < len(lines):
        fence = _FENCE.match(lines[index])
        if fence:
            end = index + 1
            while end < len(lines) and not lines[end].lstrip().startswith(fence.group(1)):
                end += 1
            segments.append(["code", lines[index:end + 1]])
            index = end + 1
            continue
        if not lines[index].strip():
            segments.append(["blank", [lines[index]]])
            index += 1
            continue
        end = index + 1
        if not _HEADING.match(lines[index]):
            while (end < len(lines) and lines[end].strip() and not _FENCE.match(lines[end])
                   and not _HEADING.match(lines[end])):
                end += 1
        if _LIST_ITEM.match(lines[index]):
            top = _indent(lines[index])
            while True:  # blank-separated items and indented continuation paragraphs belong to the list
                gap = end
                while gap < len(lines) and not lines[gap].strip():
                    gap += 1
                if gap == end or gap >= len(lines) or _FENCE.match(lines[gap]):
                    break
                following = lines[gap]
                if not ((_ANY_LIST_ITEM.match(following) and _indent(following) >= top) or _indent(following) > top + 1):
                    break
                end = gap
                while (end < len(lines) and lines[end].strip() and not _FENCE.match(lines[end])
                       and not _HEADING.match(lines[end])):
                    end += 1
        segments.append(["text", lines[index:end]])
        index = end
    return segments


def _drop_offending_sections(segments: list[list], shipped: frozenset[str], private: frozenset[str],
                             modules: frozenset[str] | None) -> None:
    """A heading whose own line points at something missing goes with its whole section."""
    level = None
    for segment in segments:
        heading = _HEADING.match(segment[1][0]) if segment[0] == "text" else None
        if level is not None:
            if heading and len(heading.group(1)) <= level:
                level = None
            elif segment[0] != "blank":
                segment[1] = []
                continue
        if heading and _links_unshipped(segment[1][0], shipped, private, modules):
            level = len(heading.group(1))
            segment[1] = []


def _section_is_empty(segments: list[list], index: int) -> bool:
    lines = segments[index][1]
    level = len(_HEADING.match(lines[0]).group(1))
    if any(line.strip() for line in lines[1:]):
        return False
    for later in segments[index + 1:]:
        if later[0] == "blank" or not later[1]:
            continue
        heading = _HEADING.match(later[1][0]) if later[0] == "text" else None
        return bool(heading) and len(heading.group(1)) <= level
    return True


def _close_numbering_gap(segments: list[list], start: int, dropped: int) -> None:
    """Renumber the next ordered list when it continued the sequence of a dropped item."""
    for segment in segments[start + 1:]:
        if segment[0] == "blank" or not segment[1]:
            continue
        first = _ORDERED_ITEM.match(segment[1][0]) if segment[0] == "text" else None
        if not first or int(first.group(2)) != dropped + 1:
            return
        top, expected = _indent(segment[1][0]), dropped + 1
        for position, line in enumerate(segment[1]):
            match = _ORDERED_ITEM.match(line)
            if match and _indent(line) == top and int(match.group(2)) == expected:
                segment[1][position] = match.group(1) + str(expected - 1) + line[match.end(2):]
                expected += 1
        return


def _drop_emptied_intros_and_headings(segments: list[list], original: list[list]) -> None:
    """An intro (paragraph or last list item) whose content below went goes; so does a heading whose section emptied."""
    for index, (kind, lines) in enumerate(segments):
        if kind != "text" or not lines or _HEADING.match(lines[0]) or lines[0].lstrip().startswith("|"):
            continue
        if not _strip_trailing_blanks(lines)[-1].rstrip().endswith(_INTRO_END):
            continue
        following = next((later for later in range(index + 1, len(segments)) if original[later][0] != "blank"), None)
        if (following is None or segments[following][1]
                or (original[following][0] == "text" and _HEADING.match(original[following][1][0]))):
            continue
        if _LIST_ITEM.match(lines[0]):
            last = max(position for position, line in enumerate(lines)
                       if line.strip() and _ANY_LIST_ITEM.match(line) and _indent(line) <= _indent(lines[0]))
            dropped = _ORDERED_ITEM.match(lines[last])
            segments[index][1] = _strip_trailing_blanks(lines[:last])  # the last item introduced what went
            if dropped:
                _close_numbering_gap(segments, following, int(dropped.group(2)))
        else:
            segments[index][1] = _without_trailing_intro(lines)
    for index in reversed(range(len(segments))):
        kind, lines = segments[index]
        if (kind == "text" and lines and _HEADING.match(lines[0])
                and _section_is_empty(segments, index) and not _section_is_empty(original, index)):
            segments[index][1] = []


def _join(segments: list[list]) -> str:
    """Join kept segments; a left-out block takes one separating blank line with it, never both."""
    tokens: list[list | None] = [segment if segment[1] else None for segment in segments]
    index = 0
    while index < len(tokens):
        if tokens[index] is not None:
            index += 1
            continue
        if index + 1 < len(tokens) and tokens[index + 1] is None:
            del tokens[index]
            continue
        previous = tokens[index - 1] if index > 0 else None
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        previous_blank = previous is None or previous[0] == "blank"
        following_blank = following is None or following[0] == "blank"
        if previous_blank and following_blank:
            del tokens[index]
            if following is not None:
                del tokens[index]
            elif previous is not None:
                del tokens[index - 1]
                index -= 1
        elif (not previous_blank and not following_blank and previous[0] == following[0] == "text"
              and not _HEADING.match(previous[1][0]) and not _HEADING.match(following[1][0])):
            tokens[index] = ["blank", [""]]  # keep two paragraphs from merging into one
        else:
            del tokens[index]
    return "\n".join(line for token in tokens for line in token[1])


def drop_unshipped_reference_paragraphs(text: str, shipped: frozenset[str],
                                        private: frozenset[str] = frozenset(),
                                        modules: frozenset[str] | None = None) -> str:
    """Leave out Markdown that points at something the public kit does not have.

    A canonical reference may point to a sibling file or module that stays private;
    in the public Skill that pointer would dangle.  Pointers are same-folder links
    (`x.md`, `./x.md`, `<x.md>`) to unshipped siblings, relative links to a private
    file, a TypeScript file or an unshipped module, and inline-code spans naming
    an unshipped ``references/`` file, a private document, a private module (as
    ``module.attr`` or through its package) or a private import or ``-m`` run, a
    TypeScript source file, or, with ``modules`` (every Python module the kit
    ships), any other ``.py`` module.  Plain-text mentions outside inline code are
    not pointers.

    A text block holding a pointer outside its list items or table rows is left out
    whole; otherwise only the offending item (or nested item), row or definition
    goes, and an ordered list is renumbered.  A heading whose own line holds a
    pointer goes with its section, an intro (a sentence or last list item ending in
    a colon) goes when what it introduced went, a heading whose section emptied goes
    too, and so do table-of-contents links to the sections that went.  In fenced code,
    a command that runs such a module goes with its own comment; a block left with
    only comments or directory changes, a continued command, a here-document, a Python
    block that calls a private module, or a block that imports a private module (also
    through `python -c` or a here-document) goes whole.  Text without pointers is
    returned byte-for-byte.
    """
    segments = _segments(text)
    original = [[kind, list(lines)] for kind, lines in segments]
    _drop_offending_sections(segments, shipped, private, modules)
    for segment in segments:
        if not segment[1]:
            continue
        kept = (_filter_text_block(segment[1], shipped, private, modules) if segment[0] == "text"
                else _filter_code_block(segment[1], private, modules) if segment[0] == "code" else segment[1])
        segment[1] = kept
    if all(segment[1] == before[1] for segment, before in zip(segments, original)):
        return text
    _drop_emptied_intros_and_headings(segments, original)
    _drop_links_to_gone_sections(segments, original, shipped, private, modules)
    return _join(segments)


def _slug(heading: str) -> str:
    """GitHub-style anchor of a heading line."""
    title = _HEADING.sub("", heading).strip().lower()
    return re.sub(r"[^\w\- ]", "", title).replace(" ", "-")


def _drop_links_to_gone_sections(segments: list[list], original: list[list], shipped: frozenset[str],
                                 private: frozenset[str], modules: frozenset[str] | None) -> None:
    gone = {_slug(before[1][0]) for segment, before in zip(segments, original)
            if before[0] == "text" and before[1] and _HEADING.match(before[1][0]) and not segment[1]}
    if not gone:
        return
    _GONE_ANCHORS.update(gone)
    try:
        for segment in segments:
            if segment[0] == "text" and segment[1]:
                segment[1] = _filter_text_block(segment[1], shipped, private, modules)
    finally:
        _GONE_ANCHORS.clear()


def leftover_pointers(text: str, shipped: frozenset[str], private: frozenset[str] = frozenset(),
                      modules: frozenset[str] | None = None) -> list[str]:
    """Recognised pointers still present in filtered text; any is a filter gap and stops the sync."""
    found: list[str] = []
    for kind, lines in _segments(text):
        if kind == "text" and _links_unshipped("\n".join(lines), shipped, private, modules):
            found.append(lines[0])
        elif kind == "code" and (_imports_private(lines[1:], private)
                                 or (_is_python_fence(lines) and _python_uses_private(lines[1:], private))):
            found.append(lines[0])
        # Commands in fenced or indented code; plain prose mentions are not pointers.
        found += [line for line in lines
                  if (kind == "code" or (_indent(line) >= 4 and not _ANY_LIST_ITEM.match(line)))
                  and _runs_unshipped_module(line, private, modules)]
    return found
