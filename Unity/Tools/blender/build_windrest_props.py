"""Windrest props for the polish pass: the small things that make the village square feel lived in, in the same round,
warm, hand-made style as the Windrest kit (it reuses that kit's building helpers from
Unreal/Tools/blender/build_windrest_kit.py, read only). Units: metres, +Z up, origin at the base centre.

  blender --background --factory-startup --python build_windrest_props.py -- <build_windrest_kit.py> <output folder>
"""
import math
import random
import sys

ARGS = sys.argv[sys.argv.index("--") + 1:]
KIT_SRC, OUT_DIR = ARGS[0], ARGS[1]
src = open(KIT_SRC, encoding="utf-8").read()
cut = src.index('\npath_segment("SM_Path_Cobble"')          # helpers and piece builders only, no kit export
g = {"__name__": "kit_helpers", "__file__": KIT_SRC}
sys.argv = [sys.argv[0], "--", OUT_DIR]
exec(compile(src[:cut], KIT_SRC, "exec"), g)
globals().update({k: v for k, v in g.items() if not k.startswith("__")})
import bpy  # noqa: E402

random.seed(23)


def barrel():
    reset()
    o = add_cyl("staves", 0.3, 0.9, (0, 0, 0.45), "MI_Wood", verts=16)
    for v in o.data.vertices:                    # bulge in the middle like a real barrel
        k = 1.0 + 0.16 * math.cos((v.co.z / 0.45) * math.pi / 2)
        v.co.x *= k
        v.co.y *= k
    sub = o.modifiers.new("sub", "SUBSURF"); sub.levels = 1
    for z in (0.12, 0.45, 0.78):
        r = 0.3 * (1.0 + 0.16 * math.cos(((z - 0.45) / 0.45) * math.pi / 2)) + 0.012
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.018, location=(0, 0, z), major_segments=20, minor_segments=4)
        bpy.context.active_object.data.materials.append(mat("MI_Brass"))
    add_cyl("lid", 0.29, 0.03, (0, 0, 0.9), "MI_WoodFloor", verts=16)
    finish("SM_Barrel")


def cart():
    reset()
    add_cube("bed", (2.2, 1.25, 0.12), (0, 0, 0.72), "MI_WoodFloor", bevel=0.02)
    for sy in (-1, 1):
        add_cube("side", (2.2, 0.06, 0.38), (0, sy * 0.62, 0.95), "MI_Wood", bevel=0.015)
    add_cube("back", (0.06, 1.25, 0.38), (-1.08, 0, 0.95), "MI_Wood", bevel=0.015)
    for sy in (-1, 1):
        w = add_cyl("wheel", 0.5, 0.08, (0.15, sy * 0.72, 0.5), "MI_Wood", verts=20, rot=(math.pi / 2, 0, 0))
        add_cyl("hub", 0.09, 0.14, (0.15, sy * 0.72, 0.5), "MI_Brass", verts=10, rot=(math.pi / 2, 0, 0))
        for k in range(6):
            a = k * math.pi / 3
            add_cube("spoke", (0.04, 0.04, 0.82), (0.15, sy * 0.72, 0.5), "MI_Wood", bevel=0.0, rot=(0, a, 0))
        add_cube("shaft", (1.8, 0.06, 0.06), (1.85, sy * 0.45, 0.62), "MI_Wood", bevel=0.01, rot=(0, math.radians(8), 0))
    add_cube("axle", (0.08, 1.5, 0.08), (0.15, 0, 0.5), "MI_Wood", bevel=0.01)
    for k in range(5):                           # a load of sacks and a crate
        add_blob("sack", 0.25, (-0.6 + k * 0.32, random.uniform(-0.3, 0.3), 1.0), "MI_Burlap", squash=(1.1, 0.9, 0.7), lumps=0.08, subdiv=2)
    add_cube("crate", (0.5, 0.5, 0.42), (0.75, 0.2, 1.0), "MI_WoodFloor", bevel=0.02)
    finish("SM_Cart")


