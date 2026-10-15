"""Script rhythm; canonical implementation."""
from __future__ import annotations

import re


if __package__:
    from .script_parsing import _count_chars, _strip_markup, parse_beats
else:
    from script_parsing import _count_chars, _strip_markup, parse_beats


CPM_DEFAULT = 250  # PUBLIC_FIXTURE generic starter chars/min


CPM_OK_RANGE = (220, 300)  # calibrate from creator-owned recordings


_STAGE_NOTE_RE = re.compile(r"^\s*[>\s]*(?:📺|🎬|\(|（)")


_HAS_CONTENT_RE = re.compile(r"[一-鿿A-Za-z0-9]")


def _speakable_paras(text):
    """可唸段落 = 非舞台註記（📺/🎬/括號開頭）且含實際內容（中英數）。
    hook / outro CTA 檢查都以此為準，避免標題尾巴、end-screen 註記、分隔線誤判。"""
    return [p for p in _split_paragraphs(text)
            if not _STAGE_NOTE_RE.match(p) and _HAS_CONTENT_RE.search(p)]


_QUESTION_RE = re.compile(r"[？?]")


_FIRST_INTERRUPT_SEC = 30


_INTERRUPT_PERIOD_SEC = 75


_INTERRUPT_JITTER_SEC = 15


_REHOOK_FRACS = (0.25, 0.50, 0.75)


_MOMENTUM_RE = re.compile(
    r"但|結果|然後|所以|沒想到|居然|竟然|反而|問題是|直接"
    r"|最[扯猛狂強重要屌誇]|其實|真正|接下來|再來|後來|現在"
)


_CURIOSITY_RE = re.compile(
    r"更[扯猛狂強誇厲]|連[^，。,]{0,8}都|沒想到|居然|竟然|其中"
    r"|待會|等一下|最後你|秘密|沒(有)?人|你絕對|[？?]"
)


_CLOSING_FEEL_RE = re.compile(
    r"^(總而言之|總結一下|以上就是|最後總結|來總結|今天就到|總之|回顧一下)")


_ANDTHEN_RE = re.compile(r"^(然後|接著|再來|另外)")


_ANDTHEN_MAX_PER_MIN = 2.0


_BEAT_MAX_SEC = 45.0


_PUNCH_MAX_CHARS = 14


_LONGBEAT_MIN_CHARS = 160


def _split_paragraphs(text: str) -> list:
    """段落塊 = 空行分隔、去掉 beat/markdown header 行後仍有內容的塊。"""
    paras = []
    for block in re.split(r"\n\s*\n", text):
        body = _strip_markup(block).strip()
        if body:
            paras.append(body)
    return paras


def estimate_duration(text: str, cpm: int = CPM_DEFAULT) -> dict:
    """去標點/標記後字數 ÷ cpm。cpm 在 240-280 區間外給 warn。"""
    warnings = []
    if not (CPM_OK_RANGE[0] <= cpm <= CPM_OK_RANGE[1]):
        warnings.append(
            "cpm=%d outside calibrated range %d-%d; est_min unreliable"
            % (cpm, CPM_OK_RANGE[0], CPM_OK_RANGE[1])
        )

    chars = _count_chars(text)
    est_min = chars / float(cpm) if cpm else 0.0

    per_beat = []
    for b in parse_beats(text):
        b_chars = _count_chars(b["body"])
        b_est_sec = round(b_chars / float(cpm) * 60.0, 1) if cpm else 0.0
        entry = {
            "title": b["title"],
            "chars": b_chars,
            "est_sec": b_est_sec,
        }
        if b["t_start"] is not None and b["t_end"] is not None:
            planned = b["t_end"] - b["t_start"]
            entry["planned_sec"] = planned
            entry["delta_sec"] = round(b_est_sec - planned, 1)
            # 估時 vs 標記時長漂 >25% 且 >10s → warn
            if planned > 0 and abs(entry["delta_sec"]) > max(10, planned * 0.25):
                warnings.append(
                    "beat '%s' est %.0fs vs planned %ds (drift %.0fs)"
                    % (_ascii(b["title"]), b_est_sec, planned, entry["delta_sec"])
                )
        per_beat.append(entry)

    return {
        "chars": chars,
        "est_min": round(est_min, 2),
        "est_sec": round(est_min * 60.0, 1),
        "cpm": cpm,
        "per_beat": per_beat,
        "warnings": warnings,
    }


