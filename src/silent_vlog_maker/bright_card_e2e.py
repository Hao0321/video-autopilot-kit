# -*- coding: utf-8 -*-
"""Real ffmpeg regression for M116 portrait Bright Editorial cards.

This deliberately lives in a UTF-8 file. Passing CJK source copy through a
Windows shell heredoc can corrupt it before Python starts (M74 family).
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile

from shorts_vertical import _apply_visual_plan_cards, _visual_plan_card_events


def main() -> int:
    here=os.path.dirname(os.path.abspath(__file__))
    qa_dir=os.path.join(here,"_demo")
    os.makedirs(qa_dir,exist_ok=True)
    qa_frame=os.path.join(qa_dir,"bright_short_e2e.jpg")
    source_text="節奏從這裡翻面"
    assert "?" not in source_text and len(source_text)==7
    with tempfile.TemporaryDirectory(prefix="bright_short_e2e_") as td:
        src=os.path.join(td,"source.mp4")
        subprocess.run([
            "ffmpeg","-v","error","-y","-f","lavfi","-i",
            "color=c=0x152147:s=1080x1920:r=30:d=4",
            "-c:v","libx264","-pix_fmt","yuv420p",src,
        ],check=True)
        plan={
            "domain":"music",
            "template_system":{"style":"festival_block","aspect":"portrait","roles":["chapter"]},
            "events":[
                {"t":1.2,"duration":0.7,"type":"pattern_interrupt",
                 "card":"chapter","source_text":source_text,"reason":"semantic_turn"},
                {"t":2.4,"duration":0.7,"type":"pattern_interrupt",
                 "card":"steps","source_text":"結果留到最後","reason":"payoff_marker"},
            ],
        }
        card_events=_visual_plan_card_events(plan,4.0)
        assert not card_events, "unapproved semantic turn covered real footage"
        assert _apply_visual_plan_cards(src,plan,"music",os.path.join(td,"blocked"),4.0)==src
        approved_plan=dict(plan)
        approved_plan["events"]=[dict(plan["events"][0],
                                      allow_full_frame_card=True,
                                      footage_gap_verified=True)]
        card_events=_visual_plan_card_events(approved_plan,4.0)
        assert len(card_events)==1 and card_events[0][2]==source_text
        out=_apply_visual_plan_cards(src,approved_plan,"music",os.path.join(td,"result"),4.0)
        probe=json.loads(subprocess.check_output([
            "ffprobe","-v","error","-show_entries",
            "stream=width,height,pix_fmt,r_frame_rate","-show_entries","format=duration",
            "-of","json",out,
        ],text=True))
        subprocess.run([
            "ffmpeg","-v","error","-y","-ss","1.45","-i",out,
            "-frames:v","1",qa_frame,
        ],check=True)
        stream=probe["streams"][0]
        assert stream["width"]==1080 and stream["height"]==1920
        assert stream["pix_fmt"]=="yuv420p" and stream["r_frame_rate"]=="30/1"
        assert abs(float(probe["format"]["duration"])-4.0)<.1
    print("BRIGHT SHORT CARD E2E OK ->",qa_frame)
    return 0


if __name__=="__main__":
    raise SystemExit(main())
