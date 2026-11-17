"""Measure Kieran's proportions from Adam's turnaround sheet (read-only reference).

Separates each of the five figures by finding the empty columns between them, builds a silhouette mask
(anything darker or more saturated than the white paper), then reports landmarks and the width profile
of the front and side figures in head units and as fractions of body height.

  blender --background --factory-startup --python measure_reference.py -- <turnaround.png> <out.json>
"""
import json
import sys

import bpy
import numpy as np

src, dst = sys.argv[-2], sys.argv[-1]
img = bpy.data.images.load(src)
w, h = img.size
px = np.array(img.pixels[:]).reshape(h, w, 4)[::-1, :, :3]   # row 0 = top
lum = px.mean(axis=2)
sat = px.max(axis=2) - px.min(axis=2)
mask = (lum < 0.9) | (sat > 0.12)

cols = mask.sum(axis=0)
figs, inside, start = [], False, 0
for x in range(w):
    if cols[x] > 3 and not inside:
        inside, start = True, x
    elif cols[x] <= 3 and inside:
        inside = False
        if x - start > 60:
            figs.append((start, x))
if inside:
    figs.append((start, w))
names = ["front", "three_quarter_front", "side", "three_quarter_rear", "rear"]
out = {"image": src, "size": [w, h], "figures": {}}
for name, (x0, x1) in zip(names, figs):
    m = mask[:, x0:x1]
    rows = np.where(m.any(axis=1))[0]
    top, bot = int(rows[0]), int(rows[-1])
    height = bot - top
    widths = [int(m[y].sum()) for y in range(h)]
    spans = []
    for y in range(h):
        xs = np.where(m[y])[0]
        spans.append([int(xs[0]), int(xs[-1])] if len(xs) else None)
    prof = []
    for k in range(101):   # width every 1% of height, as a fraction of height
        y = top + int(height * k / 100)
        sp = spans[y]
        prof.append(round((sp[1] - sp[0]) / height, 4) if sp else 0.0)
    # skin mask (warm brown, darker than cloth) to find the face/neck for the head measurement
    r, g, b = px[:, x0:x1, 0], px[:, x0:x1, 1], px[:, x0:x1, 2]
    skin = (r > g * 1.12) & (g > b * 1.05) & (lum[:, x0:x1] < 0.62) & (lum[:, x0:x1] > 0.18)
    out["figures"][name] = {"x": [x0, x1], "top": top, "bottom": bot, "height_px": height, "width_profile": prof,
                            "skin_rows": [int(skin[y].sum()) for y in range(top, bot + 1, max(1, height // 100))]}
json.dump(out, open(dst, "w"), indent=1)
for name, f in out["figures"].items():
    print("LS_FIG", name, f["x"], f["top"], f["bottom"], f["height_px"])
