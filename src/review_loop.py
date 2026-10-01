# -*- coding: utf-8 -*-
"""Hao-owned video/image review bundle and one-click feedback ingestion.

The reviewer is Hao.  A phone or desktop browser is only an access device and
never changes who owns the aesthetic decision.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict, deque
import contextlib
from dataclasses import dataclass, field
import hashlib
import hmac
from http.cookies import SimpleCookie
import importlib
import io
import json
import math
import mimetypes
import os
import queue
import re
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from knowledge_lifecycle import record_feedback
from aesthetic_score import review_schema
from quality_95 import apply_human_review, write_report


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
MAX_REVIEW_MEDIA = 300
MAX_REVIEW_BODY_BYTES = 256 * 1024
MAX_BOOTSTRAP_BODY_BYTES = 4 * 1024
BOOTSTRAP_TTL_SECONDS = 10 * 60
REMOTE_SESSION_TTL_SECONDS = 60 * 60
REMOTE_IDLE_TIMEOUT_SECONDS = 15 * 60
REMOTE_STOP_WAIT_SECONDS = 5.0
SESSION_COOKIE = "__Host-hao_review_session"
AUTH_RATE_WINDOW_SECONDS = 60
AUTH_RATE_ATTEMPTS = 12
REVIEW_RATE_ATTEMPTS = 120
MEDIA_RATE_ATTEMPTS = 600
QUICK_TUNNEL_HOST = "trycloud" + "flare.com"
QUICK_TUNNEL_ORIGIN = re.compile(
    r"https://[-a-z0-9]+\." + re.escape(QUICK_TUNNEL_HOST), re.I)


HTML_TEMPLATE = r'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hao 遠端素材審查</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}body{margin:0;background:#090b10;color:#f7f7fb}
main{max-width:920px;margin:auto;padding:12px 12px 80px}.viewer{display:block;width:100%;height:min(68vh,760px);min-width:0;min-height:0;background:#000;border-radius:14px;overflow:hidden}
.viewer video,.viewer img{display:block;width:100%;height:100%;min-width:0;min-height:0;max-width:100%;max-height:100%;box-sizing:border-box;object-fit:contain;object-position:center;background:#000}.nav{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:10px}.name{min-width:0;text-align:center;overflow-wrap:anywhere;color:#dce3f4}
.card{background:#151924;border:1px solid #2a3041;border-radius:14px;padding:14px;margin-top:12px}
.time{font-size:26px;font-weight:800;color:#8dff54}.row{display:flex;gap:8px;flex-wrap:wrap}
button,select,input,textarea{font:inherit;border-radius:10px;border:1px solid #394158;background:#0e121c;color:#fff;padding:11px}
button{background:#2358ff;font-weight:800}.secondary{background:#252b3a}.good{background:#247a3b}.bad{background:#a8323c}textarea{width:100%;box-sizing:border-box;min-height:82px;margin-top:8px}
label{display:block;margin:9px 0 4px;color:#aeb7cb}small{display:block;color:#77839b;margin-top:3px;line-height:1.35}.rating{display:grid;grid-template-columns:1fr 76px;gap:8px;align-items:center}
#saved{color:#8dff54;min-height:24px}.issue{border-top:1px solid #2a3041;padding:8px 0}.decision{font-weight:800;color:#8dff54}</style></head><body><main>
<div class="viewer" id="viewer"></div><div class="nav"><button class="secondary" id="prev">上一個</button><div class="name"><b id="counter"></b><br><span id="mediaName"></span><br><span class="decision" id="decision"></span></div><button class="secondary" id="next">下一個</button></div>
<section class="card"><div class="row"><button class="good" id="approve">這個可用</button><button class="bad" id="redo">這個重做</button></div></section>
<section class="card"><div class="time" id="clock">00:00.00</div><div class="row">
<button id="mark">標記現在時間</button><select id="category">
<option value="rhythm">節奏／拖沓</option><option value="weird_transition">怪轉場</option>
<option value="text_cut">文字被切／難讀</option><option value="generic_card">空白模板卡</option>
<option value="grid_opener">錯用網格開場</option><option value="template_label">模板角色字外露</option>
<option value="repetition">重複／疲勞</option><option value="style_mismatch">題材風格不合</option>
<option value="overdesigned">過度設計／焦點太多</option><option value="reference_copy">太像參考圖</option>
<option value="content_mismatch">內容／主題不對</option><option value="composition">構圖有問題</option>
<option value="color">色彩有問題</option><option value="generation_artifact">生成瑕疵</option>
<option value="unusable">完全不可用</option>
<option value="other">其他</option></select></div>
<textarea id="comment" placeholder="這個素材／這一秒哪裡不好？怎麼改？"></textarea><button id="add">加入問題</button><div id="saved"></div></section>
<section class="card" id="ratingsCard"><h3>Hao 美感十維（影片可評；素材批次可略過）</h3><div id="ratings"></div></section>
<section class="card"><button id="submit">送出整批審查</button></section>
<section class="card"><h3>問題與決策</h3><div id="issues"></div></section>
</main><script>
const media=__MEDIA_JSON__, canFinalize=__CAN_FINALIZE__, key='hao-review-'+location.pathname;
if(location.hash)history.replaceState(null,'',location.pathname+location.search);
let data=JSON.parse(localStorage.getItem(key)||'{"issues":[],"ratings":{},"decisions":{}}'), marked=0, current=0, v=null;
data.issues=data.issues||[];data.ratings=data.ratings||{};data.decisions=data.decisions||{};
const dims=__AESTHETIC_DIMENSIONS__;
function fmt(t){let m=Math.floor(t/60),s=t-m*60;return String(m).padStart(2,'0')+':'+s.toFixed(2).padStart(5,'0')}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
let syncTimer=null;
async function syncNow(message='已自動同步'){try{let res=await fetch('__API_PATH__',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});saved.textContent=res.ok?message:'自動同步失敗，請按最底送出';return res.ok}catch(_){saved.textContent='自動同步失敗，請按最底送出';return false}}
function save(){localStorage.setItem(key,JSON.stringify(data));renderIssues();renderDecision();clearTimeout(syncTimer);syncTimer=setTimeout(()=>syncNow(),180)}
function renderDecision(){const x=media[current],d=data.decisions[x.id];decision.textContent=d==='approved'?'✓ 可用':d==='redo'?'✕ 重做':''}
function renderIssues(){issues.innerHTML=data.issues.map((x,i)=>`<div class="issue"><b>${esc(x.media_name||'素材')} · ${x.kind==='video'?fmt(Number(x.time||0)):''} ${esc(x.category)}</b><br>${esc(x.comment)}<br><button data-issue-index="${i}">刪除</button></div>`).join('')||'尚無問題';}
function show(i){current=(i+media.length)%media.length;const x=media[current];viewer.innerHTML='';v=null;marked=0;
 if(x.kind==='video'){v=document.createElement('video');v.controls=true;v.playsInline=true;v.preload='metadata';v.src=x.src;viewer.appendChild(v);clock.textContent='00:00.00';mark.disabled=false}
 else{let im=document.createElement('img');im.src=x.src;im.alt=x.name;viewer.appendChild(im);clock.textContent='素材 '+(current+1)+' / '+media.length;mark.disabled=true}
 counter.textContent=(current+1)+' / '+media.length;mediaName.textContent=x.name;renderDecision()}
ratings.innerHTML=Object.entries(dims).map(([k,n])=>`<div class="rating"><label>${n.label_zh}<small>${n.question}</small></label><input id="r-${k}" type="number" min="1" max="5" step="0.5" placeholder="未評" value="${Number.isFinite(data.ratings[k])&&data.ratings[k]>=1&&data.ratings[k]<=5?data.ratings[k]:''}"></div>`).join('');
if(!media.some(x=>x.kind==='video'))ratingsCard.hidden=true;
setInterval(()=>{if(v)clock.textContent=fmt(v.currentTime)},100);mark.onclick=()=>{if(v){marked=v.currentTime;clock.textContent=fmt(marked)}};
prev.onclick=()=>show(current-1);next.onclick=()=>show(current+1);approve.onclick=()=>{data.decisions[media[current].id]='approved';save()};redo.onclick=()=>{data.decisions[media[current].id]='redo';save()};
add.onclick=()=>{let c=comment.value.trim();if(!c)return;const x=media[current],t=v?(marked||v.currentTime):0;saved.textContent='已加入：'+x.name;data.issues.push({media_id:x.id,media_name:x.name,kind:x.kind,time:t,category:category.value,comment:c});comment.value='';save()};
issues.onclick=e=>{const b=e.target.closest('button[data-issue-index]');if(!b)return;data.issues.splice(Number(b.dataset.issueIndex),1);save()};
submit.onclick=async()=>{if(media.some(x=>x.kind==='video')){const explicit={};for(const k of Object.keys(dims)){const input=document.querySelector('#r-'+k);if(!input.value.trim())continue;if(!input.checkValidity()){saved.textContent='評分請填 1–5（每格 0.5），或留空。';input.focus();return;}explicit[k]=Number(input.value);}data.ratings=explicit;}data.completed_at=new Date().toISOString();data.media_count=media.length;localStorage.setItem(key,JSON.stringify(data));await syncNow(canFinalize?'已送出，可回 Codex 執行 finalize':'已送出，Codex 可直接讀取審查結果')};
if(location.protocol==='https:')setInterval(()=>fetch('/api/ping',{credentials:'same-origin',cache:'no-store'}).catch(()=>{}),60000);show(0);renderIssues();
</script></body></html>'''.replace(
    "__AESTHETIC_DIMENSIONS__",
    json.dumps(review_schema("shorts")["dimensions"], ensure_ascii=False),
)


def render_review_html(media: list[dict[str, str]] | None = None,
                       api_path: str = "/api/review",
                       *, can_finalize: bool = False) -> str:
    media = media or [{"id": "m0", "kind": "video", "name": "current.mp4",
                       "src": "../current.mp4"}]
    media_json = json.dumps(media, ensure_ascii=False).replace("<", "\\u003c")
    return (HTML_TEMPLATE.replace("__MEDIA_JSON__", media_json)
            .replace("__CAN_FINALIZE__", "true" if can_finalize else "false")
            .replace("__API_PATH__", api_path))


HTML = render_review_html()


BOOTSTRAP_HTML = r'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hao 遠端素材審查</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}body{margin:0;background:#090b10;color:#f7f7fb}
main{max-width:560px;margin:18vh auto;padding:24px}.card{background:#151924;border:1px solid #2a3041;border-radius:14px;padding:22px}
#status{line-height:1.6;color:#dce3f4}.error{color:#ff9099}</style></head><body><main><div class="card">
<h1>安全連線中</h1><p id="status">正在建立這次審片工作階段…</p></div></main><script>
(async()=>{const status=document.querySelector('#status'),p=new URLSearchParams(location.hash.slice(1)),token=p.get('bootstrap');
history.replaceState(null,'',location.pathname+location.search);
if(!token){status.className='error';status.textContent='此連結缺少一次性授權，請回 Codex 重新建立審片連結。';return}
try{const r=await fetch('/api/bootstrap',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({bootstrap:token})});
if(!r.ok){throw new Error(String(r.status))}location.replace('/review.html')}
catch(_){status.className='error';status.textContent='此連結已使用、已過期或不是有效授權，請回 Codex 重新建立。'}})();
</script></body></html>'''


def _csp_for_html(payload: bytes) -> str:
    """Build exact hashes for this response's inline script/style blocks."""
    text = payload.decode("utf-8")

    def hashes(tag: str) -> list[str]:
        blocks = re.findall(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (tag, tag), text,
                            flags=re.I | re.S)
        return ["'sha256-%s'" % base64.b64encode(
            hashlib.sha256(block.encode("utf-8")).digest()).decode("ascii")
                for block in blocks]

    script = " ".join(["'self'", *hashes("script")])
    style = " ".join(["'self'", *hashes("style")])
    return ("default-src 'self'; img-src 'self' data:; media-src 'self'; "
            "connect-src 'self'; script-src %s; style-src %s; "
            "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'" %
            (script, style))


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
    quality_path = Path(manifest["quality_json"])
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    evidence = quality.get("evidence") or {}
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

