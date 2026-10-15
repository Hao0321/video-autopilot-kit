"""Timing-preserving subtitle segmentation with explicit language and limits."""
from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class GroupingLimits:
    max_chars: int = 15
    hard_gap: float = .42
    soft_gap: float = .28
    soft_len: int = 9
    min_break_gap: float = .06
    overflow: int = 3
    punct_min: int = 7
    sent_min: int = 4


class WordGrouping:
    def __init__(self, grammar, limits, fix_text, cjklen, fixes):
        self.grammar = grammar
        self.limits = limits
        self.fix_text = fix_text
        self._cjklen = cjklen
        self.fixes = fixes
        self.lines, self.buf = [], []
        self._ALL_PUNCT = grammar['_SENT_PUNCT'] + grammar['_CLAUSE_PUNCT']

    def _emit(self, seg):
        if seg:
            txt = self.fix_text("".join(x[2] for x in seg), self.fixes)
            if txt:
                self.lines.append((seg[0][0], seg[-1][1], txt))

    def flush(self, upto=None):
        """emit buf[:upto]（或全部）。M108：若這段仍 > max_chars+overflow（例如 hard_gap/beat 收尾
        時整段太長沒被中途斷過），先在結構合格點把它拆成 ≤上限 的多段再 emit——避免超寬行溢出/自動 wrap。"""

        take = self.buf if upto is None else self.buf[:upto + 1]
        rest = [] if upto is None else self.buf[upto + 1:]
        self.buf = take                                  # 讓 best_break/_eligible 對 take 運算
        cap = self.limits.max_chars + self.limits.overflow
        while self._cjklen("".join(x[2] for x in self.buf)) > cap and len(self.buf) > 1:
            b = self.best_break(0.0, strict=True, hard=True)
            if b is None:
                b = self.best_break(0.0, strict=True, hard=False)
            if b is None:
                b = self.best_break(0.0, strict=False)
            if b is None:
                break
            self._emit(self.buf[:b + 1]); self.buf = self.buf[b + 1:]
        self._emit(self.buf)
        self.buf = rest

    def _num_cont(self, a, b0):
        """「1,」「175.」後接數字 = 千分位/小數點，不是子句邊界。"""
        return bool(re.search(r"[0-9][,\.]$", a)) and bool(re.match(r"[0-9]", b0 or ""))

    def _eligible(self, j, hard=True):
        a = self.buf[j][2].strip(); b = self.buf[j + 1][2].strip()
        if not a or not b:
            return False
        if a[-1] + b[0] in self.grammar['NEVER_SPLIT']:      # 複合詞腰斬
            return False
        if re.match(r"[A-Za-z]", b[0]) and re.search(r"[A-Za-z]$", a):
            return False                     # 拉丁字互拆（Un|real、App|Store）
        # 數字腰斬：前 token 收在數字/,/. 而下一 token 以數字或單位起（2|70萬、1,|234、94.|1%）
        if re.search(r"[0-9][0-9,\.]*$", a) and re.match(r"[0-9%萬千百億]", b[0]):
            return False
        if b[0] in self.grammar['HEAD_DANGLERS']:            # 下一行以 了/的… 開頭
            return False
        if b.startswith(self.grammar['DIR_COMPLEMENTS']):    # M108：方向補語不當行頭（做|下去）
            return False
        if a in self.grammar['TAIL_DANGLER_TOKENS']:         # 連接詞掛行尾
            return False
        # M108：情態/助動/共動收尾 = 謂語腰斬（「…真正會」「…可以靠」「…也會一直」）。帶標點收尾則豁免
        if hard and a[-1] not in self._ALL_PUNCT:
            core = a.rstrip(self._ALL_PUNCT)
            joined_head = "".join(x[2] for x in self.buf[:j + 1]).rstrip(self._ALL_PUNCT)
            if core and core[-1] in self.grammar['TAIL_HARD']:
                return False
            if joined_head.endswith(self.grammar['TAIL_HARD_TOK']):   # 2 字黏後動詞副詞（一直/幾乎…）
                return False
        return self._cjklen("".join(x[2] for x in self.buf[:j + 1])) >= 4

    def best_break(self, require_gap, strict=True, hard=True):
        best, best_score = None, -1.0
        for j in range(len(self.buf) - 1):
            g = self.buf[j + 1][0] - self.buf[j][1]
            dur_next = self.buf[j + 1][1] - self.buf[j + 1][0]
            # 停頓常被 whisper 吸進【下一個 token 的開頭】→ 下一 token 拉長 = 這裡有停頓。
            # （曾誤用「當前 token 拉長」→ 角(0.54s)|色 被當斷點腰斬，2026-07-02 抓到）
            pseudo = g + (0.15 if dur_next >= 0.50 else 0.0)
            a = self.buf[j][2].strip()
            b0 = self.buf[j + 1][2].lstrip()
            tp = a[-1:] if a else ""
            # M108 語意加分：標點邊界 > 子句開頭詞 > 純 gap
            if not self._num_cont(a, b0[:1]):
                if tp in self.grammar['_SENT_PUNCT']:
                    pseudo += 0.6
                elif tp in self.grammar['_CLAUSE_PUNCT']:
                    pseudo += 0.4
            if b0.startswith(self.grammar['CLAUSE_HEADS']):
                pseudo += 0.2
            if pseudo < require_gap:
                continue
            if strict and not self._eligible(j, hard=hard):
                continue
            core = a.rstrip(self._ALL_PUNCT)
            tail = core[-1:] if core else ""
            score = pseudo - (0.25 if tail in self.grammar['DANGLERS'] else 0.0) \
                           - (0.4 if (not hard and tail in self.grammar['TAIL_HARD'] and tp not in self._ALL_PUNCT) else 0.0)
            if score >= best_score and self._cjklen("".join(x[2] for x in self.buf[:j + 1])) >= 4:
                best, best_score = j, score
        return best

    def group(self, words, force_break_after=None):
        for i, (s, e, w) in enumerate(words):
            self.buf.append((s, e, w))
            gap_next = (words[i + 1][0] - e) if i + 1 < len(words) else 99.0
            cur_len = self._cjklen("".join(x[2] for x in self.buf))
            tw = w.strip()
            tp = tw[-1:] if tw else ""
            nxt0 = words[i + 1][2].lstrip()[:1] if i + 1 < len(words) else ""
            joined_now = "".join(x[2] for x in self.buf).replace(" ", "")
            # M108b：語意斷點 hint（buffer 尾 match 專案指定字串 → 就地斷，防上句尾+下句頭焊同行）
            if force_break_after and cur_len >= 4 and any(joined_now.endswith(h) for h in force_break_after):
                self.flush()
            # M108 ⓪.5：token 自帶標點 = whisper 偵測到的子句邊界 → 就地斷（千分位豁免）
            elif tp and not self._num_cont(tw, nxt0) and (
                    (tp in self.grammar['_SENT_PUNCT'] and cur_len >= self.limits.sent_min) or
                    (tp in self.grammar['_CLAUSE_PUNCT'] and cur_len >= self.limits.punct_min)):
                self.flush()
            elif gap_next > self.limits.hard_gap or (cur_len >= self.limits.soft_len and gap_next > self.limits.soft_gap):
                self.flush()
            elif cur_len > self.limits.max_chars:
                b = self.best_break(self.limits.min_break_gap, strict=True, hard=True)
                if b is not None:
                    self.flush(b)
                elif cur_len > self.limits.max_chars + self.limits.overflow:
                    # 連讀太長：放寬 gap 仍守全部規則 → 放行情態懸掛(結構規則仍守) → 最後才無限制
                    b2 = self.best_break(0.0, strict=True, hard=True)
                    if b2 is None:
                        b2 = self.best_break(0.0, strict=True, hard=False)
                    if b2 is None:
                        b2 = self.best_break(0.0, strict=False)
                    self.flush(b2 if b2 is not None else len(self.buf) - 2)
        self.flush()
        return self.lines
