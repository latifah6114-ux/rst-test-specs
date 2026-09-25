#!/usr/bin/env python3
"""Deduplicate the recovered sources, split the composite sheets, and prepare
every asset as a print-ready transparent PNG."""
import sys, json, pathlib, hashlib
import numpy as np
from PIL import Image
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from extract_assets import split_sheet, prepare_single

ROOT = pathlib.Path(sys.argv[1])           # scratch dir holding src/ and src2/
OUT  = pathlib.Path(sys.argv[2])           # library output dir
OUT.mkdir(parents=True, exist_ok=True)

SOURCES = [
    ROOT/"src/gallery-v1-backup/images",   # 88 originals
    ROOT/"src2/extracted",                 # 72 embedded originals
    ROOT/"src/app/images",                 # 36 thumbnails (lowest priority)
]
SHEETS = {"img-02","img-11","img-37","img-77","img-87"}

def phash(p):
    im = Image.open(p).convert("L").resize((16,16), Image.LANCZOS)
    a = np.asarray(im, dtype=np.float32)
    return hashlib.md5((a > a.mean()).tobytes()).hexdigest()

# ---- 1. gather, dedupe (keep the highest-resolution copy of each image) ----
best = {}
sheets = []
for prio, d in enumerate(SOURCES):
    if not d.exists(): continue
    for p in sorted(d.iterdir()):
        if p.suffix.lower() not in (".jpg",".jpeg",".png"): continue
        if p.stem in SHEETS and "gallery-v1" in str(d):
            sheets.append(p); continue
        try:
            w,h = Image.open(p).size
        except Exception:
            continue
        k = phash(p)
        score = (w*h, -prio)
        if k not in best or score > best[k][0]:
            best[k] = (score, p, w, h)

print(f"unique single images: {len(best)}   composite sheets: {len(sheets)}")

# ---- 2. split the composite sheets into individual assets ----------------
manifest = {"sheet_assets": [], "single_assets": []}
for sp in sheets:
    got = split_sheet(sp, OUT, f"sheet-{sp.stem.split('-')[1]}", long_edge=900)
    manifest["sheet_assets"] += got
    print(f"  {sp.name}: separated {len(got)} individual assets")

# ---- 3. prepare every unique single asset --------------------------------
n = 0
for k,(score,p,w,h) in sorted(best.items(), key=lambda kv:-kv[1][0][0]):
    n += 1
    name = f"asset-{n:03d}.png"
    try:
        rec = prepare_single(p, OUT, name, long_edge=1100)
    except Exception as e:
        print("  !", p.name, e); continue
    if rec: manifest["single_assets"].append(rec)

(OUT.parent/"library-manifest.json").write_text(json.dumps(manifest, indent=1))
print(f"prepared {len(manifest['single_assets'])} singles + "
      f"{len(manifest['sheet_assets'])} sheet assets -> {OUT}")
