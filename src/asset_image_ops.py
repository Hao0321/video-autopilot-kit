"""Asset image ops; one implementation behind the compatibility facade."""
from __future__ import annotations

import hashlib
from pathlib import Path
from PIL import Image


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _perceptual_hash(image: Image.Image) -> str:
    sample = image.convert("L").resize((16, 16), Image.Resampling.LANCZOS)
    values = list(sample.getdata())
    average = sum(values) / len(values)
    return "%064x" % int("".join("1" if value >= average else "0" for value in values), 2)

def _trim_alpha(image: Image.Image, padding: int = 18) -> Image.Image:
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    bbox = alpha.getbbox()
    if not bbox:
        raise ValueError("sprite has no visible alpha")
    left = max(0, bbox[0] - padding)
    top = max(0, bbox[1] - padding)
    right = min(rgba.width, bbox[2] + padding)
    bottom = min(rgba.height, bbox[3] + padding)
    return rgba.crop((left, top, right, bottom))

def _clean_low_alpha_fringe(image: Image.Image, *, preserve_translucency: bool = False,
                            cutoff: int = 28) -> Image.Image:
    """Drop generator colour garbage hidden in nearly transparent pixels.

    This does not chroma-key the subject or alter opaque colour.  Translucent
    smoke/steam can opt out because its low-alpha detail is intentional.
    """
    rgba = image.convert("RGBA")
    if preserve_translucency:
        return rgba
    red, green, blue, alpha = rgba.split()
    alpha = alpha.point(lambda value: 0 if value < cutoff else value)
    return Image.merge("RGBA", (red, green, blue, alpha))
