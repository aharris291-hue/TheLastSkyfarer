"""Kieran Thorn, stage 2+: face, hair, clothing, accessories and materials on the rigged MPFB body.

Every garment is cut from the body surface itself (so it follows Kieran's lean anatomy), pushed out by a small
region-dependent ease, given real thickness, finished hems and folds, and inherits the body's skin weights so it
deforms with the rig. Rigid accessories are parented to bones. Colours are sampled from Adam's turnaround
(reference/palette_sampled.json).

  blender --background --python dress_kieran.py -- full [params.json]
"""
import json
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_kieran as bk   # noqa: E402

KDIR = bk.KDIR
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["full"]
PAL = {
    "skin": "#8A5A3C", "hair": "#221D19", "jacket": "#677840", "jacket_dark": "#525F33", "shirt": "#D6C6A8",
    "cuff": "#DDCBAA", "scarf": "#7BB8D0", "trousers": "#7A6C53", "boots": "#7E5E40", "boot_dark": "#5A412C",
    "sole": "#2E2219", "belt": "#6B4C33", "satchel": "#92653E", "satchel_dark": "#7A532F", "gloves": "#594738",
    "iris": "#6B4226", "brass": "#A07A45", "lens": "#9FC6D6", "steel": "#B9BEC0", "dial": "#EFE6CF", "needle": "#B23A2E",
    "button": "#8C7A5E",
}
KIND = {"jacket": "cloth", "jacket_dark": "cloth", "shirt": "linen", "cuff": "linen", "scarf": "wool", "trousers": "cloth",
        "boots": "leather", "boot_dark": "leather", "sole": "rubber", "belt": "leather", "satchel": "leather",
        "satchel_dark": "leather", "gloves": "leather", "brass": "metal", "steel": "metal", "lens": "glass", "dial": "paper",
        "needle": "paint", "button": "metal", "hair": "hair", "skin": "skin"}


def hexrgb(h):
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (lin(int(h[1:3], 16)), lin(int(h[3:5], 16)), lin(int(h[5:7], 16)), 1.0)


# ------------------------------------------------------------------ hand-painted-inspired materials (PBR, export friendly)
def mat(key):
    name = "M_Kieran_" + key
    m = bpy.data.materials.get(name)
    if m:
        return m
    col = hexrgb(PAL[key])
    kind = KIND.get(key, "cloth")
    m = bpy.data.materials.new(name)
    m.diffuse_color = col          # what quick viewport/workbench checks show
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    L = nt.links
    rough = {"cloth": 0.85, "linen": 0.8, "wool": 0.9, "leather": 0.55, "rubber": 0.7, "metal": 0.35, "glass": 0.05,
             "paper": 0.7, "paint": 0.5, "hair": 0.5, "skin": 0.55}[kind]
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = 1.0 if kind == "metal" else 0.0
    # painterly colour variation: broad soft mottling plus a gentle darkening into crevices
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = {"cloth": 9.0, "linen": 7.0, "wool": 14.0, "leather": 6.0}.get(kind, 5.0)
    n.inputs["Detail"].default_value = 3.0
    L.new(tc.outputs["Object"], n.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (col[0] * 0.88, col[1] * 0.88, col[2] * 0.86, 1)
    ramp.color_ramp.elements[1].color = (min(col[0] * 1.08, 1), min(col[1] * 1.07, 1), min(col[2] * 1.04, 1), 1)
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.35, 0.65
    L.new(n.outputs["Fac"], ramp.inputs["Fac"])
    L.new(ramp.outputs["Color"], b.inputs["Base Color"])
    if kind in ("cloth", "linen", "wool", "leather"):
        wv = nt.nodes.new("ShaderNodeTexWave" if kind != "leather" else "ShaderNodeTexVoronoi")
        if kind != "leather":
            wv.inputs["Scale"].default_value = 260.0 if kind != "wool" else 120.0
            wv.inputs["Distortion"].default_value = 1.0
        else:
            wv.inputs["Scale"].default_value = 220.0
        L.new(tc.outputs["Object"], wv.inputs["Vector"])
        bm_ = nt.nodes.new("ShaderNodeBump")
        bm_.inputs["Strength"].default_value = 0.06
        L.new(wv.outputs[1 if kind == "leather" else 1], bm_.inputs["Height"])
        L.new(bm_.outputs["Normal"], b.inputs["Normal"])
    if kind == "glass":
        b.inputs["Transmission Weight"].default_value = 0.5
        b.inputs["Coat Weight"].default_value = 1.0
    if kind == "metal":   # restrained edge wear: brighter where exposed
        b.inputs["Coat Weight"].default_value = 0.2
    if kind == "skin":
        b.inputs["Subsurface Weight"].default_value = 0.15
        b.inputs["Subsurface Radius"].default_value = (0.9, 0.45, 0.25)
        ca = nt.nodes.new("ShaderNodeVertexColor")
        ca.layer_name = "paint"
        mul = nt.nodes.new("ShaderNodeMix")
        mul.data_type, mul.blend_type = "RGBA", "MULTIPLY"
        mul.inputs[0].default_value = 1.0
        L.new(ramp.outputs["Color"], mul.inputs[6])
        L.new(ca.outputs["Color"], mul.inputs[7])
        L.new(mul.outputs[2], b.inputs["Base Color"])
    return m


# ------------------------------------------------------------------ anatomy segments from the game_engine rig
def segments(rig):
    B = {b.name: (rig.matrix_world @ b.head_local, rig.matrix_world @ b.tail_local) for b in rig.data.bones}

    def h(n):
        return B[n][0]

    def t(n):
        return B[n][1]
    seg = {"spine": (h("pelvis"), h("neck_01")), "neck": (h("neck_01"), h("head")), "head": (h("head"), t("head"))}
    for s in ("l", "r"):
        seg["uarm_" + s] = (h("upperarm_" + s), h("lowerarm_" + s))
        seg["farm_" + s] = (h("lowerarm_" + s), h("hand_" + s))
        seg["hand_" + s] = (h("hand_" + s), t("middle_03_" + s))
        seg["thigh_" + s] = (h("thigh_" + s), h("calf_" + s))
        seg["shin_" + s] = (h("calf_" + s), h("foot_" + s))
        seg["foot_" + s] = (h("foot_" + s), t("ball_" + s))
    return seg, B


REGION = {"pelvis": "spine", "spine_01": "spine", "spine_02": "spine", "spine_03": "spine", "neck_01": "neck", "head": "head"}
for _s in "lr":
    REGION.update({"clavicle_" + _s: "spine", "upperarm_" + _s: "uarm_" + _s, "lowerarm_" + _s: "farm_" + _s, "hand_" + _s: "hand_" + _s,
                   "thigh_" + _s: "thigh_" + _s, "calf_" + _s: "shin_" + _s, "foot_" + _s: "foot_" + _s, "ball_" + _s: "foot_" + _s})
    for _f in ("thumb", "index", "middle", "ring", "pinky"):
        for _k in "123":
            REGION["%s_0%s_%s" % (_f, _k, _s)] = "hand_" + _s


def classify(body, seg):
    """Region of each vertex = the bone that moves it most (from the rig skin weights); t along that region."""
    names = {g.index: g.name for g in body.vertex_groups}
    out = {}
    for v in body.data.vertices:
        best, w = None, 0.0
        for g in v.groups:
            r = REGION.get(names.get(g.group, ""))
            if r and g.weight > w:
                best, w = r, g.weight
        if best is None:
            continue
        a, b = seg[best]
        ab = b - a
        t = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-9)))
        out[v.index] = (best, t, (v.co - (a + ab * t)).length)
    return out


