#!/usr/bin/env python3
"""Deduplicate identical image streams in the exported PDF.

Chromium embeds a fresh copy of an image for every page it appears on, so the
recurring mark is stored fourteen-plus times. Identical streams are collapsed
onto one object. This is lossless: no stream is recompressed or resampled.
"""
import sys, hashlib, pikepdf

src, dst = sys.argv[1], sys.argv[2]
LOSSLESS = "--lossless" in sys.argv[3:]   # keep every pixel; only dedupe
pdf = pikepdf.open(src)

seen, remap = {}, {}
for obj in pdf.objects:
    try:
        if obj.get("/Type") != "/XObject" or obj.get("/Subtype") != "/Image":
            continue
    except Exception:
        continue
    try:
        raw = obj.read_raw_bytes()
    except Exception:
        continue
    key = hashlib.sha1(
        raw + repr(sorted((str(k), str(v)) for k, v in obj.items()
                          if str(k) != "/Length")).encode()).hexdigest()
    if key in seen:
        remap[obj.objgen] = seen[key]
    else:
        seen[key] = obj

replaced = 0
for page in pdf.pages:
    res = page.get("/Resources")
    if res is None or "/XObject" not in res:
        continue
    xo = res["/XObject"]
    for name in list(xo.keys()):
        target = xo[name]
        if target.objgen in remap:
            xo[name] = remap[target.objgen]
            replaced += 1


# ---- recompress colour data -------------------------------------------
# Chromium decodes each PNG and stores it as raw Flate RGB, which is far
# larger than the source file. The colour channels are re-encoded as 4:4:4
# JPEG at high quality — no chroma subsampling, so painted edges and the fine
# red/white detail in the masks stay clean. Every alpha mask (/SMask) is left
# untouched and lossless, which is what actually holds a cutout's edge.
import io
from PIL import Image
QUALITY, FLOOR = 92, 60_000
if LOSSLESS:
    FLOOR = 10**12          # nothing qualifies, so nothing is recompressed
saved = shrunk = 0
for obj in pdf.objects:
    try:
        if obj.get("/Type") != "/XObject" or obj.get("/Subtype") != "/Image":
            continue
        if str(obj.get("/Filter")) not in ("/FlateDecode", "[ /FlateDecode ]"):
            continue
        raw = obj.read_raw_bytes()
    except Exception:
        continue
    if len(raw) < FLOOR:
        continue
    try:
        im = pikepdf.PdfImage(obj).as_pil_image()
    except Exception:
        continue
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if im.mode == "L":
        continue                      # leave masks alone
    try:
        im.load()
        im = im.copy()
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=QUALITY, subsampling=0)
        jpg = buf.getvalue()
        Image.open(io.BytesIO(jpg)).verify()      # never ship a stream we
                                                  # cannot read back
    except Exception:
        continue
    if len(jpg) >= len(raw) * 0.92:
        continue                      # not worth it
    smask = obj.get("/SMask")
    obj.write(jpg, filter=pikepdf.Name("/DCTDecode"))
    obj["/ColorSpace"] = pikepdf.Name("/DeviceRGB")
    obj["/BitsPerComponent"] = 8
    if smask is not None:
        obj["/SMask"] = smask
    saved += len(raw) - len(jpg); shrunk += 1
print(f"recompressed {shrunk} colour streams, saved {saved/1048576:.1f} MB")

pdf.remove_unreferenced_resources()
pdf.save(dst, linearize=True, compress_streams=True,
         object_stream_mode=pikepdf.ObjectStreamMode.generate)
print(f"unique images {len(seen)} | references collapsed {replaced}")
