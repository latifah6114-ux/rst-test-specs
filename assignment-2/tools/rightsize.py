#!/usr/bin/env python3
"""Resample each asset to exactly what its printed size needs at 300 dpi.

Carrying a 1100px cutout for a stamp printed 30mm wide costs file size and
buys nothing: 30mm at 300dpi is 354px. Assets are reduced to their real
requirement (with a little headroom), then given a light unsharp pass to
restore the edge definition that any downsample costs.
"""
import json, sys, pathlib
from PIL import Image, ImageFilter

ASSETS = pathlib.Path(sys.argv[1])
USED   = json.loads(pathlib.Path(sys.argv[2]).read_text())
DPI    = 300
HEAD   = 1.12          # headroom for viewers that render above 100%

before = after = 0
for name, mm in sorted(USED.items()):
    p = ASSETS / name
    if not p.exists():
        continue
    before += p.stat().st_size
    im = Image.open(p).convert("RGBA")
    need = int(round(mm / 25.4 * DPI * HEAD))
    cur  = max(im.size)
    if need < cur:
        s = need / cur
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))),
                       Image.LANCZOS)
        r, g, b, a = im.split()
        rgb = Image.merge("RGB", (r, g, b)).filter(
            ImageFilter.UnsharpMask(radius=1.0, percent=42, threshold=2))
        im = Image.merge("RGBA", (*rgb.split(), a))
        im.save(p, optimize=True)
    after += p.stat().st_size
    print(f"  {name}  {mm:5.1f}mm  {cur:4d}px -> {max(im.size):4d}px")

print(f"\nassets: {before/1048576:.1f} MB -> {after/1048576:.1f} MB "
      f"({100*(1-after/before):.0f}% smaller)")
