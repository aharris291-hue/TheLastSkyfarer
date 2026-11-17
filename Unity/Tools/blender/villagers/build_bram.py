"""Bram Holloway, Windsong Tavern keeper (D-10), built from Adam's turnaround (art_source/characters/Bram Holloway
Turnaround.jpeg) with the Kieran pipeline: an MPFB (CC0) body shaped as an older, broad, weathered man; clothes cut
from the body surface; rigid accessories on bones; procedural hair and beard. Colours sampled from the sheet.

  Silver hair combed back into a short ponytail, full white beard and moustache, cream work shirt with the sleeves
  rolled to the elbow, long brown leather apron with chest and hip pockets (pens, pliers), wide belt with a brass
  compass and a sextant, flying goggles round his neck, dark olive trousers, tall laced work boots.

  blender --background --python build_bram.py -- <Unreal/Tools/blender/kieran folder> <output folder>
Writes Bram_Holloway_Master.blend and preview renders to the output folder.
"""
import math
import os
import random
import sys

ARGS = sys.argv[sys.argv.index("--") + 1:]
KIERAN_TOOLS, OUT = ARGS[0], ARGS[1]
os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
sys.argv = [sys.argv[0], "--", "body"]             # the Kieran modules read their own arguments on import
sys.path.insert(0, KIERAN_TOOLS)
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
import build_kieran as bk  # noqa: E402
import dress_kieran as dk  # noqa: E402

# Bram's palette (sampled from the turnaround) and material kinds.
dk.PAL.update({
    "skin": "#B07C5E", "hair": "#B9B6AE", "beard": "#D8D4CC", "shirt": "#E3D9C1", "cuff": "#D8CDB2", "apron": "#6B4429",
    "apron_dark": "#55341F", "trousers": "#4C5240", "boots": "#5E4029", "boot_dark": "#46301F", "sole": "#2A1F17",
    "belt": "#4E3523", "brass": "#B08A44", "steel": "#A9AEB0", "lens": "#8FB4C2", "dial": "#EFE6CF", "pen": "#2F3A44",
    "feather": "#E9E4D8", "paper": "#EDE4CC",
})
dk.KIND.update({"beard": "hair", "apron": "leather", "apron_dark": "leather", "pen": "paint", "feather": "cloth", "paper": "paper"})
_orig_mat = dk.mat


def mat(key):
    m = _orig_mat(key)
    m.name = "M_Bram_" + key if not m.name.startswith("M_Bram_") else m.name
    return m


dk.mat = mat
random.seed(41)