def check_rhythm(text: str, cpm: int = CPM_DEFAULT) -> list:
    """M110 節奏（全 warn 級）：beat 過長 / 中段無動能 / 中段總結感 /
    hook 無 open loop / 長 beat 全長句沒短句打點。"""
    issues = []
    beats = parse_beats(text)
    n = len(beats)

    # hook open loop：前兩可唸段要有懸念訊號
    paras = _speakable_paras(text)
    hook_zone = " ".join(paras[:2])
    if hook_zone and not _CURIOSITY_RE.search(hook_zone):
        issues.append({"rule": "rhythm.hook_no_open_loop", "level": "warn",
                       "detail": "first 2 paragraphs lack a curiosity signal"})

    # and-then 密度：段首弱連接（然後/接著/再來/另外）>2/min = 流水帳
    est_min_total = _count_chars(text) / float(cpm) if cpm else 0.0
    if est_min_total >= 1.0:
        andthen = sum(1 for p in paras if _ANDTHEN_RE.match(p))
        rate = andthen / est_min_total
        if rate > _ANDTHEN_MAX_PER_MIN:
            issues.append({"rule": "rhythm.andthen_chain", "level": "warn",
                           "count": andthen, "per_min": round(rate, 1),
                           "detail": "weak connectors - rewrite as but/therefore chain"})

    for i, b in enumerate(beats):
        body = _strip_markup(b["body"]).strip()
        chars = _count_chars(b["body"])
        if not body or chars < 20:
            continue
        est_sec = chars / float(cpm) * 60.0 if cpm else 0.0

        if est_sec > _BEAT_MAX_SEC:
            issues.append({"rule": "rhythm.beat_too_long", "level": "warn",
                           "beat": b["title"], "est_sec": round(est_sec, 1),
                           "detail": "add payoff/visual event or split beat"})

        is_mid = 0 < i < n - 1
        if is_mid and chars >= 30 and not (
                _MOMENTUM_RE.search(body) or _QUESTION_RE.search(body)):
            issues.append({"rule": "rhythm.no_momentum", "level": "warn",
                           "beat": b["title"],
                           "detail": "no twist/momentum word and no question"})

        if i < n - 1:
            for p in _split_paragraphs(b["body"]):
                if _CLOSING_FEEL_RE.match(p.strip()):
                    issues.append({"rule": "rhythm.mid_closing_tone", "level": "warn",
                                   "beat": b["title"],
                                   "detail": "closing-feel opener mid-video"})
                    break

        if chars >= _LONGBEAT_MIN_CHARS:
            sents = [s for s in re.split(r"[。！？!?]", body) if _count_chars(s)]
            if sents and all(
                    _count_chars(s) > _PUNCH_MAX_CHARS for s in sents):
                issues.append({"rule": "rhythm.no_punch", "level": "warn",
                               "beat": b["title"],
                               "detail": "long beat, all long sentences - add a short punch line"})
    return issues


def interrupt_schedule(text: str, cpm: int = CPM_DEFAULT) -> list:
    """30s 首發 + 每 75±15s 一發的建議表；re-hook 標在 40%/70%。

    回傳 [{t_est, type}]（秒，可直接 json.dump 給 build 對接）。
    """
    total = estimate_duration(text, cpm)["est_sec"]
    if total <= 0:
        return []

    rehook_ts = [round(total * f, 1) for f in _REHOOK_FRACS]
    sched = []
    t = float(_FIRST_INTERRUPT_SEC)
    first = True
    while t < total:
        typ = "first_interrupt" if first else "interrupt"
        # 落在 re-hook 位 ±jitter 內 → 升級成 re-hook
        for rt in list(rehook_ts):
            if abs(t - rt) <= _INTERRUPT_JITTER_SEC:
                typ = "re-hook"
                rehook_ts.remove(rt)
                break
        sched.append({"t_est": round(t, 1), "type": typ,
                      "jitter_sec": _INTERRUPT_JITTER_SEC})
        t += _INTERRUPT_PERIOD_SEC
        first = False

    # 沒被吸收的 re-hook 位補進表
    for rt in rehook_ts:
        if rt > _FIRST_INTERRUPT_SEC:
            sched.append({"t_est": rt, "type": "re-hook",
                          "jitter_sec": _INTERRUPT_JITTER_SEC})
    sched.sort(key=lambda x: x["t_est"])
    return sched


def _ascii(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")
