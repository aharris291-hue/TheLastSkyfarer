"""Windrest kit (art pass 1): stylized, round and warm pieces for Brindle Isle, per STYLE_GUIDE section 2
("rounded roofs, plump trees, bulging stone walls ... slight lean and wobble so it looks hand-made").

Builds each piece procedurally and exports one FBX per piece to the output folder. Material slots are named after
the painterly instances in /Game/LastSkyfarer/Materials/Instances (MI_Stone, MI_Plaster, ...), which the Unreal
import script assigns by name. Units: metres, +Z up, the piece's origin at its base centre.

  blender --background --factory-startup --python build_windrest_kit.py -- <output folder>
"""
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.getcwd()
os.makedirs(OUT, exist_ok=True)
random.seed(7)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    return m


def add_cube(name, size, loc, material, bevel=0.08, segments=2, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        b = o.modifiers.new("bevel", "BEVEL")
        b.width = bevel
        b.segments = segments
        b.limit_method = "ANGLE"
    o.data.materials.append(mat(material))
    return o


def add_cyl(name, r, h, loc, material, verts=12, r2=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=h, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat(material))
    return o


def add_blob(name, radius, loc, material, squash=(1, 1, 1), lumps=0.18, subdiv=2):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdiv, radius=radius, location=loc)
    o = bpy.context.active_object
    o.name = name
    for v in o.data.vertices:
        n = v.co.normalized()
        v.co = v.co * (1 + random.uniform(-lumps, lumps))
        v.co.x *= squash[0]
        v.co.y *= squash[1]
        v.co.z *= squash[2]
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat(material))
    return o


def wobble(o, amount=0.04):
    """Hand-made wobble: nudge vertices a little, more at the top."""
    for v in o.data.vertices:
        k = max(0.0, v.co.z) * 0.25 + 0.5
        v.co.x += random.uniform(-amount, amount) * k
        v.co.y += random.uniform(-amount, amount) * k