def classify_nearest(body, seg):
    out = {}
    for v in body.data.vertices:
        best = None
        for k, (a, b) in seg.items():
            ab = b - a
            t = max(0.0, min(1.0, (v.co - a).dot(ab) / max(ab.length_squared, 1e-9)))
            d = (v.co - (a + ab * t)).length
            if best is None or d < best[2]:
                best = (k, t, d)
        out[v.index] = best
    return out


def pt(seg, k, t):
    a, b = seg[k]
    return a + (b - a) * t


# ------------------------------------------------------------------ garments
SRC = {}
COVERED = set()


def garment(body, rig, cls, name, key, pick, ease, thick, folds=None, hide=True, relax=12, smooth=0, smooth_group=None):
    """Cut a garment from the body: faces whose verts pick() accepts, each vertex pushed out by ease(c, co)."""
    src = SRC["body"]
    keep = {i for i, c in cls.items() if pick(c, src.vertices[i].co)}
    bm = bmesh.new()
    bm.from_mesh(src)
    bm.verts.ensure_lookup_table()
    bm.normal_update()
    for v in bm.verts:
        if v.index in keep:
            v.co = v.co + v.normal * ease(cls[v.index], v.co)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    for _ in range(relax):   # straight, clean hems
        moves = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
                if len(nb) == 2:
                    moves[v] = (nb[0].co + nb[1].co) * 0.5
        for v, c in moves.items():
            v.co = v.co.lerp(c, 0.6)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat(key))
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    for vg in body.vertex_groups:   # same vertex order as the body, so its skin weights carry straight over
        o.vertex_groups.new(name=vg.name)
    for p in me.polygons:
        p.use_smooth = True
    if smooth:
        m = o.modifiers.new("smooth", "SMOOTH")
        m.factor, m.iterations = 0.5, smooth
    if smooth_group:   # e.g. melt the toes into one rounded boot toe
        gname, test, iters = smooth_group
        g = o.vertex_groups.new(name=gname)
        g.add([v.index for v in o.data.vertices if test(v.co)], 1.0, "REPLACE")
        m = o.modifiers.new("smooth_" + gname, "SMOOTH")
        m.factor, m.iterations, m.vertex_group = 1.0, iters, gname
    if folds:
        folds(o)
    s = o.modifiers.new("thick", "SOLIDIFY")
    s.thickness, s.offset, s.use_rim = thick, 1.0, True
    sub = o.modifiers.new("sub", "SUBSURF")
    sub.levels, sub.render_levels = 1, 2
    arm = o.modifiers.new("Armature", "ARMATURE")
    arm.object = rig
    o.parent = rig
    if hide:
        COVERED.update(keep)
    return o


def fold_bands(axis_z=True, scale=0.045, strength=0.004, name="folds"):
    def f(o):
        tex = bpy.data.textures.new(o.name + "_" + name, "WOOD")
        tex.wood_type = "BANDNOISE"
        tex.noise_basis_2 = "SIN"
        tex.noise_scale = scale
        tex.turbulence = 3.0
        d = o.modifiers.new(name, "DISPLACE")
        d.texture, d.texture_coords, d.strength, d.direction = tex, "GLOBAL", strength, "NORMAL"
    return f


def hem_piping(o, key, radius):
    """A rolled hem along each open edge loop: the finished edges of real clothing."""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    seen = set()
    cu = bpy.data.curves.new(o.name + "_hem", "CURVE")
    cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", radius, 2
    for e0 in [e for e in bm.edges if e.is_boundary]:
        if e0 in seen:
            continue
        loop, cur = [e0.verts[0], e0.verts[1]], e0.verts[1]
        seen.add(e0)
        closed = False
        while True:
            nxt = [e for e in cur.link_edges if e.is_boundary and e not in seen]
            if not nxt:
                break
            seen.add(nxt[0])
            cur = nxt[0].other_vert(cur)
            if cur == loop[0]:
                closed = True
                break
            loop.append(cur)
        perim = sum((loop[i].co - loop[i - 1].co).length for i in range(len(loop)))
        if len(loop) < 4 or perim < 0.25:
            continue
        sp = cu.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for i, v in enumerate(loop):
            p = v.co + v.normal * radius * 0.6
            sp.points[i].co = (p.x, p.y, p.z, 1)
        sp.use_cyclic_u = closed
    bm.free()
    h = bpy.data.objects.new(o.name + "_hem", cu)
    bpy.context.scene.collection.objects.link(h)
    cu.materials.append(mat(key))
    h.parent = o.parent
    h["weights_from"] = o.name
    return h


