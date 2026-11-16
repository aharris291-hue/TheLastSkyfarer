"""Character and prop design drafts as stylised 3D models, rendered to turnaround sheets for Adam's approval.

Kieran and Piko follow Adam's turnaround sheets (art_source/characters, read-only reference) and the palette in
CANON_SUMMARY; they are not redesigned. The Ancient Glider has no approved design yet, so this is a first draft in
the Windrest style (wood, sailcloth, brass, an Aerian-blue glyph). Nothing here goes into the game until Adam
approves it.

Each sheet shows front, three-quarter, side and back views with outlines, and a strip of the palette.

  blender --background --factory-startup --python character_drafts.py -- <output folder> [kieran piko glider]
"""
import math
import os
import sys

import bmesh
import bpy
import numpy as np

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [os.getcwd()]
OUT = ARGS[0]
WHICH = ARGS[1:] or ["kieran", "piko", "glider"]
os.makedirs(OUT, exist_ok=True)


def hexrgb(h):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (lin(int(h[1:3], 16)), lin(int(h[3:5], 16)), lin(int(h[5:7], 16)), 1.0)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(hexcol):
    name = "C" + hexcol
    m = bpy.data.materials.get(name)
    if not m:
        m = bpy.data.materials.new(name)
        m.diffuse_color = hexrgb(hexcol)
        m.roughness = 0.8
    return m


def finish_obj(o, col, smooth=True, subdiv=0):
    o.data.materials.append(mat(col))
    if smooth:
        for p in o.data.polygons:
            p.use_smooth = True
    if subdiv:
        m = o.modifiers.new("sub", "SUBSURF")
        m.levels = subdiv
        m.render_levels = subdiv
    return o


def sph(loc, scale, col, seg=24, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=seg // 2, radius=1, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = scale
    return finish_obj(o, col)


def box(loc, scale, col, bevel=0.3, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b = o.modifiers.new("bev", "BEVEL")
    b.width = min(scale) * bevel
    b.segments = 3
    return finish_obj(o, col)


def cyl(loc, r, depth, col, r2=None, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=depth, location=loc, rotation=rot)
    return finish_obj(bpy.context.active_object, col)


def torus(loc, R, r, col, rot=(0, 0, 0), scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=32, minor_segments=10, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.scale = scale
    return finish_obj(o, col)


def limb(a, b, r1, r2, col):
    """A tapered cylinder from point a to point b."""
    a, b = np.array(a), np.array(b)
    d = b - a
    length = float(np.linalg.norm(d))
    mid = (a + b) / 2
    rot_y = math.atan2(math.hypot(d[0], d[1]), d[2])
    rot_z = math.atan2(d[1], d[0])
    return cyl(tuple(mid), r1, length, col, r2=r2, rot=(0, rot_y, rot_z))


def tube(points, radius_fn, col):
    """A smooth tube along points (a bevelled curve), radius tapering by radius_fn(t)."""
    cu = bpy.data.curves.new("tube", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 6
    sp = cu.splines.new("NURBS")
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0], p[1], p[2], 1)
        sp.points[i].radius = radius_fn(i / (len(points) - 1))
    sp.use_endpoint_u = True
    sp.order_u = 4
    o = bpy.data.objects.new("tube", cu)
    bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat(col))
    return o


# ------------------------------------------------------------------ rendering a turnaround sheet
def srgb(h):
    return [int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)]


VIEWS = (("front", 0, 0), ("three_quarter", -35, 0), ("side", -90, 0), ("back", 180, 0))