def cloth_line(name, length, posts, colours, flags=False):
    reset()
    h = 2.3
    if posts:
        for x in (-length / 2, length / 2):
            add_cube("post", (0.09, 0.09, h + 0.1), (x, 0, (h + 0.1) / 2), "MI_Wood", bevel=0.015)
            add_cube("arm", (0.06, 0.4, 0.06), (x, 0, h), "MI_Wood", bevel=0.01)
    n = 16
    pts = []
    for i in range(n + 1):                       # a sagging line
        t = i / n
        x = -length / 2 + t * length
        z = h - 0.35 * math.sin(t * math.pi) * (length / 6.0)
        pts.append((x, 0, z))
    for a, b in zip(pts, pts[1:]):
        mid = ((a[0] + b[0]) / 2, 0, (a[2] + b[2]) / 2)
        ang = math.atan2(b[2] - a[2], b[0] - a[0])
        add_cyl("rope", 0.008, math.dist(a, b) * 1.02, mid, "MI_Burlap", verts=5, rot=(0, math.pi / 2 - ang, 0))
    k = 0
    if flags:
        for i in range(1, n, 1):
            x, _, z = pts[i]
            bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.17, depth=0.02, location=(x, 0, z - 0.17), rotation=(math.pi / 2, 0, 0))
            o = bpy.context.active_object
            o.rotation_euler = (math.pi / 2, math.pi, 0)
            o.scale = (1.0, 1.0, 1.0)
            o.data.materials.append(mat(colours[k % len(colours)])); k += 1
    else:
        for i in range(2, n - 1, 3):
            x, _, z = pts[i]
            w, d = random.uniform(0.45, 0.75), random.uniform(0.55, 0.85)
            c = add_cube("cloth", (w, 0.025, d), (x, 0, z - d / 2 - 0.02), colours[k % len(colours)], bevel=0.01, rot=(random.uniform(-0.1, 0.1), 0, 0))
            wobble(c, 0.02); k += 1
    finish(name)


def flower_box():
    reset()
    add_cube("box", (1.2, 0.3, 0.24), (0, 0, 0.12), "MI_Wood", bevel=0.02)
    add_cube("soil", (1.12, 0.24, 0.04), (0, 0, 0.23), "MI_PathDirt", bevel=0.0)
    for i in range(9):
        add_blob("leaves", 0.1, (-0.5 + i * 0.125, random.uniform(-0.05, 0.05), 0.3), "MI_Foliage", squash=(1, 0.9, 0.8), lumps=0.2, subdiv=1)
        add_blob("bloom", 0.055, (-0.5 + i * 0.125 + 0.03, random.uniform(-0.06, 0.06), 0.4), random.choice(("MI_FlowerBed", "MI_Cloth_Red", "MI_Sailcloth")), lumps=0.1, subdiv=1)
    finish("SM_FlowerBox")


def sacks():
    reset()
    for (x, y, z, r) in ((0, 0, 0.28, 0.32), (0.5, 0.15, 0.25, 0.28), (0.22, -0.4, 0.24, 0.27), (0.25, -0.05, 0.65, 0.26)):
        s = add_blob("sack", r, (x, y, z), "MI_Burlap", squash=(1.0, 0.85, 1.05), lumps=0.07, subdiv=2)
        add_cyl("tie", 0.06, 0.08, (x, y, z + r * 1.0), "MI_Burlap", verts=8)
    finish("SM_Sacks")


def hay_bale():
    reset()
    add_cube("hay", (1.1, 0.6, 0.5), (0, 0, 0.25), "MI_Hay", bevel=0.09, segments=3)
    for x in (-0.3, 0.3):
        add_cube("band", (0.04, 0.62, 0.52), (x, 0, 0.25), "MI_Burlap", bevel=0.01)
    finish("SM_HayBale")