# ------------------------------------------------------------------ small modelled parts
def box(name, loc, size, key, bevel=0.3, rot=(0, 0, 0), parent=None, bone=None):
    bpy.ops.mesh.primitive_cube_add(size=2, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b = o.modifiers.new("bev", "BEVEL")
    b.width, b.segments, b.limit_method = min(size) * bevel, 3, "NONE"
    o.data.materials.append(mat(key))
    for p in o.data.polygons:
        p.use_smooth = True
    attach(o, parent, bone)
    return o


def cyl(name, loc, r, depth, key, rot=(0, 0, 0), verts=32, parent=None, bone=None, r2=None):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r, radius2=r if r2 is None else r2, depth=depth, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    b = o.modifiers.new("bev", "BEVEL")
    b.width, b.segments = min(r, depth) * 0.25, 2
    o.data.materials.append(mat(key))
    attach(o, parent, bone)
    return o


def torus(name, loc, R, r, key, rot=(0, 0, 0), scale=(1, 1, 1), parent=None, bone=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=40, minor_segments=10, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    o.scale = scale
    o.data.materials.append(mat(key))
    for p in o.data.polygons:
        p.use_smooth = True
    attach(o, parent, bone)
    return o


def strap(name, pts, width, thick, key, parent=None, bone=None):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.extrude, cu.bevel_depth = width / 2, thick / 2
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    cu.materials.append(mat(key))
    attach(o, parent, bone)
    return o


RIG = {}


def attach(o, parent, bone):
    if parent is None:
        return
    bpy.context.view_layer.update()
    mw = o.matrix_world.copy()
    o.parent = parent
    if bone:
        o.parent_type = "BONE"
        o.parent_bone = bone
    o.matrix_world = mw


def ring_at(body, cls, z, parts, ease=0.0):
    """Ellipse fitting the body cross-section at height z: centre, half-width, half-depth."""
    pts = []
    for dz in (0.012, 0.025, 0.04):
        pts = [v.co for v in SRC["body"].vertices if abs(v.co.z - z) < dz and cls[v.index][0] in parts]
        if len(pts) > 6:
            break
    if len(pts) <= 6:   # fall back to the central body column at that height
        pts = [v.co for v in SRC["body"].vertices if abs(v.co.z - z) < 0.02 and abs(v.co.x) < 0.1]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    return Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, z)), (max(xs) - min(xs)) / 2 + ease, (max(ys) - min(ys)) / 2 + ease


def ring_band(name, c, rx, ry, width, thick, key, parent=None, bone=None, tilt=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=1.0, depth=width, location=c, rotation=tilt)
    o = bpy.context.active_object
    o.name = name
    o.scale = (rx, ry, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bm = bmesh.new()   # open tube (no caps) with thickness
    bm.from_mesh(o.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if len(f.verts) > 4], context="FACES_ONLY")
    bm.to_mesh(o.data)
    bm.free()
    s = o.modifiers.new("thick", "SOLIDIFY")
    s.thickness, s.offset = thick, 1.0
    bv = o.modifiers.new("bev", "BEVEL")
    bv.width, bv.segments = thick * 0.4, 2
    o.data.materials.append(mat(key))
    for p in o.data.polygons:
        p.use_smooth = True
    attach(o, parent, bone)
    return o


# ------------------------------------------------------------------ hair: dense clustered coils
def curls(body, rig, B, seed=11):
    """Thick, tightly curled hair: hundreds of coil clumps of varied size grown from the scalp, fuller on top
    and at the front like the drawings, short at the nape and over the ears."""
    vg = body.vertex_groups.get("scalp")
    head0, head1 = B["head"]
    hl = (head1 - head0).length
    idx = [v.index for v in body.data.vertices if vg and any(g.group == vg.index and g.weight > 0.4 for g in v.groups)]
    random.seed(seed)
    mb = bpy.data.metaballs.new("Kieran_hair_mass")
    mb.resolution = mb.render_resolution = 0.0055
    mb.threshold = 0.25
    surface = []
    for i in idx:
        v = body.data.vertices[i]
        up = (v.co.z - head0.z) / hl                     # 0 at the base of the skull, 1 at the crown
        front = -v.co.y + head0.y                         # positive toward the face
        if up < 0.42 and front < -0.02:
            continue                                      # tidy nape
        n = (v.normal + Vector((0, 0, 0.25))).normalized()
        depth = 0.02 + 0.055 * max(0.0, up - 0.2) ** 0.7   # rounded: full on top, still generous at the sides
        if front > 0.04 and up > 0.55:
            depth *= 1.1
        for k in range(2):
            t = random.uniform(0.25, 1.0)
            e = mb.elements.new()
            e.co = v.co + n * depth * t + Vector((random.uniform(-.004, .004), random.uniform(-.004, .004), random.uniform(-.003, .003)))
            e.radius = random.uniform(0.018, 0.027)
            e.stiffness = 1.2
            if t > 0.8:
                surface.append((e.co.copy(), n))
    mobj = bpy.data.objects.new("Kieran_hair", mb)
    bpy.context.scene.collection.objects.link(mobj)
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = mobj
    mobj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    hair_mesh = bpy.context.active_object
    hair_mesh.name = "Kieran_hair"
    hair_mesh.data.materials.append(mat("hair"))
    for p in hair_mesh.data.polygons:
        p.use_smooth = True
    attach(hair_mesh, rig, "head")
    # small tight coils on the outside of the mass give the curl texture of the drawings
    cu = bpy.data.curves.new("Kieran_hair_coils", "CURVE")
    cu.dimensions, cu.bevel_resolution, cu.resolution_u, cu.bevel_depth = "3D", 1, 4, 1.0
    random.shuffle(surface)
    for co, n in surface[:900]:
        a_ = n.orthogonal().normalized()
        b_ = n.cross(a_)
        L, r, th, ph = random.uniform(0.008, 0.016), random.uniform(0.004, 0.006), random.uniform(0.004, 0.0055), random.uniform(0, 6.28)
        sp = cu.splines.new("NURBS")
        sp.points.add(7)
        for j in range(8):
            t = j / 7
            ang = ph + t * 1.6 * 2 * math.pi
            q = co + n * (0.006 + L * t) + (a_ * math.cos(ang) + b_ * math.sin(ang)) * r
            sp.points[j].co = (q.x, q.y, q.z, 1)
            sp.points[j].radius = th * (1 - 0.4 * t)
        sp.use_endpoint_u, sp.order_u = True, 4
    o = bpy.data.objects.new("Kieran_hair_coils", cu)
    bpy.context.scene.collection.objects.link(o)
    cu.materials.append(mat("hair"))
    attach(o, rig, "head")
    # hair-coloured scalp underneath so no skin shows between the coils
    on = set(idx)
    body.data.materials.append(mat("hair"))
    slot = len(body.data.materials) - 1
    for p in body.data.polygons:
        if sum(1 for i in p.vertices if i in on) >= 3:
            p.material_index = slot
    return o