def render_sheet(name, height, palette, cam_dist=None, target_z=None, width=None, views_def=VIEWS):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.show_shadows = True
    sh.shadow_intensity = 0.25
    sh.show_cavity = True
    sh.cavity_type = "BOTH"
    sh.show_object_outline = True
    sh.object_outline_color = (0.12, 0.09, 0.07)
    sc.display.render_aa = "16"
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"   # keep the palette true (AgX greys whites)
    sh.background_type = "VIEWPORT"
    sh.background_color = tuple(hexrgb("#EFE6D2")[:3])
    sc.render.resolution_x, sc.render.resolution_y = 640, 900
    # Group everything under one parent we can turn.
    root = bpy.data.objects.new("root", None)
    sc.collection.objects.link(root)
    for o in list(sc.objects):
        if o != root and o.parent is None and o.type in ("MESH", "CURVE"):
            o.parent = root
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(height, (width or 0) * 900 / 640) * 1.15
    tz = target_z if target_z is not None else height * 0.5
    dist = cam_dist or max(height, width or 0) * 4
    sc.camera = cam
    views = []
    for label, yaw, elev in views_def:
        e = math.radians(elev)
        cam.location = (0, -dist * math.cos(e), tz + dist * math.sin(e))
        cam.rotation_euler = (math.radians(90) - e, 0, 0)
        root.rotation_euler = (0, 0, math.radians(yaw))
        path = os.path.join(OUT, "_%s_%s.png" % (name, label))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        px = np.array(img.pixels[:]).reshape(900, 640, 4)
        views.append(px)
        bpy.data.images.remove(img)
        os.remove(path)
    # Sheet: four views side by side over a palette strip, on warm parchment.
    sheet = np.concatenate(views, axis=1)
    strip = np.ones((140, sheet.shape[1], 4))
    strip[:, :, :3] = np.array(srgb("#E6DAC0"))
    for i, h in enumerate(palette):
        x0 = 40 + i * 150
        strip[30:110, x0:x0 + 110, :3] = np.array(srgb(h))
    sheet = np.concatenate([strip, sheet], axis=0)   # image rows run bottom-up, so this puts the palette underneath
    out = bpy.data.images.new(name, sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels.foreach_set(sheet.astype(np.float32).ravel())
    out.filepath_raw = os.path.join(OUT, name + "_turnaround.png")
    out.file_format = "PNG"
    out.save()
    print("LS_SHEET " + out.filepath_raw)


# ------------------------------------------------------------------ Kieran Thorn (from Adam's turnaround sheet)
def kieran():
    reset()
    SKIN, HAIR, JACKET, SCARF, SHIRT, PANTS = "#6E4630", "#16110F", "#5C6E4F", "#4B9FE1", "#E9E1CC", "#6B6A55"
    LEATHER, BOOT, BRASS, GLOVE = "#8B5A2B", "#6B4426", "#C79A3B", "#3E2C22"
    # Boots with cream sock cuffs, trousers, hips
    for s in (-1, 1):
        sph((s * 0.105, -0.05, 0.06), (0.07, 0.13, 0.06), BOOT)
        box((s * 0.105, -0.03, 0.035), (0.075, 0.135, 0.035), "#3E2A1A", 0.3)   # sole
        cyl((s * 0.105, 0, 0.15), 0.075, 0.18, BOOT)
        cyl((s * 0.105, 0, 0.27), 0.072, 0.12, BOOT)
        cyl((s * 0.105, 0, 0.345), 0.074, 0.05, SHIRT)
        limb((s * 0.105, 0, 0.36), (s * 0.095, 0, 0.88), 0.07, 0.082, PANTS)
    box((0, 0, 0.9), (0.165, 0.11, 0.07), PANTS, 0.4)
    # Shirt and open jacket
    box((0, 0.0, 1.14), (0.15, 0.1, 0.24), SHIRT, 0.4)
    for s in (-1, 1):
        box((s * 0.11, 0.0, 1.13), (0.075, 0.115, 0.255), JACKET, 0.35, rot=(0, 0, 0))
        box((s * 0.115, -0.115, 1.2), (0.045, 0.012, 0.04), JACKET, 0.3)                 # chest pocket flaps
        box((s * 0.08, -0.06, 1.37), (0.05, 0.05, 0.035), JACKET, 0.3, rot=(0.4, 0, s * 0.3))   # collar
    box((0, 0.08, 1.13), (0.17, 0.04, 0.25), JACKET, 0.3)                                   # back panel
    # Arms: jacket sleeves rolled to the forearm, cream cuffs, fingerless gloves
    for s in (-1, 1):
        limb((s * 0.2, 0, 1.33), (s * 0.235, 0, 1.08), 0.06, 0.055, JACKET)
        limb((s * 0.235, 0, 1.08), (s * 0.24, -0.01, 0.94), 0.055, 0.05, JACKET)
        torus((s * 0.24, -0.01, 0.93), 0.05, 0.022, SHIRT)
        limb((s * 0.24, -0.01, 0.92), (s * 0.24, -0.02, 0.83), 0.038, 0.034, SKIN)
        sph((s * 0.24, -0.02, 0.79), (0.038, 0.032, 0.05), GLOVE)
        sph((s * 0.24, -0.03, 0.75), (0.026, 0.024, 0.03), SKIN)          # bare fingertips
    # Belt with brass compass on the left hip
    cyl((0, 0, 0.965), 0.168, 0.04, LEATHER)
    box((0, -0.115, 0.965), (0.025, 0.008, 0.02), BRASS, 0.2)
    cyl((0.12, -0.125, 0.89), 0.045, 0.015, BRASS, rot=(math.radians(90), 0, 0))
    cyl((0.12, -0.134, 0.89), 0.036, 0.004, SHIRT, rot=(math.radians(90), 0, 0))
    # Satchel on the right hip, strap over the left shoulder
    box((-0.2, -0.04, 0.88), (0.08, 0.05, 0.075), LEATHER, 0.35)
    box((-0.2, -0.085, 0.91), (0.082, 0.012, 0.05), LEATHER, 0.3)
    limb((0.14, -0.1, 1.36), (-0.18, -0.09, 0.93), 0.012, 0.012, LEATHER)
    # Neck, sky-blue scarf, head
    cyl((0, 0, 1.4), 0.04, 0.08, SKIN)
    torus((0, -0.005, 1.39), 0.065, 0.035, SCARF, scale=(1.15, 1.0, 1.0))
    sph((0.02, -0.07, 1.33), (0.05, 0.03, 0.05), SCARF)
    sph((0, -0.005, 1.53), (0.105, 0.11, 0.125), SKIN)
    for s in (-1, 1):
        sph((s * 0.04, -0.098, 1.54), (0.022, 0.01, 0.017), "#F2EDE4")                  # eyes
        sph((s * 0.04, -0.106, 1.54), (0.012, 0.006, 0.012), "#5A3A1E")                 # hazel-brown irises
        sph((s * 0.105, 0, 1.53), (0.018, 0.025, 0.03), SKIN)                           # ears
    sph((0, -0.11, 1.5), (0.016, 0.014, 0.014), SKIN)                                   # nose
    box((0, -0.1, 1.465), (0.022, 0.004, 0.004), "#4A2A1E", 0.2)                        # mouth
    # Curly black hair: a cluster of curls, longer on top
    import random
    random.seed(4)
    for _ in range(70):
        a = random.uniform(0, 2 * math.pi)
        up = random.uniform(0.05, 1.0)
        r = 0.115 + 0.02 * random.random()
        x = math.cos(a) * r * math.sqrt(1 - up * up) * 1.05
        y = math.sin(a) * r * math.sqrt(1 - up * up) * 1.05
        z = 1.55 + up * 0.13
        if y < -0.06 and z < 1.6:
            continue   # keep the face clear
        sph((x, y + 0.01, z), (0.035,) * 3, HAIR, seg=12)
    # Goggles pushed up on the forehead, with their strap
    torus((0, 0, 1.6), 0.108, 0.012, LEATHER, scale=(1.0, 1.05, 1.0))
    for s in (-1, 1):
        torus((s * 0.04, -0.105, 1.615), 0.03, 0.011, BRASS, rot=(math.radians(80), 0, 0))
        sph((s * 0.04, -0.108, 1.615), (0.026, 0.01, 0.026), "#8FD0EE")
    render_sheet("Kieran", 1.75, [SKIN, HAIR, JACKET, SCARF, SHIRT, PANTS, LEATHER, BOOT, BRASS, GLOVE])


# ------------------------------------------------------------------ Piko (from Adam's turnaround)
def piko():
    reset()
    FUR, SHADE, BLUE, MARK, EYE, PINK = "#F5F4EF", "#D8DCE2", "#87C7FF", "#ADEFFF", "#F4BC42", "#E8B7A8"
    sph((0, 0, 0.17), (0.085, 0.075, 0.12), FUR)                     # body
    sph((0, -0.045, 0.21), (0.065, 0.04, 0.07), "#FFFFFF")           # chest fluff
    for s in (-1, 1):
        sph((s * 0.045, -0.02, 0.04), (0.03, 0.045, 0.03), SHADE)    # feet
        limb((s * 0.07, -0.02, 0.23), (s * 0.095, -0.05, 0.16), 0.018, 0.015, FUR)   # little arms
        sph((s * 0.095, -0.055, 0.155), (0.016,) * 3, FUR)
    sph((0, -0.01, 0.37), (0.1, 0.09, 0.09), FUR)                    # head (about 40% of mass)
    sph((0, -0.085, 0.35), (0.035, 0.025, 0.025), "#FFFFFF")         # muzzle
    sph((0, -0.105, 0.36), (0.008, 0.006, 0.006), PINK)              # nose
    for s in (-1, 1):
        sph((s * 0.042, -0.075, 0.385), (0.03, 0.018, 0.034), EYE)   # big golden-amber eyes
        sph((s * 0.042, -0.09, 0.385), (0.016, 0.006, 0.02), "#3A2412")
        sph((s * 0.035, -0.095, 0.4), (0.007, 0.003, 0.007), "#FFF6DC")
        # Long feather-like ears with blue tips
        e = sph((s * 0.06, 0.0, 0.53), (0.035, 0.012, 0.13), FUR, rot=(0, s * 0.25, 0))
        sph((s * 0.083, 0.0, 0.62), (0.025, 0.01, 0.055), BLUE, rot=(0, s * 0.25, 0))
        sph((s * 0.058, -0.008, 0.52), (0.02, 0.006, 0.09), "#F0D5C8", rot=(0, s * 0.25, 0))
    # Flying-squirrel flaps from wrist to hip
    for s in (-1, 1):
        sph((s * 0.085, -0.005, 0.17), (0.03, 0.04, 0.07), SHADE, rot=(0, s * -0.2, 0))
    # Swirl markings (faint) on the forehead and haunches
    torus((0, -0.088, 0.42), 0.012, 0.0025, MARK, rot=(math.radians(90), 0, 0))
    for s in (-1, 1):
        torus((s * 0.06, -0.06, 0.12), 0.014, 0.003, MARK, rot=(math.radians(90), 0, s * 0.5))
    # The flowing spirit tail, about 1.5x body length, ending in wisps
    tube([(0, 0.07, 0.1), (0.05, 0.16, 0.12), (0.16, 0.22, 0.2), (0.28, 0.24, 0.3), (0.38, 0.2, 0.36), (0.46, 0.14, 0.33)],
         lambda t: 0.035 * (1 - t) + 0.006, BLUE)
    render_sheet("Piko", 0.7, [FUR, SHADE, BLUE, MARK, EYE, PINK], width=0.85)


# ------------------------------------------------------------------ the Ancient Glider (draft from the FIREFLY_PROMPTS brief)
def glider():
    """Pale wind-carved wood and aged brass, sky-blue sailcloth with faded route markings, crescent wings, a
    crossbar handle and foot loops, small spiral glyphs on the brass joints."""
    reset()
    WOOD, CLOTH, BRASS, ROUTE, CORD = "#D2B48A", "#A9D8F2", "#B8893A", "#6E9FC0", "#7A6248"

    def lead(u):
        return -0.6 + 0.75 * u ** 2          # crescent: the tips sweep back

    def chord(u):
        return 1.3 * (1 - 0.72 * u ** 1.5)

    def height(u):
        return 0.25 * u ** 2

    limb((0, -0.9, 0.0), (0, 1.0, 0.05), 0.04, 0.03, WOOD)                       # keel
    limb((-0.45, -0.2, -0.75), (0.45, -0.2, -0.75), 0.02, 0.02, WOOD)            # crossbar handle
    for s in (-1, 1):
        limb((s * 0.45, -0.2, -0.75), (s * 0.12, -0.1, 0.0), 0.016, 0.016, WOOD)
        torus((s * 0.16, 0.75, -0.08), 0.08, 0.012, CORD, rot=(0, math.radians(90), 0))   # foot loops
    span = 2.3
    for s in (-1, 1):
        mesh = bpy.data.meshes.new("wing")
        bm = bmesh.new()
        nx, ny = 16, 6
        grid = []
        for i in range(nx + 1):
            u = i / nx
            row = []
            for j in range(ny + 1):
                v = j / ny
                row.append(bm.verts.new((s * (0.08 + u * span), lead(u) + v * chord(u), 0.08 * math.sin(math.pi * v) + height(u))))
            grid.append(row)
        for i in range(nx):
            for j in range(ny):
                bm.faces.new((grid[i][j], grid[i + 1][j], grid[i + 1][j + 1], grid[i][j + 1]))
        bm.to_mesh(mesh)
        bm.free()
        w = bpy.data.objects.new("wing", mesh)
        bpy.context.scene.collection.objects.link(w)
        w.modifiers.new("t", "SOLIDIFY").thickness = 0.015
        finish_obj(w, CLOTH)
        for k in range(6):                                                       # ribs
            u = k / 5
            x = s * (0.08 + u * span)
            limb((x, lead(u), height(u) + 0.02), (x, lead(u) + chord(u), height(u) + 0.02), 0.014, 0.01, WOOD)
            sph((x, lead(u), height(u) + 0.02), (0.03, 0.03, 0.03), BRASS)       # brass joints
            torus((x, lead(u), height(u) + 0.052), 0.016, 0.003, ROUTE)          # spiral glyph on each joint
        pts = [(s * (0.08 + u * span), lead(u), height(u) + 0.02) for u in (0, 0.25, 0.5, 0.75, 1.0)]
        for a, b in zip(pts, pts[1:]):
            limb(a, b, 0.02, 0.016, WOOD)                                        # curved leading-edge spar
        # Faded route markings painted on the sail: a dashed curve and two waypoint rings
        for k in range(8):
            u0, u1 = 0.1 + k * 0.1, 0.14 + k * 0.1
            v = 0.45 + 0.15 * math.sin(k)
            p0 = (s * (0.08 + u0 * span), lead(u0) + v * chord(u0), height(u0) + 0.09)
            p1 = (s * (0.08 + u1 * span), lead(u1) + v * chord(u1), height(u1) + 0.09)
            limb(p0, p1, 0.008, 0.008, ROUTE)
        for u in (0.3, 0.75):
            torus((s * (0.08 + u * span), lead(u) + 0.5 * chord(u), height(u) + 0.095), 0.05, 0.006, ROUTE, scale=(1, 1, 0.2))
    sph((0, -0.1, 0.03), (0.09, 0.09, 0.06), BRASS)                              # brass hub
    for s in (-1, 1):
        limb((s * 0.45, -0.2, -0.75), (s * 1.6, lead(0.65) + 0.3, height(0.65)), 0.004, 0.004, CORD)
    render_sheet("AncientGlider_draft", 1.6, [WOOD, CLOTH, BRASS, ROUTE, CORD], target_z=-0.2, width=4.9,
                 views_def=(("front", 0, 10), ("three_quarter", -35, 25), ("side", -90, 5), ("top", 0, 89)))


# ------------------------------------------------------------------ shared human base (Kieran's proportions, scaled after)
def scale_all(k, sx=1.0):
    for o in bpy.context.scene.objects:
        o.location = (o.location[0] * k * sx, o.location[1] * k * sx, o.location[2] * k)
        o.scale = (o.scale[0] * k * sx, o.scale[1] * k * sx, o.scale[2] * k)


def face(skin, iris, z=1.53, brows=None):
    sph((0, -0.005, z), (0.105, 0.11, 0.125), skin)
    for s in (-1, 1):
        sph((s * 0.04, -0.098, z + 0.01), (0.022, 0.01, 0.017), "#F2EDE4")
        sph((s * 0.04, -0.106, z + 0.01), (0.012, 0.006, 0.012), iris)
        sph((s * 0.105, 0, z), (0.018, 0.025, 0.03), skin)
        if brows:
            box((s * 0.042, -0.1, z + 0.04), (0.022, 0.006, 0.006), brows, 0.2)
    sph((0, -0.11, z - 0.03), (0.016, 0.014, 0.014), skin)
    box((0, -0.1, z - 0.065), (0.022, 0.004, 0.004), "#4A2A1E", 0.2)


def curls(hair, count, seed, r0, rj, zc, zr, up_min, xs=1.0, size=0.035, clear_x=0.0):
    import random
    random.seed(seed)
    for _ in range(count):
        a = random.uniform(0, 2 * math.pi)
        up = random.uniform(up_min, 1.0)
        r = r0 + rj * random.random()
        x = math.cos(a) * r * math.sqrt(1 - up * up) * xs
        y = math.sin(a) * r * math.sqrt(1 - up * up)
        z = zc + up * zr
        if y < -0.05 and z < 1.62 and abs(x) < max(clear_x, 0.2):
            continue   # keep the face clear
        sph((x, y + 0.015, z), (size,) * 3, hair, seg=12)


def legs_boots(pants, boot, cuff=None, boot_top=0.3, roll=None):
    for s in (-1, 1):
        sph((s * 0.105, -0.05, 0.06), (0.07, 0.13, 0.06), boot)
        box((s * 0.105, -0.03, 0.035), (0.075, 0.135, 0.035), "#3E2A1A", 0.3)
        cyl((s * 0.105, 0, boot_top / 2 + 0.03), 0.075, boot_top, boot)
        if cuff:
            cyl((s * 0.105, 0, boot_top + 0.04), 0.074, 0.05, cuff)
        limb((s * 0.105, 0, boot_top + 0.04), (s * 0.095, 0, 0.88), 0.075, 0.085, pants)
        if roll:
            torus((s * 0.105, 0, boot_top + 0.1), 0.075, 0.022, roll)
    box((0, 0, 0.9), (0.165, 0.11, 0.07), pants, 0.4)


def arms(sleeve, cuff, skin, hand=None, sx=0.2):
    for s in (-1, 1):
        limb((s * sx, 0, 1.33), (s * (sx + 0.035), 0, 1.08), 0.06, 0.055, sleeve)
        torus((s * (sx + 0.035), 0, 1.07), 0.055, 0.022, cuff)
        limb((s * (sx + 0.035), 0, 1.07), (s * (sx + 0.04), -0.02, 0.83), 0.045, 0.036, skin)
        sph((s * (sx + 0.04), -0.02, 0.79), (0.038, 0.032, 0.05), hand or skin)


def bram():
    """Bram Holloway, from Adam's turnaround: grey ponytail and beard, cream shirt with rolled sleeves, long brown
    leather apron with pockets, goggles round the neck, tool belt with a brass compass dial and sextant, olive
    trousers and worn brown boots."""
    reset()
    SKIN, HAIR, SHIRT, APRON, PANTS = "#C98E6A", "#C9CBCC", "#E6DCC6", "#6A4429", "#4F5A43"
    BOOT, BELT, BRASS, STEEL = "#6B4426", "#5A3A22", "#C79A3B", "#9AA3A8"
    legs_boots(PANTS, BOOT, boot_top=0.3)
    box((0, 0.0, 1.13), (0.19, 0.12, 0.26), SHIRT, 0.4)
    arms(SHIRT, SHIRT, SKIN, sx=0.23)
    box((0, -0.125, 0.85), (0.16, 0.012, 0.42), APRON, 0.15)                     # apron, chest to knee
    for x, z in ((-0.05, 1.12), (0.05, 1.12), (-0.09, 0.78), (0.09, 0.78)):
        box((x, -0.14, z), (0.045, 0.006, 0.05), APRON, 0.2)                     # pockets
    for s in (-1, 1):
        limb((s * 0.12, -0.12, 1.27), (s * 0.07, -0.02, 1.38), 0.012, 0.012, APRON)
    cyl((0, 0, 0.98), 0.2, 0.05, BELT)
    box((0, -0.15, 0.98), (0.03, 0.006, 0.022), BRASS, 0.2)
    cyl((0.18, -0.1, 0.9), 0.05, 0.015, BRASS, rot=(math.radians(90), 0, 0.5))  # compass dial
    limb((-0.2, -0.08, 0.92), (-0.17, -0.1, 0.82), 0.012, 0.004, STEEL)         # sextant
    limb((-0.2, -0.08, 0.92), (-0.24, -0.1, 0.83), 0.012, 0.004, STEEL)
    cyl((0, 0, 1.4), 0.045, 0.08, SKIN)
    torus((0, -0.01, 1.38), 0.075, 0.012, BELT)                                  # goggles round the neck
    for s in (-1, 1):
        torus((s * 0.04, -0.09, 1.36), 0.03, 0.011, BRASS, rot=(math.radians(80), 0, 0))
        sph((s * 0.04, -0.093, 1.36), (0.026, 0.01, 0.026), "#9FB8BE")
    face(SKIN, "#5A7A95", brows=HAIR)
    sph((0, 0.0, 1.6), (0.112, 0.115, 0.07), HAIR)                               # swept-back hair
    sph((0, 0.06, 1.55), (0.1, 0.07, 0.09), HAIR)
    sph((0, 0.13, 1.45), (0.035, 0.035, 0.09), HAIR)                             # ponytail
    sph((0, -0.085, 1.44), (0.075, 0.05, 0.08), HAIR)                            # full beard
    box((0, -0.112, 1.48), (0.03, 0.01, 0.01), HAIR, 0.3)                        # moustache
    scale_all(1.02, sx=1.05)
    render_sheet("Bram", 1.8, [SKIN, HAIR, SHIRT, APRON, PANTS, BOOT, BELT, BRASS, STEEL])


def elara():
    """Elara Greenborough, from Adam's turnaround: dark curly hair in a long braid, cream button shirt with rolled
    sleeves, satchel across the body, seed pouches on her belt, green trousers cuffed at the calf, dark brown
    lace-up boots, a green book."""
    reset()
    SKIN, HAIR, SHIRT, PANTS, BELT, BAG, BOOT, BOOK = "#8C5A3C", "#1E1612", "#ECE4CF", "#6E8A4A", "#4A3220", "#7A5434", "#4A3324", "#3F6B3A"
    legs_boots(PANTS, BOOT, boot_top=0.27, roll=PANTS)
    box((0, 0.0, 1.14), (0.14, 0.095, 0.24), SHIRT, 0.4)
    for s in (-1, 1):
        box((s * 0.05, -0.1, 1.33), (0.04, 0.03, 0.03), SHIRT, 0.3, rot=(0.3, 0, s * 0.4))   # collar
    arms(SHIRT, SHIRT, SKIN, sx=0.18)
    cyl((0, 0, 0.94), 0.16, 0.04, BELT)
    for s in (-1, 1):
        sph((s * 0.15, -0.06, 0.88), (0.035, 0.03, 0.045), BAG)                   # seed pouches
    limb((-0.13, -0.112, 1.35), (0.19, -0.1, 0.92), 0.013, 0.013, BELT)          # satchel strap
    box((0.2, -0.03, 0.88), (0.035, 0.08, 0.08), BAG, 0.3)
    box((-0.23, -0.04, 0.84), (0.015, 0.06, 0.085), BOOK, 0.2)                   # green book in hand
    cyl((0, 0, 1.39), 0.038, 0.08, SKIN)
    face(SKIN, "#6A6A30", brows=HAIR)
    curls(HAIR, 60, 9, 0.115, 0.01, 1.55, 0.11, 0.1, size=0.03)
    for i in range(7):                                                           # long braid
        sph((0.01 * math.sin(i), 0.12 + 0.005 * i, 1.48 - i * 0.055), (0.032, 0.03, 0.035), HAIR, seg=12)
    scale_all(0.95)
    render_sheet("Elara", 1.7, [SKIN, HAIR, SHIRT, PANTS, BELT, BAG, BOOT, BOOK])


def tessa():
    """Tessa Reed, from Adam's turnaround: big curly auburn hair, green eyes and freckles, open green jacket with
    rolled sleeves over a long cream tunic, work gloves tucked in her belt, canvas satchel, woven bracelet, loose
    brown trousers and brown pull-on boots."""
    reset()
    SKIN, HAIR, JACKET, TUNIC, PANTS = "#A8714E", "#7A1F1B", "#3F6E4A", "#EFE6CF", "#8A5A2E"
    BOOT, BELT, BAG, GLOVE, BAND = "#6B4A30", "#5A3A22", "#C9B48A", "#A0703A", "#C04848"
    legs_boots(PANTS, BOOT, boot_top=0.3)
    box((0, 0.0, 1.08), (0.145, 0.1, 0.3), TUNIC, 0.4)                          # long tunic
    for s in (-1, 1):
        box((s * 0.11, 0.0, 1.12), (0.07, 0.115, 0.27), JACKET, 0.35)
        box((s * 0.08, -0.06, 1.35), (0.05, 0.05, 0.035), JACKET, 0.3, rot=(0.4, 0, s * 0.3))
    box((0, 0.08, 1.12), (0.165, 0.04, 0.27), JACKET, 0.3)
    arms(JACKET, JACKET, SKIN, sx=0.19)
    torus((-0.23, -0.02, 0.86), 0.04, 0.008, BAND)                               # woven bracelet
    cyl((0, 0, 0.98), 0.165, 0.035, BELT)
    box((-0.15, -0.1, 0.9), (0.03, 0.012, 0.07), GLOVE, 0.3)                     # gloves tucked in belt
    limb((-0.12, -0.13, 1.36), (0.19, -0.12, 0.95), 0.013, 0.013, BELT)
    box((0.2, -0.03, 0.9), (0.04, 0.09, 0.08), BAG, 0.3)
    cyl((0, 0, 1.39), 0.038, 0.08, SKIN)
    face(SKIN, "#4F8A4A", brows=HAIR)
    for s in (-1, 1):
        for k in range(3):
            sph((s * (0.035 + 0.012 * k), -0.104, 1.505 + 0.006 * (k % 2)), (0.004,) * 3, "#7A4A30", seg=8)   # freckles
    curls(HAIR, 120, 12, 0.13, 0.03, 1.54, 0.14, -0.75, xs=1.2, size=0.038, clear_x=0.1)
    scale_all(0.93)
    render_sheet("Tessa", 1.7, [SKIN, HAIR, JACKET, TUNIC, PANTS, BOOT, BELT, BAG, GLOVE, BAND])


# ------------------------------------------------------------------ new designs (drafts for approval, no added lore)
def maren():
    """Maren Holt, postmaster (draft from the FIREFLY_PROMPTS brief): woman in her fifties, reading glasses on a cord,
    hair pinned up, wool waistcoat over a rolled-sleeve blouse, long apron with pockets of letters and a pencil,
    satchel strap, sensible boots; warm earth colours with a postal-blue accent."""
    reset()
    SKIN, HAIR, BLOUSE, VEST, APRON, SKIRT = "#B07A58", "#7B6A5E", "#EDE4D0", "#7A4E34", "#C9B48A", "#7A6450"
    BOOT, BELT, POST, PAPER = "#4A3324", "#5A3A22", "#3D6FA8", "#F5EFE0"
    for s in (-1, 1):                                                           # boots under a long skirt
        sph((s * 0.095, -0.05, 0.06), (0.065, 0.12, 0.06), BOOT)
        cyl((s * 0.095, 0, 0.13), 0.068, 0.14, BOOT)
    cyl((0, 0, 0.58), 0.2, 0.86, SKIRT, r2=0.16)
    box((0, 0.0, 1.14), (0.15, 0.1, 0.24), BLOUSE, 0.4)
    box((0, -0.005, 1.12), (0.155, 0.1, 0.19), VEST, 0.35)                     # wool waistcoat
    box((0, -0.025, 1.3), (0.06, 0.09, 0.05), BLOUSE, 0.35)                    # blouse showing at the neck
    for z in (1.06, 1.12, 1.18):
        sph((0, -0.108, z), (0.01, 0.005, 0.01), "#C79A3B", seg=8)              # buttons
    arms(BLOUSE, BLOUSE, SKIN, sx=0.18)
    box((0, -0.17, 0.66), (0.15, 0.01, 0.34), APRON, 0.15)                     # long work apron
    for x in (-0.07, 0.07):
        box((x, -0.18, 0.78), (0.055, 0.006, 0.06), APRON, 0.2)
        box((x, -0.18, 0.84), (0.03, 0.003, 0.025), PAPER, 0.1, rot=(0, 0, 0.15 * x / 0.07))   # letters
    limb((0.1, -0.19, 0.8), (0.11, -0.19, 0.9), 0.006, 0.006, "#D9A441")       # pencil
    cyl((0, 0, 0.98), 0.165, 0.035, BELT)
    limb((-0.12, -0.115, 1.36), (0.2, -0.12, 0.9), 0.013, 0.013, BELT)          # satchel strap
    box((0.21, -0.03, 0.86), (0.04, 0.09, 0.08), BELT, 0.3)
    box((0.21, -0.12, 0.88), (0.04, 0.005, 0.03), POST, 0.2)                    # postal-blue flap band
    cyl((0, 0, 1.39), 0.038, 0.08, SKIN)
    torus((0, 0, 1.385), 0.06, 0.02, POST)                                     # postal-blue neckerchief
    face(SKIN, "#5A4636", brows=HAIR)
    for s in (-1, 1):                                                          # reading glasses on a cord
        torus((s * 0.035, -0.12, 1.3), 0.022, 0.004, "#8A6A3A", rot=(math.radians(85), 0, 0))
    limb((-0.06, -0.12, 1.3), (-0.07, -0.05, 1.42), 0.002, 0.002, "#3A2A1E")
    limb((0.06, -0.12, 1.3), (0.07, -0.05, 1.42), 0.002, 0.002, "#3A2A1E")
    sph((0, 0.0, 1.6), (0.112, 0.115, 0.075), HAIR)                            # hair pinned up in a bun
    sph((0, 0.05, 1.55), (0.105, 0.075, 0.08), HAIR)
    sph((0, 0.06, 1.69), (0.05, 0.045, 0.045), HAIR)
    scale_all(0.95)
    render_sheet("MarenHolt_draft", 1.7, [SKIN, HAIR, BLOUSE, VEST, APRON, SKIRT, BOOT, BELT, POST])


def rowan():
    """Rowan Finch, village elder (draft from the FIREFLY_PROMPTS brief): older man, kind but cautious face, neat
    white beard, long patterned knitted shawl over a simple tunic, walking stick carved with windmill motifs, soft
    cap; muted greens and creams."""
    reset()
    SKIN, HAIR, TUNIC, SHAWL, PATTERN, PANTS, BOOT, STICK, CAP = "#C08A66", "#EDEBE6", "#E3DAC2", "#6F7F5A", "#D9CFAE", "#8A8468", "#5A4030", "#8A6440", "#55664A"
    legs_boots(PANTS, BOOT, boot_top=0.22)
    cyl((0, 0, 1.0), 0.17, 0.62, TUNIC, r2=0.15)                               # simple long tunic
    cyl((0, 0, 0.95), 0.165, 0.03, "#6A4A30")
    box((0, 0.0, 1.17), (0.165, 0.12, 0.2), SHAWL, 0.45)                        # knitted shawl round the shoulders
    for s in (-1, 1):
        box((s * 0.07, -0.12, 0.88), (0.045, 0.015, 0.25), SHAWL, 0.3)         # long ends hanging in front
        for k in range(5):
            box((s * 0.07, -0.137, 0.7 + k * 0.09), (0.04, 0.004, 0.008), PATTERN, 0.2)   # knitted stripes
        for k in range(4):
            box((s * 0.07 + (k - 1.5) * 0.02, -0.12, 0.62), (0.004, 0.008, 0.025), SHAWL, 0.2)   # fringe
    for k in range(3):
        torus((0, 0, 1.12 + k * 0.08), 0.165, 0.006, PATTERN, scale=(1.0, 0.75, 1.0))
    arms(TUNIC, SHAWL, SKIN, sx=0.19)
    cyl((0.26, -0.06, 0.62), 0.016, 1.24, STICK, r2=0.012)                     # walking stick
    for k in range(3):
        z = 1.1 + k * 0.035
        for a in range(4):                                                     # carved windmill-sail motif near the top
            ang = a * math.pi / 2 + k * 0.4
            limb((0.26, -0.078, z), (0.26 + 0.02 * math.cos(ang), -0.078, z + 0.02 * math.sin(ang)), 0.003, 0.003, "#5A3E28")
    sph((0.26, -0.06, 1.25), (0.025, 0.025, 0.025), STICK)
    cyl((0, 0, 1.39), 0.04, 0.08, SKIN)
    face(SKIN, "#5A6A7A", brows=HAIR)
    sph((0, -0.085, 1.44), (0.06, 0.045, 0.065), HAIR)                         # neat white beard
    box((0, -0.112, 1.48), (0.028, 0.01, 0.009), HAIR, 0.3)
    sph((0, 0.01, 1.6), (0.115, 0.118, 0.075), CAP)                            # soft cap
    sph((0, -0.02, 1.64), (0.11, 0.11, 0.05), CAP)
    for s in (-1, 1):
        sph((s * 0.1, 0.02, 1.53), (0.02, 0.04, 0.04), HAIR)                   # white hair at the temples
    scale_all(0.97)
    render_sheet("RowanFinch_draft", 1.7, [SKIN, HAIR, TUNIC, SHAWL, PATTERN, PANTS, BOOT, STICK, CAP])


def villagers():
    """Three background villagers for Windrest: unnamed, no roles, just clothing variety in the village palette."""
    looks = (
        ("A", "#9A6648", "#3A2A20", "#D9C9A6", "#7D5A3C", "#5B6B4A", "#4A3324", "#C79A3B"),   # farmer: tan shirt, brown vest
        ("B", "#E0B090", "#8A5A2E", "#B8C9D6", "#E8DFC8", "#6A5A48", "#5A4030", "#9B4A3A"),   # blue-grey shirt, cream apron
        ("C", "#6E4630", "#222222", "#C8A06A", "#556E7A", "#7A6A50", "#3E2C22", "#E8DFC8"),   # mustard shirt, slate jacket
    )
    for tag, SKIN, HAIR, SHIRT, OUTER, PANTS, BOOT, ACCENT in looks:
        reset()
        legs_boots(PANTS, BOOT, boot_top=0.26, roll=PANTS if tag == "A" else None)
        box((0, 0.0, 1.14), (0.15, 0.1, 0.24), SHIRT, 0.4)
        if tag == "A":
            box((0, -0.005, 1.13), (0.155, 0.1, 0.2), OUTER, 0.35)
            box((0, -0.108, 1.2), (0.05, 0.005, 0.12), SHIRT, 0.2)
            sph((0, 0.0, 1.62), (0.16, 0.16, 0.03), "#D8BF7A")                # straw hat brim
            cyl((0, 0, 1.66), 0.1, 0.08, "#D8BF7A")
            torus((0, 0, 1.635), 0.1, 0.01, ACCENT)
        elif tag == "B":
            box((0, -0.12, 0.9), (0.14, 0.01, 0.3), OUTER, 0.15)                # cream apron
            torus((0, 0, 1.385), 0.06, 0.02, ACCENT)                           # red neckerchief
            sph((0, 0.06, 1.62), (0.06, 0.05, 0.05), HAIR)                     # bun
        else:
            for s in (-1, 1):
                box((s * 0.11, 0.0, 1.13), (0.075, 0.115, 0.255), OUTER, 0.35)
            box((0, 0.08, 1.13), (0.17, 0.04, 0.25), OUTER, 0.3)
            torus((0, 0, 1.39), 0.065, 0.03, ACCENT, scale=(1.15, 1, 1))      # cream scarf
        arms(OUTER if tag == "C" else SHIRT, SHIRT, SKIN, sx=0.2)
        cyl((0, 0, 0.965), 0.168, 0.035, "#5A3A22")
        cyl((0, 0, 1.39), 0.038, 0.08, SKIN)
        face(SKIN, "#4A3A2A", brows=HAIR)
        if tag != "A":
            sph((0, 0.0, 1.59), (0.112, 0.118, 0.085), HAIR)
            if tag == "B":
                sph((0, 0.04, 1.53), (0.11, 0.08, 0.08), HAIR)
            else:
                curls(HAIR, 40, 21, 0.112, 0.01, 1.56, 0.1, 0.2, size=0.026)
        render_sheet("Villager%s_draft" % tag, 1.75, [SKIN, HAIR, SHIRT, OUTER, PANTS, BOOT, ACCENT])


def compass():
    """The Brass Compass (draft from the FIREFLY_PROMPTS brief): worn engraved brass casing, eight-point wind-blade
    rose, a needle that glows faint sky blue, tiny spiral glyphs round the rim, a leather belt strap. Views: closed,
    open (front), side, top."""
    reset()
    BRASS, DARK, FACE, NEEDLE, LEATHER, GLYPH = "#C79A3B", "#8A6A2A", "#EFE6CF", "#7FD3FF", "#7A4E2E", "#9A7430"
    cyl((0, 0, 0), 0.5, 0.18, BRASS, rot=(math.radians(90), 0, 0), verts=48)     # case, face toward -y
    torus((0, -0.09, 0), 0.47, 0.035, DARK, rot=(math.radians(90), 0, 0))         # rim
    cyl((0, -0.092, 0), 0.43, 0.01, FACE, rot=(math.radians(90), 0, 0), verts=48)
    for k in range(8):                                                           # eight-point rose
        a = k * math.pi / 4
        L = 0.38 if k % 2 == 0 else 0.24
        limb((0, -0.1, 0), (L * math.sin(a), -0.1, L * math.cos(a)), 0.035 if k % 2 == 0 else 0.025, 0.002, DARK)
    limb((0, -0.12, -0.03), (0, -0.12, 0.33), 0.02, 0.003, NEEDLE)               # glowing needle
    sph((0, -0.125, 0), (0.035, 0.015, 0.035), BRASS)
    for k in range(16):                                                          # spiral glyphs round the rim
        a = k * math.pi / 8
        torus((0.47 * math.sin(a), -0.13, 0.47 * math.cos(a)), 0.016, 0.004, GLYPH, rot=(math.radians(90), 0, 0))
    # hinged lid standing open, tilted back 25 degrees from the hinge at the top of the case, inside engraved
    LID = (math.radians(-115), 0, 0)
    cyl((0, 0.30, 0.95), 0.5, 0.05, BRASS, rot=LID, verts=48)
    torus((0, 0.27, 0.94), 0.32, 0.01, DARK, rot=LID)
    torus((0, 0.27, 0.94), 0.18, 0.008, DARK, rot=LID)
    cyl((0, 0.09, 0.5), 0.05, 0.12, DARK, rot=(0, math.radians(90), 0))          # hinge
    torus((0, 0, -0.56), 0.07, 0.025, BRASS, rot=(math.radians(90), 0, 0))       # bail ring
    box((0, 0.02, -0.82), (0.07, 0.02, 0.2), LEATHER, 0.3)                       # belt strap
    sph((0, -0.002, -0.95), (0.025, 0.01, 0.025), BRASS)
    render_sheet("BrassCompass_draft", 2.5, [BRASS, DARK, FACE, NEEDLE, LEATHER, GLYPH], target_z=0.2)


for w in WHICH:
    {"kieran": kieran, "piko": piko, "glider": glider, "bram": bram, "elara": elara, "tessa": tessa,
     "maren": maren, "rowan": rowan, "villagers": villagers, "compass": compass}[w]()
print("LS_DRAFTS_OK")
