"""Realistic character drafts: MPFB (MakeHuman, CC0 output) bodies with hand-made clothes, rendered in Cycles.

Each character follows Adam's turnaround (or the approved written brief): the body, face, skin, eyes and hair come
from MPFB and its CC0 asset packs; every garment and prop is built here, shaped from the body itself (offset, given
thickness, folds and real cloth/leather/brass materials). Nothing goes into the game until Adam approves.

Needs the MPFB extension and the CC0 packs (see docs/unreal/ASSET_MANIFEST.md).

  blender --background --python realistic_humans.py -- <output folder> [kieran ...]
"""
import math
import os
import random
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import character_drafts as cd   # noqa: E402
import realistic_drafts as rd   # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [os.getcwd()]
OUT = ARGS[0]
WHICH = ARGS[1:] or ["kieran"]
os.makedirs(OUT, exist_ok=True)
cd.OUT = rd.OUT = OUT
KIND = rd.KIND


def mpfb():
    addon_utils.enable("bl_ext.blender_org.mpfb")
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService
    return HumanService


# ------------------------------------------------------------------ body
def make_human(name, pheno, race, parts, skin, arms_down=52, targets=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    HS = mpfb()
    info = HS._create_default_human_info_dict()
    info["phenotype"].update(pheno)
    info["phenotype"]["race"] = race
    info.update(parts)
    info.update({"skin_mhmat": skin, "skin_material_type": "ENHANCED_SSS", "rig": "default", "name": name})
    if targets:
        info["targets"] = [{"target": t, "value": v} for t, v in targets.items()]
    st = HS.get_default_deserialization_settings()
    st["load_clothes"] = False
    st["subdiv_levels"] = 0
    body = HS.deserialize_from_dict(info, st)
    rig = body.parent if body.parent and body.parent.type == "ARMATURE" else None
    if rig is None:
        rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    # Arms relaxed at the sides: aim each arm bone at a target direction (rig space)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for side, sgn in (("L", 1), ("R", -1)):
        for bone, target in (("upperarm01", (sgn * 0.22, 0.03, -1.0)), ("lowerarm01", (sgn * 0.12, -0.1, -1.0))):
            pb = rig.pose.bones["%s.%s" % (bone, side)]
            head = pb.head.copy()
            cur = (pb.tail - pb.head).normalized()
            q = cur.rotation_difference(Vector(target).normalized())
            pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
            bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    bones = {b.name: (rig.matrix_world @ b.head, rig.matrix_world @ b.tail) for b in rig.pose.bones}
    # Bake the pose into plain meshes
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in meshes:
        ev = o.evaluated_get(dg)
        me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
        mw = o.matrix_world.copy()
        o.shape_key_clear() if o.data.shape_keys else None
        o.modifiers.clear()
        o.parent = None
        o.matrix_world = mw
        o.data = me
    bpy.data.objects.remove(rig)
    for o in meshes:
        for p in o.data.polygons:
            p.use_smooth = True
        m = o.modifiers.new("sub", "SUBSURF")
        m.levels = 0
        m.render_levels = 1
    body = bpy.data.objects.get(name + ".body") or body
    return body, bones


def segments(bones):
    """Body regions as bone segments (head, tail) for classifying vertices."""
    def h(n):
        return bones[n][0]

    def t(n):
        return bones[n][1]
    seg = {"spine": (h("spine05"), h("neck01")), "neck": (h("neck01"), h("head")), "head": (h("head"), t("head"))}
    for s in ("L", "R"):
        seg["uarm" + s] = (h("upperarm01." + s), h("lowerarm01." + s))
        seg["farm" + s] = (h("lowerarm01." + s), h("wrist." + s))
        seg["hand" + s] = (h("wrist." + s), t("wrist." + s) + (t("wrist." + s) - h("wrist." + s)) * 1.6)
        seg["thigh" + s] = (h("upperleg01." + s), h("lowerleg01." + s))
        seg["shin" + s] = (h("lowerleg01." + s), h("foot." + s))
        seg["foot" + s] = (h("foot." + s), t("toe1-1." + s) if "toe1-1." + s in bones else t("foot." + s))
    return seg


SRC = {}


def classify(body, seg):
    """For each vertex: (region, t along the region's bone, distance)."""
    out = {}
    SRC[body.name] = body.data.copy()
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


# ------------------------------------------------------------------ garments shaped from the body
def garment(body, cls, name, hexcol, pick, offset, thick, folds=0.004, hide_skin=True, smooth=0, extra=None):
    """Copy the body faces whose vertices pick() accepts, push them out by offset and give them thickness."""
    src = SRC[body.name]          # the untouched body, so layered garments all have the full surface to copy
    keep = {i for i, c in cls.items() if pick(c, src.vertices[i].co)}
    bm = bmesh.new()
    bm.from_mesh(src)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.index not in keep], context="VERTS")
    # Straighten the stair-stepped hems: relax open-edge vertices along their edge loop
    for _ in range(12):
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
    me.materials.clear()
    me.materials.append(rd.real_mat(hexcol))
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    if smooth:
        m = o.modifiers.new("smooth", "SMOOTH")
        m.factor = 0.8
        m.iterations = smooth
    d = o.modifiers.new("offset", "DISPLACE")
    d.direction = "NORMAL"
    d.mid_level = 0.0
    d.strength = offset
    if folds:
        tex = bpy.data.textures.new(name + "_folds", "CLOUDS")
        tex.noise_scale = 0.06
        tex.noise_depth = 2
        f = o.modifiers.new("folds", "DISPLACE")
        f.texture = tex
        f.texture_coords = "GLOBAL"
        f.strength = folds
    s = o.modifiers.new("thick", "SOLIDIFY")
    s.thickness = thick
    s.offset = 1.0
    s.use_rim = True
    sub = o.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    if extra:
        extra(o)
    if hide_skin:   # remove skin fully covered by the garment so it can't poke through
        bm = bmesh.new()
        bm.from_mesh(body.data)
        bm.faces.ensure_lookup_table()
        inner = [f for f in bm.faces if all(v.index in keep for v in f.verts)]
        bmesh.ops.delete(bm, geom=inner, context="FACES_ONLY")
        bm.to_mesh(body.data)
        bm.free()
        # garments reuse the same vertex indices, so rebuild the classification for the remaining skin later
    return o