# ------------------------------------------------------------------ body
def build_body():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    HS = bk.mpfb()
    info = HS._create_default_human_info_dict()
    info["phenotype"].update({"gender": 1.0, "age": 0.8, "muscle": 0.74, "weight": 0.68, "height": 0.6, "proportions": 0.55})
    info["phenotype"]["race"] = {"african": 0.0, "asian": 0.0, "caucasian": 1.0}
    info.update({"eyes": "high-poly.mhclo", "eyebrows": "eyebrow001.mhclo", "eyelashes": "mindfront_eyelashes_01.mhclo",
                 "teeth": "teeth_base.mhclo", "skin_mhmat": "old_caucasian_male.mhmat", "skin_material_type": "ENHANCED_SSS",
                 "rig": "game_engine", "name": "Bram"})
    info["targets"] = [{"target": t, "value": v} for t, v in {
        "torso-scale-horiz-incr": 0.35, "torso-scale-depth-incr": 0.2, "shoulder-scale-horiz-incr": 0.3,
        "l-upperarm-scale-horiz-incr": 0.3, "r-upperarm-scale-horiz-incr": 0.3, "l-lowerarm-scale-horiz-incr": 0.35,
        "r-lowerarm-scale-horiz-incr": 0.35, "chin-prominent-incr": 0.3, "nose-scale-vert-incr": 0.3, "nose-hump-incr": 0.4,
        "l-eye-scale-decr": 0.2, "r-eye-scale-decr": 0.2, "forehead-scale-vert-incr": 0.2}.items()]
    st = HS.get_default_deserialization_settings()
    st["load_clothes"] = False
    st["subdiv_levels"] = 0
    try:
        body = HS.deserialize_from_dict(info, st)
    except Exception as e:   # unknown targets are skipped one at a time by retrying without them
        print("LS_BRAM target problem:", e, flush=True)
        info["targets"] = []
        body = HS.deserialize_from_dict(info, st)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rig.name = "Bram_Rig"
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for side, s in (("l", 1), ("r", -1)):            # stands like the sheet: arms a little out, feet apart
        for bone, target in (("upperarm", (s * 0.24, 0.02, -1.0)), ("lowerarm", (s * 0.16, -0.1, -1.0)),
                             ("thigh", (s * 0.07, 0.0, -1.0)), ("calf", (s * 0.045, 0.02, -1.0))):
            pb = rig.pose.bones["%s_%s" % (bone, side)]
            head = pb.head.copy()
            q = (pb.tail - pb.head).normalized().rotation_difference(Vector(target).normalized())
            pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
            bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    baked = {o: bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg) for o in meshes}
    for o, me in baked.items():
        if o.data.shape_keys:
            o.shape_key_clear()
        for m in list(o.modifiers):
            if m.type != "ARMATURE":
                o.modifiers.remove(m)
        o.data = me
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    bpy.ops.pose.select_all(action="SELECT")
    bpy.ops.pose.armature_apply(selected=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for o in meshes:
        for p in o.data.polygons:
            p.use_smooth = True
    return bpy.data.objects.get("Bram.body") or body, rig


def skin_weights_to(o, groups):
    """groups: list of (bone, weight function of world co)."""
    for vg in list(o.vertex_groups):
        o.vertex_groups.remove(vg)
    vgs = {b: o.vertex_groups.new(name=b) for b, _ in groups}
    for v in o.data.vertices:
        ws = [(b, f(v.co)) for b, f in groups]
        tot = sum(w for _, w in ws) or 1.0
        for b, w in ws:
            if w > 0:
                vgs[b].add([v.index], w / tot, "REPLACE")


def skinned(o, rig):
    a = o.modifiers.new("Armature", "ARMATURE")
    a.object = rig
    o.parent = rig


# ------------------------------------------------------------------ hair and beard
def metaball_mesh(name, elements, key, rig, bone, resolution=0.006):
    mb = bpy.data.metaballs.new(name + "_mass")
    mb.resolution = mb.render_resolution = resolution
    mb.threshold = 0.3
    for co, r in elements:
        e = mb.elements.new()
        e.co, e.radius, e.stiffness = co, r, 1.3
    mo = bpy.data.objects.new(name, mb)
    bpy.context.scene.collection.objects.link(mo)
    bpy.context.view_layer.update()
    for o in bpy.context.selected_objects:
        o.select_set(False)
    bpy.context.view_layer.objects.active = mo
    mo.select_set(True)
    bpy.ops.object.convert(target="MESH")
    m = bpy.context.active_object
    m.name = name
    m.data.materials.append(mat(key))
    for p in m.data.polygons:
        p.use_smooth = True
    dk.attach(m, rig, bone)
    return m


def strands(name, roots, key, rig, bone, length, thick, combed):
    """Thin swept strands over a mass for texture (combed: the direction they run)."""
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions, cu.bevel_resolution, cu.resolution_u, cu.bevel_depth = "3D", 0, 3, 1.0
    for co, n in roots:
        sp = cu.splines.new("NURBS")
        sp.points.add(4)
        d = combed(co)
        d = (d - n * d.dot(n)).normalized()             # lies along the surface, combed
        L = length * random.uniform(0.7, 1.2)
        for j in range(5):
            t = j / 4
            q = co + n * 0.002 + d * L * t - n * 0.004 * t * t
            sp.points[j].co = (q.x, q.y, q.z, 1)
            sp.points[j].radius = thick * (1 - 0.6 * t)
        sp.use_endpoint_u, sp.order_u = True, 4
    o = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(o)
    cu.materials.append(mat(key))
    dk.attach(o, rig, bone)
    return o


def hair_and_beard(body, rig, B):
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    me = body.data
    scalp = body.vertex_groups.get("scalp")
    sidx = [v.index for v in me.vertices if scalp and any(g.group == scalp.index and g.weight > 0.4 for g in v.groups)]
    back_y = max(me.vertices[i].co.y for i in sidx)
    face_y = min(v.co.y for v in me.vertices if abs(v.co.z - (h0.z + hl * 0.3)) < 0.02 and abs(v.co.x) < 0.02)
    # Combed-back silver hair: a close cap, a little fuller at the crown and swept at the temples.
    els, roots = [], []
    for i in sidx:
        v = me.vertices[i]
        up = (v.co.z - h0.z) / hl
        n = v.normal.normalized()
        depth = 0.006 + 0.012 * max(0.0, up - 0.35)
        els.append((v.co + n * depth + Vector((0, 0.004, 0)), random.uniform(0.02, 0.024)))
        if random.random() < 0.2:
            roots.append((v.co + n * (depth + 0.006), n))
    cap = metaball_mesh("Bram_hair", els, "hair", rig, "head", resolution=0.008)
    dk.fold_bands(scale=0.008, strength=0.0025, name="combed")(cap)          # sculpted, combed-back grooves
    strands("Bram_hair_strands", roots[:700], "hair", rig, "head", 0.05, 0.0022,
            lambda co: Vector((0, 1, -0.15 if co.z > h0.z + hl * 0.6 else -0.6)))
    # Short ponytail tied at the back of the head.
    tie = Vector((0, back_y + 0.012, h0.z + hl * 0.42))
    pts = [tie + Vector((0, 0.02 * t + 0.02 * t * t, -0.2 * t)) for t in (0, 0.25, 0.5, 0.75, 1.0)]
    pels = []
    for k, p in enumerate(pts[:-1]):
        for s in range(6):
            q = p.lerp(pts[k + 1], s / 6)
            r = 0.026 * (1 - (k + s / 6) / 4 * 0.75)
            pels.append((q, r))
    metaball_mesh("Bram_ponytail", pels, "hair", rig, "head")
    dk.ring_band("Bram_hair_tie", tie + Vector((0, 0.008, -0.01)), 0.016, 0.014, 0.012, 0.004, "belt", parent=rig, bone="head",
                 tilt=(math.radians(80), 0, 0))
    # Full white beard and moustache, placed from his measured profile: nose tip, mouth and chin.
    prof = [v for v in me.vertices if abs(v.co.x) < 0.01 and v.co.z > h0.z - hl * 0.6 and v.co.z < h0.z + hl * 0.9]
    nose = min(prof, key=lambda v: v.co.y)
    nose_z, nose_y = nose.co.z, nose.co.y
    front = [v for v in prof if v.co.y < nose_y + 0.04 and v.co.z < nose_z]
    chin_z = min(v.co.z for v in front)
    mouth_z = nose_z - (nose_z - chin_z) * 0.42
    print("LS_BRAM face: nose %.3f mouth %.3f chin %.3f" % (nose_z, mouth_z, chin_z), flush=True)
    bels, broots = [], []
    for v in me.vertices:
        co = v.co
        if co.y > nose_y + 0.09 or co.z > nose_z - 0.012 or co.z < chin_z - 0.045:
            continue
        side = abs(co.x)
        if side > 0.075:
            continue
        if side < 0.03 and mouth_z - 0.012 < co.z < mouth_z + 0.014:
            continue                                   # keep the lips clear
        if side < 0.05 and co.z > mouth_z + 0.014:
            continue                                   # moustache only under the nose (added below)
        n = v.normal.normalized()
        if n.z > 0.6:
            continue
        below = max(0.0, mouth_z - co.z) / max(mouth_z - chin_z + 0.04, 0.01)
        depth = 0.006 + 0.018 * min(1.0, below)
        bels.append((co + n * depth + Vector((0, 0, -0.012 * below)), random.uniform(0.012, 0.016)))
        if random.random() < 0.25:
            broots.append((co + n * (depth + 0.006), n))
    for sx in (-1, 1):                                 # moustache sweeping down into the beard at the corners
        for k in range(8):
            t = k / 7
            p = Vector((sx * (0.004 + 0.032 * t), nose_y + 0.012 + 0.016 * t, mouth_z + 0.016 - 0.03 * t * t))
            bels.append((p, 0.012 - 0.003 * t))
    beard = metaball_mesh("Bram_beard", bels, "beard", rig, "head", resolution=0.005)
    dk.fold_bands(scale=0.006, strength=0.002, name="wavy")(beard)
    strands("Bram_beard_strands", broots[:350], "beard", rig, "head", 0.022, 0.0018, lambda co: Vector((0, -0.2, -1)))


# ------------------------------------------------------------------ the outfit
def dress(body, rig):
    seg, B = dk.segments(rig)
    cls = dk.classify(body, seg)
    dk.SRC["body"] = body.data.copy()
    src = dk.SRC["body"]
    hip_z = seg["thigh_l"][0].z
    neck_z = seg["neck"][0].z
    chest_z = neck_z - 0.17
    waist_z = hip_z + 0.11
    knee_z = seg["shin_l"][0].z
    sy = seg["spine"][1].y
    body.data.materials.clear()
    body.data.materials.append(mat("skin"))
    dk.paint_skin(body, B)
    eye = os.path.join(os.environ["APPDATA"], "Blender Foundation", "Blender", "5.2", "extensions", ".user", "blender_org", "mpfb",
                       "data", "eyes", "materials", "bluegreen_eye.png")
    for o in bpy.data.objects:
        if o.type == "MESH" and "high-poly" in o.name and os.path.exists(eye):
            img = bpy.data.images.load(eye)
            for slot in o.material_slots:
                if slot.material and slot.material.node_tree:
                    for n in slot.material.node_tree.nodes:
                        if n.type == "TEX_IMAGE" and n.image and "eye" in n.image.name.lower() and "normal" not in n.image.name.lower():
                            n.image = img
        if o.type == "MESH" and ("eyebrow" in o.name or "eyelash" in o.name):
            o.data.materials.clear()
            o.data.materials.append(mat("beard"))
    G = lambda *a, **k: dk.garment(body, rig, cls, *a, **k)   # noqa: E731

    # Cream work shirt, sleeves rolled to the elbow (forearms bare), loose over the belly.
    shirt = G("Bram_shirt", "shirt", lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.06) or (c[0] == "neck" and c[1] < 0.22)
              or c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.06),
              lambda c, co: 0.012 if c[0] == "spine" else 0.01, 0.003, folds=dk.fold_bands(strength=0.003), smooth=1)
    dk.hem_piping(shirt, "cuff", 0.003)
    for s in "lr":
        a, b = seg["farm_" + s]
        c, rx, ry = dk.ring_at(body, cls, dk.pt(seg, "farm_" + s, 0.06).z, ("farm_" + s, "uarm_" + s), 0.022)
        q = Vector((0, 0, 1)).rotation_difference((b - a).normalized())
        dk.ring_band("Bram_rolled_sleeve_" + s, dk.pt(seg, "farm_" + s, 0.05), rx, ry, 0.05, 0.01, "cuff", parent=rig,
                     bone="lowerarm_" + s, tilt=q.to_euler())
    # Dark olive trousers into the boots.
    G("Bram_trousers", "trousers", lambda c, co: c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < 0.6) or
      (c[0] == "spine" and co.z < waist_z + 0.01), lambda c, co: 0.016 if c[0].startswith("thigh") else (0.02 if c[0].startswith("shin") else 0.013),
      0.004, folds=dk.fold_bands(scale=0.035, strength=0.005),
      smooth_group=("crotch", lambda co: abs(co.x) < 0.07 and hip_z - 0.15 < co.z < hip_z - 0.02, 8))
    # Tall laced work boots.
    G("Bram_boots", "boots", lambda c, co: (c[0].startswith("shin") and c[1] > 0.4) or (c[0].startswith("foot") and co.z > 0.07),
      lambda c, co: 0.02, 0.007, smooth=2)
    for s in "lr":
        fv = [src.vertices[i].co.copy() for i, c in cls.items() if c[0] == "foot_" + s or (c[0] == "shin_" + s and c[1] > 0.85)]
        bmh = bmesh.new()
        for co in fv:
            bmh.verts.new(co + Vector((0, -0.006, 0)))
        bmesh.ops.convex_hull(bmh, input=bmh.verts)
        me = bpy.data.meshes.new("Bram_bootfoot_" + s)
        bmh.to_mesh(me)
        bmh.free()
        bf = bpy.data.objects.new("Bram_bootfoot_" + s, me)
        bpy.context.scene.collection.objects.link(bf)
        me.materials.append(mat("boots"))
        sm = bf.modifiers.new("sub", "SUBSURF"); sm.levels = 1
        dk.attach(bf, rig, "foot_" + s)
        zmin = min(v.co.z for v in me.vertices)
        cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
        cyy = sum(v.co.y for v in me.vertices) / len(me.vertices)
        ylen = max(v.co.y for v in me.vertices) - min(v.co.y for v in me.vertices)
        dk.box("Bram_sole_" + s, (cx, cyy - 0.005, zmin + 0.012), (0.05, ylen / 2 * 0.9, 0.01), "sole", 0.4, parent=rig, bone="foot_" + s)
        z = dk.pt(seg, "shin_" + s, 0.42).z
        c, rx, ry = dk.ring_at(body, cls, z, ("shin_" + s,), 0.03)
        dk.ring_band("Bram_boot_cuff_" + s, c, rx, ry, 0.03, 0.008, "boot_dark", parent=rig, bone="calf_" + s)
        for k in range(5):                              # laces up the front
            zz = dk.pt(seg, "shin_" + s, 0.55 + k * 0.08).z
            cc, rx2, ry2 = dk.ring_at(body, cls, zz, ("shin_" + s,), 0.03)
            dk.box("Bram_lace_%s%d" % (s, k), (cc.x, cc.y - ry2 - 0.002, zz), (0.016, 0.002, 0.003), "boot_dark", 0.2, parent=rig, bone="calf_" + s)

    # The long leather apron: a bib cut from the chest (so it follows him) and a skirt hanging straight from the waist.
    def front_y(x, z, tol=0.025):
        ys = [v.co.y for i, v in enumerate(src.vertices) if abs(v.co.z - z) < tol and abs(v.co.x - x) < tol and i in cls and cls[i][0] in ("spine", "thigh_l", "thigh_r")]
        return min(ys) if ys else None
    top_z, bottom_z = chest_z + 0.07, knee_z - 0.03
    bib = G("Bram_apron_bib", "apron", lambda c, co: c[0] == "spine" and co.y < sy - 0.005 and abs(co.x) < 0.125 + 0.4 * max(0.0, (chest_z - co.z))
            and waist_z - 0.04 < co.z < top_z, lambda c, co: 0.026, 0.005, folds=dk.fold_bands(scale=0.06, strength=0.003, name="wear"), hide=False, smooth=10)
    dk.hem_piping(bib, "apron_dark", 0.004)
    hang_y = min(y for y in (front_y(x, hip_z) for x in (-0.12, -0.06, 0, 0.06, 0.12)) if y is not None) - 0.03
    belly_y = min(y for y in (front_y(x, waist_z) for x in (-0.06, 0, 0.06)) if y is not None) - 0.03
    nx, nz = 12, 18
    verts, faces = [], []
    sz0 = waist_z - 0.02
    for j in range(nz + 1):
        t = j / nz
        z = sz0 - (sz0 - bottom_z) * t
        half = 0.2 + 0.05 * t
        for i in range(nx + 1):
            u = i / nx
            x = -half + 2 * half * u
            y = min(belly_y, hang_y) * (1 - min(1.0, t * 3)) + hang_y * min(1.0, t * 3) - 0.015 * t
            y += (abs(x) / half) ** 2 * 0.06                # wraps round the sides of the legs
            verts.append((x, y, z))
    for j in range(nz):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me = bpy.data.meshes.new("Bram_apron")
    me.from_pydata(verts, [], faces)
    me.materials.append(mat("apron"))
    apron = bpy.data.objects.new("Bram_apron", me)
    bpy.context.scene.collection.objects.link(apron)
    for p in me.polygons:
        p.use_smooth = True
    dk.fold_bands(scale=0.06, strength=0.004, name="wear")(apron)
    s = apron.modifiers.new("thick", "SOLIDIFY"); s.thickness, s.offset = 0.006, 1.0
    sub = apron.modifiers.new("sub", "SUBSURF"); sub.levels = 1
    skin_weights_to(apron, [("pelvis", lambda co: 1.0),
                            ("thigh_l", lambda co: max(0.0, co.x) * 2.0 * max(0.0, (hip_z - co.z) / 0.3)),
                            ("thigh_r", lambda co: max(0.0, -co.x) * 2.0 * max(0.0, (hip_z - co.z) / 0.3))])
    skinned(apron, rig)
    # Neck strap and waist ties.
    for sx in (-1, 1):
        dk.strap("Bram_apron_strap_%d" % sx, [Vector((sx * 0.11, front_y(sx * 0.11, top_z) - 0.012, top_z)),
                                               Vector((sx * 0.08, sy - 0.02, neck_z + 0.02)), Vector((sx * 0.05, sy + 0.05, neck_z + 0.03)),
                                               Vector((0, sy + 0.08, neck_z + 0.02))], 0.022, 0.004, "apron_dark", parent=rig, bone="spine_03")
    c, rx, ry = dk.ring_at(body, cls, waist_z, ("spine",), 0.03)
    dk.ring_band("Bram_apron_tie", c, rx + 0.02, ry + 0.02, 0.02, 0.004, "apron_dark", parent=rig, bone="pelvis")
    # Pockets, pens and tools.
    pz = chest_z - 0.03
    py = front_y(0, pz) - 0.024
    dk.box("Bram_chest_pocket", (0, py, pz), (0.075, 0.006, 0.055), "apron_dark", 0.3, parent=rig, bone="spine_03")
    for k, (x, col) in enumerate(((-0.03, "pen"), (-0.01, "feather"), (0.018, "pen"), (0.034, "steel"))):
        dk.cyl("Bram_pen_%d" % k, (x, py - 0.004, pz + 0.07), 0.0045, 0.08, col, verts=8, parent=rig, bone="spine_03")
    for sx in (-1, 1):
        lz = hip_z - 0.1
        dk.box("Bram_hip_pocket_%d" % sx, (sx * 0.13, hang_y - 0.01, lz), (0.065, 0.006, 0.07), "apron_dark", 0.3, parent=rig, bone="pelvis")
    dk.box("Bram_pliers", (0.12, hang_y - 0.016, hip_z - 0.02), (0.008, 0.004, 0.05), "steel", 0.3, rot=(0, math.radians(12), 0), parent=rig, bone="pelvis")
    dk.box("Bram_wrench", (0.145, hang_y - 0.016, hip_z - 0.03), (0.007, 0.004, 0.055), "steel", 0.3, rot=(0, math.radians(-10), 0), parent=rig, bone="pelvis")
    dk.cyl("Bram_screwdriver", (-0.14, hang_y - 0.016, hip_z - 0.02), 0.007, 0.1, "apron_dark", verts=8, parent=rig, bone="pelvis")
    # Wide belt with a brass compass on the left hip and a sextant on the right.
    c, rx, ry = dk.ring_at(body, cls, waist_z - 0.035, ("spine",), 0.045)
    dk.ring_band("Bram_belt", c, rx, ry, 0.045, 0.008, "belt", parent=rig, bone="pelvis")
    dk.box("Bram_belt_buckle", (0, c.y - ry - 0.01, waist_z - 0.035), (0.028, 0.004, 0.024), "brass", 0.3, parent=rig, bone="pelvis")
    side_x = c.x + rx + 0.015
    dk.cyl("Bram_compass", (side_x, c.y - 0.02, waist_z - 0.09), 0.04, 0.016, "brass", rot=(0, math.radians(90), 0), verts=24, parent=rig, bone="pelvis")
    dk.cyl("Bram_compass_face", (side_x + 0.009, c.y - 0.02, waist_z - 0.09), 0.033, 0.002, "dial", rot=(0, math.radians(90), 0), verts=24, parent=rig, bone="pelvis")
    sx_ = -(c.x + rx + 0.015)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.07, minor_radius=0.005, location=(sx_, c.y - 0.01, waist_z - 0.11),
                                     rotation=(0, math.radians(90), 0), major_segments=24, minor_segments=4)
    arc = bpy.context.active_object
    arc.name = "Bram_sextant_arc"
    bm = bmesh.new(); bm.from_mesh(arc.data)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > 0.0 or abs(v.co.x) > 0.055], context="VERTS")
    bm.to_mesh(arc.data); bm.free()
    arc.data.materials.append(mat("brass"))
    dk.attach(arc, rig, "pelvis")
    for a in (-30, 0, 30):
        dk.box("Bram_sextant_arm%d" % a, (sx_ - 0.006, c.y - 0.01, waist_z - 0.075), (0.003, 0.004, 0.04), "steel", 0.2,
               rot=(math.radians(a), 0, 0), parent=rig, bone="pelvis")
    # Flying goggles resting round his neck.
    gz = neck_z - 0.035
    gy = front_y(0, gz, 0.03)
    gy = (gy if gy is not None else sy - 0.08) - 0.03
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.026, minor_radius=0.007, location=(sx * 0.034, gy, gz), rotation=(math.radians(80), 0, 0),
                                         major_segments=20, minor_segments=6)
        r = bpy.context.active_object; r.name = "Bram_goggle_rim_%d" % sx
        r.data.materials.append(mat("brass")); dk.attach(r, rig, "spine_03")
        dk.cyl("Bram_goggle_lens_%d" % sx, (sx * 0.034, gy + 0.002, gz), 0.021, 0.004, "lens", rot=(math.radians(80), 0, 0), verts=20,
               parent=rig, bone="spine_03")
    dk.box("Bram_goggle_bridge", (0, gy, gz), (0.01, 0.004, 0.005), "brass", 0.2, parent=rig, bone="spine_03")
    nk = dk.pt(seg, "neck", 0.25)
    dk.ring_band("Bram_goggle_strap", Vector((nk.x, nk.y - 0.005, gz + 0.01)), 0.068, 0.07, 0.018, 0.004, "belt", parent=rig, bone="neck_01",
                 tilt=(math.radians(-14), 0, 0))
    dk.COVERED.update(i for i, c in cls.items() if c[0].startswith("foot"))
    # Remove skin hidden under the clothes.
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.index in dk.COVERED for v in f.verts)], context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()
    hair_and_beard(body, rig, B)