def paint_skin(body, B):
    """Hand-painted touches as vertex colour: warm cheeks and nose, deeper lips, soft shadow round the eyes."""
    me = body.data
    attr = me.color_attributes.new("paint", "BYTE_COLOR", "POINT")
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    lips = body.vertex_groups.get("lips")
    lip_idx = {v.index for v in me.vertices if lips and any(g.group == lips.index and g.weight > 0.3 for g in v.groups)}
    eyes = [b for n, b in B.items() if n.startswith("eye")] if any(n.startswith("eye") for n in B) else []
    face_y = min(v.co.y for v in me.vertices if abs(v.co.z - (h0.z + hl * 0.3)) < 0.02 and abs(v.co.x) < 0.02)
    for v in me.vertices:
        c = [1.0, 1.0, 1.0]
        co = v.co
        rel = (co.z - h0.z) / hl
        if 0.0 < rel < 0.6 and co.y < face_y + 0.06:
            for sx in (-1, 1):   # cheeks
                d = (Vector((co.x, co.z)) - Vector((sx * 0.042, h0.z + hl * 0.22))).length
                w = max(0.0, 1 - d / 0.03) * 0.12
                c = [c[0] + w * 0.4, c[1] - w * 0.25, c[2] - w * 0.35]
            d = (Vector((co.x, co.z)) - Vector((0, h0.z + hl * 0.25))).length   # nose tip
            w = max(0.0, 1 - d / 0.02) * 0.08
            c = [c[0] + w * 0.3, c[1] - w * 0.2, c[2] - w * 0.3]
            for sx in (-1, 1):   # soft shadow round the eyes
                d = (Vector((co.x, co.z)) - Vector((sx * 0.033, h0.z + hl * 0.4))).length
                w = max(0.0, 1 - d / 0.025) * 0.12
                c = [c[0] - w, c[1] - w * 1.1, c[2] - w]
        if v.index in lip_idx:
            c = [0.82, 0.62, 0.6]
        attr.data[v.index].color = (max(0, min(1, c[0])), max(0, min(1, c[1])), max(0, min(1, c[2])), 1.0)