def band(center, radius, z_axis, width, thick, hexcol, scale=(1, 1, 1)):
    """A ring band (belt, cuff, scarf wrap) around an axis."""
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=width, location=center)
    o = bpy.context.active_object
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference(Vector(z_axis).normalized()).to_euler()
    o.scale = scale
    s = o.modifiers.new("thick", "SOLIDIFY")
    s.thickness = thick
    bev = o.modifiers.new("bev", "BEVEL")
    bev.width = thick * 0.4
    bev.segments = 2
    o.data.materials.append(rd.real_mat(hexcol))
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def strap(points, width, thick, hexcol):
    """A flat leather strap following points."""
    cu = bpy.data.curves.new("strap", "CURVE")
    cu.dimensions = "3D"
    cu.extrude = width / 2
    cu.bevel_depth = thick / 2
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(points) - 1)
    for i, p in enumerate(points):
        bp = sp.bezier_points[i]
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    o = bpy.data.objects.new("strap", cu)
    bpy.context.scene.collection.objects.link(o)
    cu.materials.append(rd.real_mat(hexcol))
    return o


def curly_hair(body, hexcol, length=0.03, count=3000, curl=0.006, group="scalp", kink="CURL"):
    """Hair strands grown from a vertex group: natural curls on the scalp, or a beard with kink="NO"."""
    m = rd.hair_mat("hair_%s_%s" % (group, hexcol), cd.hexrgb(hexcol))
    body.data.materials.append(m)
    mod = body.modifiers.new("hair_" + group, "PARTICLE_SYSTEM")
    ps = mod.particle_system.settings
    mod.particle_system.vertex_group_density = group
    ps.type = "HAIR"
    ps.use_advanced_hair = False
    ps.count = count
    ps.hair_length = length
    ps.hair_step = 10
    ps.child_type = "INTERPOLATED"
    ps.rendered_child_count = 30
    ps.child_percent = 10
    ps.clump_factor = 0.85
    ps.kink = kink
    ps.kink_amplitude = curl
    ps.kink_frequency = 12.0
    ps.kink_shape = 0.2
    ps.roughness_2 = 0.004
    ps.material_slot = m.name
    ps.root_radius = 1.0
    ps.tip_radius = 0.4
    ps.radius_scale = 0.0006
    return ps


def tint_skin(body, value=0.75, sat=1.0):
    """Darken or lift the skin texture to match the character's tone in Adam's art."""
    for slot in body.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        for n in list(m.node_tree.nodes):
            if n.type == "TEX_IMAGE" and n.image and "diffuse" in n.image.name.lower():
                hs = m.node_tree.nodes.new("ShaderNodeHueSaturation")
                hs.inputs["Value"].default_value = value
                hs.inputs["Saturation"].default_value = sat
                for link in list(n.outputs["Color"].links):
                    m.node_tree.links.new(hs.outputs["Color"], link.to_socket)
                m.node_tree.links.new(n.outputs["Color"], hs.inputs["Color"])


def pt(seg, key, t):
    a, b = seg[key]
    return a + (b - a) * t


