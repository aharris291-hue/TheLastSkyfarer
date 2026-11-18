"""Stylised Windrest trees for the polish pass: a gently curved trunk that splits into branches, each ending in a
cluster of plump, lumpy foliage clumps (big shapes first, small clumps on the outside for a painted silhouette).
Same names, origins and sizes as the art-pass-1 trees, so every placement on Brindle Isle stays the same:
  SM_Tree_Round    the island's broadleaf tree (about 6 m wide, 6.5 m tall)
  SM_Tree_Blossom  the orchard's fruit trees in blossom (about 5.5 m wide and tall), pink blossom and a few apples
Reuses the Windrest kit's helpers (Unreal/Tools/blender/build_windrest_kit.py, read only).

  blender --background --factory-startup --python build_trees.py -- <build_windrest_kit.py> <output folder>
"""
import math
import random
import sys

ARGS = sys.argv[sys.argv.index("--") + 1:]
KIT_SRC, OUT_DIR = ARGS[0], ARGS[1]
src = open(KIT_SRC, encoding="utf-8").read()
cut = src.index('\npath_segment("SM_Path_Cobble"')
g = {"__name__": "kit_helpers", "__file__": KIT_SRC}
sys.argv = [sys.argv[0], "--", OUT_DIR]
exec(compile(src[:cut], KIT_SRC, "exec"), g)
globals().update({k: v for k, v in g.items() if not k.startswith("__")})
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402


def limb(a, b, r0, r1, material):
    """A tapered branch from a to b."""
    d = Vector(b) - Vector(a)
    o = add_cyl("limb", r0, d.length, tuple((Vector(a) + Vector(b)) / 2), material, verts=10, r2=r1)
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    return o


def tree(name, height, spread, leaf, extra=None, seed=1):
    reset()
    random.seed(seed)
    # Trunk: three slightly offset segments with a flared root.
    pts = [Vector((0, 0, 0)), Vector((0.08, -0.05, height * 0.22)), Vector((-0.05, 0.06, height * 0.42))]
    for k in range(2):
        limb(pts[k], pts[k + 1], 0.34 - k * 0.1, 0.24 - k * 0.08, "MI_Wood")
    for k in range(5):                                   # root flare
        a = k * 2 * math.pi / 5 + 0.3
        limb((0, 0, 0.25), (math.cos(a) * 0.55, math.sin(a) * 0.55, -0.05), 0.12, 0.05, "MI_Wood")
    crown = pts[-1]
    tips = []
    n = 5
    for k in range(n):                                   # main branches fanning out and up
        a = k * 2 * math.pi / n + random.uniform(-0.3, 0.3)
        r = spread * random.uniform(0.32, 0.45)
        tip = crown + Vector((math.cos(a) * r, math.sin(a) * r, height * random.uniform(0.22, 0.34)))
        limb(crown, tip, 0.15, 0.06, "MI_Wood")
        tips.append(tip)
    tips.append(crown + Vector((0, 0, height * 0.42)))
    limb(crown, tips[-1], 0.16, 0.07, "MI_Wood")
    # Foliage: a big clump on every branch tip, then smaller clumps around them.
    for t in tips:
        add_blob("leaves", spread * random.uniform(0.2, 0.25), tuple(t), leaf, squash=(1.0, 1.0, 0.82), lumps=0.22, subdiv=2)
        for j in range(4):
            a = random.uniform(0, 2 * math.pi)
            off = Vector((math.cos(a) * spread * 0.17, math.sin(a) * spread * 0.17, random.uniform(-0.25, 0.45)))
            add_blob("leaves", spread * random.uniform(0.1, 0.15), tuple(t + off), leaf, squash=(1.0, 1.0, 0.85), lumps=0.25, subdiv=2)
    if extra:
        extra(tips, spread)
    finish(name)


def blossom_and_apples(tips, spread):
    for t in tips:
        for j in range(5):
            a = random.uniform(0, 2 * math.pi)
            p = t + Vector((math.cos(a) * spread * 0.2, math.sin(a) * spread * 0.2, random.uniform(0.0, 0.5)))
            add_blob("blossom", spread * 0.06, tuple(p), "MI_FlowerBed", lumps=0.2, subdiv=1)
        for j in range(2):
            a = random.uniform(0, 2 * math.pi)
            p = t + Vector((math.cos(a) * spread * 0.18, math.sin(a) * spread * 0.18, random.uniform(-0.45, -0.2)))
            add_blob("apple", 0.08, tuple(p), "MI_Cloth_Red", lumps=0.05, subdiv=1)


tree("SM_Tree_Round", 6.4, 6.2, "MI_Foliage", seed=3)
tree("SM_Tree_Blossom", 5.4, 5.6, "MI_FoliageBlossom", extra=blossom_and_apples, seed=7)
print("LS_TREES_OK", flush=True)
