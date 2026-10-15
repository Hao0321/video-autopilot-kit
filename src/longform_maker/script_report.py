"""Public workflow component (public distribution).

Configurable source-only workflow implementation; no creator data or live capability proof.

Defaults are configurable starter values. Public source contains no maintainer
project result, dated review, private route, transcript or preference evidence.

PUBLIC_FIXTURE: calibrate with creator-owned media and retain the evidence receipt.
"""
from __future__ import annotations

import json
import os


def write_report(report: dict, path: str) -> str:
    """人可讀 report 存檔（UTF-8）；同名 .json 存機器版。"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = []
    lines.append("SCRIPT GATE REPORT")
    lines.append("=" * 50)
    lines.append("verdict: %s" % ("PASS" if report["ok"] else "FAIL"))
    d = report["duration"]
    lines.append("")
    lines.append("[duration] chars=%d  est=%.2f min (%.0fs) @ cpm=%d"
                 % (d["chars"], d["est_min"], d["est_sec"], d["cpm"]))
    for b in d["per_beat"]:
        extra = ""
        if "planned_sec" in b:
            extra = "  planned=%ds delta=%+.0fs" % (b["planned_sec"], b["delta_sec"])
        lines.append("  - %s: %d chars ~%.0fs%s"
                     % (b["title"], b["chars"], b["est_sec"], extra))
    lines.append("")
    lines.append("[hook] violations=%d" % len(report["hook_violations"]))
    for v in report["hook_violations"]:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    s = report["structure"]
    lines.append("")
    lines.append("[structure] chapters=%d paragraphs=%d ok=%s"
                 % (s["chapters"], s["paragraphs"], s["ok"]))
    for v in s["chapter_issues"] + s["cta_issues"]:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    for g in s["interrupt_gaps"]:
        lines.append("  - WARN interrupt gap %.0fs-%.0fs" % (g["from_sec"], g["to_sec"]))
    lang = report.get("language", [])
    lines.append("")
    lines.append("[language M110] fails=%d warns=%d"
                 % (len([v for v in lang if v["level"] == "fail"]),
                    len([v for v in lang if v["level"] == "warn"])))
    for v in lang:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    rhythm = report.get("rhythm", [])
    lines.append("")
    lines.append("[rhythm M110] warns=%d" % len(rhythm))
    for v in rhythm:
        lines.append("  - %s" % json.dumps(v, ensure_ascii=False))
    lines.append("")
    lines.append("[interrupt schedule] (30s first, then every 75+/-15s; re-hook @40%/70%)")
    for it in report["interrupt_schedule"]:
        lines.append("  - %6.1fs  %s" % (it["t_est"], it["type"]))
    lines.append("")
    if report["warnings"]:
        lines.append("[warnings]")
        for w in report["warnings"]:
            lines.append("  - %s" % w)

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    jpath = os.path.splitext(path)[0] + ".json"
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path