def finish(name):
    """Join everything into one mesh, apply modifiers, set the origin to the base centre and export."""
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        for m in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    o = bpy.context.active_object
    o.name = name
    bpy.context.scene.cursor.location = (0, 0, 0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    path = os.path.join(OUT, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False)
    print("LS_KIT " + path)


def gable_z(t, h):
    """Height of the rounded gable at t in -1..1 across the house (1 at the ridge, 0 at the eaves)."""
    return h * (1 - abs(t) ** 1.5)


def roof(name, w, d, h, z, material, overhang=0.5, sag=0.18):
    """A rounded gable roof with a soft ridge that sags a little in the middle, like an old roof."""
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    nx, ny = 10, 12
    half_w, half_d = w / 2 + overhang, d / 2 + overhang
    grid = []
    for i in range(nx + 1):
        x = -half_w + 2 * half_w * i / nx
        row = []
        for j in range(ny + 1):
            t = -1 + 2 * j / ny
            sag_here = sag * (1 - (x / half_w) ** 2) * (1 - abs(t))
            row.append(bm.verts.new((x, t * half_d, z - overhang * 0.6 + gable_z(t, h + overhang * 0.6) - sag_here)))
        grid.append(row)
    for i in range(nx):
        for j in range(ny):
            bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    s = o.modifiers.new("thick", "SOLIDIFY")
    s.thickness = 0.3
    bpy.ops.object.shade_smooth()
    o.data.materials.append(mat(material))
    return o


# ------------------------------------------------------------------ cottage (8 x 8 m footprint, 6 m walls)
def cottage(name, w=8.0, d=8.0, wall_h=6.0, roof_mat="MI_RoofTerracotta"):
    reset()
    base_h = 1.6
    add_cube("base", (w + 0.3, d + 0.3, base_h), (0, 0, base_h / 2), "MI_Stone", bevel=0.25, segments=3)
    upper = add_cube("upper", (w, d, wall_h - base_h), (0, 0, base_h + (wall_h - base_h) / 2), "MI_Plaster", bevel=0.15)
    # Timber frame: corner posts and a mid beam.
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_cube("post", (0.35, 0.35, wall_h - base_h), (sx * (w / 2 - 0.05), sy * (d / 2 - 0.05), base_h + (wall_h - base_h) / 2), "MI_Wood", bevel=0.05)
    add_cube("beam_f", (w + 0.1, 0.3, 0.3), (0, -d / 2 - 0.05, base_h + 0.15), "MI_Wood", bevel=0.05)
    add_cube("beam_b", (w + 0.1, 0.3, 0.3), (0, d / 2 + 0.05, base_h + 0.15), "MI_Wood", bevel=0.05)
    roof("roof", w, d, 3.2, wall_h, roof_mat)
    # Gable ends: plaster filling the rounded gable under the roof.
    for sx in (-1, 1):
        mesh = bpy.data.meshes.new("gable")
        bm = bmesh.new()
        steps = 12
        pts = [bm.verts.new((sx * (w / 2 - 0.05), (-1 + 2 * j / steps) * d / 2, wall_h + gable_z(-1 + 2 * j / steps, 3.0))) for j in range(steps + 1)]
        bm.faces.new(pts)
        bm.to_mesh(mesh)
        bm.free()
        g = bpy.data.objects.new("gable", mesh)
        bpy.context.scene.collection.objects.link(g)
        sol = g.modifiers.new("thick", "SOLIDIFY")
        sol.thickness = 0.3
        g.data.materials.append(mat("MI_Plaster"))
    add_cube("chimney", (0.9, 0.9, 3.0), (w * 0.28, d * 0.15, wall_h + 2.0), "MI_Stone", bevel=0.12)
    # Front: door, two windows with flower boxes, a lantern.
    add_cube("door", (1.3, 0.2, 2.3), (0, -d / 2 - 0.1, 1.15), "MI_Wood", bevel=0.1)
    for sx in (-1, 1):
        add_cube("window", (1.1, 0.15, 1.0), (sx * w * 0.3, -d / 2 - 0.08, base_h + 1.6), "MI_Wood", bevel=0.05)
        add_cube("flowerbox", (1.3, 0.4, 0.35), (sx * w * 0.3, -d / 2 - 0.25, base_h + 0.95), "MI_Wood", bevel=0.05)
        add_blob("flowers", 0.35, (sx * w * 0.3, -d / 2 - 0.25, base_h + 1.25), "MI_FlowerBed", squash=(1.9, 0.7, 0.6), lumps=0.3, subdiv=1)
    add_cube("lantern", (0.3, 0.3, 0.45), (w * 0.15 + 0.6, -d / 2 - 0.45, 2.6), "MI_Brass", bevel=0.05)
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and o.name in ("upper", "base"):
            wobble(o, 0.05)
    finish(name)


# ------------------------------------------------------------------ trees
def tree(name, canopy_mat, height=3.0, radius=2.6):
    reset()
    add_cyl("trunk", 0.35, height, (0, 0, height / 2), "MI_Wood", verts=8, r2=0.25)
    add_blob("canopy0", radius, (0, 0, height + radius * 0.6), canopy_mat, squash=(1, 1, 0.85))
    add_blob("canopy1", radius * 0.7, (radius * 0.6, 0.3, height + radius * 0.3), canopy_mat, squash=(1, 1, 0.8))
    add_blob("canopy2", radius * 0.65, (-radius * 0.5, -0.4, height + radius * 0.4), canopy_mat, squash=(1, 1, 0.8))
    finish(name)


# ------------------------------------------------------------------ windmill (tower and cap; the sails are separate so they can turn)
def windmill():
    reset()
    o = add_cyl("tower", 3.2, 16.0, (0, 0, 8.0), "MI_Stone", verts=16, r2=2.4)
    wobble(o, 0.06)
    add_cyl("band", 2.9, 0.4, (0, 0, 9.0), "MI_Wood", verts=16)
    add_cube("door", (1.4, 0.3, 2.4), (0, -3.15, 1.2), "MI_Wood", bevel=0.1)
    add_blob("cap", 3.0, (0, 0, 17.2), "MI_RoofTerracotta", squash=(1, 1, 0.75), lumps=0.03)
    add_cyl("hub", 0.5, 1.6, (0, -3.2, 17.0), "MI_Wood", verts=10, rot=(math.pi / 2, 0, 0))
    finish("SM_Windmill_Tower")

    reset()
    add_cyl("axle", 0.4, 0.8, (0, 0, 0), "MI_Wood", verts=10, rot=(math.pi / 2, 0, 0))
    for i in range(4):
        a = i * math.pi / 2
        arm = add_cube("arm", (0.25, 0.25, 10.0), (0, 0, 5.0), "MI_Wood", bevel=0.03)
        sail = add_cube("sail", (1.8, 0.08, 7.5), (0.9, 0, 6.2), "MI_Sailcloth", bevel=0.02)
        for p in (arm, sail):
            # Turn each arm around the axle (the world origin), not around its own centre.
            bpy.ops.object.select_all(action="DESELECT")
            p.select_set(True)
            bpy.context.view_layer.objects.active = p
            bpy.context.scene.cursor.location = (0, 0, 0)
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            p.rotation_euler = (0, a, 0)
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=False)
    finish("SM_Windmill_Sails")


