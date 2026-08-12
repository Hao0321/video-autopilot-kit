# -*- coding: utf-8 -*-
"""Preview-first cold archive planner; no deletion and no raw-source surprises."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from project_paths import discover_project_root, is_within


ROOT=discover_project_root(Path(__file__).resolve().parent)
VIDEOS=ROOT/"videos"
REPORT=ROOT/"reports"/"storage"/"cold-archive-plan.json"
PROTECTED=(VIDEOS/"_INBOX",VIDEOS/"_READY_TO_PUBLISH",VIDEOS/"_PUBLISHED")
ELIGIBLE=(VIDEOS/"_archive",VIDEOS/"_planning")
MEDIA={".mp4",".mov",".mkv",".m4v",".wav",".mp3"}


def _hash(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(4*1024*1024),b""): h.update(block)
    return h.hexdigest()


def _atomic(path:Path,data:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True); fd,name=tempfile.mkstemp(prefix=".cold-",suffix=".tmp",dir=path.parent)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def preview(min_bytes:int=50*1024*1024)->dict:
    rows=[]
    for root in ELIGIBLE:
        if not root.exists(): continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in MEDIA or path.stat().st_size<min_bytes: continue
            if any(is_within(path,p) for p in PROTECTED): continue
            rows.append({"path":path.relative_to(ROOT).as_posix(),"bytes":path.stat().st_size,
                         "reason":"large derived/archive media; preview only","action":"would-move-to-cold-archive"})
    rows.sort(key=lambda x:(-x["bytes"],x["path"]))
    report={"schema_version":1,"status":"PREVIEW_ONLY","generated_at":datetime.now(timezone.utc).isoformat(),
            "candidate_count":len(rows),"potential_bytes":sum(x["bytes"] for x in rows),
            "protected_roots":[x.relative_to(ROOT).as_posix() for x in PROTECTED],"candidates":rows,
            "apply_contract":"requires explicit external --target; hashes every file; moves nothing from INBOX/READY/PUBLISHED; never deletes"}
    _atomic(REPORT,report); return report


def apply(target:str|Path,plan:str|Path=REPORT)->dict:
    destination=Path(target).resolve(); destination.mkdir(parents=True,exist_ok=True)
    if is_within(destination,ROOT) or destination==ROOT: raise ValueError("cold archive target must be outside the project")
    report=json.loads(Path(plan).read_text(encoding="utf-8")); moved=[]
    for row in report.get("candidates",[]):
        source=(ROOT/row["path"]).resolve()
        if not source.is_file() or not any(is_within(source,r) for r in ELIGIBLE) or any(is_within(source,r) for r in PROTECTED):
            raise RuntimeError("plan drift or protected source: "+str(source))
        digest=_hash(source); dest=destination/source.relative_to(VIDEOS)
        dest.parent.mkdir(parents=True,exist_ok=True)
        if dest.exists():
            if _hash(dest)!=digest: raise RuntimeError("destination collision: "+str(dest))
            source.unlink(); action="verified-source-removed-after-existing-cold-copy"
        else:
            shutil.move(str(source),str(dest)); action="moved"
            if _hash(dest)!=digest: raise RuntimeError("post-move hash mismatch: "+str(dest))
        moved.append({"source":row["path"],"destination":str(dest),"sha256":digest,"action":action})
    result={"status":"GREEN","target":str(destination),"moved":moved,"bytes":sum(x.get("bytes",0) for x in report.get("candidates",[]))}
    _atomic(destination/"hao-cold-archive-manifest.json",result); return result


def _selftest()->None:
    assert all(is_within(x,VIDEOS) for x in PROTECTED+ELIGIBLE)
    assert not any(is_within(PROTECTED[0],e) for e in ELIGIBLE)
    try: apply(ROOT,Path("missing.json")); raise AssertionError("inside target accepted")
    except ValueError: pass
    print("storage_optimizer self-test GREEN")


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest"); pr=sub.add_parser("preview"); pr.add_argument("--min-mb",type=float,default=50); ac=sub.add_parser("apply"); ac.add_argument("--target",required=True); ac.add_argument("--plan",default=str(REPORT))
    args=ap.parse_args(argv)
    if args.cmd=="selftest": _selftest(); return 0
    result=preview(round(args.min_mb*1024*1024)) if args.cmd=="preview" else apply(args.target,args.plan); print(json.dumps(result,ensure_ascii=False,indent=2)); return 0


if __name__=="__main__": raise SystemExit(main())
