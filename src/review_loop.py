# -*- coding: utf-8 -*-
"""Hao-owned video/image review bundle and one-click feedback ingestion.

The reviewer is Hao.  A phone or desktop browser is only an access device and
never changes who owns the aesthetic decision.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import queue
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

from knowledge_lifecycle import record_feedback
from aesthetic_score import review_schema
from quality_95 import apply_human_review, write_report


VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".bmp"}
MEDIA_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
MAX_REVIEW_MEDIA = 300


HTML_TEMPLATE = r'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hao 遠端素材審查</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}body{margin:0;background:#090b10;color:#f7f7fb}
main{max-width:920px;margin:auto;padding:12px 12px 80px}.viewer{display:grid;place-items:center;width:100%;height:min(68vh,760px);background:#000;border-radius:14px;overflow:hidden}
.viewer video,.viewer img{display:block;width:100%;height:100%;object-fit:contain;background:#000}.nav{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:10px}.name{min-width:0;text-align:center;overflow-wrap:anywhere;color:#dce3f4}
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
let data=JSON.parse(localStorage.getItem(key)||'{"issues":[],"ratings":{},"decisions":{}}'), marked=0, current=0, v=null;
data.issues=data.issues||[];data.ratings=data.ratings||{};data.decisions=data.decisions||{};
const dims=__AESTHETIC_DIMENSIONS__;
function fmt(t){let m=Math.floor(t/60),s=t-m*60;return String(m).padStart(2,'0')+':'+s.toFixed(2).padStart(5,'0')}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
let syncTimer=null;
async function syncNow(message='已自動同步'){try{let res=await fetch('__API_PATH__',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});saved.textContent=res.ok?message:'自動同步失敗，請按最底送出';return res.ok}catch(_){saved.textContent='自動同步失敗，請按最底送出';return false}}
function save(){localStorage.setItem(key,JSON.stringify(data));renderIssues();renderDecision();clearTimeout(syncTimer);syncTimer=setTimeout(()=>syncNow(),180)}
function renderDecision(){const x=media[current],d=data.decisions[x.id];decision.textContent=d==='approved'?'✓ 可用':d==='redo'?'✕ 重做':''}
function renderIssues(){issues.innerHTML=data.issues.map((x,i)=>`<div class="issue"><b>${esc(x.media_name||'素材')} · ${x.kind==='video'?fmt(Number(x.time||0)):''} ${esc(x.category)}</b><br>${esc(x.comment)}<br><button onclick="data.issues.splice(${i},1);save()">刪除</button></div>`).join('')||'尚無問題';}
function show(i){current=(i+media.length)%media.length;const x=media[current];viewer.innerHTML='';v=null;marked=0;
 if(x.kind==='video'){v=document.createElement('video');v.controls=true;v.playsInline=true;v.preload='metadata';v.src=x.src;viewer.appendChild(v);clock.textContent='00:00.00';mark.disabled=false}
 else{let im=document.createElement('img');im.src=x.src;im.alt=x.name;viewer.appendChild(im);clock.textContent='素材 '+(current+1)+' / '+media.length;mark.disabled=true}
 counter.textContent=(current+1)+' / '+media.length;mediaName.textContent=x.name;renderDecision()}
ratings.innerHTML=Object.entries(dims).map(([k,n])=>`<div class="rating"><label>${n.label_zh}<small>${n.question}</small></label><input id="r-${k}" type="number" min="1" max="5" step="0.5" value="${data.ratings[k]||5}"></div>`).join('');
if(!media.some(x=>x.kind==='video'))ratingsCard.style.display='none';
setInterval(()=>{if(v)clock.textContent=fmt(v.currentTime)},100);mark.onclick=()=>{if(v){marked=v.currentTime;clock.textContent=fmt(marked)}};
prev.onclick=()=>show(current-1);next.onclick=()=>show(current+1);approve.onclick=()=>{data.decisions[media[current].id]='approved';save()};redo.onclick=()=>{data.decisions[media[current].id]='redo';save()};
add.onclick=()=>{let c=comment.value.trim();if(!c)return;const x=media[current],t=v?(marked||v.currentTime):0;saved.textContent='已加入：'+x.name;data.issues.push({media_id:x.id,media_name:x.name,kind:x.kind,time:t,category:category.value,comment:c});comment.value='';save()};
submit.onclick=async()=>{if(media.some(x=>x.kind==='video'))for(const k of Object.keys(dims))data.ratings[k]=Number(document.querySelector('#r-'+k).value);data.completed_at=new Date().toISOString();data.media_count=media.length;localStorage.setItem(key,JSON.stringify(data));await syncNow(canFinalize?'已送出，可回 Codex 執行 finalize':'已送出，Codex 可直接讀取審查結果')};show(0);renderIssues();
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
            src = "media/%d" % index
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


class _MediaReviewHandler(BaseHTTPRequestHandler):
    bundle: Path
    media: list[dict[str, str]]
    token: str
    can_finalize: bool
    protocol_version = "HTTP/1.1"

    def _tail(self) -> str | None:
        path = urlparse(self.path).path
        prefix = "/%s/" % self.token if self.token else "/"
        return path[len(prefix):] if path.startswith(prefix) else None

    def _send_bytes(self, payload: bytes, content_type: str, *, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_media(self, index: int) -> None:
        if index < 0 or index >= len(self.media):
            self.send_error(404)
            return
        path = Path(self.media[index]["path"])
        if not path.is_file():
            self.send_error(404, "review media is missing")
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
        self.send_header("Cache-Control", "private, max-age=300")
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
        tail = self._tail()
        if tail in {"", "review.html"}:
            client_media = _browser_media(self.media, remote=True)
            self._send_bytes(render_review_html(client_media, "api/review",
                                                can_finalize=self.can_finalize).encode("utf-8"),
                             "text/html; charset=utf-8")
        elif tail and re.fullmatch(r"media/\d+", tail):
            self._send_media(int(tail.split("/", 1)[1]))
        else:
            self.send_error(404)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if self._tail() != "api/review":
            self.send_error(404)
            return
        length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        _atomic_json(self.bundle / "review.json", payload)
        self._send_bytes(b'{"ok":true}', "application/json")

    def log_message(self, _format: str, *_args: object) -> None:
        return


def _handler_factory(bundle: Path, media: list[dict[str, str]], token: str,
                     can_finalize: bool = False):
    class Bound(_MediaReviewHandler):
        pass
    Bound.bundle, Bound.media, Bound.token = bundle, media, token
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
        return {"status": "INACTIVE", "session": str(session_path)}
    session = json.loads(session_path.read_text(encoding="utf-8"))
    server_alive = _pid_alive(int(session.get("server_pid", 0)))
    tunnel_alive = _pid_alive(int(session.get("tunnel_pid", 0)))
    session.update(server_alive=server_alive, tunnel_alive=tunnel_alive,
                   status="ACTIVE" if server_alive and tunnel_alive else "INACTIVE")
    return session


def stop_remote(bundle_dir: str | Path) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    session_path = bundle / "remote_session.json"
    if not session_path.is_file():
        return {"status": "INACTIVE", "session": str(session_path)}
    session = json.loads(session_path.read_text(encoding="utf-8"))
    stopped = []
    for key in ("tunnel_pid", "server_pid"):
        pid = int(session.get(key, 0))
        if _terminate_pid(pid):
            stopped.append(pid)
    session.update(status="STOPPED", stopped_pids=stopped,
                   stopped_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    _atomic_json(session_path, session)
    return session


def start_remote_background(bundle_dir: str | Path, port: int = 0,
                            cloudflared: str = "", startup_timeout: float = 45.0) -> dict[str, Any]:
    """Start a detached review daemon that survives the launching Codex shell."""
    bundle = Path(bundle_dir).resolve()
    manifest_path = bundle / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError("review manifest is missing: %s" % manifest_path)
    current = remote_status(bundle)
    if current.get("status") == "ACTIVE":
        return current
    if (bundle / "remote_session.json").is_file():
        stop_remote(bundle)
        (bundle / "remote_session.json").unlink(missing_ok=True)
    command = [sys.executable, str(Path(__file__).resolve()), "remote", str(bundle),
               "--port", str(port)]
    if cloudflared:
        command.extend(("--cloudflared", cloudflared))
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    stdout_path = bundle / "remote_daemon.stdout.log"
    stderr_path = bundle / "remote_daemon.stderr.log"
    stdout = stdout_path.open("a", encoding="utf-8", newline="\n")
    stderr = stderr_path.open("a", encoding="utf-8", newline="\n")
    kwargs: dict[str, Any] = {
        "cwd": str(Path(__file__).resolve().parent), "env": env,
        "stdin": subprocess.DEVNULL, "stdout": stdout, "stderr": stderr,
    }
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.CREATE_NO_WINDOW | 0x01000000 |
                                     subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        kwargs["start_new_session"] = True
    try:
        process = subprocess.Popen(command, **kwargs)
    finally:
        stdout.close(); stderr.close()
    session_path = bundle / "remote_session.json"
    deadline = time.monotonic() + startup_timeout
    while time.monotonic() < deadline:
        if session_path.is_file():
            session = json.loads(session_path.read_text(encoding="utf-8"))
            if int(session.get("server_pid", 0)) == process.pid and session.get("url"):
                return session
        if process.poll() is not None:
            error = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            raise RuntimeError("remote review daemon exited before startup: %s" % error)
        time.sleep(0.25)
    _terminate_pid(process.pid)
    raise TimeoutError("remote review daemon did not start; see %s" % stderr_path)


def verify_remote_review(url: str, *, timeout: float = 12.0,
                         attempts: int = 8, retry_delay: float = 1.0) -> dict[str, Any]:
    """Verify the public review page and byte-range media route before delivery."""
    if not url.lower().startswith("https://"):
        raise ValueError("remote review delivery requires an HTTPS URL")
    media_url = urljoin(url, "media/0")
    last_error = ""
    for attempt in range(1, max(1, attempts) + 1):
        try:
            page = urlopen(Request(url, headers={"User-Agent": "Hao-Mobile-Review-QA/1.0"}),
                           timeout=timeout)
            page_status = int(getattr(page, "status", page.getcode()))
            page_body = page.read(1_000_000).decode("utf-8", errors="replace")
            if page_status != 200 or "Hao 遠端素材審查" not in page_body:
                raise RuntimeError("review page failed identity/status check: %s" % page_status)
            media = urlopen(Request(media_url, headers={
                "Range": "bytes=0-0", "User-Agent": "Hao-Mobile-Review-QA/1.0",
            }), timeout=timeout)
            media_status = int(getattr(media, "status", media.getcode()))
            content_range = str(media.headers.get("Content-Range", ""))
            if media_status != 206 or not content_range.startswith("bytes 0-0/"):
                raise RuntimeError("review media Range check failed: %s %s" %
                                   (media_status, content_range))
            media.read(1)
            return {
                "status": "VERIFIED", "page_status": page_status,
                "media_status": media_status, "content_range": content_range,
                "attempts": attempt,
                "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
        except Exception as exc:  # network readiness is eventually consistent
            last_error = "%s: %s" % (type(exc).__name__, exc)
            if attempt < max(1, attempts):
                time.sleep(max(0.0, retry_delay))
    raise RuntimeError("remote review verification failed after %d attempts: %s" %
                       (max(1, attempts), last_error))


def deliver_remote(source: str | Path, content_id: str, *,
                   quality_json: str | Path | None = None,
                   bundle_dir: str | Path | None = None, port: int = 0,
                   cloudflared: str = "") -> dict[str, Any]:
    """Create, launch and verify the mobile review required for visual delivery."""
    bundle_result = create_bundle(source, content_id, quality_json, bundle_dir)
    bundle = Path(bundle_result["bundle"])
    if remote_status(bundle).get("status") == "ACTIVE":
        stop_remote(bundle)
    try:
        session = start_remote_background(bundle, port, cloudflared)
        verification = verify_remote_review(str(session["url"]))
    except Exception:
        stop_remote(bundle)
        raise
    result = {
        "status": "READY_FOR_MOBILE_REVIEW",
        "content_id": content_id,
        "url": session["url"],
        "bundle": str(bundle),
        "media_count": bundle_result["media_count"],
        "verification": verification,
        "temporary_public_url": True,
        "computer_must_remain_online": True,
    }
    _atomic_json(bundle / "remote_delivery.json", result)
    return result


def serve_remote(bundle_dir: str | Path, port: int = 0, cloudflared: str = "",
                 startup_timeout: float = 30.0) -> None:
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    missing = [item["path"] for item in media if not Path(item["path"]).is_file()]
    if missing:
        raise FileNotFoundError("review media is missing: %s" % missing[0])
    binary = _find_cloudflared(cloudflared)
    token = secrets.token_urlsafe(24)
    can_finalize = bool(manifest.get("quality_json") and len(media) == 1 and
                        media[0]["kind"] == "video")
    server = ThreadingHTTPServer(("127.0.0.1", port),
                                 _handler_factory(bundle, media, token, can_finalize))
    local_port = int(server.server_address[1])
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    command = [str(binary), "tunnel", "--url", "http://127.0.0.1:%d" % local_port,
               "--no-autoupdate", "--loglevel", "info"]
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               text=True, encoding="utf-8", errors="replace",
                               creationflags=flags)
    lines: queue.Queue[str] = queue.Queue()
    log_path = bundle / "remote_tunnel.log"

    def pump() -> None:
        assert process.stdout is not None
        with log_path.open("w", encoding="utf-8", newline="\n") as log:
            for line in process.stdout:
                log.write(line); log.flush(); lines.put(line)

    threading.Thread(target=pump, daemon=True).start()
    deadline, public_base = time.monotonic() + startup_timeout, ""
    try:
        while time.monotonic() < deadline and process.poll() is None:
            try:
                line = lines.get(timeout=0.25)
            except queue.Empty:
                continue
            match = re.search(r"https://[-a-z0-9]+\.trycloudflare\.com", line, re.I)
            if match:
                public_base = match.group(0)
                break
        if not public_base:
            raise RuntimeError("cloudflared did not produce a Quick Tunnel URL; see %s" % log_path)
        url = "%s/%s/review.html" % (public_base, token)
        session = {
            "schema_version": 1, "status": "ACTIVE", "url": url,
            "server_pid": os.getpid(), "tunnel_pid": process.pid, "port": local_port,
            "source": manifest.get("source") or manifest.get("video", ""),
            "media_count": len(media), "media_kinds": sorted({item["kind"] for item in media}),
            "video": manifest.get("video", ""),
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "access": "temporary_public_url_with_secret_path",
        }
        _atomic_json(bundle / "remote_session.json", session)
        print("REMOTE_REVIEW_URL=" + url, flush=True)
        print("此連結是臨時公開入口；秘密路徑不可轉傳，審完請執行 remote-stop。", flush=True)
        while process.poll() is None:
            time.sleep(0.5)
        raise RuntimeError("cloudflared stopped unexpectedly; see %s" % log_path)
    finally:
        server.shutdown(); server.server_close()
        if process.poll() is None:
            process.terminate()


def serve(bundle_dir: str | Path, port: int = 8765) -> None:
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    media = _manifest_media(manifest)
    can_finalize = bool(manifest.get("quality_json") and len(media) == 1 and
                        media[0]["kind"] == "video")
    host = socket.gethostbyname(socket.gethostname())
    print("手機同 Wi-Fi 開啟：http://%s:%d/review.html" % (host, port))
    ThreadingHTTPServer(("0.0.0.0", port),
                        _handler_factory(bundle, media, "", can_finalize)).serve_forever()


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="review-loop-") as temp:
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
        token = "test-token"
        manifest = json.loads((Path(bundle["bundle"]) / "manifest.json").read_text(encoding="utf-8"))
        media = _manifest_media(manifest)
        server = ThreadingHTTPServer(("127.0.0.1", 0),
                                     _handler_factory(Path(bundle["bundle"]), media, token))
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        base = "http://127.0.0.1:%d/%s" % (server.server_address[1], token)
        try:
            page = urlopen(base + "/review.html", timeout=3).read().decode("utf-8")
            assert "media/0" in page and "media/1" in page
            response = urlopen(Request(base + "/media/0", headers={"Range": "bytes=2-5"}), timeout=3)
            assert response.status == 206 and response.read() == b"2345"
            assert urlopen(base + "/media/1", timeout=3).read() == b"fake-png"
            payload = json.dumps({"issues": [], "decisions": {"m1": "approved"}}).encode("utf-8")
            posted = urlopen(Request(base + "/api/review", data=payload,
                                     headers={"Content-Type": "application/json"}), timeout=3)
            assert posted.status == 200 and (Path(bundle["bundle"]) / "review.json").is_file()
            original_urlopen = globals()["urlopen"]
            globals()["urlopen"] = lambda request, timeout=0: original_urlopen(
                Request(str(getattr(request, "full_url", request)).replace(
                    "https://local.test", base),
                    headers=dict(getattr(request, "headers", {}))), timeout=timeout)
            try:
                verified = verify_remote_review("https://local.test/review.html", attempts=1)
                assert verified["page_status"] == 200 and verified["media_status"] == 206
            finally:
                globals()["urlopen"] = original_urlopen
        finally:
            server.shutdown(); server.server_close()
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
        serve_remote(args.bundle, args.port, args.cloudflared); return 0
    if args.command == "remote-start":
        print(json.dumps(start_remote_background(args.bundle, args.port, args.cloudflared),
                         ensure_ascii=False, indent=2)); return 0
    if args.command == "deliver":
        print(json.dumps(deliver_remote(
            args.source, args.content_id, quality_json=args.quality_json or None,
            bundle_dir=args.bundle_dir or None, port=args.port,
            cloudflared=args.cloudflared,
        ), ensure_ascii=False, indent=2)); return 0
    if args.command == "remote-status":
        print(json.dumps(remote_status(args.bundle), ensure_ascii=False, indent=2)); return 0
    if args.command == "remote-stop":
        print(json.dumps(stop_remote(args.bundle), ensure_ascii=False, indent=2)); return 0
    if args.command == "finalize":
        print(json.dumps(finalize(args.bundle, learn=not args.no_learn), ensure_ascii=False, indent=2)); return 0
    self_test(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