def _parse_byte_range(value: str, size: int) -> tuple[int, int] | None:
    if not value:
        return None
    if not value.startswith("bytes=") or "," in value:
        raise ValueError("unsupported byte range")
    start_text, end_text = value[6:].split("-", 1)
    if not start_text:
        length = int(end_text)
        if length <= 0:
            raise ValueError("invalid suffix range")
        return max(0, size - length), size - 1
    start = int(start_text)
    end = int(end_text) if end_text else size - 1
    if start < 0 or start >= size or end < start:
        raise ValueError("invalid byte range")
    return start, min(end, size - 1)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(timespec="seconds")


def _normalized_origin(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return "%s://%s" % (parsed.scheme.lower(), parsed.netloc.lower())


@dataclass
class _RemoteReviewAuth:
    """In-memory capability state. Only non-secret fingerprints go to disk."""

    bootstrap_digest: str
    bootstrap_expires_epoch: float
    public_origin: str
    session_ttl_seconds: int = REMOTE_SESSION_TTL_SECONDS
    idle_timeout_seconds: int = REMOTE_IDLE_TIMEOUT_SECONDS
    created_epoch: float = field(default_factory=time.time)
    created_monotonic: float = field(default_factory=time.monotonic)
    bootstrap_used: bool = False
    session_digest: str = ""
    last_activity_monotonic: float = field(default_factory=time.monotonic)
    _lock: threading.RLock = field(default_factory=threading.RLock, repr=False)
    _rate_hits: dict[str, deque[float]] = field(
        default_factory=lambda: defaultdict(deque), repr=False)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.bootstrap_digest):
            raise ValueError("bootstrap digest must be a SHA-256 hex digest")
        self.public_origin = _normalized_origin(self.public_origin)
        if not self.public_origin:
            raise ValueError("remote review requires an explicit public origin")
        requested_expiry = float(self.bootstrap_expires_epoch)
        if not math.isfinite(requested_expiry):
            raise ValueError("bootstrap expiry must be finite")
        self.bootstrap_expires_epoch = min(
            requested_expiry, self.created_epoch + BOOTSTRAP_TTL_SECONDS)
        self.session_ttl_seconds = min(REMOTE_SESSION_TTL_SECONDS,
                                       max(1, int(self.session_ttl_seconds)))
        self.idle_timeout_seconds = min(REMOTE_IDLE_TIMEOUT_SECONDS,
                                        max(1, int(self.idle_timeout_seconds)))

    @property
    def session_expires_epoch(self) -> float:
        return self.created_epoch + self.session_ttl_seconds

    @property
    def fingerprint(self) -> str:
        return self.bootstrap_digest[:16]

    def allow_request(self, bucket: str, limit: int) -> bool:
        now = time.monotonic()
        with self._lock:
            hits = self._rate_hits[bucket]
            while hits and now - hits[0] >= AUTH_RATE_WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    def exchange(self, bootstrap: str) -> tuple[int, str]:
        """Consume the bootstrap once and return a new browser credential."""
        with self._lock:
            if self.bootstrap_used:
                return 409, ""
            if time.time() >= self.bootstrap_expires_epoch:
                return 410, ""
            if not bootstrap or not hmac.compare_digest(_sha256(bootstrap),
                                                        self.bootstrap_digest):
                return 401, ""
            credential = secrets.token_urlsafe(32)
            self.session_digest = _sha256(credential)
            self.bootstrap_used = True
            self.last_activity_monotonic = time.monotonic()
            return 200, credential

    def authorized(self, credential: str) -> bool:
        with self._lock:
            if (time.time() >= self.session_expires_epoch
                    or time.monotonic() - self.last_activity_monotonic >=
                    self.idle_timeout_seconds or not self.session_digest):
                return False
            if not credential or not hmac.compare_digest(_sha256(credential),
                                                         self.session_digest):
                return False
            self.last_activity_monotonic = time.monotonic()
            return True

    def shutdown_due(self) -> str:
        with self._lock:
            now_epoch, now_mono = time.time(), time.monotonic()
            if now_epoch >= self.session_expires_epoch:
                return "session_ttl_expired"
            if not self.bootstrap_used and now_epoch >= self.bootstrap_expires_epoch:
                return "bootstrap_expired"
            if now_mono - self.last_activity_monotonic >= self.idle_timeout_seconds:
                return "idle_timeout"
            return ""