# ------------------------------------------------------------------ previews
def render_views():
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = 48
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.exposure = -0.6
    w = bpy.data.worlds.new("look"); sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.86, 0.82, 0.74, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.5
    rig = bpy.data.objects["Bram_Rig"]
    for name, loc, size, energy, col in (("Key", (-2.0, -3.0, 3.2), 2.5, 900, (1.0, 0.95, 0.88)), ("Fill", (3.0, -2.2, 1.4), 3.0, 350, (0.88, 0.92, 1.0)),
                                          ("Rim", (0.8, 3.2, 2.8), 1.5, 700, (1.0, 0.92, 0.8))):
        ld = bpy.data.lights.new("Look_" + name, "AREA"); ld.size, ld.energy, ld.color = size, energy, col
        o = bpy.data.objects.new("Look_" + name, ld); sc.collection.objects.link(o); o.location = loc
        c = o.constraints.new("TRACK_TO"); c.target = rig
    cam = bpy.data.objects.new("LookCam", bpy.data.cameras.new("LookCam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type in ("MESH", "CURVE") for c in o.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    for name, yaw, res, frame in (("Bram_Front", 0, (800, 1200), None), ("Bram_ThreeQuarter", 40, (800, 1200), None), ("Bram_Side", 90, (800, 1200), None),
                                  ("Bram_Rear", 180, (800, 1200), None), ("Bram_Face", 25, (800, 800), 0.42)):
        sc.render.resolution_x, sc.render.resolution_y = res
        a = math.radians(yaw)
        if frame:
            cam.data.ortho_scale = frame
            cz = zmax - 0.16
        else:
            cam.data.ortho_scale = (zmax - zmin) * 1.06
            cz = (zmax + zmin) / 2
        cam.location = (10 * math.sin(a), -10 * math.cos(a), cz)
        cam.rotation_euler = (math.radians(90), 0, a)
        sc.camera = cam
        sc.render.filepath = os.path.join(OUT, "renders", name + ".png")
        bpy.ops.render.render(write_still=True)
        print("LS_RENDER", sc.render.filepath, flush=True)


body, rig = build_body()
z = [(body.matrix_world @ v.co).z for v in body.data.vertices]
print("LS_BRAM height %.3f m" % (max(z) - min(z)), flush=True)
dress(body, rig)
render_views()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Bram_Holloway_Master.blend"))
print("LS_BRAM_OK", flush=True)
