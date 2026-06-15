import os, sys
sys.path.insert(0, r"D:\video-autopilot-kit\src")
from silent_vlog_maker import text_overlay as t

print("FONT_NOTO_BLACK =", repr(t.FONT_NOTO_BLACK))
print("title_hook font =", repr(t.POSITION_PRESETS["title_hook"]["font"]))
print("title_detail font =", repr(t.POSITION_PRESETS["title_detail"]["font"]))

ov = t.Overlay(text="HELLO", position="title_hook", t_start=0, t_end=3)
dt = ov.to_drawtext("caption.txt")
print("drawtext head:", dt.split(":textfile")[0])

raw = t.FONT_NOTO_BLACK.replace("\\", "")
print("raw path resolved:", raw)
print("Noto Black exists on THIS machine:", os.path.exists(raw))
print("msjhbd legacy exists:", os.path.exists(r"C:/Windows/Fonts/msjhbd.ttc"))
print("serif default has drive letter:", bool(os.path.splitdrive(t.FONT_NOTO_SERIF_BOLD)[0]))

# Count distinct fonts used across every portrait/landscape/variety preset
from silent_vlog_maker import text_overlay as t2
fonts = set()
for fam in t2.LAYOUT_PRESETS.values():
    for p in fam.values():
        fonts.add(p["font"])
print("distinct fonts across ALL presets:", fonts)
print("all are C:/Windows Noto absolute:", all("Windows/Fonts/NotoSansTC" in f for f in fonts))
