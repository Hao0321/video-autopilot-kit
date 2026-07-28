# -*- coding: utf-8 -*-
"""interview_autopilot.py — 線上訪談節目一鍵流程（訪前企劃 → 錄製 → 訪後）

你的操作只有三次「複製貼上」，其餘全自動：

    步驟1  python src/interview_autopilot.py invite 01 --name "小明" --hint "用 X 方法做到 Y"
           → 產出 邀約訊息（三種關係溫度，直接複製貼給對方）＋ 來賓資訊表
           ↳ 你：挑一則貼給對方（第 1 次貼上）

    步驟2  把對方回填的資訊貼給你的 AI 助手 → 填 <ep>/_guest.py
           → python src/interview_autopilot.py plan 01 [--compliance-ok]
           → 過 interview_gate（來賓資料）＋ plan_gate（選題與包裝先行）
           → 產出 7 件套：主持台本(照唸)/訪綱/準備包/授權書/checklist/發布套件/Shorts 切條
           → 自動排程進 channel_tracker（pre-call / 錄製日 / 發布日 ＋ D2/D7/D28 快照）
           ↳ 你：把「準備包＋授權書」貼給對方（第 2 次貼上）

    步驟3  錄製當天：開著 host_script.md 照唸
           錄完丟素材 → python src/interview_autopilot.py build 01
           ↳ 你：發布日把「來賓分享文」貼給對方（第 3 次貼上）

SoT 分工（骨架在 code、文案在 templates）：
    templates/interview/*.template.md  = 所有交付檔的**唯一內容來源**，本檔只做 `((欄位))`
                                         替換（render()）—— 改話術改模板，不要改程式。
    profiles/show.md                   = 節目名/主持人/頻道/社群連結/平台清單/片尾招牌句
                                         （模板：templates/show_profile.template.md）。
                                         沒填 → 產出檔留 `{你的…}` 佔位字樣，看到就知道要補。
    interview_gate.py                  = 來賓資料機械閘門
    longform_maker/plan_gate.py        = 選題/包裝機械閘門
    channel_tracker.py                 = 排程狀態機
    knowledge/interview-show-playbook.md = 格式知識（beat 結構/錄製規格/剪輯規則）

⚠️ 合規章只能由人蓋：`plan` 預設寫「合規：待複核」→ 被 plan_gate P4 擋下；跑過平台 AI 內容
政策 checklist 後才 `--compliance-ok` 人工簽章。理由見 `_packaging_block()` docstring。

路徑：預設寫進 <PROJECT_ROOT>/videos/_planning/interview_EP{N}_{slug}/（**全 ASCII 目錄名**，
非中文 locale 也不會出事）。用環境變數覆寫：VIDEO_KIT_PROJECT_ROOT / VIDEO_KIT_PLAN_ROOT /
VIDEO_KIT_INBOX。
cp950 安全：console 純 ASCII 標記＋中文（無 emoji）；I/O 一律 utf-8。
"""
from __future__ import annotations