# ------------------------------------------------------------------ Kieran Thorn (Adam's turnaround)
def kieran():
    SKIN, HAIR, JACKET, SCARF, SHIRT, PANTS = "#6E4630", "#16110F", "#5C6E4F", "#4B9FE1", "#E9E1CC", "#6B6A55"
    LEATHER, BOOT, BRASS, GLOVE, SOCK = "#8B5A2B", "#6B4426", "#C79A3B", "#3E2C22", "#E6DCC6"
    KIND.clear()
    KIND.update({JACKET: "cloth_heavy", SCARF: "wool", SHIRT: "linen", PANTS: "cloth_heavy", LEATHER: "leather",
                 BOOT: "leather", BRASS: "brass", GLOVE: "leather", SOCK: "wool", "#8FD0EE": "glass"})
    body, bones = make_human(
        "Kieran",
        {"gender": 1.0, "age": 0.3, "muscle": 0.55, "weight": 0.42, "height": 0.62, "proportions": 0.65},
        {"african": 1.0, "asian": 0.0, "caucasian": 0.0},
        {"eyes": "high-poly.mhclo", "eyebrows": "mindfront_eyebrows_03.mhclo", "eyelashes": "mindfront_eyelashes_01.mhclo",
         "teeth": "teeth_base.mhclo", "hair": "afro01.mhclo"},
        "young_african_male.mhmat")
    print("LS_BONES", sorted(bones.keys())[:200], flush=True)
    seg = segments(bones)
    cls = classify(body, seg)
    tint_skin(body, 0.72)
    hip_z = seg["thighL"][0].z
    neck_z = seg["neck"][0].z
    CLS[body.name], HIP[body.name] = cls, hip_z

    def side(k):
        return k[-1] if k[-1] in "LR" else ""
    # Shirt: torso up to the collar, sleeves to the elbow (hidden under the jacket except the open front)
    garment(body, cls, "shirt", SHIRT, lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.12) or (c[0] == "neck" and c[1] < 0.3)
            or c[0].startswith("uarm"), 0.006, 0.003)
    # Jacket: open front, sleeves rolled to mid-forearm, hem below the belt
    garment(body, cls, "jacket", JACKET,
            lambda c, co: ((c[0] == "spine" and co.z > hip_z - 0.1 and not (abs(co.x) < 0.045 and co.y < -0.02))
                           or c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.45)),
            0.024, 0.005, folds=0.008, hide_skin=False)
    sy = seg["spine"][1].y
    for sx in (-1, 1):   # chest pockets with flaps, and a turned-down collar
        cd.box((sx * 0.085, sy - 0.135, neck_z - 0.17), (0.045, 0.008, 0.05), JACKET, 0.2)
        cd.box((sx * 0.085, sy - 0.142, neck_z - 0.13), (0.048, 0.01, 0.018), JACKET, 0.3)
        c = cd.box((sx * 0.07, sy - 0.07, neck_z - 0.01), (0.055, 0.012, 0.04), JACKET, 0.3)
        c.rotation_euler = (math.radians(-35), 0, sx * math.radians(25))
    for s in "LR":   # rolled cream cuffs
        a, b = seg["farm" + s]
        band(pt(seg, "farm" + s, 0.45), 0.052, b - a, 0.05, 0.012, SHIRT)
    # Trousers, belt and boots
    # Loose travel/cargo cut: plenty of ease, deep folds, a cargo pocket on each outer thigh
    garment(body, cls, "trousers", PANTS, lambda c, co: (c[0].startswith("thigh")) or (c[0].startswith("shin") and c[1] < 0.6)
            or (c[0] == "spine" and co.z < hip_z + 0.1), 0.038, 0.004, folds=0.022)
    for s, sx in (("L", 1), ("R", -1)):
        z = pt(seg, "thigh" + s, 0.55).z
        rx, ry, c = extent(body, z, ("thigh" + s,))
        x = c.x + sx * (rx + 0.04)
        pk = cd.box((x, c.y, z), (0.012, 0.055, 0.07), PANTS, 0.3)
        cd.box((x + sx * 0.004, c.y, z + 0.065), (0.013, 0.058, 0.02), PANTS, 0.35)
        cd.sph((x + sx * 0.016, c.y, z + 0.06), (0.004, 0.006, 0.006), BRASS)
    band(Vector((0, seg["spine"][0].y, hip_z + 0.04)), 0.165, (0, 0, 1), 0.045, 0.008, LEATHER, scale=(1.0, 0.72, 1.0))
    garment(body, cls, "boots", BOOT, lambda c, co: c[0].startswith("foot") or (c[0].startswith("shin") and c[1] > 0.45),
            0.014, 0.006, folds=0.0, smooth=1)
    KIND["#2E211A"] = "leather"
    for s in "LR":   # stitched leather soles under each boot
        pts = [v.co for v in SRC[body.name].vertices if cls[v.index][0] == "foot" + s or (cls[v.index][0] == "shin" + s and v.co.z < 0.06)]
        xs, ys = [p.x for p in pts], [p.y for p in pts]
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        cd.box((cx, cy - 0.006, 0.012), ((max(xs) - min(xs)) / 2 + 0.018, (max(ys) - min(ys)) / 2 + 0.02, 0.012), "#2E211A", 0.35)
    for s in "LR":
        a, b = seg["shin" + s]
        band(pt(seg, "shin" + s, 0.58), 0.066, b - a, 0.055, 0.014, SOCK)     # cream sock cuff over the boot top
        for k in range(5):   # laces up the boot front
            p0 = pt(seg, "shin" + s, 0.62 + k * 0.08)
            cd.box((p0.x, p0.y - 0.062, p0.z), (0.022, 0.003, 0.003), SOCK, 0.2)
    # Fingerless gloves
    garment(body, cls, "gloves", GLOVE, lambda c, co: (c[0].startswith("hand") and c[1] < 0.62) or (c[0].startswith("farm") and c[1] > 0.9),
            0.003, 0.002, folds=0.0)
    # Sky-blue scarf wrapped at the neck with a knot falling at the front
    nz = neck_z + 0.03
    band(Vector((0, seg["neck"][0].y, nz)), 0.075, (0, 0, 1), 0.07, 0.03, SCARF, scale=(1.1, 1.05, 1))
    # a second, looser turn of the scarf and two soft ends falling over the left collarbone
    lw = band(Vector((0.01, seg["neck"][0].y - 0.01, nz - 0.045)), 0.085, (0.15, -0.25, 1), 0.06, 0.025, SCARF, scale=(1.12, 1.05, 1))
    ny = seg["neck"][0].y
    strap([(0.05, ny - 0.085, nz - 0.03), (0.075, ny - 0.105, nz - 0.1), (0.085, ny - 0.11, nz - 0.17)], 0.07, 0.014, SCARF)
    strap([(0.035, ny - 0.09, nz - 0.035), (0.05, ny - 0.115, nz - 0.08), (0.055, ny - 0.125, nz - 0.12)], 0.06, 0.014, SCARF)
    # Goggles pushed up on the forehead, strap round the head
    hz = seg["head"][0].z + (seg["head"][1].z - seg["head"][0].z) * 0.62
    hy = seg["head"][0].y
    band(Vector((0, hy, hz)), 0.098, (0, 0.25, 1), 0.025, 0.006, LEATHER, scale=(1.0, 1.12, 1.0))
    for sx in (-1, 1):
        g = band(Vector((sx * 0.035, hy - 0.105, hz + 0.01)), 0.028, (0, -1, 0.35), 0.02, 0.008, BRASS)
        cd.sph((sx * 0.035, hy - 0.112, hz + 0.012), (0.026, 0.008, 0.026), "#8FD0EE")
    # Satchel on the right hip, strap over the left shoulder; brass compass on the left hip
    lsh = seg["uarmL"][0]
    rhip = Vector((-0.17, seg["spine"][0].y - 0.02, hip_z - 0.03))
    strap([(lsh.x - 0.04, lsh.y - 0.06, lsh.z + 0.02), (0.0, lsh.y - 0.155, lsh.z - 0.2), (rhip.x + 0.02, rhip.y - 0.13, rhip.z + 0.12),
           (rhip.x - 0.02, rhip.y - 0.05, rhip.z + 0.07)],
          0.035, 0.005, LEATHER)
    cd.box((rhip.x - 0.02, rhip.y, rhip.z), (0.085, 0.045, 0.08), LEATHER, 0.25)
    cd.box((rhip.x - 0.02, rhip.y - 0.045, rhip.z + 0.025), (0.088, 0.01, 0.06), LEATHER, 0.25)
    cz = hip_z - 0.02
    KIND.update({"#EFE6CF": "linen", "#7FD3FF": "glow"})
    cd.cyl((0.13, seg["spine"][0].y - 0.12, cz), 0.04, 0.014, BRASS, rot=(math.radians(90), 0, 0), verts=40)
    cd.cyl((0.13, seg["spine"][0].y - 0.128, cz), 0.032, 0.004, "#EFE6CF", rot=(math.radians(90), 0, 0))
    cd.limb((0.13, seg["spine"][0].y - 0.132, cz - 0.004), (0.13, seg["spine"][0].y - 0.132, cz + 0.026), 0.004, 0.001, "#7FD3FF")
    curly_hair(body, HAIR)
    rd.render_sheet_real("Kieran", 1.8, [SKIN, HAIR, JACKET, SCARF, SHIRT, PANTS, LEATHER, BOOT, BRASS, GLOVE])


# ------------------------------------------------------------------ shared pieces for the rest of the cast
def tint_obj(o, value=1.0, sat=1.0, hue=0.5):
    """Recolour an MPFB asset's texture (hair, skin) through a hue/saturation/value node."""
    for slot in o.material_slots:
        m = slot.material
        if not m or not m.node_tree:
            continue
        for n in list(m.node_tree.nodes):
            if n.type == "TEX_IMAGE" and n.image and n.outputs["Color"].links:
                hs = m.node_tree.nodes.new("ShaderNodeHueSaturation")
                hs.inputs["Value"].default_value = value
                hs.inputs["Saturation"].default_value = sat
                hs.inputs["Hue"].default_value = hue
                for link in list(n.outputs["Color"].links):
                    m.node_tree.links.new(hs.outputs["Color"], link.to_socket)
                m.node_tree.links.new(n.outputs["Color"], hs.inputs["Color"])
                break