def _review_payload_valid(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    issues = payload.get("issues", [])
    ratings = payload.get("ratings", {})
    decisions = payload.get("decisions", {})
    if not isinstance(issues, list) or len(issues) > 1000:
        return False
    if not isinstance(ratings, dict) or len(ratings) > 64:
        return False
    if not isinstance(decisions, dict) or len(decisions) > MAX_REVIEW_MEDIA:
        return False
    stack: list[tuple[Any, int]] = [(payload, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > 8:
            return False
        if isinstance(value, str) and len(value) > 10_000:
            return False
        if isinstance(value, dict):
            if len(value) > 2_000:
                return False
            stack.extend((key, depth + 1) for key in value)
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            if len(value) > 2_000:
                return False
            stack.extend((item, depth + 1) for item in value)
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            return False
    return True


def _load_qr_runtime(module_loader: Any = None) -> Any:
    loader = module_loader or importlib.import_module
    try:
        return loader("qrcode")
    except Exception:
        raise RuntimeError(
            "SECURE_REVIEW_RUNTIME_REQUIRED: install qrcode==7.4.2 before remote review"
        ) from None


def _render_pairing_qr(remote_url: str, module_loader: Any = None) -> bytes:
    """Render the secret-bearing QR in memory; never write it to the bundle."""
    try:
        qrcode = _load_qr_runtime(module_loader)
        image = qrcode.make(remote_url)
        output = io.BytesIO()
        image.save(output, format="PNG")
        payload = output.getvalue()
    except Exception:
        raise RuntimeError(
            "SECURE_REVIEW_RUNTIME_REQUIRED: install qrcode==7.4.2 before remote review"
        ) from None
    if not payload.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("SECURE_REVIEW_RUNTIME_REQUIRED: QR renderer did not return PNG")
    return payload


def _load_pairing_ui_runtime(module_loader: Any = None) -> Any:
    loader = module_loader or importlib.import_module
    try:
        return loader("tkinter")
    except Exception:
        raise RuntimeError(
            "SECURE_REVIEW_RUNTIME_REQUIRED: Python tkinter and an interactive desktop "
            "are required for the in-memory pairing window"
        ) from None


class _NativePairingWindow:
    """Display the secret-bearing QR as pixels without a URL or file locator."""

    def __init__(self, qr_png: bytes, fingerprint: str, expires_at: str,
                 tk_module: Any = None) -> None:
        self._tk = tk_module or _load_pairing_ui_runtime()
        self._root: Any = None
        self._image: Any = None
        self._closed = False
        try:
            root = self._tk.Tk()
            self._root = root
            root.withdraw()
            root.title("Hao 安全審片授權")
            root.configure(bg="#090b10")
            root.resizable(False, False)
            root.protocol("WM_DELETE_WINDOW", self.close)
            title = self._tk.Label(
                root, text="掃碼授權這次審片", bg="#090b10", fg="#f7f7fb",
                font=("TkDefaultFont", 18, "bold"), pady=12)
            title.pack()
            note = self._tk.Label(
                root, text="一次性 QR 只存在這個視窗的記憶體中；請在到期前掃描。",
                bg="#090b10", fg="#dce3f4", padx=18, wraplength=430,
                justify="center")
            note.pack()
            encoded = base64.b64encode(qr_png).decode("ascii")
            self._image = self._tk.PhotoImage(data=encoded, format="png")
            del encoded
            image = self._tk.Label(root, image=self._image, bg="#ffffff", padx=10, pady=10)
            image.pack(padx=20, pady=16)
            meta = self._tk.Label(
                root, text="指紋：%s\n配對到期：%s" % (fingerprint, expires_at),
                bg="#090b10", fg="#aeb7cb", padx=18, pady=10, justify="center")
            meta.pack()
            root.update_idletasks()
            root.deiconify()
            root.lift()
            try:
                root.attributes("-topmost", True)
                root.after(1200, self._release_topmost)
            except Exception:
                pass
            root.update_idletasks()
            root.update()
        except Exception:
            self.close()
            raise RuntimeError(
                "SECURE_REVIEW_RUNTIME_REQUIRED: could not open the in-memory native "
                "pairing window on this interactive desktop"
            ) from None

    @property
    def is_open(self) -> bool:
        return not self._closed and self._root is not None

    def _release_topmost(self) -> None:
        if self.is_open:
            try:
                self._root.attributes("-topmost", False)
            except Exception:
                pass

    def pump(self) -> bool:
        if not self.is_open:
            return False
        try:
            self._root.update_idletasks()
            self._root.update()
            return True
        except Exception:
            self.close()
            return False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        root, self._root = self._root, None
        self._image = None
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


class _MediaReviewHandler(BaseHTTPRequestHandler):
    bundle: Path
    media: list[dict[str, str]]
    auth: _RemoteReviewAuth | None
    can_finalize: bool
    protocol_version = "HTTP/1.1"

    def _send_bytes(self, payload: bytes, content_type: str, *, status: int = 200,
                    headers: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if self.auth is not None and self.auth.public_origin.startswith("https://"):
            self.send_header("Strict-Transport-Security", "max-age=86400")
        if content_type.startswith("text/html"):
            self.send_header("Content-Security-Policy", _csp_for_html(payload))
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)
            self.wfile.flush()

    def _send_json(self, payload: dict[str, Any], *, status: int = 200,
                   headers: dict[str, str] | None = None) -> None:
        self._send_bytes(json.dumps(payload, separators=(",", ":")).encode("utf-8"),
                         "application/json; charset=utf-8", status=status, headers=headers)

    def _fail(self, status: int, code: str) -> None:
        self._send_json({"ok": False, "error": code}, status=status,
                        headers={"Connection": "close"})
        self.close_connection = True

    def _credential(self) -> str:
        try:
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            morsel = cookie.get(SESSION_COOKIE)
            return morsel.value if morsel else ""
        except Exception:
            return ""

    def _authenticated(self) -> bool:
        return self.auth is None or self.auth.authorized(self._credential())

    def _same_origin_post(self) -> bool:
        if self.auth is None:
            return True
        origin = _normalized_origin(self.headers.get("Origin", ""))
        fetch_site = self.headers.get("Sec-Fetch-Site", "").lower()
        fetch_mode = self.headers.get("Sec-Fetch-Mode", "").lower()
        return (origin == self.auth.public_origin and fetch_site == "same-origin"
                and fetch_mode in {"cors", "same-origin"})

    def _read_json(self, limit: int) -> tuple[int, Any]:
        if self.headers.get("Transfer-Encoding"):
            return 400, None
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            return 415, None
        try:
            length = int(self.headers.get("Content-Length", ""))
        except (TypeError, ValueError):
            return 411, None
        if length <= 0:
            return 400, None
        if length > limit:
            return 413, None
        try:
            previous_timeout = self.connection.gettimeout()
            self.connection.settimeout(5.0)
            raw = self.rfile.read(length)
            if len(raw) != length:
                return 400, None
            return 200, json.loads(raw.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            return 400, None
        finally:
            try:
                self.connection.settimeout(previous_timeout)
            except (NameError, OSError):
                pass

    def _send_media(self, index: int) -> None:
        if index < 0 or index >= len(self.media):
            self._fail(404, "not_found")
            return
        path = Path(self.media[index]["path"])
        if not path.is_file():
            self._fail(404, "media_missing")
            return
        size = path.stat().st_size
        try:
            byte_range = _parse_byte_range(self.headers.get("Range", ""), size)
        except (ValueError, TypeError):
            self.send_response(416)
            self.send_header("Content-Range", "bytes */%d" % size)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        start, end = byte_range or (0, size - 1)
        self.send_response(206 if byte_range else 200)
        fallback = "video/mp4" if self.media[index]["kind"] == "video" else "image/jpeg"
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or fallback)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if byte_range:
            self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.send_header("Cache-Control", "private, no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        if self.auth is not None and self.auth.public_origin.startswith("https://"):
            self.send_header("Strict-Transport-Security", "max-age=86400")
        self.end_headers()
        if self.command == "HEAD":
            return
        remaining = end - start + 1
        with path.open("rb") as handle:
            handle.seek(start)
            while remaining:
                chunk = handle.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/healthz" and self.auth is not None:
            self._send_json({"ok": True, "service": "hao-remote-review",
                             "authentication": "required"})
        elif path in {"/", "/review.html"}:
            if not self._authenticated():
                self._send_bytes(BOOTSTRAP_HTML.encode("utf-8"),
                                 "text/html; charset=utf-8")
                return
            client_media = _browser_media(self.media, remote=True)
            self._send_bytes(render_review_html(client_media, "/api/review",
                                                can_finalize=self.can_finalize).encode("utf-8"),
                             "text/html; charset=utf-8")
        elif re.fullmatch(r"/media/\d+", path):
            if not self._authenticated():
                self._fail(401, "authentication_required")
                return
            if self.auth is not None and not self.auth.allow_request(
                    "media", MEDIA_RATE_ATTEMPTS):
                self._fail(429, "rate_limited")
                return
            self._send_media(int(path.rsplit("/", 1)[1]))
        elif path == "/api/ping" and self.auth is not None:
            if not self._authenticated():
                self._fail(401, "authentication_required")
                return
            self._send_json({"ok": True})
        else:
            self._fail(404, "not_found")

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if self.auth is None and path != "/api/review":
            self._fail(404, "not_found")
            return
        if self.auth is not None and path not in {"/api/bootstrap", "/api/review"}:
            self._fail(404, "not_found")
            return
        if not self._same_origin_post():
            self._fail(403, "cross_origin_request_blocked")
            return

        if path == "/api/bootstrap":
            assert self.auth is not None
            if not self.auth.allow_request("bootstrap", AUTH_RATE_ATTEMPTS):
                self._fail(429, "rate_limited")
                return
            status, payload = self._read_json(MAX_BOOTSTRAP_BODY_BYTES)
            if status != 200:
                self._fail(status, "invalid_bootstrap_request")
                return
            if not isinstance(payload, dict) or set(payload) != {"bootstrap"} or not isinstance(
                    payload.get("bootstrap"), str):
                self._fail(400, "invalid_bootstrap_request")
                return
            status, credential = self.auth.exchange(payload["bootstrap"])
            if status != 200:
                reason = {401: "invalid_bootstrap", 409: "bootstrap_already_used",
                          410: "bootstrap_expired"}.get(status, "bootstrap_failed")
                self._fail(status, reason)
                return
            max_age = max(1, int(self.auth.session_expires_epoch - time.time()))
            cookie = ("%s=%s; Path=/; Max-Age=%d; HttpOnly; Secure; SameSite=Strict" %
                      (SESSION_COOKIE, credential, max_age))
            self._send_json({"ok": True}, headers={"Set-Cookie": cookie})
            return

        assert path == "/api/review"
        if not self._authenticated():
            self._fail(401, "authentication_required")
            return
        if self.auth is not None and not self.auth.allow_request("review", REVIEW_RATE_ATTEMPTS):
            self._fail(429, "rate_limited")
            return
        status, payload = self._read_json(MAX_REVIEW_BODY_BYTES)
        if status != 200:
            self._fail(status, "invalid_review_request")
            return
        if not _review_payload_valid(payload):
            self._fail(400, "invalid_review_payload")
            return
        _atomic_json(self.bundle / "review.json", payload)
        self._send_json({"ok": True})

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _handler_factory(bundle: Path, media: list[dict[str, str]],
                     auth: _RemoteReviewAuth | None,
                     can_finalize: bool = False):
    class Bound(_MediaReviewHandler):
        pass
    Bound.bundle, Bound.media, Bound.auth = bundle, media, auth
    Bound.can_finalize = can_finalize
    return Bound


def _find_cloudflared(explicit: str = "") -> Path:
    candidates = [explicit, shutil.which("cloudflared") or ""]
    if os.name == "nt":
        candidates += [
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "cloudflared", "cloudflared.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "cloudflared", "cloudflared.exe"),
        ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    raise FileNotFoundError("cloudflared not found; install it before using remote review")


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p,
                                                ctypes.POINTER(ctypes.c_ulong)]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            return bool(kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
                        and exit_code.value == 259)  # STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except (OSError, SystemError):
        return False
    return True


def _process_identity(pid: int) -> dict[str, Any]:
    """Return enough immutable process identity to reject recycled PIDs."""
    if not _pid_alive(pid):
        return {}
    try:
        if os.name == "nt":
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
            kernel32.OpenProcess.restype = ctypes.c_void_p
            kernel32.GetProcessTimes.argtypes = [
                ctypes.c_void_p, ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME),
            ]
            kernel32.QueryFullProcessImageNameW.argtypes = [
                ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p,
                ctypes.POINTER(ctypes.c_ulong),
            ]
            kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if not handle:
                return {}
            try:
                created, exited = wintypes.FILETIME(), wintypes.FILETIME()
                kernel, user = wintypes.FILETIME(), wintypes.FILETIME()
                if not kernel32.GetProcessTimes(handle, ctypes.byref(created),
                                                ctypes.byref(exited), ctypes.byref(kernel),
                                                ctypes.byref(user)):
                    return {}
                size = ctypes.c_ulong(32768)
                image = ctypes.create_unicode_buffer(size.value)
                if not kernel32.QueryFullProcessImageNameW(handle, 0, image,
                                                           ctypes.byref(size)):
                    return {}
                ticks = (int(created.dwHighDateTime) << 32) | int(created.dwLowDateTime)
                executable = os.path.normcase(os.path.realpath(image.value))
                return {"pid": pid, "start_marker": str(ticks),
                        "executable_fingerprint": _sha256(executable)[:32]}
            finally:
                kernel32.CloseHandle(handle)
        proc = Path("/proc") / str(pid)
        if proc.is_dir():
            stat = (proc / "stat").read_text(encoding="utf-8")
            tail = stat[stat.rfind(")") + 2:].split()
            executable = str((proc / "exe").resolve())
            return {"pid": pid, "start_marker": tail[19],
                    "executable_fingerprint": _sha256(executable)[:32]}
        marker = subprocess.check_output(
            ["ps", "-p", str(pid), "-o", "lstart=", "-o", "comm="],
            text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
        return {"pid": pid, "start_marker": marker,
                "executable_fingerprint": _sha256(marker.split()[-1])[:32]}
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return {}


def _process_identity_matches(expected: Any) -> bool:
    if not isinstance(expected, dict):
        return False
    try:
        pid = int(expected.get("pid", 0))
    except (TypeError, ValueError):
        return False
    current = _process_identity(pid)
    return bool(current and str(current.get("start_marker")) == str(expected.get("start_marker"))
                and str(current.get("executable_fingerprint", "")) ==
                str(expected.get("executable_fingerprint", "")))


def _terminate_pid(pid: int) -> bool:
    if not _pid_alive(pid):
        return False
    if os.name == "nt":
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
        if not handle:
            return False
        try:
            return bool(kernel32.TerminateProcess(handle, 0))
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, signal.SIGTERM)
        return True
    except (OSError, SystemError):
        return False


def remote_status(bundle_dir: str | Path) -> dict[str, Any]:
    session_path = Path(bundle_dir).resolve() / "remote_session.json"
    if not session_path.is_file():
        return {"status": "INACTIVE"}
    session = json.loads(session_path.read_text(encoding="utf-8"))
    server_alive = _process_identity_matches(session.get("server_identity"))
    tunnel_alive = _process_identity_matches(session.get("tunnel_identity"))
    try:
        expiry = float(session.get("expires_epoch", 0))
        expired = not math.isfinite(expiry) or time.time() >= expiry
    except (TypeError, ValueError):
        expired = True
    recorded_status = str(session.get("status", "")).upper()
    any_alive = server_alive or tunnel_alive
    if any_alive and recorded_status in {"STOPPED", "STOP_FAILED"}:
        effective_status = "STOP_FAILED"
    elif any_alive and recorded_status == "STARTING":
        effective_status = "STARTING"
    elif any_alive and expired:
        effective_status = "EXPIRED_RUNNING"
    elif server_alive and tunnel_alive:
        effective_status = "ACTIVE"
    elif any_alive:
        effective_status = "DEGRADED"
    elif recorded_status in {"STOPPED", "EXPIRED"}:
        effective_status = recorded_status
    else:
        effective_status = "INACTIVE"
    session.update(server_alive=server_alive, tunnel_alive=tunnel_alive,
                   process_identity_verified=server_alive and tunnel_alive,
                   status=effective_status)
    return _without_secret_metadata(session)


def stop_remote(bundle_dir: str | Path, *,
                wait_timeout: float = REMOTE_STOP_WAIT_SECONDS) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    session_path = bundle / "remote_session.json"
    if not session_path.is_file():
        return {"status": "INACTIVE"}
    session = json.loads(session_path.read_text(encoding="utf-8"))
    stopped = []
    skipped = []
    requested: list[tuple[int, dict[str, Any]]] = []
    for pid_key, identity_key in (("tunnel_pid", "tunnel_identity"),
                                  ("server_pid", "server_identity")):
        try:
            pid = int(session.get(pid_key, 0))
        except (TypeError, ValueError):
            pid = 0
        expected = session.get(identity_key)
        if _process_identity_matches(expected):
            first_request = not any(
                existing_pid == pid and existing_identity == expected
                for existing_pid, existing_identity in requested)
            if first_request:
                requested.append((pid, expected))
            if first_request and not _terminate_pid(pid):
                skipped.append({"pid": pid, "reason": "terminate_request_failed"})
        elif _pid_alive(pid):
            skipped.append({"pid": pid, "reason": "process_identity_not_verified"})
    deadline = time.monotonic() + max(0.0, min(float(wait_timeout),
                                                REMOTE_STOP_WAIT_SECONDS))
    while requested and time.monotonic() < deadline:
        if not any(_process_identity_matches(expected) for _, expected in requested):
            break
        time.sleep(0.05)
    lingering = [pid for pid, expected in requested
                 if _process_identity_matches(expected)]
    stopped = [pid for pid, expected in requested
               if not _process_identity_matches(expected)]
    status = "STOP_FAILED" if lingering else "STOPPED"
    session.update(status=status, stopped_pids=stopped,
                   skipped_pids=skipped,
                   lingering_pids=lingering)
    stop_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if status == "STOPPED":
        session["stopped_at"] = stop_timestamp
        session.pop("stop_attempted_at", None)
    else:
        session["stop_attempted_at"] = stop_timestamp
        session.pop("stopped_at", None)
    session = _without_secret_metadata(session)
    _atomic_json(session_path, session)
    return session


def _remote_daemon_command(bundle: Path, port: int, cloudflared: str,
                           bootstrap_digest: str,
                           bootstrap_expires_epoch: float) -> list[str]:
    command = [sys.executable, str(Path(__file__).resolve()), "remote", str(bundle),
               "--port", str(port), "--bootstrap-digest", bootstrap_digest,
               "--bootstrap-expires-epoch", str(bootstrap_expires_epoch)]
    if cloudflared:
        command.extend(("--cloudflared", cloudflared))
    return command


def _read_bootstrap_pipe(stream: Any, expected_digest: str) -> str:
    """Read one bounded token from an inherited anonymous pipe."""
    raw = stream.readline(1025)
    if not raw or len(raw) > 1024:
        raise RuntimeError("secure bootstrap pipe was empty or oversized")
    if isinstance(raw, str):
        raw = raw.encode("ascii", errors="strict")
    token_bytes = raw.rstrip(b"\r\n")
    if not re.fullmatch(rb"[A-Za-z0-9_-]{43,128}", token_bytes):
        raise RuntimeError("secure bootstrap pipe contained an invalid token")
    token = token_bytes.decode("ascii")
    if not hmac.compare_digest(_sha256(token), expected_digest):
        raise RuntimeError("secure bootstrap pipe integrity check failed")
    return token


def _safe_remote_announcements(auth: _RemoteReviewAuth) -> tuple[str, str]:
    return (
        "REMOTE_REVIEW_STATUS=READY_FOR_LOCAL_SCAN",
        "REMOTE_REVIEW_FINGERPRINT=" + auth.fingerprint,
    )


def _remote_cli_summary(payload: dict[str, Any]) -> dict[str, str]:
    """Keep remote command output safe for terminals and conversation capture."""
    safe = _without_secret_metadata(payload)
    summary = {"status": str(safe.get("status") or "UNKNOWN")}
    fingerprint = str(safe.get("url_fingerprint") or "")
    if re.fullmatch(r"[0-9a-f]{16}", fingerprint):
        summary["url_fingerprint"] = fingerprint
    return summary


def _remote_session_payload(auth: _RemoteReviewAuth, tunnel_pid: int,
                            media: list[dict[str, str]],
                            server_identity: dict[str, Any],
                            tunnel_identity: dict[str, Any],
                            verification: dict[str, Any],
                            pairing_status: str = "NATIVE_WINDOW_DISPLAYED",
                            status: str = "ACTIVE") -> dict[str, Any]:
    return {
        "schema_version": 4, "status": status,
        "url_fingerprint": auth.fingerprint,
        "server_pid": os.getpid(), "tunnel_pid": tunnel_pid,
        "server_identity": server_identity, "tunnel_identity": tunnel_identity,
        "media_count": len(media), "media_kinds": sorted({item["kind"] for item in media}),
        "started_at": _utc_iso(auth.created_epoch),
        "bootstrap_expires_at": _utc_iso(auth.bootstrap_expires_epoch),
        "expires_at": _utc_iso(auth.session_expires_epoch),
        "expires_epoch": auth.session_expires_epoch,
        "idle_timeout_seconds": auth.idle_timeout_seconds,
        "pairing_status": pairing_status,
        "verification": _without_secret_metadata(verification),
        "access": "native_memory_qr_then_one_time_fragment_and_browser_session_cookie",
    }


def start_remote_background(bundle_dir: str | Path, port: int = 0,
                            cloudflared: str = "", startup_timeout: float = 75.0) -> dict[str, Any]:
    """Start a detached review daemon that survives the launching Codex shell."""
    bundle = Path(bundle_dir).resolve()
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("review manifest is missing: %s" % manifest_path)
    current = remote_status(bundle)
    if current.get("status") in {"ACTIVE", "STARTING"}:
        raise RuntimeError("remote review is already active; stop it to mint a new one-time link")
    if (bundle / "remote_session.json").is_file():
        stopped = stop_remote(bundle)
        if (stopped.get("status") != "STOPPED" or stopped.get("skipped_pids")
                or stopped.get("lingering_pids")):
            raise RuntimeError("refusing to replace a session whose process identity cannot be verified")
        (bundle / "remote_session.json").unlink(missing_ok=True)
    bootstrap = secrets.token_urlsafe(32)
    bootstrap_digest = _sha256(bootstrap)
    bootstrap_expires_epoch = time.time() + BOOTSTRAP_TTL_SECONDS
    command = _remote_daemon_command(bundle, port, cloudflared, bootstrap_digest,
                                     bootstrap_expires_epoch)
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    # Remove legacy diagnostic surfaces. The detached daemon emits no URL-bearing logs.
    for legacy_name in ("remote_daemon.stdout.log", "remote_daemon.stderr.log",
                        "remote_tunnel.log"):
        (bundle / legacy_name).unlink(missing_ok=True)
    kwargs: dict[str, Any] = {
        "cwd": str(Path(__file__).resolve().parent), "env": env,
        "stdin": subprocess.PIPE, "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.CREATE_NO_WINDOW | 0x01000000 |
                                     subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    try:
        if process.stdin is None:
            raise RuntimeError("secure bootstrap pipe was not created")
        process.stdin.write((bootstrap + "\n").encode("ascii"))
        process.stdin.flush()
    except Exception:
        _terminate_pid(process.pid)
        raise
    finally:
        if process.stdin is not None:
            process.stdin.close()
        del bootstrap
    session_path = bundle / "remote_session.json"
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if session_path.is_file():
            session = json.loads(session_path.read_text(encoding="utf-8"))
            if (int(session.get("server_pid", 0)) == process.pid
                    and int(session.get("schema_version", 0)) >= 4
                    and session.get("status") == "ACTIVE"
                    and session.get("url_fingerprint") == bootstrap_digest[:16]
                    and session.get("pairing_status") in {
                        "NATIVE_WINDOW_DISPLAYED", "SESSION_AUTHORIZED"}
                    and isinstance(session.get("verification"), dict)
                    and session["verification"].get("status") == "VERIFIED"
                    and _process_identity_matches(session.get("server_identity"))
                    and _process_identity_matches(session.get("tunnel_identity"))):
                return _without_secret_metadata(dict(session))
        if process.poll() is not None:
            if session_path.is_file():
                failed = json.loads(session_path.read_text(encoding="utf-8"))
                code = (failed.get("verification") or {}).get("failure_code")
                if (failed.get("url_fingerprint") == bootstrap_digest[:16]
                        and int(failed.get("server_pid", 0)) == process.pid
                        and code in _READINESS_FAILURE_CODES):
                    raise _RemoteReadinessError(code)
            raise RuntimeError(
                "remote review daemon exited before secure native pairing was ready")
        time.sleep(0.25)
    if session_path.is_file():
        stopped = stop_remote(bundle)
        if stopped.get("status") != "STOPPED":
            _terminate_pid(process.pid)
    else:
        _terminate_pid(process.pid)
    raise TimeoutError("remote review daemon did not open secure native pairing in time")


_READINESS_FAILURE_CODES = frozenset({
    "DNS_RESOLUTION_FAILED", "TLS_VERIFICATION_FAILED", "ENDPOINT_TIMEOUT",
    "ENDPOINT_HTTP_ERROR", "ENDPOINT_UNAVAILABLE", "INVALID_ENDPOINT_RESPONSE",
    "HEALTH_IDENTITY_FAILED", "PAGE_IDENTITY_FAILED", "MEDIA_AUTH_GATE_FAILED",
})


class _RemoteReadinessError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.failure_code = code if code in _READINESS_FAILURE_CODES else "ENDPOINT_UNAVAILABLE"
        super().__init__("remote review verification failed: " + self.failure_code)


def _readiness_failure_code(exc: Exception) -> str:
    if isinstance(exc, _RemoteReadinessError):
        return exc.failure_code
    reason = exc.reason if isinstance(exc, URLError) else exc
    if isinstance(reason, socket.gaierror):
        return "DNS_RESOLUTION_FAILED"
    if isinstance(reason, ssl.SSLError):
        return "TLS_VERIFICATION_FAILED"
    if isinstance(reason, (TimeoutError, socket.timeout)):
        return "ENDPOINT_TIMEOUT"
    if isinstance(exc, HTTPError):
        return "ENDPOINT_HTTP_ERROR"
    if isinstance(exc, (json.JSONDecodeError, UnicodeError)):
        return "INVALID_ENDPOINT_RESPONSE"
    return "ENDPOINT_UNAVAILABLE"


def verify_remote_review(url: str, *, timeout: float = 12.0,
                         attempts: int = 32, retry_delay: float = 1.0,
                         total_timeout: float = 30.0) -> dict[str, Any]:
    """Verify the public origin only; secrets never cross this API boundary."""
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("remote review delivery requires an HTTPS origin")
    if parsed.fragment or parsed.query or parsed.username or parsed.password:
        raise ValueError("remote readiness verification refuses secret-bearing URLs")
    if (not isinstance(attempts, int) or isinstance(attempts, bool) or not 1 <= attempts <= 64
            or any(not math.isfinite(value) or value <= 0 for value in (timeout, total_timeout))
            or total_timeout > 30 or not math.isfinite(retry_delay) or retry_delay < 0):
        raise ValueError("invalid bounded remote readiness budget")
    public_origin = "%s://%s" % (parsed.scheme.lower(), parsed.netloc.lower())
    page_url = urljoin(public_origin + "/", "review.html")
    health_url = urljoin(public_origin + "/", "healthz")
    media_url = urljoin(public_origin + "/", "media/0")
    deadline = time.monotonic() + total_timeout
    last_code = "ENDPOINT_TIMEOUT"

    def remaining_timeout() -> float:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError()
        return min(timeout, remaining)

    for attempt in range(1, attempts + 1):
        if time.monotonic() >= deadline:
            break
        try:
            health = urlopen(Request(health_url, headers={
                "User-Agent": "Hao-Mobile-Review-QA/2.0",
            }), timeout=remaining_timeout())
            try:
                health_status = int(getattr(health, "status", health.getcode()))
                health_body = json.loads(health.read(64_000).decode("utf-8"))
            finally:
                health.close()
            if (health_status != 200 or not isinstance(health_body, dict)
                    or health_body.get("service") != "hao-remote-review"
                    or health_body.get("authentication") != "required"):
                raise _RemoteReadinessError("HEALTH_IDENTITY_FAILED")
            page = urlopen(Request(page_url, headers={
                "User-Agent": "Hao-Mobile-Review-QA/2.0",
            }), timeout=remaining_timeout())
            try:
                page_status = int(getattr(page, "status", page.getcode()))
                page_body = page.read(1_000_000).decode("utf-8", errors="replace")
            finally:
                page.close()
            if page_status != 200 or "安全連線中" not in page_body:
                raise _RemoteReadinessError("PAGE_IDENTITY_FAILED")
            try:
                media_probe = urlopen(Request(media_url, headers={
                    "User-Agent": "Hao-Mobile-Review-QA/2.0",
                    "Range": "bytes=0-0", "Cache-Control": "no-store",
                }), timeout=remaining_timeout())
                try:
                    media_status = int(getattr(media_probe, "status", media_probe.getcode()))
                finally:
                    media_probe.close()
            except HTTPError as exc:
                media_status = int(exc.code)
                exc.close()
            if media_status != 401:
                raise _RemoteReadinessError("MEDIA_AUTH_GATE_FAILED")
            remaining_timeout()  # A late response cannot turn expired readiness green.
            return {
                "status": "VERIFIED", "health_status": health_status,
                "page_status": page_status, "media_status": media_status,
                "media_gate": "AUTH_GATED",
                "pairing_required": True,
                "attempts": attempt,
                "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        except Exception as exc:  # DNS/tunnel startup is eventually consistent.
            last_code = _readiness_failure_code(exc)
            if isinstance(exc, HTTPError):
                exc.close()
            # Identity/authentication failures are not propagation delays.
            if isinstance(exc, _RemoteReadinessError) or last_code == "TLS_VERIFICATION_FAILED":
                break
            remaining = deadline - time.monotonic()
            if attempt < attempts and remaining > 0:
                time.sleep(min(retry_delay * 2 ** min(attempt - 1, 3), 3.0, remaining))
    # URL-bearing urllib errors never reach disk, CLI, or the parent daemon.
    raise _RemoteReadinessError(last_code) from None


def deliver_remote(source: str | Path, content_id: str, *,
                   quality_json: str | Path | None = None,
                   bundle_dir: str | Path | None = None, port: int = 0,
                   cloudflared: str = "") -> dict[str, Any]:
    """Create, launch and verify the mobile review required for visual delivery."""
    bundle_result = create_bundle(source, content_id, quality_json, bundle_dir)
    bundle = Path(bundle_result["bundle"])
    _atomic_json(bundle / "remote_delivery.json", {
        "schema_version": 4, "status": "STARTING", "content_id": content_id,
        "bundle": str(bundle), "media_count": bundle_result["media_count"],
    })
    if remote_status(bundle).get("status") == "ACTIVE":
        stop_remote(bundle)
    try:
        session = start_remote_background(bundle, port, cloudflared)
        verification = dict(session.get("verification") or {})
        if verification.get("status") != "VERIFIED":
            raise RuntimeError("remote review daemon did not report verified readiness")
    except Exception as exc:
        stop_remote(bundle)
        if isinstance(exc, _RemoteReadinessError):
            _atomic_json(bundle / "remote_delivery.json", {
                "schema_version": 4, "status": "SECURE_REVIEW_RUNTIME_REQUIRED",
                "failure_code": exc.failure_code,
            })
        raise
    result = {
        "status": "READY_FOR_SECURE_NATIVE_PAIRING",
        "content_id": content_id,
        "url_fingerprint": session["url_fingerprint"],
        "bootstrap_expires_at": session["bootstrap_expires_at"],
        "expires_at": session["expires_at"],
        "bundle": str(bundle),
        "media_count": bundle_result["media_count"],
        "verification": verification,
        "temporary_public_url": True,
        "computer_must_remain_online": True,
        "pairing_status": session["pairing_status"],
        "pairing_qr_storage": "MEMORY_ONLY_NATIVE_WINDOW",
    }
    persisted = dict(result, schema_version=4)
    _atomic_json(bundle / "remote_delivery.json", persisted)
    return result


def serve_remote(bundle_dir: str | Path, port: int = 0, cloudflared: str = "",
                 startup_timeout: float = 30.0, *, bootstrap_digest: str = "",
                 bootstrap_expires_epoch: float = 0.0, bootstrap_stream: Any = None,
                 session_ttl_seconds: int = REMOTE_SESSION_TTL_SECONDS,
                 idle_timeout_seconds: int = REMOTE_IDLE_TIMEOUT_SECONDS) -> None:
    if not bootstrap_digest or not bootstrap_expires_epoch or bootstrap_stream is None:
        raise RuntimeError(
            "direct remote mode is disabled: use remote-start for anonymous-pipe pairing")
    bootstrap_token = _read_bootstrap_pipe(bootstrap_stream, bootstrap_digest)
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    missing = [item["path"] for item in media if not Path(item["path"]).is_file()]
    if missing:
        raise FileNotFoundError("review media is missing: %s" % missing[0])
    qr_module = _load_qr_runtime()
    tk_module = _load_pairing_ui_runtime()
    binary = _find_cloudflared(cloudflared)
    can_finalize = bool(manifest.get("quality_json") and len(media) == 1 and
                        media[0]["kind"] == "video")
    auth = _RemoteReviewAuth(
        bootstrap_digest=bootstrap_digest,
        bootstrap_expires_epoch=bootstrap_expires_epoch,
        public_origin="http://127.0.0.1",
        session_ttl_seconds=session_ttl_seconds,
        idle_timeout_seconds=idle_timeout_seconds,
    )
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 _handler_factory(bundle, media, auth, can_finalize))
    server.daemon_threads = True
    local_port = int(server.server_address[1])
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    command = [str(binary), "tunnel", "--url", "http://127.0.0.1:%d" % local_port,
               "--no-autoupdate", "--loglevel", "info"]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace",
                               creationflags=flags)
    starting_server_identity = _process_identity(os.getpid())
    starting_tunnel_identity = _process_identity(process.pid)
    if not starting_server_identity or not starting_tunnel_identity:
        if process.poll() is None:
            process.terminate()
        server.shutdown(); server.server_close()
        raise RuntimeError("could not establish immutable process identity; refusing remote access")
    _atomic_json(bundle / "remote_session.json", _remote_session_payload(
        auth, process.pid, media, starting_server_identity, starting_tunnel_identity,
        {"status": "PENDING"}, pairing_status="STARTING_NATIVE_WINDOW",
        status="STARTING"))
    lines: queue.Queue[str] = queue.Queue(maxsize=128)

    def pump() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            try:
                lines.put(line, timeout=0.1)
            except queue.Full:
                pass

    threading.Thread(target=pump, daemon=True).start()
    deadline, public_base = time.monotonic() + startup_timeout, ""
    pairing_window: _NativePairingWindow | None = None
    try:
        while time.monotonic() < deadline and process.poll() is None:
            try:
                line = lines.get(timeout=0.25)
            except queue.Empty:
                continue
            match = QUICK_TUNNEL_ORIGIN.search(line)
            if match:
                public_base = match.group(0)
                break
        if not public_base:
            raise RuntimeError("cloudflared did not produce a Quick Tunnel URL")
        with auth._lock:
            auth.public_origin = _normalized_origin(public_base)
        verification = verify_remote_review(auth.public_origin, timeout=5.0, attempts=32,
                                            retry_delay=1.0, total_timeout=30.0)
        remote_url = "%s/review.html#%s" % (
            auth.public_origin, urlencode({"bootstrap": bootstrap_token}))
        qr_png = _render_pairing_qr(remote_url, lambda _name: qr_module)
        del remote_url, bootstrap_token
        pairing_window = _NativePairingWindow(
            qr_png, auth.fingerprint, _utc_iso(auth.bootstrap_expires_epoch), tk_module)
        qr_png = b""
        server_identity = _process_identity(os.getpid())
        tunnel_identity = _process_identity(process.pid)
        if not server_identity or not tunnel_identity:
            raise RuntimeError("could not establish immutable process identity; refusing remote access")
        session = _remote_session_payload(
            auth, process.pid, media, server_identity, tunnel_identity, verification)
        _atomic_json(bundle / "remote_session.json", session)
        for announcement in _safe_remote_announcements(auth):
            print(announcement, flush=True)
        while process.poll() is None:
            if auth.bootstrap_used and pairing_window is not None:
                pairing_window.close()
                pairing_window = None
                session["pairing_status"] = "SESSION_AUTHORIZED"
                _atomic_json(bundle / "remote_session.json", session)
            elif pairing_window is not None and not pairing_window.pump():
                session.update(
                    status="EXPIRED", stop_reason="pairing_window_closed",
                    stopped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                _atomic_json(bundle / "remote_session.json", session)
                return
            reason = auth.shutdown_due()
            if reason:
                session.update(status="EXPIRED", stop_reason=reason,
                               stopped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
                _atomic_json(bundle / "remote_session.json", session)
                return
            time.sleep(0.05)
        raise RuntimeError("cloudflared stopped unexpectedly")
    except _RemoteReadinessError as exc:
        _atomic_json(bundle / "remote_session.json", _remote_session_payload(
            auth, process.pid, media, starting_server_identity, starting_tunnel_identity,
            {"status": "FAILED", "failure_code": exc.failure_code},
            pairing_status="NOT_READY", status="STARTUP_FAILED"))
        raise
    finally:
        server.shutdown(); server.server_close()
        if pairing_window is not None:
            pairing_window.close()
        if process.poll() is None:
            process.terminate()


def serve(bundle_dir: str | Path, port: int = 8765) -> None:
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    can_finalize = bool(manifest.get("quality_json") and len(media) == 1 and
                        media[0]["kind"] == "video")
    print("僅限本機開啟：http://127.0.0.1:%d/review.html" % port)
    ThreadingHTTPServer(("127.0.0.1", port),
                        _handler_factory(bundle, media, None, can_finalize)).serve_forever()


def _self_test_bundle(temp: str) -> tuple[dict[str, Any], list[dict[str, Any]], Path]:
    source = Path(temp) / "assets"; source.mkdir()
    video = source / "current.mp4"
    video.write_bytes(b"0123456789")
    image = source / "taste-board.png"; image.write_bytes(b"fake-png")
    (source / "notes.txt").write_text("skip", encoding="utf-8")
    bundle = create_bundle(source, "demo")
    assert Path(bundle["page"]).is_file()
    assert bundle["media_count"] == 2
    assert create_bundle(source, "demo")["media_count"] == 2
    assert _manifest_media({"video": str(video)})[0]["path"] == str(video.resolve())
    assert _pid_alive(os.getpid()) and not _pid_alive(-1)
    cli_bundle = Path(temp) / "cli-review"
    assert main(["create", str(image), "--content-id", "cli-demo",
                 "--bundle-dir", str(cli_bundle)]) == 0
    assert json.loads((cli_bundle / "manifest.json").read_text(encoding="utf-8"))["media_count"] == 1
    assert "taste-board.png" in Path(bundle["page"]).read_text(encoding="utf-8")
    assert _parse_byte_range("bytes=2-5", 10) == (2, 5)
    manifest = json.loads((Path(bundle["bundle"]) / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    return bundle, media, image

def _self_test_http(bundle: dict[str, Any], media: list[dict[str, Any]]) -> None:
    token = secrets.token_urlsafe(32)
    auth = _RemoteReviewAuth(_sha256(token), time.time() + BOOTSTRAP_TTL_SECONDS,
                             "http://127.0.0.1")
    assert auth.bootstrap_expires_epoch <= auth.created_epoch + BOOTSTRAP_TTL_SECONDS
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 _handler_factory(Path(bundle["bundle"]), media, auth))
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = "http://127.0.0.1:%d" % server.server_address[1]
    auth.public_origin = base

    def request(path: str, *, data: bytes | None = None,
                headers: dict[str, str] | None = None) -> tuple[int, bytes, Any]:
        try:
            response = urlopen(Request(base + path, data=data, headers=headers or {}), timeout=3)
            return int(response.status), response.read(), response.headers
        except HTTPError as exc:
            return int(exc.code), exc.read(), exc.headers

    post_headers = {"Content-Type": "application/json", "Origin": base,
                    "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}
    forbidden_inline_csp = "unsafe" + "-inline"
    try:
        status, page, page_headers = request("/review.html")
        assert status == 200 and "安全連線中" in page.decode("utf-8")
        bootstrap_csp = str(page_headers.get("Content-Security-Policy", ""))
        assert "sha256-" in bootstrap_csp and forbidden_inline_csp not in bootstrap_csp
        assert request("/media/0")[0] == 401  # no cookie cannot read media
        unknown_cookie = {"Cookie": SESSION_COOKIE + "=" + secrets.token_urlsafe(32)}
        assert request("/media/0", headers=unknown_cookie)[0] == 401

        wrong_origin = dict(post_headers, Origin="https://evil.invalid")
        unknown = json.dumps({"bootstrap": "wrong"}).encode("utf-8")
        assert request("/api/bootstrap", data=b"", headers=wrong_origin)[0] == 403
        assert request("/api/bootstrap", data=b"",
                       headers=dict(post_headers, **{"Sec-Fetch-Site": "cross-site"}))[0] == 403
        assert request("/api/bootstrap", data=b"",
                       headers={"Content-Type": "application/json",
                                "Origin": base})[0] == 403
        assert request("/api/bootstrap", data=unknown, headers=post_headers)[0] == 401

        bootstrap_body = json.dumps({"bootstrap": token}).encode("utf-8")
        status, _, response_headers = request(
            "/api/bootstrap", data=bootstrap_body, headers=post_headers)
        assert status == 200
        set_cookie = str(response_headers.get("Set-Cookie", ""))
        assert (SESSION_COOKIE + "=") in set_cookie
        assert "HttpOnly" in set_cookie and "Secure" in set_cookie
        assert "SameSite=Strict" in set_cookie
        cookie = set_cookie.split(";", 1)[0]
        assert len(cookie.split("=", 1)[1]) >= 43
        assert token not in cookie and token not in repr(auth)
        assert request("/api/bootstrap", data=bootstrap_body,
                       headers=post_headers)[0] == 409  # one-time replay

        auth_headers = {"Cookie": cookie}
        status, page, page_headers = request("/review.html", headers=auth_headers)
        assert status == 200 and b"/media/0" in page and b"/media/1" in page
        assert b" onclick=\"" not in page
        app_csp = str(page_headers.get("Content-Security-Policy", ""))
        assert "sha256-" in app_csp and forbidden_inline_csp not in app_csp
        range_headers = {"Cookie": cookie, "Range": "bytes=2-5"}
        status, body, _ = request("/media/0", headers=range_headers)
        assert status == 206 and body == b"2345"
        assert request("/media/1", headers=auth_headers)[1] == b"fake-png"

        payload = json.dumps({"issues": [], "decisions": {"m1": "approved"}}).encode("utf-8")
        review_headers = dict(post_headers, Cookie=cookie)
        assert request("/api/review", data=b"", headers=post_headers)[0] == 401
        assert request("/api/review", data=b"",
                       headers=dict(post_headers, **unknown_cookie))[0] == 401
        assert request("/api/review", data=b"",
                       headers=dict(review_headers, Origin="https://evil.invalid"))[0] == 403
        assert request("/api/review", data=b"",
                       headers={key: value for key, value in review_headers.items()
                                if key != "Content-Type"})[0] == 415
        declared_oversize = dict(
            review_headers, **{"Content-Length": str(MAX_REVIEW_BODY_BYTES + 1)})
        assert request("/api/review", data=b"x",
                       headers=declared_oversize)[0] == 413
        assert request("/api/review", data=payload, headers=review_headers)[0] == 200
        assert (Path(bundle["bundle"]) / "review.json").is_file()

        original_urlopen = globals()["urlopen"]
        probed_urls: list[str] = []

        def routed_urlopen(probe: Any, timeout: float = 0) -> Any:
            original_url = str(getattr(probe, "full_url", probe))
            probed_urls.append(original_url)
            return original_urlopen(
                Request(original_url.replace("https://local.test", base),
                        headers=dict(getattr(probe, "headers", {}))), timeout=timeout)

        globals()["urlopen"] = routed_urlopen
        try:
            verified = verify_remote_review("https://local.test", attempts=1)
            assert verified["page_status"] == 200
            assert verified["media_status"] == 401
            assert verified["media_gate"] == "AUTH_GATED"
            assert verified["pairing_required"]
            assert probed_urls and all("bootstrap" not in item for item in probed_urls)
            assert any(item.endswith("/media/0") for item in probed_urls)

            class UngatedMedia:
                def __init__(self, status: int) -> None:
                    self.status = status
                def getcode(self) -> int: return self.status
                def read(self, _limit: int = -1) -> bytes: return b"leaked"
                def close(self) -> None: pass

            for leaked_status in (200, 206):
                def ungated_urlopen(probe: Any, timeout: float = 0,
                                     status: int = leaked_status) -> Any:
                    probe_url = str(getattr(probe, "full_url", probe))
                    if probe_url.endswith("/media/0"):
                        return UngatedMedia(status)
                    return routed_urlopen(probe, timeout=timeout)

                globals()["urlopen"] = ungated_urlopen
                try:
                    verify_remote_review("https://local.test", attempts=1)
                    raise AssertionError(
                        "public media status %d unexpectedly passed readiness" %
                        leaked_status)
                except RuntimeError as exc:
                    assert isinstance(exc, _RemoteReadinessError)
                    assert exc.failure_code == "MEDIA_AUTH_GATE_FAILED"
        finally:
            globals()["urlopen"] = original_urlopen
    finally:
        server.shutdown(); server.server_close()


def _self_test_pairing_ui() -> None:
    pairing_token = secrets.token_urlsafe(32)
    pairing_remote_url = ("https://pairing.example.invalid/review.html#" +
                          urlencode({"bootstrap": pairing_token}))
    qr_png = _render_pairing_qr(pairing_remote_url)
    assert qr_png.startswith(b"\x89PNG\r\n\x1a\n") and len(qr_png) > 100

    def missing_qr_runtime(_name: str) -> Any:
        raise ModuleNotFoundError("qrcode")

    try:
        _render_pairing_qr(pairing_remote_url, missing_qr_runtime)
        raise AssertionError("missing qrcode runtime unexpectedly succeeded")
    except RuntimeError as exc:
        assert str(exc).startswith("SECURE_REVIEW_RUNTIME_REQUIRED")

    def missing_ui_runtime(_name: str) -> Any:
        raise ModuleNotFoundError("tkinter")

    try:
        _load_pairing_ui_runtime(missing_ui_runtime)
        raise AssertionError("missing tkinter runtime unexpectedly succeeded")
    except RuntimeError as exc:
        assert str(exc).startswith("SECURE_REVIEW_RUNTIME_REQUIRED")

    class BrokenTk:
        @staticmethod
        def Tk() -> Any:
            raise RuntimeError("no interactive desktop")

    try:
        _NativePairingWindow(qr_png, _sha256(pairing_token)[:16],
                             "2099-01-01T00:00:00+00:00", BrokenTk())
        raise AssertionError("unavailable native desktop unexpectedly succeeded")
    except RuntimeError as exc:
        assert str(exc).startswith("SECURE_REVIEW_RUNTIME_REQUIRED")

    class FakeRoot:
        def __init__(self) -> None:
            self.visible = False
            self.destroyed = False
            self.protocols: dict[str, Any] = {}
            self.attributes_seen: list[tuple[Any, ...]] = []

        def withdraw(self) -> None: self.visible = False
        def title(self, _value: str) -> None: return
        def configure(self, **_kwargs: Any) -> None: return
        def resizable(self, *_args: Any) -> None: return
        def protocol(self, name: str, callback: Any) -> None:
            self.protocols[name] = callback
        def update_idletasks(self) -> None: return
        def deiconify(self) -> None: self.visible = True
        def lift(self) -> None: return
        def attributes(self, *args: Any) -> None: self.attributes_seen.append(args)
        def after(self, _delay: int, _callback: Any) -> None: return
        def update(self) -> None:
            if self.destroyed:
                raise RuntimeError("destroyed")
        def destroy(self) -> None: self.destroyed = True

    class FakeWidget:
        def __init__(self, _root: Any, **kwargs: Any) -> None:
            fake_tk.widget_kwargs.append(kwargs)
        def pack(self, **_kwargs: Any) -> None: return

    class FakePhoto:
        def __init__(self, **kwargs: Any) -> None:
            self.data = kwargs.get("data", "")
            self.format = kwargs.get("format", "")

    class FakeTk:
        def __init__(self) -> None:
            self.root = FakeRoot()
            self.widget_kwargs: list[dict[str, Any]] = []
            self.Label = FakeWidget
            self.PhotoImage = FakePhoto
        def Tk(self) -> FakeRoot: return self.root

    fake_tk = FakeTk()
    pairing_window = _NativePairingWindow(
        qr_png, _sha256(pairing_token)[:16],
        "2099-01-01T00:00:00+00:00", fake_tk)
    assert pairing_window.is_open and pairing_window.pump() and fake_tk.root.visible
    assert pairing_window._image.format == "png"
    assert base64.b64decode(pairing_window._image.data) == qr_png
    visible_text = "\n".join(
        str(item.get("text", "")) for item in fake_tk.widget_kwargs)
    assert pairing_token not in visible_text
    assert "pairing.example.invalid" not in visible_text
    fake_tk.root.protocols["WM_DELETE_WINDOW"]()
    assert not pairing_window.is_open and fake_tk.root.destroyed


def _self_test_remote_lifecycle(temp: str, bundle: dict[str, Any],
                                media: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    expired_token = secrets.token_urlsafe(32)
    expired_auth = _RemoteReviewAuth(_sha256(expired_token), time.time() - 1,
                                     "http://127.0.0.1")
    expired_server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _handler_factory(Path(bundle["bundle"]), media, expired_auth))
    expired_thread = threading.Thread(target=expired_server.serve_forever, daemon=True)
    expired_thread.start()
    expired_base = "http://127.0.0.1:%d" % expired_server.server_address[1]
    expired_auth.public_origin = expired_base
    try:
        expired_headers = {"Content-Type": "application/json", "Origin": expired_base,
                       "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"}
        expired_body = json.dumps({"bootstrap": expired_token}).encode("utf-8")
        try:
            urlopen(Request(expired_base + "/api/bootstrap", data=expired_body,
                            headers=expired_headers), timeout=3)
            raise AssertionError("expired bootstrap unexpectedly succeeded")
        except HTTPError as exc:
            assert exc.code == 410
    finally:
        expired_server.shutdown(); expired_server.server_close()

    idle_auth = _RemoteReviewAuth(_sha256("idle"), time.time() + 60,
                                  "https://local.test", idle_timeout_seconds=1)
    idle_auth.session_digest = _sha256("idle-credential")
    idle_auth.bootstrap_used = True
    idle_auth.last_activity_monotonic -= 2
    assert not idle_auth.authorized("idle-credential")
    assert idle_auth.shutdown_due() == "idle_timeout"
    ttl_auth = _RemoteReviewAuth(_sha256("ttl"), time.time() + 60,
                                 "https://local.test", session_ttl_seconds=1)
    ttl_auth.created_epoch -= 2
    assert ttl_auth.shutdown_due() == "session_ttl_expired"
    identity = _process_identity(os.getpid())
    assert identity and _process_identity_matches(identity)
    assert not _process_identity_matches(dict(identity, start_marker="reused-pid"))
    limiter = _RemoteReviewAuth(_sha256("limit"), time.time() + 60,
                                "https://local.test")
    assert all(limiter.allow_request("bootstrap", AUTH_RATE_ATTEMPTS)
               for _ in range(AUTH_RATE_ATTEMPTS))
    assert not limiter.allow_request("bootstrap", AUTH_RATE_ATTEMPTS)
    starting_bundle = Path(temp) / "starting-review"; starting_bundle.mkdir()
    _atomic_json(starting_bundle / "remote_session.json", {
        "schema_version": 4, "status": "STARTING",
        "server_pid": os.getpid(), "tunnel_pid": os.getpid(),
        "server_identity": identity, "tunnel_identity": identity,
        "expires_epoch": time.time() + 60,
        "url_fingerprint": "0" * 16,
    })
    assert remote_status(starting_bundle)["status"] == "STARTING"
    assert _remote_cli_summary(remote_status(starting_bundle)) == {
        "status": "STARTING", "url_fingerprint": "0" * 16}
    status_bundle = Path(temp) / "status-review"; status_bundle.mkdir()
    raw_url_key = "u" + "rl"
    forbidden_url_json = '"' + raw_url_key + '":'
    status_payload = {
        "schema_version": 2, "server_pid": os.getpid(), "tunnel_pid": os.getpid(),
        "server_identity": identity, "tunnel_identity": identity,
        "expires_epoch": time.time() + 60,
    }
    status_payload[raw_url_key] = (
        "https://legacy." + QUICK_TUNNEL_HOST + "/legacy-bearer/review.html")
    status_payload["public_origin"] = "https://legacy." + QUICK_TUNNEL_HOST
    status_payload["local_pairing_url"] = "http://127.0.0.1:43210/pair"
    status_payload["pairing_port"] = 43210
    status_payload["port"] = 8765
    status_payload["nested"] = {
        raw_url_key: "https://legacy." + QUICK_TUNNEL_HOST + "/nested-secret",
        "safe": "metadata",
    }
    _atomic_json(status_bundle / "remote_session.json", status_payload)
    safe_status = remote_status(status_bundle)
    assert safe_status["status"] == "ACTIVE" and raw_url_key not in safe_status
    assert "legacy-bearer" not in json.dumps(safe_status)
    assert safe_status["nested"] == {"safe": "metadata"}
    assert not ({"public_origin", "local_pairing_url", "pairing_port", "port"}
                & set(safe_status))
    status_payload["server_identity"] = dict(identity, start_marker="reused-pid")
    _atomic_json(status_bundle / "remote_session.json", status_payload)
    assert remote_status(status_bundle)["status"] == "DEGRADED"

    stop_failure_bundle = Path(temp) / "stop-failure-review"
    stop_failure_bundle.mkdir()
    stop_failure_payload = {
        "schema_version": 4, "status": "ACTIVE",
        "server_pid": os.getpid(), "tunnel_pid": os.getpid(),
        "server_identity": identity, "tunnel_identity": identity,
        "expires_epoch": time.time() + 60,
    }
    _atomic_json(stop_failure_bundle / "remote_session.json", stop_failure_payload)
    original_terminate = globals()["_terminate_pid"]
    globals()["_terminate_pid"] = lambda _pid: False
    try:
        failed_stop = stop_remote(stop_failure_bundle, wait_timeout=0.0)
    finally:
        globals()["_terminate_pid"] = original_terminate
    assert failed_stop["status"] == "STOP_FAILED"
    assert failed_stop["lingering_pids"] == [os.getpid()]
    assert failed_stop["skipped_pids"] == [
        {"pid": os.getpid(), "reason": "terminate_request_failed"}]
    assert "stop_attempted_at" in failed_stop and "stopped_at" not in failed_stop
    truthful_status = remote_status(stop_failure_bundle)
    assert truthful_status["status"] == "STOP_FAILED"
    assert truthful_status["server_alive"] and truthful_status["tunnel_alive"]

    stopped_bundle = Path(temp) / "already-stopped-review"
    stopped_bundle.mkdir()
    dead_pid = 2_000_000_000
    dead_identity = dict(identity, pid=dead_pid, start_marker="not-running")
    _atomic_json(stopped_bundle / "remote_session.json", {
        "schema_version": 4, "status": "ACTIVE",
        "server_pid": dead_pid, "tunnel_pid": dead_pid,
        "server_identity": dead_identity, "tunnel_identity": dead_identity,
        "expires_epoch": time.time() + 60,
    })
    stopped_result = stop_remote(stopped_bundle, wait_timeout=0.0)
    assert stopped_result["status"] == "STOPPED" and "stopped_at" in stopped_result
    assert remote_status(stopped_bundle)["status"] == "STOPPED"

    return identity, forbidden_url_json

def _self_test_secret_surfaces(temp: str, image: Path, media: list[dict[str, Any]],
                               identity: dict[str, Any], forbidden_url_json: str) -> None:
    delivery_bundle = Path(temp) / "delivery-review"
    surface_token = secrets.token_urlsafe(32)
    surface_digest = _sha256(surface_token)
    command = _remote_daemon_command(delivery_bundle, 0, "", surface_digest,
                                     time.time() + BOOTSTRAP_TTL_SECONDS)
    assert surface_token not in "\0".join(command)
    assert _read_bootstrap_pipe(io.BytesIO((surface_token + "\n").encode("ascii")),
                                surface_digest) == surface_token
    surface_auth = _RemoteReviewAuth(surface_digest, time.time() + 60,
                                     "https://example.invalid")
    announcements = "\n".join(_safe_remote_announcements(surface_auth))
    assert surface_token not in announcements and "#bootstrap=" not in announcements
    assert "example.invalid" not in announcements and "127.0.0.1" not in announcements
    surface_verification = {
        "status": "VERIFIED", "health_status": 200, "page_status": 200,
        "media_status": 401, "media_gate": "AUTH_GATED",
        "pairing_required": True,
    }
    safe_session = _remote_session_payload(
        surface_auth, os.getpid(), media, identity, identity,
        surface_verification)
    session_text = json.dumps(safe_session, ensure_ascii=False)
    assert surface_token not in session_text and forbidden_url_json not in session_text
    forbidden_locator_keys = {
        "public_origin", "local_pairing_url", "pairing_url", "pairing_port", "port"}
    assert not (forbidden_locator_keys & set(safe_session))
    assert "example.invalid" not in session_text and "127.0.0.1" not in session_text
    safe_artifacts = Path(temp) / "safe-surfaces"; safe_artifacts.mkdir()
    _atomic_json(safe_artifacts / "remote_session.json", safe_session)
    original_start = globals()["start_remote_background"]
    globals()["start_remote_background"] = lambda *_args, **_kwargs: dict(safe_session)
    try:
        cli_stdout = io.StringIO()
        with contextlib.redirect_stdout(cli_stdout):
            assert main(["remote-start", str(delivery_bundle)]) == 0
        cli_text = cli_stdout.getvalue()
        assert surface_token not in cli_text and forbidden_url_json not in cli_text
        assert set(json.loads(cli_text)) == {"status", "url_fingerprint"}
        deliver_stdout = io.StringIO()
        cli_delivery_bundle = Path(temp) / "cli-delivery-review"
        with contextlib.redirect_stdout(deliver_stdout):
            assert main(["deliver", str(image), "--content-id", "cli-secret-free",
                         "--bundle-dir", str(cli_delivery_bundle)]) == 0
        deliver_cli_text = deliver_stdout.getvalue()
        assert surface_token not in deliver_cli_text
        assert forbidden_url_json not in deliver_cli_text
        assert set(json.loads(deliver_cli_text)) == {"status", "url_fingerprint"}
        delivered = deliver_remote(image, "secret-free", bundle_dir=delivery_bundle)
        delivered_text = json.dumps(delivered, ensure_ascii=False)
        assert surface_token not in delivered_text and forbidden_url_json not in delivered_text
        assert delivered["pairing_status"] == "NATIVE_WINDOW_DISPLAYED"
        assert delivered["pairing_qr_storage"] == "MEMORY_ONLY_NATIVE_WINDOW"
        assert not (forbidden_locator_keys & set(delivered))
        assert "example.invalid" not in delivered_text and "127.0.0.1" not in delivered_text
        delivery_text = (delivery_bundle / "remote_delivery.json").read_text(encoding="utf-8")
        assert surface_token not in delivery_text and forbidden_url_json not in delivery_text
        assert all(key not in delivery_text for key in forbidden_locator_keys)
        for artifact in safe_artifacts.iterdir():
            text = artifact.read_text(encoding="utf-8", errors="replace")
            assert surface_token not in text and "#bootstrap=" not in text
            assert "example.invalid" not in text and "127.0.0.1" not in text
    finally:
        globals()["start_remote_background"] = original_start

def self_test() -> None:
    assert '.viewer{display:block' in HTML_TEMPLATE
    assert 'placeholder="未評"' in HTML_TEMPLATE
    assert "data.ratings[k]||5" not in HTML_TEMPLATE
    assert "input.checkValidity()" in HTML_TEMPLATE
    with tempfile.TemporaryDirectory(prefix="review-loop-") as temp:
        bundle, media, image = _self_test_bundle(temp)
        _self_test_http(bundle, media)
        _self_test_pairing_ui()
        identity, forbidden_url_json = _self_test_remote_lifecycle(temp, bundle, media)
        _self_test_secret_surfaces(temp, image, media, identity, forbidden_url_json)
    print("review_loop self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("video", help="browser-viewable video, image, or media directory")
    create.add_argument("--content-id", required=True)
    create.add_argument("--quality-json", default="")
    create.add_argument("--bundle-dir", default="")
    server = sub.add_parser("serve"); server.add_argument("bundle"); server.add_argument("--port", type=int, default=8765)
    remote = sub.add_parser("remote"); remote.add_argument("bundle"); remote.add_argument("--port", type=int, default=0)
    remote.add_argument("--cloudflared", default="")
    remote.add_argument("--bootstrap-digest", default="", help=argparse.SUPPRESS)
    remote.add_argument("--bootstrap-expires-epoch", type=float, default=0.0,
                        help=argparse.SUPPRESS)
    remote_start = sub.add_parser("remote-start"); remote_start.add_argument("bundle")
    remote_start.add_argument("--port", type=int, default=0); remote_start.add_argument("--cloudflared", default="")
    deliver = sub.add_parser("deliver")
    deliver.add_argument("source", help="finished visual asset, video, or media directory")
    deliver.add_argument("--content-id", required=True)
    deliver.add_argument("--quality-json", default="")
    deliver.add_argument("--bundle-dir", default="")
    deliver.add_argument("--port", type=int, default=0)
    deliver.add_argument("--cloudflared", default="")
    status = sub.add_parser("remote-status"); status.add_argument("bundle")
    stop = sub.add_parser("remote-stop"); stop.add_argument("bundle")
    final = sub.add_parser("finalize"); final.add_argument("bundle"); final.add_argument("--no-learn", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "create":
        print(json.dumps(create_bundle(args.video, args.content_id, args.quality_json or None,
                                       args.bundle_dir or None), ensure_ascii=False, indent=2)); return 0
    if args.command == "serve":
        serve(args.bundle, args.port); return 0
    if args.command == "remote":
        if not args.bootstrap_digest or not args.bootstrap_expires_epoch:
            raise RuntimeError("direct remote mode is disabled; use remote-start")
        serve_remote(args.bundle, args.port, args.cloudflared,
                     bootstrap_digest=args.bootstrap_digest,
                     bootstrap_expires_epoch=args.bootstrap_expires_epoch,
                     bootstrap_stream=sys.stdin.buffer); return 0
    if args.command == "remote-start":
        try:
            started = start_remote_background(args.bundle, args.port, args.cloudflared)
        except _RemoteReadinessError as exc:
            print(json.dumps({"status": "SECURE_REVIEW_RUNTIME_REQUIRED",
                              "failure_code": exc.failure_code})); return 1
        print(json.dumps(_remote_cli_summary(started), ensure_ascii=False, indent=2)); return 0
    if args.command == "deliver":
        try:
            delivered = deliver_remote(
                args.source, args.content_id, quality_json=args.quality_json or None,
                bundle_dir=args.bundle_dir or None, port=args.port, cloudflared=args.cloudflared)
        except _RemoteReadinessError as exc:
            print(json.dumps({"status": "SECURE_REVIEW_RUNTIME_REQUIRED",
                              "failure_code": exc.failure_code})); return 1
        print(json.dumps(_remote_cli_summary(delivered), ensure_ascii=False, indent=2)); return 0
    if args.command == "remote-status":
        print(json.dumps(_remote_cli_summary(remote_status(args.bundle)),
                         ensure_ascii=False, indent=2)); return 0
    if args.command == "remote-stop":
        print(json.dumps(_remote_cli_summary(stop_remote(args.bundle)),
                         ensure_ascii=False, indent=2)); return 0
    if args.command == "finalize":
        print(json.dumps(finalize(args.bundle, learn=not args.no_learn), ensure_ascii=False, indent=2)); return 0
    self_test(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
