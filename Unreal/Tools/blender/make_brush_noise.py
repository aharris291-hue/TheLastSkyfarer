"""Generates T_BrushNoise.png: a seamless 512x512 painterly noise texture for the painterly master materials.

R = soft paint blotches (low frequency), G = brush-stroke streaks (stretched), B = fine grain.
Run with Blender (it bundles numpy):
  blender --background --factory-startup --python make_brush_noise.py -- <output.png>
"""
import sys

import bpy
import numpy as np

SIZE = 512
out = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "T_BrushNoise.png"
rng = np.random.default_rng(1729)
u, v = np.meshgrid(np.arange(SIZE) / SIZE, np.arange(SIZE) / SIZE)


def periodic(freqs, stretch=(1.0, 1.0), octaves=24):
    """Sum of random sine waves with integer frequencies, so the texture tiles seamlessly."""
    acc = np.zeros((SIZE, SIZE))
    for _ in range(octaves):
        fx = int(rng.integers(freqs[0], freqs[1] + 1)) * stretch[0]
        fy = int(rng.integers(freqs[0], freqs[1] + 1)) * stretch[1]
        sx, sy = rng.choice([-1, 1], 2)
        phase = rng.uniform(0, 2 * np.pi)
        acc += np.sin(2 * np.pi * (sx * round(fx) * u + sy * round(fy) * v) + phase) / max(1.0, (fx * fx + fy * fy) ** 0.25)
    acc -= acc.min()
    return acc / acc.max()


def soften(x, lo=0.3, hi=0.7):
    # Posterize lightly into soft bands, like dabs of paint.
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


blotch = soften(periodic((1, 4)))
strokes = soften(periodic((2, 10), stretch=(1.0, 0.25)), 0.25, 0.75)
grain = periodic((16, 48), octaves=40)
rgba = np.stack([blotch, strokes, grain, np.ones_like(blotch)], axis=-1).astype(np.float32)

img = bpy.data.images.new("T_BrushNoise", SIZE, SIZE, alpha=True)
img.colorspace_settings.name = "Non-Color"
img.pixels.foreach_set(rgba.ravel())
img.filepath_raw = out
img.file_format = "PNG"
img.save()
print("LS_TEXTURE_OK " + out)