def find(part):
    return next((o for o in bpy.data.objects if part in o.name), None)


def base(name, pheno, race, skin, hair, skin_value=1.0, skin_sat=1.0, brows="mindfront_eyebrows_03.mhclo"):
    parts = {"eyes": "high-poly.mhclo", "eyebrows": brows, "eyelashes": "mindfront_eyelashes_01.mhclo", "teeth": "teeth_base.mhclo"}
    if hair:
        parts["hair"] = hair
    body, bones = make_human(name, pheno, race, parts, skin)
    seg = segments(bones)
    cls = classify(body, seg)
    if skin_value != 1.0 or skin_sat != 1.0:
        tint_skin(body, skin_value, skin_sat)
    return body, seg, cls, seg["thighL"][0].z, seg["neck"][0].z


def extent(body, z, parts=("spine",), dz=0.025):
    """Half-width, half-depth and centre of the body cross-section at height z."""
    cls = CLS[body.name]
    pts = [v.co for v in SRC[body.name].vertices if abs(v.co.z - z) < dz and cls[v.index][0] in parts]
    if not pts:
        return 0.15, 0.1, Vector((0, 0, z))
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    return (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2, Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, z))


CLS = {}


def belt(body, z, hexcol, off=0.012, width=0.045):
    rx, ry, c = extent(body, z, ("spine", "thighL", "thighR"))
    return band(c, 1.0, (0, 0, 1), width, 0.008, hexcol, scale=(rx + off, ry + off, 1))


def front_y(body, z, half_w, dz=0.03):
    cls = CLS[body.name]
    ys = [v.co.y for v in SRC[body.name].vertices if abs(v.co.z - z) < dz and abs(v.co.x) < half_w
          and not cls[v.index][0].startswith(("uarm", "farm", "hand"))]
    return min(ys) if ys else -0.12


