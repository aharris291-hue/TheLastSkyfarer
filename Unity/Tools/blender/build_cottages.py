"""Windrest cottages, polish pass 3: real architecture on the same 8 x 8 m footprint and 6 m walls as art pass 1 (so
every placement and collision box on Brindle stays the same, and the door is still on the -Y side):

  * a foundation of rounded fieldstones, two courses high;
  * plaster walls held by a full timber frame: corner posts, sill and top plates, a mid rail, studs and braces;
  * a deep roof of overlapping shingle rows with a ridge cap and wide overhangs;
  * a fieldstone chimney with a cap;
  * framed windows with mullions, glazing, painted shutters and window boxes of flowers;
  * a plank door with trim, iron hinges, a stone step and a little porch roof on brackets.

Three variants: SM_Cottage_A (terracotta roof, green shutters), SM_Cottage_B (green roof, red shutters, a dormer),
SM_Cottage_Blue (blue roof, blue shutters, a lean-to woodshed: Elias's workshop and the Bluff houses use it).
Reuses the Windrest kit's helpers (Unreal/Tools/blender/build_windrest_kit.py, read only).

  blender --background --factory-startup --python build_cottages.py -- <build_windrest_kit.py> <output folder>
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

W, D, WALL, BASE = 8.0, 8.0, 6.0, 0.9
ROOF_H = 3.2


def foundation():
    for course, z in enumerate((0.22, 0.62)):
        for side in range(4):
            length = W if side % 2 == 0 else D
            n = int(length / 0.75)
            for i in range(n + 1):
                t = -length / 2 + length * i / n + (0.37 if course else 0.0)
                if t > length / 2:
                    continue
                if side == 0:
                    p = (t, -D / 2 - 0.08, z)
                elif side == 1:
                    p = (W / 2 + 0.08, t, z)
                elif side == 2:
                    p = (t, D / 2 + 0.08, z)
                else:
                    p = (-W / 2 - 0.08, t, z)
                if side == 0 and abs(t) < 0.9 and course == 1:
                    continue                                   # leave room for the door
                add_blob("stone", 0.27, p, "MI_CliffRock", squash=(1.3, 0.75, 0.52), lumps=0.2, subdiv=1)
    add_cube("plinth", (W + 0.1, D + 0.1, BASE), (0, 0, BASE / 2), "MI_Stone", bevel=0.1)


def frame(walls_z0):
    h = WALL - walls_z0
    zc = walls_z0 + h / 2
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_cube("post", (0.32, 0.32, h), (sx * (W / 2 + 0.02), sy * (D / 2 + 0.02), zc), "MI_Wood", bevel=0.04)
    for side, (length, axis) in enumerate(((W, "x"), (D, "y"), (W, "x"), (D, "y"))):
        sgn = -1 if side < 2 else 1
        off = (D / 2 + 0.06) if axis == "x" else (W / 2 + 0.06)
        for z, th in ((walls_z0 + 0.12, 0.26), (WALL - 0.12, 0.26), (walls_z0 + h * 0.48, 0.2)):
            size = (length + 0.2, 0.2, th) if axis == "x" else (0.2, length + 0.2, th)
            pos = (0, sgn * off, z) if axis == "x" else (sgn * off, 0, z)
            add_cube("rail", size, pos, "MI_Wood", bevel=0.03)
        studs = [-length * 0.32, length * 0.32]
        for t in studs:
            size = (0.2, 0.18, h) if axis == "x" else (0.18, 0.2, h)
            pos = (t, sgn * off, zc) if axis == "x" else (sgn * off, t, zc)
            add_cube("stud", size, pos, "MI_Wood", bevel=0.03)
        for k, t in enumerate((-length * 0.44, length * 0.44)):           # braces near the corners
            ang = math.radians(42 if k == 0 else -42)
            length_b = h * 0.48 / math.cos(ang)
            if axis == "x":
                add_cube("brace", (0.16, 0.16, length_b), (t * 0.8, sgn * off, walls_z0 + h * 0.74), "MI_Wood", bevel=0.02, rot=(0, ang, 0))
            else:
                add_cube("brace", (0.16, 0.16, length_b), (sgn * off, t * 0.8, walls_z0 + h * 0.74), "MI_Wood", bevel=0.02, rot=(ang, 0, 0))


def shingled_roof(roof_mat, overhang=0.75):
    roof("roof_core", W, D, ROOF_H, WALL, roof_mat, overhang=overhang, sag=0.14)
    # Shingle rows down each slope (the roof runs along X, sloping to +-Y).
    half_d = D / 2 + overhang
    rows = 11
    for sy in (-1, 1):
        for r in range(rows):
            t0 = r / rows
            t = 1 - t0
            y = sy * half_d * (1 - t * 0.98)
            z = WALL - overhang * 0.6 + gable_z(abs(y) / half_d * (1 if True else 1) * 1.0 - 0.0, ROOF_H + overhang * 0.6) if False else None
            yy = sy * half_d * (r + 0.5) / rows
            zz = WALL - overhang * 0.6 + gable_z(abs(yy) / half_d, ROOF_H + overhang * 0.6) + 0.16
            slope = math.atan2(ROOF_H + overhang * 0.6, half_d) * (1.5 * (abs(yy) / half_d) ** 0.5)
            for seg in range(3):
                x0 = -W / 2 - overhang + (W + 2 * overhang) * (seg + 0.5) / 3 + (0.35 if r % 2 else 0.0) - 0.17
                add_cube("shingles", ((W + 2 * overhang) / 3 + 0.05, half_d / rows * 1.25, 0.09), (x0, yy, zz), roof_mat, bevel=0.03,
                         rot=(-sy * slope, 0, random.uniform(-0.01, 0.01)))
    ridge = add_cyl("ridge", 0.22, W + 2 * overhang + 0.1, (0, 0, WALL + ROOF_H + 0.1), roof_mat, verts=10, rot=(0, math.pi / 2, 0))


def gables():
    for sx in (-1, 1):
        mesh = bpy.data.meshes.new("gable")
        bm = bmesh.new()
        steps = 12
        pts = [bm.verts.new((sx * (W / 2 - 0.02), (-1 + 2 * j / steps) * D / 2, WALL + gable_z(-1 + 2 * j / steps, ROOF_H - 0.2))) for j in range(steps + 1)]
        bm.faces.new(pts)
        bm.to_mesh(mesh)
        bm.free()
        gb = bpy.data.objects.new("gable", mesh)
        bpy.context.scene.collection.objects.link(gb)
        sol = gb.modifiers.new("thick", "SOLIDIFY"); sol.thickness = 0.28
        gb.data.materials.append(mat("MI_Plaster"))
        # timber king post and a small round window in each gable
        add_cube("kingpost", (0.22, 0.2, ROOF_H - 0.4), (sx * (W / 2 + 0.05), 0, WALL + (ROOF_H - 0.4) / 2), "MI_Wood", bevel=0.03)
        win = add_cyl("gable_window", 0.42, 0.12, (sx * (W / 2 + 0.06), 0.9, WALL + 1.25), "MI_Wood", verts=16, rot=(0, math.pi / 2, 0))
        add_cyl("gable_glass", 0.32, 0.14, (sx * (W / 2 + 0.07), 0.9, WALL + 1.25), "MI_Glass", verts=16, rot=(0, math.pi / 2, 0))


def window(x, y, z, face, shutter_mat, box=True, w=1.1, h=1.2):
    """face: 'f' (-Y), 'b' (+Y), 'l' (-X), 'r' (+X)."""
    def place(dx, dy, dz, sx, sy, sz):
        if face in "fb":
            s = -1 if face == "f" else 1
            return (x + dx, y + s * dy, z + dz), (sx, sy, sz)
        s = -1 if face == "l" else 1
        return (x + s * dy, y + dx, z + dz), (sy, sx, sz)
    p, sz = place(0, 0.02, 0, w, 0.1, h); add_cube("glass", sz, p, "MI_Glass", bevel=0.0)
    for dz in (-h / 2, h / 2):
        p, sz = place(0, 0.1, dz, w + 0.24, 0.16, 0.14); add_cube("frame", sz, p, "MI_Wood", bevel=0.03)
    for dx in (-w / 2, w / 2):
        p, sz = place(dx, 0.1, 0, 0.14, 0.16, h + 0.2); add_cube("frame", sz, p, "MI_Wood", bevel=0.03)
    p, sz = place(0, 0.08, 0, 0.07, 0.08, h); add_cube("mullion", sz, p, "MI_Wood", bevel=0.0)
    p, sz = place(0, 0.08, 0, w, 0.08, 0.07); add_cube("mullion", sz, p, "MI_Wood", bevel=0.0)
    for sxs in (-1, 1):                                                   # shutters, opened out
        p, sz = place(sxs * (w / 2 + 0.36), 0.12, 0, 0.6, 0.07, h + 0.05); add_cube("shutter", sz, p, shutter_mat, bevel=0.03)
        for k in range(3):
            p, sz = place(sxs * (w / 2 + 0.36), 0.17, -h / 2 + 0.25 + k * (h - 0.5) / 2, 0.5, 0.03, 0.06); add_cube("slat", sz, p, "MI_Wood", bevel=0.0)
    if box:
        p, sz = place(0, 0.32, -h / 2 - 0.25, w + 0.2, 0.36, 0.3); add_cube("windowbox", sz, p, "MI_Wood", bevel=0.04)
        for k in range(4):
            p, _ = place(-w / 2 + 0.15 + k * (w - 0.3) / 3, 0.34, -h / 2 - 0.02, 0, 0, 0)
            add_blob("flowers", 0.2, p, random.choice(("MI_FlowerBed", "MI_Foliage")), squash=(1.2, 0.8, 0.8), lumps=0.3, subdiv=1)


def door(shutter_mat):
    y = -D / 2 - 0.08
    add_cube("door", (1.3, 0.12, 2.3), (0, y, BASE + 1.15), shutter_mat, bevel=0.03)
    for k in range(4):
        add_cube("plank", (0.03, 0.14, 2.25), (-0.48 + k * 0.32, y - 0.02, BASE + 1.15), "MI_Wood", bevel=0.0)
    for z in (BASE + 0.45, BASE + 1.85):
        add_cube("hinge", (0.9, 0.05, 0.07), (-0.2, y - 0.07, z), "MI_Brass", bevel=0.01)
    add_cube("trim_top", (1.75, 0.2, 0.22), (0, y - 0.02, BASE + 2.4), "MI_Wood", bevel=0.03)
    for sx in (-1, 1):
        add_cube("trim_side", (0.2, 0.2, 2.45), (sx * 0.78, y - 0.02, BASE + 1.2), "MI_Wood", bevel=0.03)
    add_blob("step", 0.55, (0, y - 0.55, BASE - 0.25), "MI_Stone", squash=(1.6, 0.9, 0.45), lumps=0.08, subdiv=2)
    add_cube("porch_roof", (2.2, 1.0, 0.12), (0, y - 0.45, BASE + 2.85), "MI_Wood", bevel=0.03, rot=(math.radians(-14), 0, 0))
    for sx in (-1, 1):
        add_cube("bracket", (0.12, 0.7, 0.12), (sx * 0.9, y - 0.3, BASE + 2.55), "MI_Wood", bevel=0.02, rot=(math.radians(40), 0, 0))
    add_cube("lantern", (0.26, 0.26, 0.4), (1.25, y - 0.2, BASE + 2.0), "MI_Brass", bevel=0.04)


def chimney(x, y):
    top = WALL + ROOF_H + 1.0
    z = WALL - 0.5
    while z < top:
        for k in range(4):
            a = k * math.pi / 2 + (0.4 if int(z * 2) % 2 else 0)
            add_blob("chimney_stone", 0.33, (x + math.cos(a) * 0.32, y + math.sin(a) * 0.32, z), "MI_Stone", squash=(1.1, 1.1, 0.7), lumps=0.1, subdiv=1)
        z += 0.42
    add_cube("chimney_core", (0.9, 0.9, top - WALL + 0.5), (x, y, (top + WALL - 0.5) / 2), "MI_Stone", bevel=0.08)
    add_cube("chimney_cap", (1.25, 1.25, 0.18), (x, y, top + 0.1), "MI_Stone", bevel=0.05)
    add_cyl("chimney_pot", 0.2, 0.45, (x, y, top + 0.4), "MI_RoofTerracotta", verts=10)


def cottage(name, roof_mat, shutter_mat, dormer=False, shed=False, seed=1):
    reset()
    random.seed(seed)
    foundation()
    walls = add_cube("walls", (W, D, WALL - BASE), (0, 0, BASE + (WALL - BASE) / 2), "MI_Plaster", bevel=0.12)
    wobble(walls, 0.04)
    frame(BASE)
    shingled_roof(roof_mat)
    gables()
    chimney(W * 0.27, D * 0.18)
    door(shutter_mat)
    for sx in (-1, 1):
        window(sx * W * 0.3, -D / 2 - 0.08, BASE + 2.3, "f", shutter_mat)
        window(sx * W * 0.25, D / 2 + 0.08, BASE + 2.3, "b", shutter_mat, box=False)
    window(-W / 2 - 0.08, -D * 0.12, BASE + 2.3, "l", shutter_mat)
    window(W / 2 + 0.08, D * 0.12, BASE + 2.3, "r", shutter_mat)
    if dormer:
        add_cube("dormer", (1.6, 1.4, 1.3), (-W * 0.18, -D * 0.2, WALL + 1.1), "MI_Plaster", bevel=0.08)
        add_cube("dormer_roof", (2.0, 1.7, 0.14), (-W * 0.18, -D * 0.22, WALL + 1.85), roof_mat, bevel=0.04, rot=(math.radians(-18), 0, 0))
        window(-W * 0.18, -D * 0.2 - 0.72, WALL + 1.05, "f", shutter_mat, box=False, w=0.8, h=0.8)
    if shed:
        add_cube("shed_wall", (0.12, 3.6, 2.4), (-W / 2 - 1.5, 0.6, 1.2), "MI_Wood", bevel=0.03)
        add_cube("shed_roof", (2.0, 4.0, 0.12), (-W / 2 - 0.95, 0.6, 2.6), roof_mat, bevel=0.03, rot=(0, math.radians(-16), 0))
        for k in range(5):
            for j in range(3):
                add_cyl("log", 0.12, 1.1, (-W / 2 - 0.9, -0.6 + k * 0.42, 0.14 + j * 0.24), "MI_Wood", verts=8, rot=(0, math.pi / 2, 0))
    finish(name)


cottage("SM_Cottage_A", "MI_RoofTerracotta", "MI_RoofGreen", seed=2)
cottage("SM_Cottage_B", "MI_RoofGreen", "MI_Cloth_Red", dormer=True, seed=4)
cottage("SM_Cottage_Blue", "MI_RoofBlue", "MI_RoofBlue", shed=True, seed=6)
print("LS_COTTAGES_OK", flush=True)