import argparse
import glob
import io
import os
import re
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))          # src/
ROOT = os.path.dirname(HERE)                                # repo root
for _p in (HERE, os.path.join(HERE, "longform_maker")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

TPL_DIR = os.path.join(ROOT, "templates", "interview")
PROFILE_PATH = os.path.join(ROOT, "profiles", "show.md")

PROJECT_ROOT = os.environ.get("VIDEO_KIT_PROJECT_ROOT") or ROOT
PLAN_ROOT = os.environ.get("VIDEO_KIT_PLAN_ROOT") or \
    os.path.join(PROJECT_ROOT, "videos", "_planning")
INBOX = os.environ.get("VIDEO_KIT_INBOX") or \
    os.path.join(PROJECT_ROOT, "videos", "_INBOX", "landscape-longform")

try:
    from plan_gate import gate_plan
except ImportError:                                   # noqa: BLE001
    gate_plan = None

try:
    import channel_tracker
except ImportError:                                   # noqa: BLE001
    channel_tracker = None

_PH_RE = re.compile(r"\(\(([^()]+)\)\)")
_HOST_ONLY_RE = re.compile(r"<!--\s*HOST-ONLY\s*-->.*?<!--\s*/HOST-ONLY\s*-->\s*",
                           re.DOTALL)


try:
    from av_util import write_text as _w      # 共用寫檔（建目錄 + utf-8 + 印產出）
except ImportError:                           # 單檔複製出去也要能跑
    def _w(path: str, text: str, announce: bool = True) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(text)
        if announce:
            print("   -> " + os.path.basename(path))
        return path


try:
    from gate_core import raise_if_failed as _raise_if_failed
except ImportError:                                   # 單檔複製出去也要能跑
    def _raise_if_failed(rep: dict, label: str, title: str) -> None:
        if rep.get("fails"):
            raise AssertionError("[%s] %s:\n  - %s"
                                 % (label, title, "\n  - ".join(rep["fails"])))


# ───────────────────────────────────────────── 節目 profile（profiles/show.md）

PROFILE_DEFAULTS = {
    "SHOW_NAME":     "{你的節目名}",
    "HOST_NAME":     "{你的名字}",
    "CHANNEL":       "{你的頻道}",
    "COMMUNITY_URL": "{你的社群連結}",
    "CLUSTER":       "{你的cluster關鍵字}",
    "PLATFORMS":     "{你發布的平台}",
    "OUTRO_LINES":   "{你的片尾招牌句}",
}
_HEAD_RE = re.compile(r"^#{1,6}[ \t]*([A-Z][A-Z0-9_]{2,})[ \t]*$", re.M)
_KV_RE = re.compile(r"^[-*\s]{0,4}([A-Z][A-Z0-9_]{2,})[:：][ \t]*(.*)$", re.M)
_FENCE_RE = re.compile(r"^```[^\n]*\n(.*?)^```", re.M | re.S)
_PROFILE_CACHE = {}


def _filled(v: str) -> bool:
    """`______` / 空字串 / 只剩反引號 = 使用者還沒填。"""
    v = (v or "").strip().strip("`").strip()
    return bool(v) and not re.fullmatch(r"[_＿\s]+", v)


def _parse_profile(text: str) -> dict:
    out = {}
    for m in _HEAD_RE.finditer(text):                 # 多行欄位：## KEY + ``` 區塊
        seg = text[m.end():]
        nxt = _HEAD_RE.search(seg)
        if nxt:
            seg = seg[:nxt.start()]
        fm = _FENCE_RE.search(seg)
        if fm and _filled(fm.group(1)):
            out[m.group(1)] = fm.group(1).strip()
    for m in _KV_RE.finditer(text):                   # 單行欄位：KEY: 值
        if _filled(m.group(2)):
            out.setdefault(m.group(1), m.group(2).strip().strip("`").strip())
    return out


def show_profile(path: str = None) -> dict:
    """讀 profiles/show.md；沒有或沒填的欄位 → `{你的…}` 佔位字樣（不靜默用假資料）。"""
    p = path or PROFILE_PATH
    if p in _PROFILE_CACHE:
        return dict(_PROFILE_CACHE[p])
    vals = dict(PROFILE_DEFAULTS)
    if os.path.isfile(p):
        vals.update({k: v for k, v in _parse_profile(
            io.open(p, encoding="utf-8").read()).items() if k in PROFILE_DEFAULTS})
    else:
        print("   WARN 沒有 %s（複製 templates/show_profile.template.md 過去填）"
              % os.path.relpath(p, ROOT).replace("\\", "/"))
    missing = [k for k, v in vals.items() if v == PROFILE_DEFAULTS[k]]
    if missing:
        print("   WARN 節目 profile 未填：%s → 產出檔會留 {你的…} 字樣，交出去前記得補"
              % ", ".join(missing))
    _PROFILE_CACHE[p] = dict(vals)
    return vals


# ───────────────────────────────────────────── 模板渲染（templates/ = SoT）

def render(template_name: str, drop_marks=(), **fields) -> str:
    """讀 templates/interview/<name>.template.md → 去 HOST-ONLY → 丟 drop_marks 行 → 填 ((欄位))。

    佔位符用 `((欄位))` 而非 `{欄位}`：markdown 內大括號太常見（程式碼/JSON 範例），
    雙圓括號不會撞到。未填的欄位一律 raise —— 寧可擋住也不要交出帶 `(( ))` 的檔案。
    """
    base = template_name[:-3] if template_name.endswith(".md") else template_name
    if not base.endswith(".template"):
        base += ".template"
    path = os.path.join(TPL_DIR, base + ".md")
    assert os.path.exists(path), "找不到模板（templates/interview/ 是唯一 SoT）：" + path
    text = io.open(path, encoding="utf-8").read()

    text = _HOST_ONLY_RE.sub("", text)
    if drop_marks:
        text = "\n".join(ln for ln in text.splitlines()
                         if not any(m in ln for m in drop_marks))
    text = _PH_RE.sub(lambda m: str(fields.get(m.group(1).strip(), m.group(0))), text)

    left = sorted(set(_PH_RE.findall(text)))
    assert not left, "%s 有未填欄位：%s" % (os.path.basename(path), "、".join(left))
    return re.sub(r"\n{3,}", "\n\n", text).lstrip("\n")


def _slug(name: str) -> str:
    """來賓名 → **ASCII** 資料夾片段（非拉丁字元一律丟掉，非中文 locale 才不會出事）。"""
    return re.sub(r"[^A-Za-z0-9_-]+", "-", str(name or "")).strip("-")[:32]


def ep_dir(ep: str, name: str = None) -> str:
    """`interview_EP{N}[_{slug}]/`。plan/build 不帶 name → 找 invite 當初建好的那個。"""
    if name is not None:
        s = _slug(name)
        return os.path.join(PLAN_ROOT, "interview_EP%s_%s" % (ep, s) if s
                            else "interview_EP%s" % ep)
    hits = sorted(glob.glob(os.path.join(PLAN_ROOT, "interview_EP%s_*" % ep)))
    if hits:
        return hits[0]
    return os.path.join(PLAN_ROOT, "interview_EP%s" % ep)


# ───────────────────────────────────────────── 步驟1：invite

_GUEST_STUB = '''# -*- coding: utf-8 -*-
"""EP%s 來賓資料 —— 依對方回覆填寫（AI 助手可代填，你只要看過）。
每個數字都要有來源；沒截圖的標「待來賓提供」。沒有可驗證成就 = interview_gate 直接擋。"""

GUEST = dict(
    ep="%s",
    name="%s",
    one_line="TODO 一句話成就（他做到的那件事）",
    achievements=[
        # ("數字/成果", "來源：來賓自報 or 公開頁面 or 已提供截圖")
    ],
    links=[],                 # 作品/頻道/repo
    start_state="TODO 開始前的狀態（本來會什麼/不會什麼）",
    struggle="TODO 最卡的一次",
    demo="TODO 可現場示範的東西",
    audience="TODO 他的受眾在哪（發布日同步分享用）",
    on_camera=None,           # True/False/None=尊重對方
    screenshots_ok=[],        # 同意上鏡的數據截圖清單（會寫進授權書第 3 條）
)
'''


def build_invite(ep: str, name: str, hint: str = "", prof: dict = None) -> str:
    """純函式：產邀約包內容（三種關係溫度 + 來賓資訊表）。"""
    p = prof or show_profile()
    return render(
        "invite_pack",
        EP=ep, 來賓名=name,
        節目名=p["SHOW_NAME"], 主持人=p["HOST_NAME"], 頻道=p["CHANNEL"],
        亮點句=("（我看到你%s，覺得這個過程很多人會想知道）" % hint) if hint else "",
        來賓資訊表=render("guest_intake"),
    )


def invite(ep: str, name: str, hint: str = "") -> str:
    d = ep_dir(ep, name)
    _w(os.path.join(d, "EP%s_invite_pack.md" % ep), build_invite(ep, name, hint))
    gp = os.path.join(d, "_guest.py")
    if not os.path.exists(gp):
        _w(gp, _GUEST_STUB % (ep, ep, name))
    print("[invite] EP%s 邀約包完成 -> %s" % (ep, d))
    return d


# ───────────────────────────────────────────── 包裝先行（plan_gate 的輸入）

_COMPLIANCE_SIGNED = (
    "- 合規：通過（人工複核完成：真人對談無深偽合成／來賓數據走真後台截圖／"
    "授權書載明可上鏡項目）")
_COMPLIANCE_UNSIGNED = (
    "- 合規：待複核 ← **人工簽章欄，程式不代簽**。去跑一遍平台 AI 內容政策 checklist"
    "（深偽三不／擬真內容必揭露／每支要有原創貢獻），確認：真人對談無深偽合成、"
    "來賓數據走真後台截圖（meta-lessons M107）、授權書載明可上鏡項目，"
    "然後 `python src/interview_autopilot.py plan %s --compliance-ok` 重跑")


def _packaging_block(ep, one, start, top, demo, cluster, compliance_ok=False) -> str:
    """8 組「標題 | 縮圖」候選 ＋ 框架/機器/cluster/合規標記（plan_gate P1-P5 的輸入）。

    標題一律走**來賓成就框架**（不用「專訪 XXX」，人名對陌生人是零資訊）。

    ⚠️ `compliance_ok`：**合規章只能由人蓋**。預設 False → 寫「合規：待複核」→ plan_gate P4
    直接擋下，訊息告訴你去跑 AI 內容政策 checklist，複核完再 `plan <ep> --compliance-ok`
    重跑。若程式自動寫「合規：通過」＝**機器自己滿足自己的合規閘門＝假綠**，那道 gate 就
    等於不存在。訪談片牽涉他人的肖像與聲音，這一章尤其不能自動蓋。
    """
    return render(
        "packaging",
        一句話成就=one, 起點狀態=start, 核心數據=top, 示範項目=demo,
        cluster關鍵字=cluster,
        合規行=(_COMPLIANCE_SIGNED if compliance_ok else _COMPLIANCE_UNSIGNED % ep),
    )


# ───────────────────────────────────────────── 步驟2：plan

def build_docs(ep: str, g: dict, rec_d: str, pub_d: str, packaging: str,
               prof: dict = None) -> dict:
    """純函式：來賓資料 → {檔名: 內容}（7 件套）。plan() 只負責寫檔與排程。

    檔名全 ASCII；內容全部來自 templates/interview/（本函式只組欄位，不寫文案）。
    """
    p = prof or show_profile()
    achv = g.get("achievements") or []
    shots = g.get("screenshots_ok") or []
    links = g.get("links") or []
    f = dict(
        EP=ep,
        來賓名=g["name"],
        一句話成就=g["one_line"],
        起點狀態=g["start_state"],
        示範項目=g["demo"],
        核心數據=(achv[0][0] if achv else g["one_line"]),
        錄製日期=rec_d,
        發布日=pub_d,
        截圖清單="\n".join("・%s" % s for s in shots) or "・（待確認要秀哪些數據畫面）",
        截圖清單縮排="\n".join("   ・%s" % s for s in shots) or "   ・（待確認）",
        包裝候選段=packaging,
        來賓連結清單="\n".join("・%s" % x for x in links) or "・（來賓連結待補）",
        來賓首要連結=(links[0] if links else "（待補）"),
        來賓受眾=(g.get("audience") or "（來賓受眾未填）"),
        節目名=p["SHOW_NAME"], 主持人=p["HOST_NAME"], 頻道=p["CHANNEL"],
        社群連結=p["COMMUNITY_URL"], 平台清單=p["PLATFORMS"],
        片尾招牌句=p["OUTRO_LINES"],
    )
    return {
        "EP%s_host_script.md" % ep:          render("host_script", **f),
        # 發來賓的版本：拿掉 ⚡ 追問陷阱（來賓拿到方向，不是逐字稿）
        "EP%s_outline_for_guest.md" % ep:    render("interview_outline",
                                                    drop_marks=("⚡",), **f),
        "EP%s_guest_prep_kit.md" % ep:       render("guest_prep_kit", **f),
        "EP%s_consent_form.md" % ep:         render("consent_form", **f),
        "EP%s_recording_checklist.md" % ep:  render("recording_checklist", **f),
        "EP%s_publish_kit.md" % ep:          render("publish_kit", **f),
        "EP%s_shorts_cuts.md" % ep:          render("shorts_cuts", **f),
    }


def plan(ep: str, record: str = None, publish: str = None,
         compliance_ok: bool = False) -> str:
    """讀 _guest.py → 過雙閘門 → 產 7 件套 → 排程。主持台本是重點：錄製當天照唸。"""
    from interview_gate import assert_guest

    d = ep_dir(ep)
    gp = os.path.join(d, "_guest.py")
    assert os.path.exists(gp), "還沒有 _guest.py，先跑 invite：" + gp

    import importlib.util
    m = importlib.util.spec_from_file_location("guest_%s" % ep, gp)
    mod = importlib.util.module_from_spec(m)
    _bc, sys.dont_write_bytecode = sys.dont_write_bytecode, True   # 別在企劃目錄留 __pycache__
    try:
        m.loader.exec_module(mod)
    finally:
        sys.dont_write_bytecode = _bc
    g = mod.GUEST
    assert_guest(g)                      # ← 閘門①：缺料/無來源數字直接擋

    prof = show_profile()
    name = g["name"]
    want = ep_dir(ep, name)
    if os.path.normcase(want) != os.path.normcase(d):
        print("   WARN 目錄名是 %s；依來賓名應為 %s（要不要改名你決定，套件仍寫進現有目錄）"
              % (os.path.basename(d), os.path.basename(want)))

    rec_d, pub_d = _dates(record, publish)
    achv = g.get("achievements") or []
    packaging = _packaging_block(
        ep, g["one_line"], g["start_state"],
        achv[0][0] if achv else g["one_line"], g["demo"],
        prof["CLUSTER"], compliance_ok=compliance_ok)

    # ── 閘門②：包裝先行（plan_gate P1-P5）—— 包不出 8 組/合規沒人簽 就不准往下產套件
    if gate_plan is None:
        print("   SKIP plan_gate 不在（longform_maker/plan_gate.py 找不到）→ 包裝先行未機械驗證")
    else:
        _ok, rep = gate_plan(packaging)
        _raise_if_failed(rep, "EP%s %s" % (ep, name), "規劃 gate FAIL（plan_gate）")
        for w in rep["warns"]:
            print("   WARN " + w)
        print("[plan] plan_gate PASS（包裝候選 %d 組）" % rep["pairs"])

    for fname, text in build_docs(ep, g, rec_d, pub_d, packaging, prof).items():
        _w(os.path.join(d, fname), text)

    _schedule(ep, name, rec_d, pub_d)
    print("[plan] EP%s 7 件套完成 -> %s" % (ep, d))
    return d


def _dates(record: str = None, publish: str = None):
    """沒指定就給預設節奏：錄製 = 今天+7、發布 = 錄製+7（可用 --record/--publish 覆寫）。"""
    rec = date.fromisoformat(record) if record else date.today() + timedelta(days=7)
    pub = date.fromisoformat(publish) if publish else rec + timedelta(days=7)
    return rec.isoformat(), pub.isoformat()


def _schedule(ep: str, name: str, record: str, publish: str) -> bool:
    """排程進 channel_tracker：發布日 D2/D7/D28 快照 + pre-call/錄製日/發布日待辦。"""
    if channel_tracker is None:
        print("   SKIP 找不到 channel_tracker → 排程請手動（pre-call %s / 發布 %s）"
              % (record, publish))
        return False
    try:
        st = channel_tracker.load_state()
    except (IOError, OSError, ValueError) as e:       # 沒有 channel_state.json 也不該炸
        print("   SKIP 讀不到 channel_state.json（%s）→ 先複製 "
              "examples/channel_state.example.json 到 repo root，再重跑 plan" % type(e).__name__)
        return False

    vname = "訪談 EP%s %s" % (ep, name)
    cur = next((v for v in st["videos"] if v["name"] == vname), None)
    if cur is None:
        channel_tracker.add_video(st, vname, "", publish, "訪談", machine="推薦")
        vstate = "新排"
    elif cur["published"] != publish and not any(
            s["done_on"] for s in cur["snapshots"].values()):
        # 發布日改了且還沒開始快照 → 整筆重排（已做過的快照不動，避免蓋掉真實紀錄）
        st["videos"].remove(cur)
        channel_tracker.add_video(st, vname, cur.get("video_id", ""), publish,
                                  "訪談", machine="推薦")
        vstate = "改期重排"
    else:
        vstate = "已存在（沿用 %s）" % cur["published"]
        publish = cur["published"]

    todo = [
        ("me", "EP%s 訪前 15 分鐘 pre-call（挖亮點/確認可上鏡數據/對時間）" % ep, record),
        ("me", "EP%s 錄製日：開主持台本照唸（來賓 %s）" % (ep, name), record),
        ("me", "EP%s 發布日把「來賓分享文」貼給 %s（外部點火）" % (ep, name), publish),
        ("ai", "EP%s 初剪給來賓審看（爭議段落來賓有否決權）" % ep, None),
    ]
    have = {a["item"]: a for a in st["pending_actions"]}
    added = moved = 0
    for owner, item, due in todo:
        cur_a = have.get(item)
        if cur_a is None:
            channel_tracker.add_action(st, owner, item, due=due)
            added += 1
        elif not cur_a["done"] and cur_a.get("due") != due:
            cur_a["due"] = due                 # 改期重跑 plan → 待辦跟著挪
            moved += 1
    channel_tracker.save_state(st)
    print("[plan] channel_tracker：%s 發布日 %s（D2/D7/D28）%s＋待辦 +%d 改期 %d"
          % (vname, publish, vstate, added, moved))
    return True


# ───────────────────────────────────────────── 步驟3：build

def build(ep: str):
    """訪後：素材盤點（實際剪輯走 longform pipeline，本函式只把下一步列清楚）。"""
    d = ep_dir(ep)
    raw = os.path.join(INBOX, "interview_EP%s" % ep)
    print("[build] 企劃目錄：%s" % d)
    print("[build] 素材目錄：%s" % raw)
    if not os.path.isdir(raw):
        print("   WARN 尚無素材。請把分軌檔放進：%s" % raw)
        print("     命名建議：host.wav / guest.wav / guest_screen.mp4")
        return raw
    files = sorted(os.listdir(raw))
    print("   找到 %d 個檔：%s" % (len(files), ", ".join(files[:8])))
    print("   下一步：")
    print("     1. guest_screen.mp4 過 screen_clean + 全幀掃描（來賓螢幕=預設有毒，M91）")
    print("     2. host.wav / guest.wav 各自過音訊鏈（壓縮+loudnorm）再混")
    print("     3. word_captions 分軌轉寫 → 講者標記")
    print("     4. delivery_qa 全綠 + 來賓審看初剪 → 才交付")
    return raw


# ───────────────────────────────────────────── self-test（模板↔程式不漂移）

def _selftest() -> int:
    """只驗純函式（render/build_docs/包裝/日期/路徑），不寫任何 _planning 目錄。"""
    from interview_gate import selftest_runner   # 共用 PASS/FAIL 外殼（含 fallback）

    def body(check):
        prof = dict(PROFILE_DEFAULTS)            # 未填 profile 的情境（kit 預設）
        guest = dict(ep="00", name="小明", one_line="兩個月做出上架的 App",
                     achievements=[("下載 5,000", "來賓提供後台截圖")],
                     links=["https://example.com"], start_state="完全不會寫程式",
                     struggle="卡在上架審核", demo="用 AI 生成一個小工具",
                     audience="你的短文平台", screenshots_ok=["後台截圖 下載 5,000"])

        pk_unsigned = _packaging_block("00", guest["one_line"], guest["start_state"],
                                       "下載 5,000", guest["demo"], "示範主題")
        pk = _packaging_block("00", guest["one_line"], guest["start_state"],
                              "下載 5,000", guest["demo"], "示範主題",
                              compliance_ok=True)

        docs = build_docs("00", guest, "2026-01-01", "2026-01-08", pk, prof)
        check("build_docs returns 7 files", len(docs) == 7)
        check("all filenames ascii", all(f.isascii() for f in docs))
        for fname, txt in docs.items():
            check("%s renders fully" % fname, "((" not in txt and len(txt) > 200)
            check("%s drops HOST-ONLY" % fname, "HOST-ONLY" not in txt)
        check("host script fills guest name", "小明" in docs["EP00_host_script.md"])
        check("consent form keeps unfilled profile visible",
              "{你的名字}" in docs["EP00_consent_form.md"]
              and "{你發布的平台}" in docs["EP00_consent_form.md"])
        check("host script uses profile outro",
              "{你的片尾招牌句}" in docs["EP00_host_script.md"])
        check("publish kit embeds packaging block",
              "## 包裝候選" in docs["EP00_publish_kit.md"])

        g_out = docs["EP00_outline_for_guest.md"]
        check("outline guest version strips traps",
              "⚡" not in g_out and "段一" in g_out and "段三" in g_out)
        check("host script keeps traps", "⚡" in docs["EP00_host_script.md"])

        inv = build_invite("00", "小明", "用 AI 做出一個 App", prof)
        check("invite renders 3 versions",
              all(v in inv for v in ("版本 A", "版本 B", "版本 C")) and "((" not in inv)
        check("invite embeds intake sheet", "來賓資訊表" in inv and "一句話怎麼說" in inv)
        check("invite has no hardcoded show identity",
              "{你的節目名}" in inv and "{你的頻道}" in inv)

        try:                                   # 少給欄位一定要擋（不准交出帶 (( )) 的檔）
            render("consent_form", EP="00")
            check("missing field blocked", False)
        except AssertionError:
            check("missing field blocked", True)

        if gate_plan is None:
            print("[SKIP] plan_gate 不在 → 包裝先行未機械驗證（gate 相關 4 項未跑）")
        else:
            ok, rep = gate_plan(pk)
            check("packaging passes plan_gate (human-signed)", ok)
            check("packaging has >=8 pairs", rep["pairs"] >= 8)
            # 合規章只能人蓋：沒 --compliance-ok 一定要被 P4 擋（防機器自簽假綠）
            ok0, rep0 = gate_plan(pk_unsigned)
            check("unsigned compliance -> blocked by plan_gate P4",
                  (not ok0) and any("P4" in f for f in rep0["fails"]))
            check("unsigned text says pending-review, not passed",
                  "待複核" in pk_unsigned and "合規：通過" not in pk_unsigned)
            check("no loser combo warn (W2)",
                  not any(w.startswith("W2") for w in rep["warns"]))

        r, p = _dates(None, None)
        check("default dates: record +7 / publish +14",
              r == (date.today() + timedelta(days=7)).isoformat()
              and p == (date.today() + timedelta(days=14)).isoformat())
        r2, p2 = _dates("2026-03-01", None)
        check("explicit record shifts publish", (r2, p2) == ("2026-03-01", "2026-03-08"))

        check("_slug strips non-ascii", _slug("小 明/測*試 Ming") == "Ming")
        check("ep_dir ascii with latin name",
              ep_dir("07", "Ming").endswith("interview_EP07_Ming"))
        check("ep_dir stays ascii with cjk name",
              ep_dir("07", "小明").endswith("interview_EP07")
              and ep_dir("07", "小明").isascii())

        check("profile parser reads filled values",
              _parse_profile("SHOW_NAME: 我的節目\n## OUTRO_LINES\n```\n下次見\n```\n")
              == {"SHOW_NAME": "我的節目", "OUTRO_LINES": "下次見"})
        check("profile parser ignores blanks",
              _parse_profile("SHOW_NAME: ______\nCHANNEL: `____`\n") == {})

    return selftest_runner(body, width=56)


def main():
    if "--selftest" in sys.argv:
        return _selftest()
    try:  # cp950 終端印到罕見符號不炸
        sys.stdout.reconfigure(errors="replace")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(
        description="線上訪談節目一鍵流程（invite -> plan -> build）")
    ap.add_argument("cmd", choices=["invite", "plan", "build"])
    ap.add_argument("ep")
    ap.add_argument("--name", default="來賓")
    ap.add_argument("--hint", default="", help="你看到他做到什麼（會寫進邀約訊息）")
    ap.add_argument("--record", default=None, help="錄製日 YYYY-MM-DD（預設今天+7）")
    ap.add_argument("--publish", default=None, help="發布日 YYYY-MM-DD（預設錄製日+7）")
    ap.add_argument("--compliance-ok", action="store_true",
                    help="人工簽章：已跑過平台 AI 內容政策 checklist。"
                         "不給這個旗標 = plan_gate P4 擋下（程式不代簽）")
    a = ap.parse_args()
    try:
        if a.cmd == "invite":
            invite(a.ep, a.name, a.hint)
        elif a.cmd == "plan":
            plan(a.ep, a.record, a.publish, compliance_ok=a.compliance_ok)
        else:
            build(a.ep)
    except AssertionError as e:      # 閘門擋下 = 正常結果，不是 crash：印訊息就好
        print("\n[GATE FAIL] %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