def apron(body, hexcol, z_top, z_bot, width, off=0.03, curve=1.6, folds=0.004):
    """A cloth or leather apron hanging in front, following the chest, belly and thighs."""
    nx, nz = 16, 24
    bm = bmesh.new()
    grid = []
    fy = {}
    for j in range(nz + 1):
        z = z_top + (z_bot - z_top) * j / nz
        fy[j] = front_y(body, z, width / 2)
    # an apron hangs straight from the belly down: below the hips it never tucks back in toward the legs
    running = 1e9
    for j in range(nz + 1):
        running = min(running, fy[j])
        if z_top + (z_bot - z_top) * j / nz < body_hip(body):
            fy[j] = running
    for j in range(nz + 1):
        z = z_top + (z_bot - z_top) * j / nz
        row = []
        for i in range(nx + 1):
            x = (i / nx - 0.5) * width
            row.append(bm.verts.new((x, fy[j] - off + curve * x * x, z)))
        grid.append(row)
    for j in range(nz):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]))
    me = bpy.data.meshes.new("apron")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("apron", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(rd.real_mat(hexcol))
    for p in me.polygons:
        p.use_smooth = True
    if folds:
        tex = bpy.data.textures.new("apron_folds", "WOOD")
        tex.wood_type = "BANDNOISE"
        tex.noise_scale = 0.08
        f = o.modifiers.new("folds", "DISPLACE")
        f.texture = tex
        f.texture_coords = "GLOBAL"
        f.direction = "Y"
        f.strength = folds
    so = o.modifiers.new("thick", "SOLIDIFY")
    so.thickness = 0.004
    sub = o.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    return o, fy


HIP = {}


def body_hip(body):
    return HIP[body.name]


def skirt(body, hexcol, z_top, z_bot, flare=0.08, off=0.015, folds=0.012, n=64, rows=24):
    """A skirt or tunic tail: follows the waist and hips, then falls straight with folds."""
    bm = bmesh.new()
    rings = []
    rx_prev = ry_prev = 0.0
    for j in range(rows + 1):
        t = j / rows
        z = z_top + (z_bot - z_top) * t
        rx, ry, c = extent(body, z, ("spine", "thighL", "thighR", "shinL", "shinR"))
        rx = max(rx + off, rx_prev) + flare * t / rows * 2
        ry = max(ry + off, ry_prev) + flare * 0.6 * t / rows * 2
        rx_prev, ry_prev = rx, ry
        ring = []
        for i in range(n):
            a = 2 * math.pi * i / n
            fold = 1 + folds * t * 6 * math.sin(a * 9 + t * 2)
            ring.append(bm.verts.new((c.x + math.cos(a) * rx * fold, c.y + math.sin(a) * ry * fold, z)))
        rings.append(ring)
    for j in range(rows):
        for i in range(n):
            bm.faces.new((rings[j][i], rings[j][(i + 1) % n], rings[j + 1][(i + 1) % n], rings[j + 1][i]))
    me = bpy.data.meshes.new("skirt")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new("skirt", me)
    bpy.context.scene.collection.objects.link(o)
    me.materials.append(rd.real_mat(hexcol))
    for p in me.polygons:
        p.use_smooth = True
    so = o.modifiers.new("thick", "SOLIDIFY")
    so.thickness = 0.004
    sub = o.modifiers.new("sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 2
    return o


def shirt(body, cls, seg, hip_z, hexcol, sleeves="rolled", off=0.008, folds=0.004, low=0.12, name="shirt"):
    def pick(c, co):
        if c[0] == "spine" and co.z > hip_z - low:
            return True
        if c[0] == "neck" and c[1] < 0.3:
            return True
        if c[0].startswith("uarm"):
            return True
        return c[0].startswith("farm") and c[1] < (0.45 if sleeves == "rolled" else 0.97 if sleeves == "long" else 0.0)
    o = garment(body, cls, name, hexcol, pick, off, 0.003, folds=folds)
    if sleeves == "rolled":
        for s in "LR":
            a, b = seg["farm" + s]
            band(pt(seg, "farm" + s, 0.45), 0.048 + off, b - a, 0.045, 0.012, hexcol)
    return o


def trousers(body, cls, seg, hip_z, hexcol, hem=0.6, off=0.02, roll=None):
    garment(body, cls, "trousers", hexcol, lambda c, co: c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < hem)
            or (c[0] == "spine" and co.z < hip_z + 0.1), off, 0.004, folds=0.012)
    if roll:
        for s in "LR":
            a, b = seg["shin" + s]
            band(pt(seg, "shin" + s, hem - 0.03), 0.06 + off, b - a, 0.05, 0.014, roll)


def boots(body, cls, seg, hexcol, top=0.45, laces=None, cuff=None):
    garment(body, cls, "boots", hexcol, lambda c, co: c[0].startswith("foot") or (c[0].startswith("shin") and c[1] > top),
            0.014, 0.006, folds=0.0, smooth=1)
    for s in "LR":
        if laces:
            for k in range(5):
                p0 = pt(seg, "shin" + s, top + 0.18 + k * 0.08)
                cd.box((p0.x, p0.y - 0.062, p0.z), (0.022, 0.003, 0.003), laces, 0.2)
        if cuff:
            a, b = seg["shin" + s]
            band(pt(seg, "shin" + s, top + 0.1), 0.066, b - a, 0.05, 0.014, cuff)


def satchel(seg, hip_z, hexcol, bag_side=-1, flap=None, size=(0.085, 0.045, 0.08)):
    """Cross-body bag on one hip, strap over the opposite shoulder."""
    sh = seg["uarmL" if bag_side < 0 else "uarmR"][0]
    hip = Vector((bag_side * 0.17, seg["spine"][0].y - 0.02, hip_z - 0.03))
    strap([(sh.x - 0.04 * -bag_side, sh.y - 0.06, sh.z + 0.02), (0.0, sh.y - 0.155, sh.z - 0.2),
           (hip.x - bag_side * -0.02, hip.y - 0.13, hip.z + 0.12), (hip.x, hip.y - 0.05, hip.z + 0.07)], 0.035, 0.005, hexcol)
    cd.box((hip.x + bag_side * 0.02, hip.y, hip.z), size, hexcol, 0.25)
    cd.box((hip.x + bag_side * 0.02, hip.y - size[1], hip.z + 0.025), (size[0] + 0.003, 0.01, size[2] * 0.75), flap or hexcol, 0.25)
    return hip


def face_group(body, name, test):
    """A vertex group over part of the face (beard, moustache) chosen by test(co)."""
    vg = body.vertex_groups.new(name=name)
    vg.add([v.index for v in body.data.vertices if test(v.co)], 1.0, "REPLACE")


def head_frame(seg):
    h0, h1 = seg["head"]
    return h0, h1, (h1 - h0).length


# ------------------------------------------------------------------ Bram Holloway (Adam's turnaround)
def bram():
    SKIN, HAIR, SHIRT, APRON, PANTS = "#C98E6A", "#C9CBCC", "#E6DCC6", "#6A4429", "#4F5A43"
    BOOT, BELT, BRASS, STEEL = "#6B4426", "#5A3A22", "#C79A3B", "#9AA3A8"
    KIND.clear()
    KIND.update({SHIRT: "linen", APRON: "leather", PANTS: "cloth_heavy", BOOT: "leather", BELT: "leather", BRASS: "brass",
                 STEEL: "steel", "#9FB8BE": "glass", "#EFE6CF": "linen"})
    body, seg, cls, hip_z, neck_z = base("Bram", {"gender": 1.0, "age": 0.82, "muscle": 0.72, "weight": 0.62, "height": 0.6, "proportions": 0.5},
                                         {"caucasian": 1.0, "african": 0.0, "asian": 0.0}, "old_caucasian_male.mhmat", "ponytail01.mhclo",
                                         skin_value=0.9, skin_sat=1.15)
    CLS[body.name], HIP[body.name] = cls, hip_z
    tint_obj(find("ponytail01"), value=2.2, sat=0.05)
    h0, h1, hl = head_frame(seg)
    face_group(body, "beard", lambda co: co.z < h0.z + hl * 0.42 and co.z > h0.z - 0.03 and co.y < h0.y - 0.035)
    curly_hair(body, HAIR, length=0.035, count=2500, curl=0.002, group="beard", kink="NO")
    shirt(body, cls, seg, hip_z, SHIRT)
    trousers(body, cls, seg, hip_z, PANTS, hem=0.55)
    boots(body, cls, seg, BOOT, top=0.4, laces="#3A2A1E")
    knee_z = seg["thighL"][1].z
    apron(body, APRON, neck_z - 0.13, knee_z - 0.03, 0.4, off=0.035)
    for x, z in ((-0.06, neck_z - 0.24), (0.06, neck_z - 0.24), (-0.1, hip_z - 0.12), (0.1, hip_z - 0.12)):
        y = front_y(body, z, 0.2) - 0.045
        cd.box((x, y, z), (0.05, 0.006, 0.055), APRON, 0.2)                       # apron pockets
    for sx in (-1, 1):
        strap([(sx * 0.13, front_y(body, neck_z - 0.13, 0.2) - 0.035, neck_z - 0.13), (sx * 0.07, seg["neck"][0].y - 0.05, neck_z + 0.01),
               (0.0, seg["neck"][0].y + 0.06, neck_z + 0.02)], 0.025, 0.004, APRON)
    belt(body, hip_z + 0.04, BELT, off=0.045)
    y = front_y(body, hip_z, 0.25) - 0.06
    cd.cyl((0.19, y + 0.03, hip_z - 0.04), 0.045, 0.014, BRASS, rot=(math.radians(90), 0, 0.4), verts=40)   # brass dial
    cd.cyl((0.19, y + 0.022, hip_z - 0.04), 0.036, 0.004, "#EFE6CF", rot=(math.radians(90), 0, 0.4))
    for a in (-0.25, 0.25):                                                        # sextant on the other hip
        cd.limb((-0.2, y + 0.04, hip_z - 0.0), (-0.2 + 0.08 * math.sin(a), y + 0.04, hip_z - 0.1), 0.005, 0.004, STEEL)
    torus_arc = cd.torus((-0.2, y + 0.04, hip_z - 0.1), 0.05, 0.004, STEEL, rot=(math.radians(90), 0, 0), scale=(1, 1, 0.5))
    nz = neck_z + 0.01                                                            # goggles round the neck
    band(Vector((0, seg["neck"][0].y, nz)), 0.072, (0, 0.2, 1), 0.02, 0.006, BELT, scale=(1.05, 1.1, 1))
    for sx in (-1, 1):
        band(Vector((sx * 0.036, seg["neck"][0].y - 0.1, nz - 0.03)), 0.03, (0, -1, 0.3), 0.02, 0.008, BRASS)
        cd.sph((sx * 0.036, seg["neck"][0].y - 0.107, nz - 0.028), (0.027, 0.008, 0.027), "#9FB8BE")
    rd.render_sheet_real("Bram", 1.85, [SKIN, HAIR, SHIRT, APRON, PANTS, BOOT, BELT, BRASS, STEEL])


# ------------------------------------------------------------------ Elara Greenborough (Adam's turnaround)
def elara():
    SKIN, HAIR, SHIRT, PANTS, BELT, BAG, BOOT, BOOK = "#8C5A3C", "#1E1612", "#ECE4CF", "#6E8A4A", "#4A3220", "#7A5434", "#4A3324", "#3F6B3A"
    KIND.clear()
    KIND.update({SHIRT: "linen", PANTS: "cloth_heavy", BELT: "leather", BAG: "leather", BOOT: "leather", BOOK: "leather"})
    body, seg, cls, hip_z, neck_z = base("Elara", {"gender": 0.0, "age": 0.4, "muscle": 0.45, "weight": 0.45, "height": 0.45, "proportions": 0.65},
                                         {"african": 0.6, "caucasian": 0.25, "asian": 0.15}, "young_african_female.mhmat", "braid01.mhclo",
                                         skin_value=1.05)
    CLS[body.name], HIP[body.name] = cls, hip_z
    tint_obj(find("braid01"), value=0.35, sat=0.6)
    curly_hair(body, HAIR, length=0.03, count=2500, curl=0.007)
    shirt(body, cls, seg, hip_z, SHIRT, low=0.1)
    sy = seg["neck"][0].y
    for sx in (-1, 1):   # open collar points
        c = cd.box((sx * 0.045, sy - 0.07, neck_z - 0.02), (0.035, 0.008, 0.03), SHIRT, 0.3)
        c.rotation_euler = (math.radians(-30), 0, sx * math.radians(30))
    for k in range(4):   # buttons
        z = neck_z - 0.08 - k * 0.07
        cd.sph((0, front_y(body, z, 0.05) - 0.012, z), (0.006, 0.003, 0.006), "#D9CFB8")
    trousers(body, cls, seg, hip_z, PANTS, hem=0.48, off=0.022, roll=PANTS)
    boots(body, cls, seg, BOOT, top=0.42, laces="#2A1E16")
    belt(body, hip_z + 0.06, BELT, off=0.022)
    for sx in (-1, 1):   # seed pouches on the belt
        cd.sph((sx * 0.15, front_y(body, hip_z, 0.2) + 0.02, hip_z), (0.035, 0.03, 0.045), BAG)
    satchel(seg, hip_z, BAG, bag_side=1)
    wr = seg["handR"][0]
    cd.box((wr.x - 0.02, wr.y - 0.02, wr.z - 0.06), (0.015, 0.075, 0.1), BOOK, 0.15)   # green book in her right hand
    rd.render_sheet_real("Elara", 1.75, [SKIN, HAIR, SHIRT, PANTS, BELT, BAG, BOOT, BOOK])


# ------------------------------------------------------------------ Tessa Reed (Adam's turnaround)
def tessa():
    SKIN, HAIR, JACKET, TUNIC, PANTS = "#A8714E", "#7A1F1B", "#3F6E4A", "#EFE6CF", "#8A5A2E"
    BOOT, BELT, BAG, GLOVE, BAND = "#6B4A30", "#5A3A22", "#C9B48A", "#A0703A", "#C04848"
    KIND.clear()
    KIND.update({JACKET: "cloth_heavy", TUNIC: "linen", PANTS: "cloth_heavy", BOOT: "leather", BELT: "leather", BAG: "cloth_heavy",
                 GLOVE: "leather", BAND: "wool"})
    body, seg, cls, hip_z, neck_z = base("Tessa", {"gender": 0.0, "age": 0.3, "muscle": 0.5, "weight": 0.45, "height": 0.42, "proportions": 0.6},
                                         {"african": 0.45, "caucasian": 0.55, "asian": 0.0}, "young_caucasian_female.mhmat", "afro01.mhclo",
                                         skin_value=0.78, skin_sat=1.2)
    CLS[body.name], HIP[body.name] = cls, hip_z
    tint_obj(find("afro01"), value=1.6, sat=1.4, hue=0.0)
    curly_hair(body, HAIR, length=0.08, count=3500, curl=0.012)
    shirt(body, cls, seg, hip_z, TUNIC, sleeves="none", low=0.1, name="tunic")
    skirt(body, TUNIC, hip_z - 0.02, hip_z - 0.16, flare=0.01, off=0.03, folds=0.006)
    garment(body, cls, "jacket", JACKET,
            lambda c, co: ((c[0] == "spine" and co.z > hip_z - 0.06 and not (abs(co.x) < 0.05 and co.y < -0.02))
                           or c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.45)),
            0.024, 0.005, folds=0.008, hide_skin=False)
    for s in "LR":
        a, b = seg["farm" + s]
        band(pt(seg, "farm" + s, 0.45), 0.07, b - a, 0.05, 0.014, JACKET)
    trousers(body, cls, seg, hip_z, PANTS, hem=0.55, off=0.028)
    boots(body, cls, seg, BOOT, top=0.35)
    belt(body, hip_z + 0.0, BELT, off=0.04)
    y = front_y(body, hip_z, 0.2) - 0.05
    cd.box((-0.14, y, hip_z - 0.06), (0.035, 0.012, 0.075), GLOVE, 0.3)            # work gloves tucked in the belt
    satchel(seg, hip_z, BAG, bag_side=1, flap=BAG)
    a, b = seg["farmR"]
    band(pt(seg, "farmR", 0.95), 0.045, b - a, 0.012, 0.006, BAND)                 # woven bracelet
    rd.render_sheet_real("Tessa", 1.75, [SKIN, HAIR, JACKET, TUNIC, PANTS, BOOT, BELT, BAG, GLOVE, BAND])