# ------------------------------------------------------------------ small props
def fence():
    reset()
    for x in (-1.9, 0, 1.9):
        add_cube("post", (0.22, 0.22, 1.2), (x, 0, 0.6), "MI_Wood", bevel=0.04)
    for z in (0.45, 0.95):
        add_cube("rail", (4.0, 0.12, 0.16), (0, 0, z), "MI_Wood", bevel=0.03)
    finish("SM_Fence_4m")


def lantern_post():
    reset()
    add_cyl("post", 0.12, 2.8, (0, 0, 1.4), "MI_Wood", verts=8)
    add_cube("arm", (0.7, 0.1, 0.1), (0.3, 0, 2.7), "MI_Wood", bevel=0.02)
    add_cube("lamp", (0.3, 0.3, 0.42), (0.6, 0, 2.4), "MI_Brass", bevel=0.05)
    finish("SM_LanternPost")


def rocks():
    for i in range(3):
        reset()
        add_blob("rock", 1.0, (0, 0, 0.5), "MI_CliffRock", squash=(1.3 + i * 0.2, 1.0, 0.7), lumps=0.25, subdiv=2)
        finish("SM_Rock_%d" % i)


# ------------------------------------------------------------------ village square dressing
def market_stall():
    """4 x 3 m stall: wooden counter, corner posts and a striped awning that bows a little."""
    reset()
    add_cube("counter", (3.6, 1.2, 1.0), (0, -0.6, 0.5), "MI_Wood", bevel=0.08)
    for sx in (-1, 1):
        for sy in (-1, 1):
            add_cyl("post", 0.09, 2.6, (sx * 1.85, sy * 1.35, 1.3), "MI_Wood", verts=8)
    for i in range(6):
        stripe = add_cube("awning", (0.62, 3.4, 0.08), (-1.55 + i * 0.62, 0, 2.7), "MI_RoofTerracotta" if i % 2 == 0 else "MI_Sailcloth", bevel=0.02)
        for v in stripe.data.vertices:
            v.co.z -= 0.25 * (v.co.y / 1.7) ** 2   # the cloth bows down at the front and back
    for i in range(3):
        add_blob("goods", 0.3, (-1.1 + i * 1.1, -0.6, 1.15), "MI_FlowerBed" if i == 1 else "MI_Wheat", squash=(1.2, 1.0, 0.6), lumps=0.2, subdiv=1)
    finish("SM_MarketStall")


def fountain():
    """Round stone fountain: a wide basin, water, and a two-tier column."""
    reset()
    add_cyl("basin", 3.6, 1.0, (0, 0, 0.5), "MI_Stone", verts=24, r2=3.8)
    add_cyl("water", 3.3, 0.1, (0, 0, 0.85), "MI_Water", verts=24)
    add_cyl("column", 0.55, 2.6, (0, 0, 2.1), "MI_Stone", verts=12, r2=0.45)
    add_cyl("bowl", 1.2, 0.4, (0, 0, 3.3), "MI_Stone", verts=16, r2=0.6)
    add_cyl("bowl_water", 1.05, 0.06, (0, 0, 3.5), "MI_Water", verts=16)
    add_blob("finial", 0.35, (0, 0, 3.8), "MI_Brass", squash=(1, 1, 1.3), lumps=0.02, subdiv=2)
    finish("SM_Fountain")


