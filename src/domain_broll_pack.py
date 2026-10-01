# -*- coding: utf-8 -*-
"""Build small original B-roll loops for domains that lack real filler footage.

These are editorial cutaways, not transitions and never automatic openers.
They are safe for the community kit under CC-BY-4.0 with generated provenance.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "broll" / "domain_fill"
MANIFEST = OUT / "manifest.json"
FPS = 24
ASPECTS = {"landscape": ((640, 360), (1920, 1080)), "portrait": ((360, 640), (1080, 1920))}


@dataclass(frozen=True)
class Spec:
    domain: str
    label: str
    energy: float
    render: Callable[[float, tuple[int, int]], Image.Image]
    usage: str


def _grain(im: Image.Image, phase: float, amount: int = 8) -> Image.Image:
    # Deterministic texture; visual movement comes from layers, not random flicker.
    w, h = im.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0)); draw = ImageDraw.Draw(layer)
    step = max(7, min(w, h) // 64)
    for y in range(0, h, step):
        for x in range((y // step) % 2 * (step // 2), w, step):
            value = 255 if ((x // step) * 17 + (y // step) * 31) % 7 < 3 else 0
            draw.point((x, y), fill=(value, value, value, amount))
    out = im.convert("RGBA"); out.alpha_composite(layer)
    return out.convert("RGB")


def _documentary(p: float, size: tuple[int, int]) -> Image.Image:
    p = p % 1.0
    w, h = size; im = Image.new("RGB", size, (226, 216, 194)); d = ImageDraw.Draw(im, "RGBA")
    for i in range(7):
        x = int(w*(.08+i*.14)); d.line((x, 0, x, h), fill=(70, 57, 42, 20), width=1)
    y = int(h*(.52 + .03*math.sin(p*2*math.pi)))
    d.line((int(w*.06), y, int(w*.94), y), fill=(176, 35, 38, 220), width=max(2, w//320))
    for i in range(5):
        x = int(w*(.14+i*.18)); r = max(4, w//90); d.ellipse((x-r,y-r,x+r,y+r), fill=(26,24,22,230))
    shift = int(w*.035*math.sin(p*2*math.pi))
    d.rounded_rectangle((int(w*.12)+shift,int(h*.13),int(w*.50)+shift,int(h*.44)), radius=8,
                        fill=(246,241,226,230), outline=(28,25,22,220), width=2)
    d.rectangle((int(w*.57)-shift,int(h*.60),int(w*.90)-shift,int(h*.84)), fill=(34,31,29,235))
    return _grain(im, p)


def _interview(p: float, size: tuple[int, int]) -> Image.Image:
    p = p % 1.0
    w, h = size; im = Image.new("RGB", size, (17, 30, 47)); d = ImageDraw.Draw(im, "RGBA")
    # Empty-chair/no-face composition with living waveform and quote field.
    d.ellipse((int(w*.08),int(h*.18),int(w*.46),int(h*.63)), fill=(36,72,94,230))
    d.rounded_rectangle((int(w*.19),int(h*.52),int(w*.43),int(h*.88)), radius=max(10,w//40), fill=(8,13,19,240))
    d.rounded_rectangle((int(w*.54),int(h*.14),int(w*.91),int(h*.70)), radius=max(8,w//55),
                        fill=(239,231,211,235))
    cy = int(h*.80)
    pts=[]
    for x in range(int(w*.52), int(w*.92), max(2,w//180)):
        amp = h*.025*(1+math.sin(x*.07+p*2*math.pi))
        pts.append((x, int(cy + amp*math.sin(x*.14+p*4*math.pi))))
    if len(pts)>1: d.line(pts, fill=(76,220,206,230), width=max(2,w//300))
    for ox, oy in ((.62,.25),(.74,.25)):
        d.ellipse((int(w*ox),int(h*oy),int(w*(ox+.08)),int(h*(oy+.10))), fill=(15,28,43,220))
    return _grain(im, p, 5)


def _fitness(p: float, size: tuple[int, int]) -> Image.Image:
    p = p % 1.0
    w,h=size; im=Image.new("RGB",size,(9,12,14)); d=ImageDraw.Draw(im,"RGBA")
    lime=(189,255,36,235); cyan=(35,209,238,210)
    for i in range(8):
        x=int(w*(-.2+i*.18+(p*.18)% .18)); d.polygon([(x,0),(x+int(w*.07),0),(x-int(w*.23),h),(x-int(w*.30),h)],fill=lime[:3]+(26,))
    cx,cy=int(w*.72),int(h*.42); r=int(min(w,h)*.20)
    d.ellipse((cx-r,cy-r,cx+r,cy+r),outline=(255,255,255,45),width=max(2,w//100))
    end=int(360*(.70+.22*math.sin(p*2*math.pi)))
    d.arc((cx-r,cy-r,cx+r,cy+r),-90,-90+end,fill=lime,width=max(5,w//40))
    for i in range(4):
        y=int(h*(.70+i*.055)); ln=int(w*(.18+.10*math.sin(p*2*math.pi+i)))
        d.rounded_rectangle((int(w*.08),y,int(w*.08)+ln,y+max(4,h//90)),4,fill=cyan)
    return im


def _fashion(p: float, size: tuple[int, int]) -> Image.Image:
    p = p % 1.0
    w,h=size; im=Image.new("RGB",size,(242,237,229)); d=ImageDraw.Draw(im,"RGBA")
    mag=(244,48,126,225); cobalt=(31,65,210,225); ink=(11,12,16,240)
    slide=int(w*.08*math.sin(p*2*math.pi))
    d.rectangle((int(w*.08)+slide,int(h*.06),int(w*.37)+slide,int(h*.94)),fill=ink)
    d.rectangle((int(w*.42)-slide,int(h*.17),int(w*.92)-slide,int(h*.47)),fill=mag)
    d.rectangle((int(w*.52)+slide,int(h*.53),int(w*.85)+slide,int(h*.89)),fill=cobalt)
    # Runway perspective and editorial crop marks.
    vp=(int(w*.50),int(h*.25))
    for x in (int(w*.08),int(w*.28),int(w*.72),int(w*.92)): d.line((vp[0],vp[1],x,h),fill=(255,255,255,120),width=2)
    for x,y,sx,sy in ((16,16,1,1),(w-16,16,-1,1),(16,h-16,1,-1),(w-16,h-16,-1,-1)):
        d.line((x,y,x+sx*w*.09,y),fill=ink,width=2); d.line((x,y,x,y+sy*h*.06),fill=ink,width=2)
    return _grain(im,p,4)


SPECS = (
    Spec("documentary", "ARCHIVE / TIMELINE", .42, _documentary, "史料、時間線、觀點轉折的中性補畫面"),
    Spec("interview", "VOICE / QUOTE", .35, _interview, "不露臉訪談的聲音、引句與環境承接"),
    Spec("fitness", "TRAIN / METRIC", .82, _fitness, "計時、組數、進度與動作段落的補畫面"),
    Spec("fashion", "EDITORIAL / RUNWAY", .67, _fashion, "穿搭、材質、造型與章節呼吸的編輯感補畫面"),
)


def _frames(spec: Spec, size: tuple[int,int], seconds: float) -> Iterable[Image.Image]:
    count=round(seconds*FPS)
    for i in range(count): yield spec.render(i/count,size)


def _encode(frames: Iterable[Image.Image], render_size: tuple[int,int], output_size: tuple[int,int], output: Path) -> None:
    output.parent.mkdir(parents=True,exist_ok=True)
    cmd=["ffmpeg","-v","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{render_size[0]}x{render_size[1]}","-r",str(FPS),"-i","-","-an","-vf",f"scale={output_size[0]}:{output_size[1]}:flags=lanczos","-c:v","libx264","-crf","19","-preset","medium","-pix_fmt","yuv420p","-movflags","+faststart",str(output)]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        for frame in frames: proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close(); err=proc.stderr.read().decode("utf-8",errors="replace"); code=proc.wait()
    except Exception: proc.kill(); raise
    if code: raise RuntimeError("domain B-roll encode failed: "+err[-600:])


def build(seconds: float=3.0) -> dict:
    assets=[]
    for spec in SPECS:
        for aspect,(render_size,output_size) in ASPECTS.items():
            path=OUT/spec.domain/aspect/(spec.domain+"_editorial_filler.mp4")
            _encode(_frames(spec,render_size,seconds),render_size,output_size,path)
            assets.append({"id":f"{spec.domain}_{aspect}_editorial_filler","path":path.relative_to(ROOT).as_posix(),
                           "domain":spec.domain,"label":spec.label,"role":"broll","aspect":aspect,
                           "duration":seconds,"fps":FPS,"resolution":list(output_size),"energy":spec.energy,
                           "loop":True,"usage":spec.usage,"tags":[spec.domain,"editorial","filler","cutaway"],
                           "license":"CC-BY-4.0","provenance":"domain_broll_pack.py procedural original"})
            print(f"[{spec.domain}/{aspect}] OK")
    manifest={"schema_version":1,"generator":"domain_broll_pack.py","license":"CC-BY-4.0",
              "guardrails":["不是轉場","不是自動開場","只在缺真實素材且語意相符時補","不得蓋過證據或受訪聲音"],"assets":assets}
    OUT.mkdir(parents=True,exist_ok=True); MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest


def _selftest() -> None:
    for spec in SPECS:
        for render_size,_ in ASPECTS.values():
            frame=spec.render(.25,render_size); assert frame.size==render_size and frame.mode=="RGB"
            assert spec.render(0,render_size).tobytes()==spec.render(1,render_size).tobytes()
    assert {x.domain for x in SPECS}=={"documentary","interview","fitness","fashion"}
    print("domain_broll_pack self-test GREEN")


def main(argv:list[str]|None=None)->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True); sub.add_parser("selftest"); b=sub.add_parser("build"); b.add_argument("--seconds",type=float,default=3.0)
    args=ap.parse_args(argv)
    if args.cmd=="selftest": _selftest(); return 0
    result=build(args.seconds); print(json.dumps({"assets":len(result["assets"]),"manifest":str(MANIFEST)},ensure_ascii=False)); return 0


if __name__=="__main__": raise SystemExit(main())