# ------------------------------------------------------------------ Maren Holt (new design: FIREFLY_PROMPTS brief)
def maren():
    SKIN, HAIR, BLOUSE, VEST, APRON, SKIRT = "#B07A58", "#7B6A5E", "#EDE4D0", "#7A4E34", "#C9B48A", "#7A6450"
    BOOT, BELT, POST, PAPER = "#4A3324", "#5A3A22", "#3D6FA8", "#F5EFE0"
    KIND.clear()
    KIND.update({BLOUSE: "linen", VEST: "wool", APRON: "linen", SKIRT: "wool", BOOT: "leather", BELT: "leather", POST: "wool",
                 PAPER: "plain", "#8A6A3A": "brass", "#D9EEF2": "glass"})
    body, seg, cls, hip_z, neck_z = base("Maren", {"gender": 0.0, "age": 0.72, "muscle": 0.45, "weight": 0.55, "height": 0.48, "proportions": 0.5},
                                         {"caucasian": 0.7, "african": 0.2, "asian": 0.1}, "middleage_caucasian_female.mhmat", "short01.mhclo",
                                         skin_value=0.85, skin_sat=1.1)
    CLS[body.name], HIP[body.name] = cls, hip_z
    tint_obj(find("short01"), value=0.9, sat=0.25)
    h0, h1, hl = head_frame(seg)
    bun = cd.sph((0, h0.y + 0.07, h0.z + hl * 0.75), (0.045, 0.04, 0.04), "#5E5048")   # hair pinned up in a bun
    shirt(body, cls, seg, hip_z, BLOUSE)
    garment(body, cls, "waistcoat", VEST, lambda c, co: c[0] == "spine" and co.z > hip_z - 0.04 and co.z < neck_z - 0.05
            and not (abs(co.x) < 0.03 and co.y < -0.02 and co.z > neck_z - 0.2), 0.02, 0.006, folds=0.004, hide_skin=False)
    for k in range(4):
        z = neck_z - 0.2 - k * 0.06
        cd.sph((0, front_y(body, z, 0.05) - 0.03, z), (0.007, 0.004, 0.007), "#C79A3B")
    boots(body, cls, seg, BOOT, top=0.5)
    skirt(body, SKIRT, hip_z + 0.06, seg["shinL"][1].z + 0.05, flare=0.1, off=0.025)
    belt(body, hip_z + 0.06, BELT, off=0.03)
    ap, fy = apron(body, APRON, hip_z + 0.05, seg["shinL"][0].z - 0.12, 0.34, off=0.06, curve=1.2)
    for x in (-0.07, 0.07):   # pockets with letters and a pencil
        z = hip_z - 0.15
        y = front_y(body, z, 0.2) - 0.075
        cd.box((x, y - 0.03, z), (0.055, 0.005, 0.06), APRON, 0.2)
        cd.box((x + 0.01, y - 0.028, z + 0.07), (0.035, 0.002, 0.03), PAPER, 0.1)
    cd.limb((0.1, front_y(body, hip_z - 0.1, 0.2) - 0.11, hip_z - 0.12), (0.11, front_y(body, hip_z - 0.1, 0.2) - 0.11, hip_z - 0.02), 0.005, 0.005, "#D9A441")
    satchel(seg, hip_z, BELT, bag_side=1, flap=POST)
    band(Vector((0, seg["neck"][0].y, neck_z + 0.02)), 0.07, (0, 0, 1), 0.05, 0.02, POST, scale=(1.08, 1.05, 1))   # postal-blue neckerchief
    gy = front_y(body, neck_z - 0.12, 0.08) - 0.03                                   # reading glasses on a cord
    for sx in (-1, 1):
        band(Vector((sx * 0.03, gy, neck_z - 0.12)), 0.02, (0, 1, 0), 0.004, 0.003, "#8A6A3A")
        cd.sph((sx * 0.03, gy, neck_z - 0.12), (0.019, 0.002, 0.019), "#D9EEF2")
        strap([(sx * 0.05, gy, neck_z - 0.12), (sx * 0.06, gy + 0.03, neck_z - 0.05), (sx * 0.065, seg["neck"][0].y, neck_z + 0.03)],
              0.002, 0.002, "#3A2A1E")
    rd.render_sheet_real("MarenHolt_draft", 1.75, [SKIN, HAIR, BLOUSE, VEST, APRON, SKIRT, BOOT, BELT, POST])