# ------------------------------------------------------------------ the whole outfit
def dress(body, rig):
    seg, B = segments(rig)
    cls = classify(body, seg)
    SRC["body"] = body.data.copy()
    hip_z = seg["thigh_l"][0].z
    neck_z = seg["neck"][0].z
    chest_z = neck_z - 0.17
    waist_z = hip_z + 0.1
    hands = [pt(seg, "hand_" + s, t) for s in "lr" for t in (0.0, 0.3, 0.6, 1.0)]

    def near_hand(co):
        return min((co - h).length for h in hands) < 0.07

    # skin: painted tone; keep MPFB's eye textures, brown irises
    body.data.materials.clear()
    body.data.materials.append(mat("skin"))
    paint_skin(body, B)
    brown = os.path.join(os.environ["APPDATA"], "Blender Foundation", "Blender", "5.2", "extensions", ".user", "blender_org", "mpfb",
                         "data", "eyes", "materials", "brown_eye.png")
    for o in bpy.data.objects:
        if o.type == "MESH" and "high-poly" in o.name and os.path.exists(brown):
            img = bpy.data.images.load(brown)
            for slot in o.material_slots:
                if slot.material and slot.material.node_tree:
                    for n in slot.material.node_tree.nodes:
                        if n.type == "TEX_IMAGE" and n.image and "eye" in n.image.name.lower() and "normal" not in n.image.name.lower():
                            n.image = img
    for o in []:
        if o.type == "MESH" and "high-poly" in o.name:
            for slot in o.material_slots:
                if slot.material and slot.material.node_tree:
                    for n in slot.material.node_tree.nodes:
                        if n.type == "TEX_IMAGE" and n.outputs["Color"].links:
                            hs = slot.material.node_tree.nodes.new("ShaderNodeHueSaturation")
                            hs.inputs["Hue"].default_value, hs.inputs["Saturation"].default_value = 0.08, 0.6
                            hs.inputs["Value"].default_value = 0.75
                            for l in list(n.outputs["Color"].links):
                                slot.material.node_tree.links.new(hs.outputs["Color"], l.to_socket)
                            slot.material.node_tree.links.new(n.outputs["Color"], hs.inputs["Color"])
                            break
        if o.type == "MESH" and ("eyebrow" in o.name or "eyelash" in o.name):
            o.data.materials.clear()
            o.data.materials.append(mat("hair"))
    G = lambda *a, **k: garment(body, rig, cls, *a, **k)   # noqa: E731

    # Cream henley undershirt: torso to the hips, short sleeves under the jacket
    shirt = G("Kieran_shirt", "shirt", lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.035) or (c[0] == "neck" and c[1] < 0.25)
              or (c[0].startswith("uarm") and c[1] < 0.6), lambda c, co: 0.005, 0.0025, folds=fold_bands(strength=0.002))
    sy = seg["spine"][1].y
    # placket and buttons at the open neck
    fy = min(v.co.y for v in SRC["body"].vertices if abs(v.co.z - (neck_z - 0.06)) < 0.01 and abs(v.co.x) < 0.03)
    for k in range(3):
        z = neck_z - 0.04 - k * 0.032
        fy_k = min(v.co.y for v in SRC["body"].vertices if abs(v.co.z - z) < 0.01 and abs(v.co.x) < 0.03)
        cyl("Kieran_shirt_button%d" % k, (0, fy_k - 0.009, z), 0.0045, 0.003, "button", rot=(math.radians(90), 0, 0), verts=16,
            parent=rig, bone="spine_03")

    # Olive explorer jacket: fitted, open front, collar, chest and sleeve pockets, sleeves rolled to mid-forearm
    def jacket_pick(c, co):
        if c[0] == "spine" and co.z > hip_z + 0.005:
            return not (abs(co.x) < 0.045 + 0.02 * max(0, (co.z - chest_z) / 0.15) and co.y < sy - 0.02)
        if c[0] == "neck" and c[1] < 0.18 and co.y > sy - 0.03:
            return True
        return c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.42)

    def jacket_ease(c, co):
        if c[0].startswith("uarm") or c[0].startswith("farm"):
            return 0.011
        return 0.013 if co.z > waist_z else 0.016   # a touch of room over the belt, never inflated
    jacket = G("Kieran_jacket", "jacket", jacket_pick, jacket_ease, 0.004, folds=fold_bands(strength=0.003), hide=False, smooth=1)
    hem_piping(jacket, "jacket_dark", 0.0035)
    for s, sg in (("l", 1), ("r", -1)):   # rolled cream cuffs over the forearm
        c, rx, ry = ring_at(body, cls, pt(seg, "farm_" + s, 0.44).z, ("farm_" + s,), 0.016)
        a, b = seg["farm_" + s]
        q = Vector((0, 0, 1)).rotation_difference((b - a).normalized())
        ring_band("Kieran_cuff_" + s, pt(seg, "farm_" + s, 0.44), rx, ry, 0.032, 0.008, "cuff", parent=rig, bone="lowerarm_" + s,
                  tilt=q.to_euler())
        # sleeve pocket with flap on the upper arm
        p0 = pt(seg, "uarm_" + s, 0.35)
        cc, rx2, ry2 = ring_at(body, cls, p0.z, ("uarm_" + s,), 0.012)
        box("Kieran_sleeve_pocket_" + s, (cc.x + sg * (rx2 + 0.002), cc.y, p0.z), (0.004, 0.022, 0.026), "jacket", 0.4, parent=rig,
            bone="upperarm_" + s)
        box("Kieran_sleeve_flap_" + s, (cc.x + sg * (rx2 + 0.005), cc.y, p0.z + 0.024), (0.005, 0.024, 0.008), "jacket_dark", 0.4,
            parent=rig, bone="upperarm_" + s)
    cc, crx, cry = ring_at(body, cls, neck_z - 0.005, ("neck", "spine"), 0.022)
    collar = ring_band("Kieran_collar_back", cc + Vector((0, 0.008, 0)), crx, cry, 0.045, 0.005, "jacket", parent=rig, bone="spine_03",
                       tilt=(math.radians(12), 0, 0))
    bmc = bmesh.new()   # keep only the back and sides: the front stays open
    bmc.from_mesh(collar.data)
    bmesh.ops.delete(bmc, geom=[v for v in bmc.verts if v.co.y < cc.y - cry * 0.35], context="VERTS")
    bmc.to_mesh(collar.data)
    bmc.free()
    for sx in (-1, 1):   # chest pockets with flaps and buttons
        z = chest_z + 0.01
        y = min(v.co.y for v in SRC["body"].vertices if abs(v.co.z - z) < 0.01 and abs(v.co.x - sx * 0.075) < 0.02) - 0.015
        box("Kieran_chest_pocket_%d" % sx, (sx * 0.075, y - 0.002, z), (0.036, 0.004, 0.04), "jacket", 0.4, parent=rig, bone="spine_03")
        box("Kieran_chest_flap_%d" % sx, (sx * 0.075, y - 0.006, z + 0.038), (0.038, 0.005, 0.012), "jacket_dark", 0.4, parent=rig, bone="spine_03")
        cyl("Kieran_chest_button_%d" % sx, (sx * 0.075, y - 0.012, z + 0.036), 0.005, 0.003, "button", rot=(math.radians(90), 0, 0),
            verts=16, parent=rig, bone="spine_03")
        # raised collar and lapel on each side of the open front
        col = box("Kieran_collar_%d" % sx, (sx * 0.055, sy - 0.04, neck_z + 0.005), (0.035, 0.006, 0.035), "jacket", 0.5,
                  rot=(math.radians(-20), 0, sx * math.radians(-28)), parent=rig, bone="spine_03")
        lap = box("Kieran_lapel_%d" % sx, (sx * 0.06, sy - 0.07, neck_z - 0.05), (0.03, 0.005, 0.045), "jacket", 0.5,
                  rot=(math.radians(-8), 0, sx * math.radians(-18)), parent=rig, bone="spine_03")

    # Grey-olive trousers: relaxed through the thigh, tapered to the boot, rolled cuffs above the boots
    def trouser_pick(c, co):
        return c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < 0.54) or (c[0] == "spine" and co.z < waist_z + 0.01)

    def trouser_ease(c, co):
        if c[0].startswith("thigh"):
            return 0.017 + 0.006 * c[1]
        if c[0].startswith("shin"):
            return 0.024 + 0.008 * c[1]
        return 0.012
    trousers = G("Kieran_trousers", "trousers", trouser_pick, trouser_ease, 0.004, folds=fold_bands(scale=0.035, strength=0.004),
                 smooth_group=("crotch", lambda co: abs(co.x) < 0.06 and hip_z - 0.14 < co.z < hip_z - 0.02, 8))
    for s in "lr":
        z = pt(seg, "shin_" + s, 0.52).z
        c, rx, ry = ring_at(body, cls, z, ("shin_" + s,), 0.024)
        ring_band("Kieran_trouser_cuff_" + s, c, rx + 0.012, ry + 0.012, 0.034, 0.007, "trousers", parent=rig, bone="calf_" + s)
    # belt with buckle
    c, rx, ry = ring_at(body, cls, waist_z - 0.005, ("spine", "thigh_l", "thigh_r"), 0.017)
    ring_band("Kieran_belt", c, rx, ry, 0.03, 0.006, "belt", parent=rig, bone="pelvis")
    box("Kieran_belt_buckle", (0, c.y - ry - 0.007, waist_z - 0.005), (0.02, 0.003, 0.016), "steel", 0.3, parent=rig, bone="pelvis")
    box("Kieran_belt_buckle_hole", (0, c.y - ry - 0.0105, waist_z - 0.005), (0.013, 0.002, 0.009), "belt", 0.3, parent=rig, bone="pelvis")

    # Laced leather boots: shaped from the foot and lower calf, real soles, folded cuffs, laces and eyelets
    toe_y = min(seg["foot_" + s][0].y for s in "lr") - 0.05
    boots = G("Kieran_boots", "boots", lambda c, co: (c[0].startswith("shin") and c[1] > 0.45) or (c[0].startswith("foot") and co.z > 0.075),
              lambda c, co: 0.02, 0.006, smooth=2)
    for s in "lr":
        fv = [v.co.copy() for i, v in enumerate(SRC["body"].vertices) if i in cls and (cls[i][0] == "foot_" + s or
              (cls[i][0] == "shin_" + s and cls[i][1] > 0.85))]
        bmh = bmesh.new()
        for co in fv:
            bmh.verts.new(co)
        bmesh.ops.convex_hull(bmh, input=bmh.verts)
        c0 = sum(fv, Vector()) / len(fv)
        for v in bmh.verts:   # leather thickness, a slightly squared toe box
            d = v.co - c0
            v.co = c0 + Vector((d.x * 1.4, d.y * 1.18, d.z * 1.2))
            v.co.z = max(v.co.z, 0.012)
        meh = bpy.data.meshes.new("Kieran_bootfoot_" + s)
        bmh.to_mesh(meh)
        bmh.free()
        bf = bpy.data.objects.new("Kieran_bootfoot_" + s, meh)
        bpy.context.scene.collection.objects.link(bf)
        meh.materials.append(mat("boots"))
        rm = bf.modifiers.new("remesh", "REMESH")
        rm.mode, rm.voxel_size = "VOXEL", 0.006
        sm = bf.modifiers.new("smooth", "SMOOTH")
        sm.factor, sm.iterations = 1.0, 6
        for p in meh.polygons:
            p.use_smooth = True
        meh.materials.append(mat("boot_dark"))          # toe cap: front of the foot shell
        toe_front = min(v.co.y for v in meh.vertices)
        for p in meh.polygons:
            if p.center.y < toe_front + 0.045 and p.center.z < 0.07:
                p.material_index = 1
        # sole: the boot footprint, a little proud of the upper, flat on the ground
        sole_me = meh.copy()
        sole = bpy.data.objects.new("Kieran_sole_" + s, sole_me)
        bpy.context.scene.collection.objects.link(sole)
        for v in sole_me.vertices:
            d = v.co - c0
            v.co = Vector((c0.x + d.x * 1.06, c0.y + d.y * 1.05, min(v.co.z, 0.038)))
        sole_me.materials.clear()
        sole_me.materials.append(mat("sole"))
        rm2 = sole.modifiers.new("remesh", "REMESH")
        rm2.mode, rm2.voxel_size = "VOXEL", 0.005
        tex = bpy.data.textures.new("lugs_" + s, "STUCCI")      # chunky lug tread on the underside
        tex.noise_scale = 0.012
        lug = sole.modifiers.new("lugs", "DISPLACE")
        lug.texture, lug.texture_coords, lug.strength, lug.direction = tex, "GLOBAL", 0.004, "Z"
        attach(bf, rig, "foot_" + s)
        attach(sole, rig, "foot_" + s)
    for s in "lr":
        z = pt(seg, "shin_" + s, 0.575).z
        c, rx, ry = ring_at(body, cls, z, ("shin_" + s,), 0.021)
        ring_band("Kieran_boot_cuff_" + s, c, rx, ry, 0.026, 0.006, "boot_dark", parent=rig, bone="calf_" + s)
        for k in range(6):   # crossed laces and brass eyelets up the front
            p0 = pt(seg, "shin_" + s, 0.64 + k * 0.06)
            c2, rx2, ry2 = ring_at(body, cls, p0.z, ("shin_" + s, "foot_" + s), 0.027)
            yf = c2.y - ry2
            for sx in (-1, 1):
                cyl("Kieran_eyelet_%s%d%d" % (s, k, sx), (c2.x + sx * 0.013, yf - 0.002, p0.z), 0.0025, 0.002, "brass",
                    rot=(math.radians(90), 0, 0), verts=12, parent=rig, bone="calf_" + s)
            if k < 5:   # criss-cross: each lace runs from one side up to the other
                p1 = pt(seg, "shin_" + s, 0.64 + (k + 1) * 0.06)
                for sx in (-1, 1):
                    a3 = Vector((c2.x + sx * 0.013, yf - 0.004, p0.z))
                    b3 = Vector((c2.x - sx * 0.013, yf - 0.004, p1.z))
                    mid = (a3 + b3) / 2
                    ang = math.atan2(b3.z - a3.z, b3.x - a3.x)
                    box("Kieran_lace_%s%d%d" % (s, k, sx), tuple(mid), ((b3 - a3).length / 2, 0.0016, 0.0016), "cuff", 0.3,
                        rot=(0, -ang, 0), parent=rig, bone="calf_" + s)

    # Fingerless gloves: cover the palm and back of the hand, fingers free past the first knuckle
    G("Kieran_gloves", "gloves", lambda c, co: (c[0].startswith("hand") and c[1] < 0.52) or (c[0].startswith("farm") and c[1] > 0.9),
      lambda c, co: 0.0025, 0.0018)

    # Sky-blue scarf: a soft double wrap with a gathered drape at the front
    nz = neck_z + 0.02
    c, rx, ry = ring_at(body, cls, nz, ("neck",), 0.02)
    ring_band("Kieran_scarf_wrap1", c, rx, ry, 0.045, 0.016, "scarf", parent=rig, bone="neck_01")
    ring_band("Kieran_scarf_wrap2", c + Vector((0, -0.006, -0.03)), rx + 0.012, ry + 0.014, 0.04, 0.016, "scarf", parent=rig, bone="neck_01",
              tilt=(math.radians(-12), 0, 0))
    yf = c.y - ry
    for k, (x0, L) in enumerate(((-0.012, 0.1), (0.014, 0.075))):
        cu = bpy.data.curves.new("Kieran_scarf_tail%d" % k, "CURVE")
        cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", 1.0, 4
        sp = cu.splines.new("NURBS")
        pts = [(x0, yf - 0.012, nz - 0.01), (x0 + 0.004, yf - 0.03, nz - 0.03), (x0 + 0.01, yf - 0.036, nz - 0.03 - L * 0.5),
               (x0 + 0.014, yf - 0.034, nz - 0.03 - L)]
        sp.points.add(len(pts) - 1)
        for j, q in enumerate(pts):
            sp.points[j].co = (q[0], q[1], q[2], 1)
            sp.points[j].radius = (0.021, 0.019, 0.016, 0.012)[j]
        sp.use_endpoint_u, sp.order_u = True, 3
        o = bpy.data.objects.new("Kieran_scarf_tail%d" % k, cu)
        bpy.context.scene.collection.objects.link(o)
        cu.materials.append(mat("scarf"))
        attach(o, rig, "spine_03")

    # Aviator goggles pushed up over the curls: brass rims, pale-blue lenses, strap round the head
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    gz = h0.z + hl * 0.7
    hc, hrx, hry = ring_at(body, cls, gz, ("head",), 0.04)
    ring_band("Kieran_goggle_strap", hc, hrx, hry, 0.022, 0.004, "belt", parent=rig, bone="head", tilt=(math.radians(-14), 0, 0))
    gy = hc.y - hry - 0.006
    for sx in (-1, 1):
        rim = torus("Kieran_goggle_rim_%d" % sx, (sx * 0.034, gy, gz + 0.016), 0.022, 0.0055, "brass", rot=(math.radians(76), 0, 0),
                    parent=rig, bone="head")
        cyl("Kieran_goggle_cup_%d" % sx, (sx * 0.034, gy + 0.008, gz + 0.014), 0.023, 0.016, "brass", rot=(math.radians(76), 0, 0),
            parent=rig, bone="head")
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1, location=(sx * 0.034, gy - 0.002, gz + 0.017),
                                             rotation=(math.radians(76), 0, 0))
        lens = bpy.context.active_object
        lens.name = "Kieran_goggle_lens_%d" % sx
        lens.scale = (0.019, 0.019, 0.006)
        lens.data.materials.append(mat("lens"))
        for p in lens.data.polygons:
            p.use_smooth = True
        attach(lens, rig, "head")
        for k in range(4):   # rivets on the rim
            a = k * math.pi / 2 + math.pi / 4
            bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, radius=0.0022,
                                                 location=(sx * 0.034 + 0.022 * math.cos(a), gy - 0.004, gz + 0.016 + 0.022 * math.sin(a) * 0.97))
            rv = bpy.context.active_object
            rv.data.materials.append(mat("brass"))
            attach(rv, rig, "head")
    cyl("Kieran_goggle_bridge", (0, gy, gz + 0.014), 0.004, 0.024, "brass", rot=(0, math.radians(90), 0), parent=rig, bone="head")

    # Crossbody satchel: strap over the left shoulder, bag on the right hip, flap and buckle
    lsh = seg["uarm_r"][0]                                   # strap over his right shoulder
    rhip = Vector((0.17, seg["spine"][0].y + 0.0, hip_z - 0.02))   # bag on his left hip
    def surf_y(x, z, extra):
        ys = [v.co.y for v in SRC["body"].vertices if abs(v.co.z - z) < 0.012 and abs(v.co.x - x) < 0.025]
        return (min(ys) if ys else -0.12) - extra
    path = []
    for k in range(9):
        t = k / 8
        x = lsh.x + 0.05 + (rhip.x - 0.03 - (lsh.x + 0.05)) * t
        z = lsh.z + 0.03 + (rhip.z + 0.09 - (lsh.z + 0.03)) * t
        path.append((x, surf_y(x, z, 0.028 if t < 0.85 else 0.03), z))
    strap("Kieran_satchel_strap", path, 0.03, 0.004, "satchel_dark", parent=rig, bone="spine_03")

    def back_y(x, z, extra):
        ys = [v.co.y for v in SRC["body"].vertices if abs(v.co.z - z) < 0.012 and abs(v.co.x - x) < 0.025]
        return (max(ys) if ys else 0.12) + extra
    bpath = []
    for k in range(9):
        t = k / 8
        x = lsh.x + 0.05 + (rhip.x + 0.02 - (lsh.x + 0.05)) * t
        z = lsh.z + 0.03 + (rhip.z + 0.06 - (lsh.z + 0.03)) * t
        bpath.append((x, back_y(x, z, 0.03), z))
    bpath.insert(0, (path[0][0], (path[0][1] + bpath[0][1]) / 2, path[0][2] + 0.035))   # over the shoulder
    strap("Kieran_satchel_strap_back", bpath, 0.03, 0.004, "satchel_dark", parent=rig, bone="spine_03")
    box("Kieran_strap_buckle", (path[3][0], path[3][1] - 0.004, path[3][2]), (0.015, 0.002, 0.018), "steel", 0.3,
        rot=(0, math.radians(-35), 0), parent=rig, bone="spine_03")
    bag_c = Vector((rhip.x + 0.02, surf_y(rhip.x + 0.02, rhip.z, 0.035), rhip.z - 0.02))
    bag_c = bag_c + Vector((0.05, 0.035, -0.04))
    bag = box("Kieran_satchel", tuple(bag_c), (0.08, 0.034, 0.095), "satchel", 0.9, rot=(0, 0, math.radians(40)), parent=rig, bone="pelvis")
    sub = bag.modifiers.new("soft", "SUBSURF")
    sub.levels = sub.render_levels = 2
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    flap = bpy.context.active_object
    flap.name = "Kieran_satchel_flap"
    fm = flap.data
    bmf = bmesh.new()
    gw, gh = 8, 10
    grid = [[bmf.verts.new((( i / gw - 0.5) * 0.172, -0.036 - 0.03 * math.sin(math.pi * 0.5 * j / gh) * 0.3,
                            0.095 - 0.12 * j / gh + 0.02 * (1 - math.cos(math.pi * 0.5 * j / gh)))) for i in range(gw + 1)] for j in range(gh + 1)]
    for j in range(gh):
        for i in range(gw):
            bmf.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    for v in bmf.verts:   # the flap wraps over the top of the bag
        if v.co.z > 0.085:
            v.co.y += (v.co.z - 0.085) * 3.5
    bmf.to_mesh(fm)
    bmf.free()
    flap.location = bag_c
    flap.rotation_euler = (0, 0, math.radians(40))
    fm.materials.append(mat("satchel_dark"))
    so = flap.modifiers.new("thick", "SOLIDIFY")
    so.thickness = 0.005
    sf = flap.modifiers.new("soft", "SUBSURF")
    sf.levels = sf.render_levels = 2
    for p in fm.polygons:
        p.use_smooth = True
    attach(flap, rig, "pelvis")
    rot = Matrix.Rotation(math.radians(40), 3, "Z")
    for sx in (-1, 1):   # buckle straps down the flap
        loc = bag_c + rot @ Vector((sx * 0.04, -0.045, -0.005))
        box("Kieran_satchel_tab_%d" % sx, tuple(loc), (0.008, 0.003, 0.03), "belt", 0.3, rot=(0, 0, math.radians(40)), parent=rig, bone="pelvis")
        loc2 = bag_c + rot @ Vector((sx * 0.04, -0.049, -0.03))
        box("Kieran_satchel_buckle_%d" % sx, tuple(loc2), (0.01, 0.002, 0.008), "steel", 0.3, rot=(0, 0, math.radians(40)), parent=rig, bone="pelvis")

    # Compass on the belt at the left hip: metal case, readable dial, cardinal marks and needle
    cx, cz = -0.1, waist_z - 0.055
    cy = surf_y(cx, cz, 0.02)
    cyl("Kieran_compass_case", (cx, cy, cz), 0.03, 0.012, "steel", rot=(math.radians(90), 0, 0), verts=48, parent=rig, bone="pelvis")
    torus("Kieran_compass_bezel", (cx, cy - 0.006, cz), 0.028, 0.003, "steel", rot=(math.radians(90), 0, 0), parent=rig, bone="pelvis")
    cyl("Kieran_compass_dial", (cx, cy - 0.0065, cz), 0.025, 0.001, "dial", rot=(math.radians(90), 0, 0), verts=48, parent=rig, bone="pelvis")
    for k in range(8):
        a = k * math.pi / 4
        L = 0.006 if k % 2 == 0 else 0.0035
        box("Kieran_compass_mark%d" % k, (cx + 0.021 * math.sin(a), cy - 0.0072, cz + 0.021 * math.cos(a)), (0.0008, 0.0004, L / 2),
            "jacket_dark", 0.1, rot=(0, -a, 0), parent=rig, bone="pelvis")
    box("Kieran_compass_needle_n", (cx, cy - 0.0078, cz + 0.008), (0.002, 0.0005, 0.009), "needle", 0.1, parent=rig, bone="pelvis")
    box("Kieran_compass_needle_s", (cx, cy - 0.0078, cz - 0.008), (0.002, 0.0005, 0.009), "steel", 0.1, parent=rig, bone="pelvis")
    torus("Kieran_compass_bail", (cx, cy, cz + 0.035), 0.007, 0.0018, "steel", rot=(math.radians(90), 0, 0), parent=rig, bone="pelvis")

    def seam(name, pts, key, radius=0.0016):
        cu = bpy.data.curves.new(name, "CURVE")
        cu.dimensions, cu.bevel_depth, cu.bevel_resolution = "3D", radius, 1
        sp = cu.splines.new("POLY")
        sp.points.add(len(pts) - 1)
        for i, q in enumerate(pts):
            sp.points[i].co = (q[0], q[1], q[2], 1)
        o = bpy.data.objects.new(name, cu)
        bpy.context.scene.collection.objects.link(o)
        cu.materials.append(mat(key))
        o.parent = rig
        o["weights_from"] = "Kieran.body"    # skinned from the body at export, so seams follow the cloth
        return o
    yoke_z = neck_z - 0.1
    seam("Kieran_jacket_yoke", [(x / 20 * 0.36 - 0.18, back_y(x / 20 * 0.36 - 0.18, yoke_z, 0.017), yoke_z) for x in range(21)], "jacket_dark")
    for sx in (-1, 1):
        seam("Kieran_jacket_backseam_%d" % sx, [(sx * 0.07, back_y(sx * 0.07, z, 0.018), z) for z in np.linspace(yoke_z - 0.01, hip_z + 0.02, 12)],
             "jacket_dark")
        pz = hip_z - 0.07
        py = back_y(sx * 0.07, pz, 0.016)
        box("Kieran_back_pocket_%d" % sx, (sx * 0.07, py, pz), (0.04, 0.004, 0.045), "trousers", 0.3, rot=(math.radians(8), 0, 0),
            parent=rig, bone="pelvis")
        seam("Kieran_trouser_sideseam_%d" % sx, [(sx * (ring_at(body, cls, z, ("thigh_l" if sx > 0 else "thigh_r",), 0.02)[1] +
                                                     ring_at(body, cls, z, ("thigh_l" if sx > 0 else "thigh_r",), 0.02)[0].x * sx),
                                                 ring_at(body, cls, z, ("thigh_l" if sx > 0 else "thigh_r",), 0.02)[0].y, z)
                                                for z in np.linspace(hip_z - 0.02, pt(seg, "thigh_" + ("l" if sx > 0 else "r"), 0.95).z, 10)],
             "jacket_dark", 0.0012)
    # Remove skin hidden under the clothes (no poke-through, fewer polygons)
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.index in COVERED for v in f.verts)], context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()
    curls(body, rig, B)
    return seg