def firewood():
    reset()
    for row in range(4):
        for i in range(6 - row % 2):
            add_cyl("log", random.uniform(0.07, 0.09), 0.9, (0, -0.45 + i * 0.18 + (row % 2) * 0.09, 0.09 + row * 0.155), "MI_Wood", verts=8, rot=(0, math.pi / 2, 0))
    finish("SM_Firewood")


def well():
    reset()
    for k in range(14):                          # a ring of rounded stones
        a = k * math.pi * 2 / 14
        add_blob("stone", 0.32, (math.cos(a) * 0.95, math.sin(a) * 0.95, 0.35), "MI_Stone", squash=(1.0, 0.8, 1.2), lumps=0.12, subdiv=2)
    add_cyl("rim", 1.12, 0.12, (0, 0, 0.72), "MI_Stone", verts=24)
    add_cyl("water", 0.8, 0.05, (0, 0, 0.35), "MI_Water", verts=20)
    for sx in (-1, 1):
        add_cube("post", (0.12, 0.12, 2.3), (sx * 1.0, 0, 1.15), "MI_Wood", bevel=0.02)
    add_cyl("winch", 0.08, 2.1, (0, 0, 1.75), "MI_Wood", verts=10, rot=(0, math.pi / 2, 0))
    roof("roof", 2.6, 1.4, 0.6, 2.35, "MI_RoofTerracotta", overhang=0.15, sag=0.06)
    add_cyl("bucket", 0.16, 0.26, (0.2, 0, 1.25), "MI_Wood", verts=12, r2=0.19)
    add_cyl("rope", 0.012, 0.4, (0.2, 0, 1.55), "MI_Burlap", verts=5)
    finish("SM_Well")


def trough():
    reset()
    add_cube("trough", (1.8, 0.6, 0.5), (0, 0, 0.35), "MI_Wood", bevel=0.03)
    add_cube("water", (1.66, 0.46, 0.04), (0, 0, 0.56), "MI_Water", bevel=0.0)
    for x in (-0.7, 0.7):
        add_cube("leg", (0.12, 0.64, 0.15), (x, 0, 0.075), "MI_Wood", bevel=0.02)
    finish("SM_Trough")


def potted_plant():
    reset()
    add_cyl("pot", 0.2, 0.32, (0, 0, 0.16), "MI_RoofTerracotta", verts=14, r2=0.25)
    add_cyl("lip", 0.27, 0.06, (0, 0, 0.33), "MI_RoofTerracotta", verts=14)
    for i in range(5):
        add_blob("leaves", random.uniform(0.16, 0.22), (random.uniform(-0.12, 0.12), random.uniform(-0.12, 0.12), 0.5 + random.uniform(0, 0.15)), "MI_Foliage", lumps=0.2, subdiv=2)
    for i in range(4):
        add_blob("bloom", 0.06, (random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2), 0.68), "MI_FlowerBed", lumps=0.1, subdiv=1)
    finish("SM_PottedPlant")


def bush():
    reset()
    for i in range(7):
        a = random.uniform(0, math.pi * 2)
        r = random.uniform(0, 0.6)
        add_blob("leaves", random.uniform(0.45, 0.7), (math.cos(a) * r, math.sin(a) * r, 0.45 + random.uniform(0, 0.3)), "MI_Foliage", squash=(1, 1, 0.85), lumps=0.22, subdiv=2)
    finish("SM_Bush")


barrel()
cart()
cloth_line("SM_LaundryLine", 5.0, True, ("MI_Sailcloth", "MI_Cloth_Blue", "MI_Cloth_Red", "MI_Plaster", "MI_Cloth_Yellow"))
cloth_line("SM_Bunting", 10.0, False, ("MI_Cloth_Red", "MI_Cloth_Yellow", "MI_Cloth_Blue", "MI_Sailcloth"), flags=True)
flower_box()
sacks()
hay_bale()
firewood()
well()
trough()
potted_plant()
bush()
print("LS_PROPS_OK", flush=True)
