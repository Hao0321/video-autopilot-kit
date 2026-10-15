"""Public privacy cleanup; canonical implementation."""
from __future__ import annotations

import re
from public_privacy_legacy import PUBLIC_FIXTURE, _lf


_VOICE_IDENTIFIER = re.compile(r"\b[A-Za-z][A-Za-z0-9]*-voice\b", re.I)


_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")


def _is_voice_profile_path(value: str) -> bool:
    normalized = value.replace("\\", "/")
    segments = [segment for segment in normalized.split("/") if segment]
    has_voice_segment = any(re.search(r"voice", segment, re.I) for segment in segments)
    is_user_path = (
        _WINDOWS_ABSOLUTE.match(value) is not None
        or normalized.startswith("~/")
        or any(segment.lower() in {"skills", "references"} for segment in segments)
    )
    return has_voice_segment and is_user_path


def _cleanup_changelog(text: str) -> str:
    """Generalize legacy voice-profile discovery history without retaining its values."""
    public = _lf(text)

    def replace_code_span(match: re.Match[str]) -> str:
        value = match.group(1)
        if _is_voice_profile_path(value):
            return "`<user-skill-root>/creator-voice/profile.md`"
        return match.group(0)

    public = re.sub(r"`([^`\r\n]+)`", replace_code_span, public)

    def replace_skill_discovery(match: re.Match[str]) -> str:
        line = match.group(0)
        if "<user-skill-root>/creator-voice/profile.md" not in line:
            return line
        if re.search(r"session", line, re.I):
            return (
                "- `SKILL.md` Session discovery loads only the explicitly configured "
                "`<user-skill-root>/creator-voice/profile.md`; public builds do not probe host-local paths"
            )
        return (
            "- `SKILL.md` creator-voice discovery uses "
            "`<user-skill-root>/creator-voice/profile.md`; legacy project adapters remain local-only"
        )

    public = re.sub(r"(?m)^- `SKILL\.md`[^\r\n]*$", replace_skill_discovery, public)
    public = _VOICE_IDENTIFIER.sub("creator-voice", public)
    public = re.sub(
        r"(?m)^- Audit report output[^\r\n]*creator-voice[^\r\n]*$",
        "- Audit report output may use the active creator voice profile while preserving the report contract",
        public,
    )
    public = re.sub(
        r"(?m)^- [^\r\n]*safety\s*>\s*creator-voice\s*>\s*generic default\s*$",
        "- Precedence remains: audit rules and safety > active creator voice profile > generic default",
        public,
    )
    public = re.sub(
        r"(?m)^- creator-voice[^\r\n]*(?:user-level skill|<user-skill-root>)[^\r\n]*$",
        "- Creator voice profiles are configurable user-level inputs, never repository-bound public data",
        public,
    )
    if PUBLIC_FIXTURE not in public:
        first_newline = public.find("\n")
        marker = (
            "\n\n<!-- PUBLIC_FIXTURE: maintainer paths and profile identities are generalized. -->"
        )
        public = public + marker + "\n" if first_newline < 0 else public[:first_newline] + marker + public[first_newline:]
    if re.search(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]", public):
        raise ValueError("public cleanup changelog retained an absolute drive path")
    return public
