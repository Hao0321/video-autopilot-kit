from __future__ import annotations
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote
from knowledge_lifecycle import record_feedback
from quality_95 import apply_human_review, write_report
from publish_contract import sha256 as media_sha256
from review_auth import IMAGE_EXTENSIONS, MAX_REVIEW_MEDIA, MEDIA_EXTENSIONS, QUICK_TUNNEL_HOST, VIDEO_EXTENSIONS
from review_page import render_review_html

CATEGORY_SIGNALS = {
    "weird_transition": ("unmotivated_geometric_transition", True),
    "text_cut": ("text_safe_area_pass", False),
    "generic_card": ("generic_fullscreen_card", True),
    "grid_opener": ("grid_used_as_default_opener", True),
    "template_label": ("template_role_label_visible", True),
    "repetition": ("narrative_similarity_high", True),
    "style_mismatch": ("style_domain_match", False),
    "overdesigned": ("visual_density_overload", True),
    "reference_copy": ("exact_reference_layout_copy", True),
}


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".review-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _without_secret_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    blocked_keys = {"url", "token", "bootstrap", "bootstrap_token", "credential",
                    "session_credential", "capability_url", "origin", "public_origin",
                    "local_pairing_url", "pairing_url", "pairing_port", "port"}
    omitted = object()

    def sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            safe: dict[str, Any] = {}
            for raw_key, nested in value.items():
                key = str(raw_key)
                if key.lower() in blocked_keys:
                    continue
                cleaned = sanitize(nested)
                if cleaned is not omitted:
                    safe[key] = cleaned
            return safe
        if isinstance(value, list):
            return [cleaned for item in value if (cleaned := sanitize(item)) is not omitted]
        if isinstance(value, str):
            lowered = value.lower()
            if ("#bootstrap=" in lowered or QUICK_TUNNEL_HOST in lowered
                    or re.fullmatch(r"https?://(?:127\.0\.0\.1|localhost):\d+(?:/.*)?",
                                    lowered)):
                return omitted
        return value

    cleaned = sanitize(payload)
    return cleaned if isinstance(cleaned, dict) else {}


def _kind(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    raise ValueError("unsupported review media: %s" % path)


def _discover_media(source: Path) -> list[dict[str, str]]:
    if not source.exists():
        raise FileNotFoundError("review source is missing: %s" % source)
    if source.is_file():
        paths = [source]
        root = source.parent
    elif source.is_dir():
        root = source
        paths = sorted(
            (path for path in source.rglob("*")
             if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
             and "_review" not in path.relative_to(source).parts),
            key=lambda path: path.relative_to(source).as_posix().casefold(),
        )
    else:
        raise ValueError("review source must be a file or directory: %s" % source)
    if not paths:
        raise ValueError("no browser-viewable video or image found under: %s" % source)
    if len(paths) > MAX_REVIEW_MEDIA:
        raise ValueError("review source has %d media files; limit is %d" %
                         (len(paths), MAX_REVIEW_MEDIA))
    return [
        {
            "id": "m%d" % index,
            "kind": _kind(path),
            "name": path.name if source.is_file() else path.relative_to(root).as_posix(),
            "path": str(path.resolve()),
        }
        for index, path in enumerate(paths)
    ]


def _manifest_media(manifest: dict[str, Any]) -> list[dict[str, str]]:
    raw = manifest.get("media")
    if not raw and manifest.get("video"):
        video = Path(str(manifest["video"])).resolve()
        raw = [{"id": "m0", "kind": "video", "name": video.name, "path": str(video)}]
    media = []
    for index, item in enumerate(raw or []):
        path = Path(str(item.get("path", ""))).resolve()
        media.append({
            "id": str(item.get("id") or "m%d" % index),
            "kind": str(item.get("kind") or _kind(path)),
            "name": str(item.get("name") or path.name),
            "path": str(path),
        })
    if not media:
        raise ValueError("review manifest contains no media")
    return media


def _browser_media(media: list[dict[str, str]], *, remote: bool,
                   bundle: Path | None = None) -> list[dict[str, str]]:
    output = []
    for index, item in enumerate(media):
        if remote:
            src = "/media/%d" % index
        else:
            assert bundle is not None
            relative = os.path.relpath(item["path"], bundle).replace(os.sep, "/")
            src = quote(relative, safe="/.")
        output.append({"id": item["id"], "kind": item["kind"],
                       "name": item["name"], "src": src})
    return output


def create_bundle(video: str | Path, content_id: str,
                  quality_json: str | Path | None = None,
                  bundle_dir: str | Path | None = None) -> dict[str, Any]:
    source = Path(video).resolve()
    media = _discover_media(source)
    bundle = (Path(bundle_dir).resolve() if bundle_dir else
              (source / "_review" if source.is_dir() else source.parent / "_review"))
    bundle.mkdir(parents=True, exist_ok=True)
    can_finalize = bool(quality_json and len(media) == 1 and media[0]["kind"] == "video")
    page = render_review_html(_browser_media(media, remote=False, bundle=bundle),
                              can_finalize=can_finalize)
    (bundle / "review.html").write_text(page, encoding="utf-8")
    first_video = next((item["path"] for item in media if item["kind"] == "video"), "")
    manifest = {"schema_version": 2, "content_id": content_id, "source": str(source),
                "media": media, "media_count": len(media), "video": first_video,
                "quality_json": str(Path(quality_json).resolve()) if quality_json else "",
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if can_finalize:
        manifest["artifact_sha256"] = media_sha256(Path(first_video))
    _atomic_json(bundle / "manifest.json", manifest)
    return {"bundle": str(bundle), "page": str(bundle / "review.html"),
            "media_count": len(media),
            "serve_command": "python review_loop.py serve %s" % json.dumps(str(bundle))}


def finalize(bundle_dir: str | Path, *, learn: bool = True) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    review = json.loads((bundle / "review.json").read_text(encoding="utf-8"))
    if not manifest.get("quality_json") or not manifest.get("video"):
        raise ValueError("finalize is only for one QA-linked delivery video; material reviews stay in review.json")
    video = Path(manifest["video"])
    actual_sha = media_sha256(video)
    if manifest.get("artifact_sha256") != actual_sha:
        raise ValueError("Reviewed film changed or uses a retired unbound review bundle; create a current bundle")
    quality_path = Path(manifest["quality_json"])
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    evidence = quality.get("evidence") or {}
    evidence["artifact_binding"] = {"outputPath": str(video.resolve()), "outputSha256": actual_sha}
    for issue in review.get("issues", []):
        mapping = CATEGORY_SIGNALS.get(issue.get("category"))
        if mapping:
            evidence.setdefault("signals", {})[mapping[0]] = mapping[1]
        if learn:
            record_feedback(
                rule="%s：%s" % (issue.get("category", "review"), issue.get("comment", "")),
                evidence="%s @ %.2fs / %s" % (manifest["content_id"], float(issue.get("time", 0)),
                                               manifest["video"]),
                scope="project", formats=[evidence.get("format", "*")],
                domains=["*"], kind="soft",
            )
    review["review_id"] = review.get("review_id") or (manifest["content_id"] + "-mobile")
    evidence = apply_human_review(evidence, review)
    result = write_report(quality_path.parent, evidence, remember_narrative=True)
    _atomic_json(bundle / "finalized.json", {"review": review, "quality": result})
    return result