def setup_look():
    """Soft studio light for the five-view renders (EEVEE, materials as authored)."""
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 64
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -0.6
    w = bpy.data.worlds.new("look") if not sc.world else sc.world
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.82, 0.74, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    for name, loc, size, energy, col in (("Key", (-2.0, -3.0, 3.2), 2.5, 900, (1.0, 0.95, 0.88)),
                                          ("Fill", (3.0, -2.2, 1.4), 3.0, 350, (0.88, 0.92, 1.0)),
                                          ("Rim", (0.8, 3.2, 2.8), 1.5, 700, (1.0, 0.92, 0.8))):
        if bpy.data.objects.get("Look_" + name):
            continue
        ld = bpy.data.lights.new("Look_" + name, "AREA")
        ld.size, ld.energy, ld.color = size, energy, col
        o = bpy.data.objects.new("Look_" + name, ld)
        sc.collection.objects.link(o)
        o.location = loc
        c = o.constraints.new("TRACK_TO")
        c.target = bpy.data.objects["Kieran_Rig"]


def render_look(name, yaw, res=(800, 1200)):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = res
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type in ("MESH", "CURVE") and not o.hide_render for c in o.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    cam = bpy.data.objects.get("LookCam") or bpy.data.objects.new("LookCam", bpy.data.cameras.new("LookCam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = (zmax - zmin) * 1.06
    a = math.radians(yaw)
    cam.location = (10 * math.sin(a), -10 * math.cos(a), (zmax + zmin) / 2)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.camera = cam
    sc.render.filepath = os.path.join(KDIR, "renders", name + ".png")
    bpy.ops.render.render(write_still=True)
    print("LS_RENDER", sc.render.filepath, flush=True)


VIEWS5 = (("Kieran_Front", 0), ("Kieran_ThreeQuarterFront", 40), ("Kieran_Side", 90), ("Kieran_ThreeQuarterRear", 140), ("Kieran_Rear", 180))


if __name__ == "__main__":
    params = json.load(open(ARGS[1])) if len(ARGS) > 1 else {}
    p = dict(bk.DEFAULT)
    for k, v in params.items():
        p[k] = dict(p[k], **v) if isinstance(v, dict) and k in p else v
    body, rig = bk.build_body(p)
    dress(body, rig)
    bk.check_body("dressed")
    for name, yaw in VIEWS5[:3]:
        bk.render_view("check_" + name, yaw)
    setup_look()
    for name, yaw in VIEWS5:
        render_look(name, yaw)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KDIR, "Kieran_Thorn_Master.blend"))
    print("LS_DRESS_OK", flush=True)
