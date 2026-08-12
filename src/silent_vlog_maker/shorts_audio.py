# -*- coding: utf-8 -*-
"""Audio finishing helpers extracted from shorts_vertical."""
from __future__ import annotations

import json
import re
import subprocess


def loudnorm_two_pass(src, dst, I=-14.0, TP=-1.5, LRA=11.0):
    """Measure then normalize accurately; return False when measurement fails."""
    run = subprocess.run(
        ['ffmpeg', '-hide_banner', '-i', src, '-af',
         f'loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json', '-f', 'null', '-'],
        capture_output=True, text=True, encoding='utf-8', errors='replace')
    match = re.search(r'\{[^{}]*"input_i"[^{}]*\}', run.stderr, re.S)
    if not match:
        return False
    try:
        data = json.loads(match.group(0))
        af = (f"loudnorm=I={I}:TP={TP}:LRA={LRA}:measured_I={data['input_i']}:"
              f"measured_TP={data['input_tp']}:measured_LRA={data['input_lra']}:"
              f"measured_thresh={data['input_thresh']}:offset={data['target_offset']}:linear=true")
    except (ValueError, KeyError):
        return False
    second = subprocess.run(
        ['ffmpeg', '-v', 'error', '-y', '-i', src, '-af', af,
         '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest',
         '-movflags', '+faststart', dst], capture_output=True, text=True,
        encoding='utf-8', errors='replace')
    return second.returncode == 0