# ------------------------------------------------------------------ Rowan Finch (new design: FIREFLY_PROMPTS brief)
def rowan():
    SKIN, HAIR, TUNIC, SHAWL, PATTERN, PANTS, BOOT, STICK, CAP = "#C08A66", "#EDEBE6", "#E3DAC2", "#6F7F5A", "#D9CFAE", "#8A8468", "#5A4030", "#8A6440", "#55664A"
    KIND.clear()
    KIND.update({TUNIC: "linen", SHAWL: "wool", PATTERN: "wool", PANTS: "cloth_heavy", BOOT: "leather", STICK: "wood", CAP: "wool"})
    body, seg, cls, hip_z, neck_z = base("Rowan", {"gender": 1.0, "age": 0.93, "muscle": 0.35, "weight": 0.5, "height": 0.5, "proportions": 0.5},
                                         {"caucasian": 0.8, "african": 0.2, "asian": 0.0}, "old_caucasian_male.mhmat", "short02.mhclo",
                                         skin_value=0.92, skin_sat=1.1)
    CLS[body.name], HIP[body.name] = cls, hip_z
    tint_obj(find("short02"), value=2.4, sat=0.0)
    h0, h1, hl = head_frame(seg)
    face_group(body, "beard", lambda co: co.z < h0.z + hl * 0.4 and co.z > h0.z - 0.02 and co.y < h0.y - 0.04)
    curly_hair(body, HAIR, length=0.02, count=2500, curl=0.001, group="beard", kink="NO")
    shirt(body, cls, seg, hip_z, TUNIC, sleeves="long", low=0.05, name="tunic")
    skirt(body, TUNIC, hip_z + 0.02, seg["thighL"][1].z + 0.02, flare=0.03, off=0.03, folds=0.008)
    belt(body, hip_z + 0.03, "#6A4A30", off=0.04)
    trousers(body, cls, seg, hip_z, PANTS, hem=0.6)
    boots(body, cls, seg, BOOT, top=0.5)
    garment(body, cls, "shawl", SHAWL, lambda c, co: (c[0] == "spine" and co.z > neck_z - 0.22) or (c[0].startswith("uarm") and c[1] < 0.3)
            or (c[0] == "neck" and c[1] < 0.4), 0.03, 0.012, folds=0.006, hide_skin=False)
    for sx in (-1, 1):   # long knitted ends hanging in front, with stripes and fringe
        top = Vector((sx * 0.08, front_y(body, neck_z - 0.1, 0.15) - 0.04, neck_z - 0.08))
        bot = Vector((sx * 0.075, front_y(body, hip_z - 0.1, 0.15) - 0.05, hip_z - 0.12))
        strap([tuple(top), tuple((top + bot) / 2 + Vector((0, -0.02, 0))), tuple(bot)], 0.09, 0.012, SHAWL)
        for k in range(4):
            p0 = top.lerp(bot, 0.3 + k * 0.17)
            cd.box((p0.x, p0.y - 0.012, p0.z), (0.045, 0.003, 0.008), PATTERN, 0.2)
        for k in range(6):
            cd.limb((bot.x + (k - 2.5) * 0.015, bot.y, bot.z), (bot.x + (k - 2.5) * 0.015, bot.y, bot.z - 0.05), 0.003, 0.002, SHAWL)
    hr = seg["handR"][0]   # walking stick with a windmill-sail carving
    cd.cyl((hr.x - 0.03, hr.y - 0.06, hr.z / 2 + 0.05), 0.014, hr.z + 0.1, STICK, r2=0.011)
    for k in range(4):
        ang = k * math.pi / 2 + 0.4
        cd.limb((hr.x - 0.03, hr.y - 0.076, hr.z + 0.12), (hr.x - 0.03 + 0.025 * math.cos(ang), hr.y - 0.076, hr.z + 0.12 + 0.025 * math.sin(ang)),
                0.004, 0.004, "#5A3E28")
    cd.sph((hr.x - 0.03, hr.y - 0.06, hr.z + 0.16), (0.024, 0.024, 0.024), STICK)
    cz = h0.z + hl * 0.82   # soft knitted cap
    cd.sph((0, h0.y + 0.01, cz), (0.112, 0.118, 0.06), CAP)
    band(Vector((0, h0.y + 0.0, cz - 0.03)), 0.104, (0, 0.15, 1), 0.03, 0.01, CAP, scale=(1.0, 1.08, 1))
    rd.render_sheet_real("RowanFinch_draft", 1.75, [SKIN, HAIR, TUNIC, SHAWL, PATTERN, PANTS, BOOT, STICK, CAP])


