"""Measure Kieran's base body for a set of MPFB parameters: barefoot height and an estimated weight
(enclosed volume x 985 kg/m3, average human body density). Used to hit Adam's spec: 17 years, 5 ft 8 in, 145-155 lb.

  blender --background --python measure_body.py -- params.json [params2.json ...]
"""
import json
import os
import sys

import bmesh
import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_kieran as bk   # noqa: E402

files = sys.argv[sys.argv.index("--") + 1:]
for f in files:
    p = dict(bk.DEFAULT)
    for k, v in json.load(open(f)).items():
        p[k] = dict(p[k], **v) if isinstance(v, dict) and k in p else v
    body, rig = bk.build_body(p)
    zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    h = max(zs) - min(zs)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    holes = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=holes, sides=0)   # close the eye and mouth openings for a volume estimate
    vol = abs(bm.calc_volume(signed=True))
    bm.free()
    kg = vol * 985.0
    xs = [(body.matrix_world @ v.co).x for v in body.data.vertices if abs((body.matrix_world @ v.co).z - h * 0.81) < 0.02]
    print("LS_BODY %s height %.3f m (%.1f in) weight %.1f kg (%.0f lb) shoulder-width %.3f m" %
          (os.path.basename(f), h, h / 0.0254, kg, kg * 2.2046, max(xs) - min(xs)), flush=True)
