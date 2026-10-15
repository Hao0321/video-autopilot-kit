from __future__ import annotations
import base64
import hashlib
import json
import re
from aesthetic_score import review_schema

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
