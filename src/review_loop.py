# -*- coding: utf-8 -*-
"""Hao-owned timestamp review bundle and one-click feedback ingestion.

The reviewer is Hao.  A phone or desktop browser is only an access device and
never changes who owns the aesthetic decision.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import tempfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from knowledge_lifecycle import record_feedback
from aesthetic_score import review_schema
from quality_95 import apply_human_review, write_report


HTML = r'''<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Hao 人工審片</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif}body{margin:0;background:#090b10;color:#f7f7fb}
main{max-width:820px;margin:auto;padding:12px 12px 80px}video{width:100%;max-height:68vh;background:#000;border-radius:14px}
.card{background:#151924;border:1px solid #2a3041;border-radius:14px;padding:14px;margin-top:12px}
.time{font-size:26px;font-weight:800;color:#8dff54}.row{display:flex;gap:8px;flex-wrap:wrap}
button,select,input,textarea{font:inherit;border-radius:10px;border:1px solid #394158;background:#0e121c;color:#fff;padding:11px}
button{background:#2358ff;font-weight:800}textarea{width:100%;box-sizing:border-box;min-height:82px;margin-top:8px}
label{display:block;margin:9px 0 4px;color:#aeb7cb}small{display:block;color:#77839b;margin-top:3px;line-height:1.35}.rating{display:grid;grid-template-columns:1fr 76px;gap:8px;align-items:center}
#saved{color:#8dff54;min-height:24px}.issue{border-top:1px solid #2a3041;padding:8px 0}</style></head><body><main>
<video id="v" controls playsinline src="../current.mp4"></video>
<section class="card"><div class="time" id="clock">00:00.00</div><div class="row">
<button id="mark">標記現在時間</button><select id="category">
<option value="rhythm">節奏／拖沓</option><option value="weird_transition">怪轉場</option>
<option value="text_cut">文字被切／難讀</option><option value="generic_card">空白模板卡</option>
<option value="grid_opener">錯用網格開場</option><option value="template_label">模板角色字外露</option>
<option value="repetition">重複／疲勞</option><option value="style_mismatch">題材風格不合</option>
<option value="overdesigned">過度設計／焦點太多</option><option value="reference_copy">太像參考圖</option>
<option value="other">其他</option></select></div>
<textarea id="comment" placeholder="這一秒哪裡不好？怎麼改？"></textarea><button id="add">加入問題</button><div id="saved"></div></section>
<section class="card"><h3>Hao 美感十維（1–5 分）</h3><div id="ratings"></div><button id="submit">送出審片</button></section>
<section class="card"><h3>問題時間碼</h3><div id="issues"></div></section>
</main><script>
const v=document.querySelector('#v'), key='hao-review-'+location.pathname;
let data=JSON.parse(localStorage.getItem(key)||'{"issues":[],"ratings":{}}'), marked=0;
const dims=__AESTHETIC_DIMENSIONS__;
function fmt(t){let m=Math.floor(t/60),s=t-m*60;return String(m).padStart(2,'0')+':'+s.toFixed(2).padStart(5,'0')}
function save(){localStorage.setItem(key,JSON.stringify(data));render()}
function render(){issues.innerHTML=data.issues.map((x,i)=>`<div class="issue"><b>${fmt(x.time)} · ${x.category}</b><br>${x.comment}<br><button onclick="data.issues.splice(${i},1);save()">刪除</button></div>`).join('')||'尚無問題';}
ratings.innerHTML=Object.entries(dims).map(([k,n])=>`<div class="rating"><label>${n.label_zh}<small>${n.question}</small></label><input id="r-${k}" type="number" min="1" max="5" step="0.5" value="${data.ratings[k]||5}"></div>`).join('');
setInterval(()=>clock.textContent=fmt(v.currentTime),100);mark.onclick=()=>{marked=v.currentTime;clock.textContent=fmt(marked)};
add.onclick=()=>{let c=comment.value.trim();if(!c)return;saved.textContent='已加入 '+fmt(marked||v.currentTime);data.issues.push({time:marked||v.currentTime,category:category.value,comment:c});comment.value='';save()};
submit.onclick=async()=>{for(const k of Object.keys(dims))data.ratings[k]=Number(document.querySelector('#r-'+k).value);data.completed_at=new Date().toISOString();
let res=await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});saved.textContent=res.ok?'已送出，可回 Codex 執行 finalize':'送出失敗';save()};render();
</script></body></html>'''.replace(
    "__AESTHETIC_DIMENSIONS__",
    json.dumps(review_schema("shorts")["dimensions"], ensure_ascii=False),
)


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


def create_bundle(video: str | Path, content_id: str,
                  quality_json: str | Path | None = None) -> dict[str, str]:
    video = Path(video).resolve()
    bundle = video.parent / "_review"
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "review.html").write_text(HTML, encoding="utf-8")
    manifest = {"schema_version": 1, "content_id": content_id, "video": str(video),
                "quality_json": str(Path(quality_json).resolve()) if quality_json else "",
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _atomic_json(bundle / "manifest.json", manifest)
    return {"bundle": str(bundle), "page": str(bundle / "review.html"),
            "serve_command": "python review_loop.py serve %s" % json.dumps(str(bundle))}


def finalize(bundle_dir: str | Path, *, learn: bool = True) -> dict[str, Any]:
    bundle = Path(bundle_dir).resolve()
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    review = json.loads((bundle / "review.json").read_text(encoding="utf-8"))
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


class _ReviewHandler(SimpleHTTPRequestHandler):
    bundle: Path

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/review":
            self.send_error(404)
            return
        length = min(int(self.headers.get("Content-Length", "0")), 1_000_000)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self.send_error(400)
            return
        _atomic_json(self.bundle / "review.json", payload)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


def serve(bundle_dir: str | Path, port: int = 8765) -> None:
    bundle = Path(bundle_dir).resolve()
    root = bundle.parent
    class Bound(_ReviewHandler):
        pass
    Bound.bundle = bundle
    def factory(*args, **kwargs):
        return Bound(*args, directory=str(root), **kwargs)
    host = socket.gethostbyname(socket.gethostname())
    print("手機同 Wi-Fi 開啟：http://%s:%d/_review/review.html" % (host, port))
    ThreadingHTTPServer(("0.0.0.0", port), factory).serve_forever()


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="review-loop-") as temp:
        video = Path(temp) / "current.mp4"
        video.write_bytes(b"test")
        bundle = create_bundle(video, "demo")
        assert Path(bundle["page"]).is_file()
        assert "時間碼" in Path(bundle["page"]).read_text(encoding="utf-8")
    print("review_loop self-test GREEN")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create")
    create.add_argument("video"); create.add_argument("--content-id", required=True)
    create.add_argument("--quality-json", default="")
    server = sub.add_parser("serve"); server.add_argument("bundle"); server.add_argument("--port", type=int, default=8765)
    final = sub.add_parser("finalize"); final.add_argument("bundle"); final.add_argument("--no-learn", action="store_true")
    sub.add_parser("selftest")
    args = parser.parse_args(argv)
    if args.command == "create":
        print(json.dumps(create_bundle(args.video, args.content_id, args.quality_json or None), ensure_ascii=False, indent=2)); return 0
    if args.command == "serve":
        serve(args.bundle, args.port); return 0
    if args.command == "finalize":
        print(json.dumps(finalize(args.bundle, learn=not args.no_learn), ensure_ascii=False, indent=2)); return 0
    self_test(); return 0


if __name__ == "__main__":
    raise SystemExit(main())