def notice_board():
    reset()
    for sx in (-1, 1):
        add_cube("leg", (0.16, 0.16, 2.6), (sx * 1.3, 0, 1.3), "MI_Wood", bevel=0.03)
    add_cube("board", (2.6, 0.12, 1.5), (0, 0, 1.75), "MI_WoodFloor", bevel=0.04)
    add_cube("roof", (3.0, 0.7, 0.12), (0, 0, 2.65), "MI_RoofTerracotta", bevel=0.04, rot=(0.2, 0, 0))
    for i, (x, z) in enumerate(((-0.8, 1.9), (0.1, 2.0), (0.8, 1.7), (-0.3, 1.45), (0.6, 1.35))):
        add_cube("note", (0.45, 0.04, 0.55), (x, -0.08, z), "MI_Sailcloth", bevel=0.0, rot=(0, (i - 2) * 0.08, 0))
    finish("SM_NoticeBoard")


def planter():
    reset()
    add_cube("box", (1.6, 0.8, 0.6), (0, 0, 0.3), "MI_Wood", bevel=0.06)
    add_blob("flowers", 0.5, (0, 0, 0.75), "MI_FlowerBed", squash=(1.6, 0.8, 0.6), lumps=0.3, subdiv=2)
    finish("SM_Planter")


def bench():
    reset()
    add_cube("seat", (2.0, 0.5, 0.1), (0, 0, 0.5), "MI_Wood", bevel=0.03)
    add_cube("back", (2.0, 0.08, 0.5), (0, 0.24, 0.85), "MI_Wood", bevel=0.03)
    for sx in (-1, 1):
        add_cube("leg", (0.12, 0.5, 0.5), (sx * 0.85, 0, 0.25), "MI_Stone", bevel=0.03)
    finish("SM_Bench")


def grass_patch():
    """A 20 x 20 m patch of grass tufts (crossed cards) in the foliage material, so the meadows sway."""
    reset()
    mesh = bpy.data.meshes.new("grass")
    bm = bmesh.new()
    for _ in range(260):
        x, y = random.uniform(-10, 10), random.uniform(-10, 10)
        h = random.uniform(0.35, 0.8)
        w = random.uniform(0.25, 0.45)
        for a in (0.0, math.pi / 2):
            dx, dy = math.cos(a) * w, math.sin(a) * w
            lean = random.uniform(-0.12, 0.12)
            v = [bm.verts.new((x - dx, y - dy, 0)), bm.verts.new((x + dx, y + dy, 0)),
                 bm.verts.new((x + dx * 0.2 + lean, y + dy * 0.2, h)), bm.verts.new((x - dx * 0.2 + lean, y - dy * 0.2, h))]
            bm.faces.new(v)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("grass", mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat("MI_Grass"))
    finish("SM_GrassPatch")


def flower_bed():
    """A 6 x 3 m terrace bed of soil with clumps of flowers (Cloud Edge)."""
    reset()
    add_cube("soil", (6.0, 3.0, 0.4), (0, 0, 0.2), "MI_PathDirt", bevel=0.1)
    for i in range(9):
        add_blob("flowers", 0.55, (-2.4 + (i % 5) * 1.2, -0.7 + (i // 5) * 1.3, 0.55), "MI_FlowerBed", squash=(1.2, 1.1, 0.7), lumps=0.3, subdiv=1)
    finish("SM_FlowerBed")


def wind_ribbon():
    """Two crossed 1 x 1 m cards along +X with UVs running along the length, for the glowing wind streaks."""
    reset()
    mesh = bpy.data.meshes.new("ribbon")
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    for axis in ("y", "z"):
        pts = []
        for x, s in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)):
            pts.append(bm.verts.new((x, s, 0) if axis == "y" else (x, 0, s)))
        f = bm.faces.new(pts)
        for loop, (u, v) in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            loop[uv].uv = (u, v)
    bm.to_mesh(mesh)
    bm.free()
    o = bpy.data.objects.new("ribbon", mesh)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat("MI_WindRibbon"))
    finish("SM_WindRibbon")


wind_ribbon()
market_stall()
fountain()
notice_board()
planter()
bench()
grass_patch()
flower_bed()
cottage("SM_Cottage_A")
cottage("SM_Cottage_B", roof_mat="MI_RoofGreen")
cottage("SM_Cottage_Blue", roof_mat="MI_RoofBlue")
tree("SM_Tree_Round", "MI_Foliage")
tree("SM_Tree_Blossom", "MI_FoliageBlossom", height=2.4, radius=2.2)
windmill()
fence()
lantern_post()
rocks()
print("LS_KIT_OK")
