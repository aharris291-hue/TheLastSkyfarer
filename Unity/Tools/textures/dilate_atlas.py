"""Fills the empty (black) background of a baked character atlas with the colour of the nearest painted island
(push-pull: average down a mip pyramid, then fill back up), so mipmaps never bleed black into the cloth at a
distance. Painted pixels are left exactly as they are.

  blender --background --factory-startup --python dilate_atlas.py -- <in.png> [<more.png> ...]   (overwrites each file)
Runs inside Blender for its bundled numpy (no extra installs).
"""
import sys

import bpy
import numpy as np


def push_pull(rgb, mask):
    if min(rgb.shape[:2]) <= 1:
        return rgb
    h, w = rgb.shape[:2]
    h2, w2 = (h + 1) // 2, (w + 1) // 2
    pad = np.zeros((h2 * 2, w2 * 2, 3)); pad[:h, :w] = rgb * mask[..., None]
    mpad = np.zeros((h2 * 2, w2 * 2)); mpad[:h, :w] = mask
    s = pad.reshape(h2, 2, w2, 2, 3).sum((1, 3))
    m = mpad.reshape(h2, 2, w2, 2).sum((1, 3))
    small = np.where(m[..., None] > 0, s / np.maximum(m, 1e-6)[..., None], 0)
    small = push_pull(small, (m > 0).astype(float))
    up = small.repeat(2, 0).repeat(2, 1)[:h, :w]
    return np.where(mask[..., None] > 0, rgb, up)


for path in sys.argv[sys.argv.index("--") + 1:]:
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:]).reshape(h, w, 4)
    rgb = px[..., :3] * 255.0
    mask = (rgb.sum(-1) > 6).astype(float)             # painted wherever it is not (near) black
    out = push_pull(rgb, mask) / 255.0
    px[..., :3] = out
    px[..., 3] = 1.0
    im.pixels[:] = px.ravel()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("LS_DILATE %s: %.0f%% painted" % (path, mask.mean() * 100), flush=True)
