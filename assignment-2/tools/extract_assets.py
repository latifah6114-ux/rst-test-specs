#!/usr/bin/env python3
"""
Assignment 2 — specialty asset preparation.

The recovered library ships its artwork three ways: cut out on flat black, cut
out on flat white, and packed many-to-a-sheet over a baked-in transparency
checkerboard. Placed straight onto cream notebook paper these read as hard
rectangles, so every asset is rebuilt here to one standard:

  1. classify the backdrop from the border ring
  2. build a backdrop mask, then keep ONLY the part touching the border, so
     black inside a mask or white inside an eye survives
  3. feather the matte, then UN-MULTIPLY the backdrop back out of the edge
     pixels — this is what removes the dark halo that betrays a cheap cutout
  4. tight-crop, resample with Lanczos, finish with a restrained unsharp pass

Composite sheets additionally get segmented into their individual assets.
Nothing is redrawn: identity, colour and symbolism are the source file's.
"""
import sys, json, pathlib
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage

# ---------------------------------------------------------------- utilities
def to_arrays(im):
    rgb = np.asarray(im.convert("RGB"), dtype=np.float32) / 255.0
    lum = rgb @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    sat = rgb.max(2) - rgb.min(2)
    return rgb, lum, sat

def border_ring(a, frac=0.02):
    h, w = a.shape[:2]
    b = max(2, int(min(h, w) * frac))
    return np.concatenate([a[:b].ravel(), a[-b:].ravel(),
                           a[:, :b].ravel(), a[:, -b:].ravel()])

def classify(lum, sat):
    bl, bs = border_ring(lum), border_ring(sat)
    mlum, msat = float(bl.mean()), float(bs.mean())
    if msat < 0.10 and mlum < 0.18:
        return "black"
    if msat < 0.10 and mlum > 0.86:
        # a checkerboard also reads as bright+desaturated; separate the two by
        # how bimodal the ring is (checker = two plateaus, white = one)
        hi = (bl > 0.93).mean(); mid = ((bl > 0.70) & (bl < 0.90)).mean()
        return "checker" if (hi > 0.15 and mid > 0.15) else "white"
    if msat < 0.12 and 0.62 < mlum <= 0.86:
        return "checker"
    return "none"

def backdrop_mask(lum, sat, kind):
    if kind == "black":
        return (lum < 0.16) & (sat < 0.20)
    if kind == "white":
        return (lum > 0.90) & (sat < 0.10)
    if kind == "checker":
        return (sat < 0.085) & (lum > 0.68)
    return np.zeros(lum.shape, bool)

def border_connected(mask):
    """Keep only backdrop that reaches the frame edge."""
    lab, n = ndimage.label(mask)
    if n == 0:
        return mask
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    edge = edge[edge > 0]
    return np.isin(lab, edge) if edge.size else np.zeros_like(mask)

def fill_holes_in_subject(alpha_bin):
    """Close pinholes inside the subject so eyes/teeth don't punch through."""
    return ndimage.binary_fill_holes(alpha_bin)

def matte(rgb, lum, sat, kind):
    bg = backdrop_mask(lum, sat, kind)
    bg = border_connected(bg)
    a = ~bg
    a = fill_holes_in_subject(a)
    a = ndimage.binary_opening(a, np.ones((3, 3), bool))
    a = ndimage.binary_closing(a, np.ones((3, 3), bool))
    if a.sum() < 64:
        return None, None
    af = ndimage.gaussian_filter(a.astype(np.float32), 0.7)
    af = np.clip((af - 0.30) / 0.45, 0.0, 1.0)          # crisp but anti-aliased

    # un-multiply the backdrop out of partially covered edge pixels
    bgc = np.array([0.0, 0.0, 0.0], np.float32) if kind == "black" else \
          np.array([1.0, 1.0, 1.0], np.float32)
    if kind == "checker":
        bgc = np.array([0.92, 0.92, 0.92], np.float32)
    d = np.maximum(af, 1e-3)[..., None]
    out = np.clip((rgb - bgc * (1.0 - d)) / d, 0.0, 1.0)
    out = np.where(af[..., None] > 0.995, rgb, out)
    return out, af

def tight_crop(rgb, a, pad=3, thr=0.04):
    ys, xs = np.where(a > thr)
    if ys.size == 0:
        return None, None
    y0, y1 = max(0, ys.min() - pad), min(a.shape[0], ys.max() + 1 + pad)
    x0, x1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + 1 + pad)
    return rgb[y0:y1, x0:x1], a[y0:y1, x0:x1]

def finish(rgb, a, long_edge, sharpen=0.55):
    h, w = a.shape
    im = Image.fromarray(
        np.dstack([(rgb * 255).astype(np.uint8), (a * 255).astype(np.uint8)]), "RGBA")
    s = long_edge / max(h, w)
    if s > 1.02:
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.LANCZOS)
    if sharpen > 0:
        r, g, b, al = im.split()
        rgbim = Image.merge("RGB", (r, g, b)).filter(
            ImageFilter.UnsharpMask(radius=1.4, percent=int(sharpen * 100), threshold=2))
        im = Image.merge("RGBA", (*rgbim.split(), al))
    return im

# ---------------------------------------------------------- sheet splitting
def split_sheet(path, outdir, stem, long_edge=900, min_frac=0.0016):
    im = Image.open(path)
    rgb, lum, sat = to_arrays(im)
    kind = classify(lum, sat)
    if kind != "checker":
        kind = "checker"
    col, a = matte(rgb, lum, sat, kind)
    if col is None:
        return []
    solid = a > 0.35
    # bridge internal gaps (a jester's bells, dangling ribbons) without
    # merging neighbouring cells
    grouped = ndimage.binary_dilation(solid, np.ones((9, 9), bool))
    lab, n = ndimage.label(grouped)
    H, W = solid.shape
    min_area = min_frac * H * W
    out = []
    objs = ndimage.find_objects(lab)
    order = []
    for i, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        m = (lab[sl] == i) & solid[sl]
        if m.sum() < min_area:
            continue
        order.append((sl[0].start, sl[1].start, i, sl))
    order.sort()                                     # reading order
    for k, (_, _, i, sl) in enumerate(order, start=1):
        m = (lab[sl] == i)
        sub_rgb = col[sl]
        sub_a = a[sl] * m
        c = tight_crop(sub_rgb, sub_a)
        if c[0] is None:
            continue
        img = finish(c[0], c[1], long_edge)
        name = f"{stem}-{k:02d}.png"
        img.save(outdir / name, optimize=True)
        out.append({"file": name, "w": img.width, "h": img.height,
                    "source": path.name, "cell": k})
    return out

# --------------------------------------------------------- single artefacts
def prepare_single(path, outdir, name, long_edge=1100):
    im = Image.open(path)
    rgb, lum, sat = to_arrays(im)
    kind = classify(lum, sat)
    if kind == "none":
        base = Image.open(path).convert("RGBA")
        s = long_edge / max(base.size)
        if s > 1.02:
            base = base.resize((round(base.width * s), round(base.height * s)),
                               Image.LANCZOS)
        base.save(outdir / name, optimize=True)
        return {"file": name, "w": base.width, "h": base.height,
                "source": path.name, "backdrop": "kept"}
    col, a = matte(rgb, lum, sat, kind)
    if col is None:
        return None
    c = tight_crop(col, a)
    if c[0] is None:
        return None
    img = finish(c[0], c[1], long_edge)
    img.save(outdir / name, optimize=True)
    return {"file": name, "w": img.width, "h": img.height,
            "source": path.name, "backdrop": kind}

if __name__ == "__main__":
    print("module — driven by prepare_library.py")