# ------------------------------------------------------------------ three background villagers (new, unnamed)
def villagers():
    looks = (
        ("A", {"gender": 1.0, "age": 0.55, "muscle": 0.6, "weight": 0.55, "height": 0.55}, {"african": 0.7, "caucasian": 0.3, "asian": 0.0},
         "middleage_african_male.mhmat", "short02.mhclo", ("#9A6648", "#3A2A20", "#D9C9A6", "#7D5A3C", "#5B6B4A", "#4A3324", "#C79A3B")),
        ("B", {"gender": 0.0, "age": 0.6, "muscle": 0.45, "weight": 0.6, "height": 0.45}, {"caucasian": 1.0, "african": 0.0, "asian": 0.0},
         "middleage_caucasian_female.mhmat", "bob02.mhclo", ("#E0B090", "#8A5A2E", "#B8C9D6", "#E8DFC8", "#6A5A48", "#5A4030", "#9B4A3A")),
        ("C", {"gender": 1.0, "age": 0.4, "muscle": 0.5, "weight": 0.45, "height": 0.6}, {"asian": 0.5, "african": 0.3, "caucasian": 0.2},
         "young_asian_male.mhmat", "short04.mhclo", ("#6E4630", "#222222", "#C8A06A", "#556E7A", "#7A6A50", "#3E2C22", "#E8DFC8")),
    )
    for tag, pheno, race, skin, hair, (SKIN, HAIR, SHIRT, OUTER, PANTS, BOOT, ACCENT) in looks:
        KIND.clear()
        KIND.update({SHIRT: "linen", OUTER: "wool" if tag != "C" else "cloth_heavy", PANTS: "cloth_heavy", BOOT: "leather",
                     ACCENT: "wool", "#D8BF7A": "cloth_heavy", "#5A3A22": "leather"})
        body, seg, cls, hip_z, neck_z = base("Villager" + tag, pheno, race, skin, hair)
        CLS[body.name], HIP[body.name] = cls, hip_z
        h0, h1, hl = head_frame(seg)
        shirt(body, cls, seg, hip_z, SHIRT, sleeves="rolled" if tag != "C" else "long")
        trousers(body, cls, seg, hip_z, PANTS, roll=PANTS if tag == "A" else None)
        boots(body, cls, seg, BOOT, top=0.45)
        belt(body, hip_z + 0.04, "#5A3A22", off=0.03)
        if tag == "A":   # farmer: brown waistcoat, straw hat
            garment(body, cls, "vest", OUTER, lambda c, co: c[0] == "spine" and co.z > hip_z - 0.04 and co.z < neck_z - 0.04
                    and not (abs(co.x) < 0.03 and co.y < -0.02), 0.02, 0.006, folds=0.004, hide_skin=False)
            cd.cyl((0, h0.y, h0.z + hl * 0.85), 0.2, 0.012, "#D8BF7A", verts=48)
            cd.cyl((0, h0.y, h0.z + hl * 0.95), 0.1, 0.1, "#D8BF7A", r2=0.09, verts=48)
            band(Vector((0, h0.y, h0.z + hl * 0.9)), 0.1, (0, 0, 1), 0.02, 0.004, ACCENT)
        elif tag == "B":  # cream apron, red neckerchief
            apron(body, OUTER, hip_z + 0.06, seg["thighL"][1].z, 0.34, off=0.04)
            band(Vector((0, seg["neck"][0].y, neck_z + 0.02)), 0.068, (0, 0, 1), 0.045, 0.02, ACCENT, scale=(1.08, 1.05, 1))
        else:             # slate jacket, cream scarf
            garment(body, cls, "jacket", OUTER, lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.1 and not (abs(co.x) < 0.04 and co.y < -0.02))
                    or c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.95), 0.024, 0.005, folds=0.008, hide_skin=False)
            band(Vector((0, seg["neck"][0].y, neck_z + 0.03)), 0.075, (0, 0, 1), 0.07, 0.03, ACCENT, scale=(1.1, 1.05, 1))
        rd.render_sheet_real("Villager%s_draft" % tag, 1.8, [SKIN, HAIR, SHIRT, OUTER, PANTS, BOOT, ACCENT])
        bpy.ops.wm.read_factory_settings(use_empty=True)


if __name__ == "__main__":
    for w in WHICH:
        {"kieran": kieran, "bram": bram, "elara": elara, "tessa": tessa, "maren": maren, "rowan": rowan, "villagers": villagers}[w]()
    print("LS_HUMANS_OK", flush=True)
