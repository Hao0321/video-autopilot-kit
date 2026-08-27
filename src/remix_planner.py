# -*- coding: utf-8 -*-
"""General remix discovery from publish packages and original-source metadata."""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from project_paths import discover_project_root
from publish_hub_layout import PUBLISHED, READY


ROOT = discover_project_root(Path(__file__).resolve().parent)
VIDEOS = ROOT / "videos"
PLANNING = VIDEOS / "_planning" / "remix"
PACKAGE_ROOTS = (READY, PUBLISHED)


def _now() -> str: return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".remix-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle: json.dump(payload, handle, ensure_ascii=False, indent=2); handle.write("\n")
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def load_packages() -> list[dict]:
    rows=[]
    for root in PACKAGE_ROOTS:
        for manifest in root.rglob("publish.json") if root.exists() else []:
            try: row=json.loads(manifest.read_text(encoding="utf-8-sig"))
            except (OSError,ValueError): continue
            row["package_manifest"]=manifest.relative_to(ROOT).as_posix(); rows.append(row)
    unique={row.get("content_id"):row for row in rows if row.get("content_id")}
    return sorted(unique.values(),key=lambda x:x["content_id"])


def _key(row: dict) -> list[tuple[str, str]]:
    """Build generic grouping keys without hard-coded maintainer projects."""
    out = []
    niche = str(row.get("niche") or "").lower()
    place = str(row.get("place") or "").strip()
    series = str(row.get("series") or "").strip()
    if place:
        out.append(("place", place))
    if niche and niche not in {"auto", "general"}:
        out.append(("niche", niche))
    if series:
        out.append(("series", series))
    return out


def discover(min_sources:int=2)->list[dict]:
    groups:dict[tuple[str,str],list[dict]]=defaultdict(list)
    for row in load_packages():
        for key in _key(row): groups[key].append(row)
    candidates=[]
    for (kind,label),rows in groups.items():
        ids=sorted({x["content_id"] for x in rows})
        if len(ids)<min_sources: continue
        diversity=len({str(x.get("what")) for x in rows})
        score=min(100,45+10*len(ids)+5*min(diversity,5)+(10 if kind=="series" else 0))
        candidates.append({"group_type":kind,"label":label,"source_count":len(ids),"source_ids":ids,
                           "candidate_score":score,"score_basis":["來源數", "主題一致性", "內容多樣性", "只從原始來源重剪"]})
    return sorted(candidates,key=lambda x:(-x["candidate_score"],x["label"]))


def create_plans(limit:int=5)->dict:
    packages={x["content_id"]:x for x in load_packages()}; made=[]
    existing=list(PLANNING.glob("R[0-9][0-9][0-9]_*/remix_plan.json")) if PLANNING.exists() else []
    next_id=max([int(x.parent.name[1:4]) for x in existing if re.match(r"R\d{3}_",x.parent.name)]+[1])+1
    existing_labels={json.loads(x.read_text(encoding="utf-8")).get("group_label") for x in existing}
    for candidate in discover():
        if candidate["label"] in existing_labels or len(made)>=limit: continue
        cid=f"R{next_id:03d}"; next_id+=1
        safe=re.sub(r'[<>:"/\\|?*]+','_',candidate["label"]).strip() or "remix"
        folder=PLANNING/f"{cid}_{safe}"
        sources=[]
        for source_id in candidate["source_ids"]:
            row=packages[source_id]
            sources.append({"content_id":source_id,"what":row.get("what"),"canonical_source":row.get("canonical_source"),
                            "reuse_rule":"回原始素材挑新片段；禁止直接串接帶字幕發布檔"})
        plan={"schema_version":1,"content_id":cid,"status":"planned","format":"remix","group_type":candidate["group_type"],
              "group_label":candidate["label"],"target_seconds":{"shorts":50,"longform":360},
              "story_options":["Shorts：先給總 payoff，再按路線／強弱排序", "長片：新增旁白脈絡、比較與結論，不做片段合集"],
              "sources":sources,"candidate_score":candidate["candidate_score"],"score_basis":candidate["score_basis"],
              "quality_gates":["新敘事增量明確","至少 30% 使用未發布鏡頭或新旁白","字幕與畫面不得沿用舊成片燒錄層","重新做音樂呼吸與調色一致性","creator 審片後才進 READY"],
              "created_at":_now()}
        _atomic(folder/"remix_plan.json",plan); made.append({"content_id":cid,"label":candidate["label"],"path":str((folder/"remix_plan.json").relative_to(ROOT))})
    report={"status":"GREEN","candidates":discover(),"created":made,"planning_root":str(PLANNING.relative_to(ROOT))}
    _atomic(PLANNING/"remix_candidates.json",report); return report


def _selftest() -> None:
    rows = [
        {"content_id": "S901", "niche": "travel", "place": "示範城", "series": "public-demo-series"},
        {"content_id": "S902", "niche": "travel", "place": "示範城", "series": "public-demo-series"},
    ]
    groups = defaultdict(list)
    for row in rows:
        for key in _key(row):
            groups[key].append(row)
    assert len(groups[("series", "public-demo-series")]) == 2
    assert len(groups[("place", "示範城")]) == 2
    print("remix_planner self-test GREEN (PUBLIC_FIXTURE)")


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest"); sub.add_parser("discover"); cr=sub.add_parser("create"); cr.add_argument("--limit",type=int,default=5)
    args=ap.parse_args(argv)
    if args.cmd=="selftest": _selftest(); return 0
    result=discover() if args.cmd=="discover" else create_plans(args.limit); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
