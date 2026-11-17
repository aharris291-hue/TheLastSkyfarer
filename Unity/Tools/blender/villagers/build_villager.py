"""Windrest villagers from Adam's approved turnarounds, built with the Kieran pipeline (MPFB/CC0 body, clothes cut from
the body surface, rigid accessories on bones, procedural hair). One script, one outfit function per villager:

  tessa  Tessa Reed (art_source/characters/Tessa Reed Turnaround.jpeg): Kieran's age, big curly auburn hair, green
         eyes, freckles; long cream tunic under an open green jacket with rolled sleeves, brown belt with leather gloves,
         canvas satchel across the body, beaded bracelet, loose brown trousers bunched over brown boots.
  maren  Maren Holt, postmaster (no sheet yet: designed from the Bible role and docs/unreal/FIREFLY_PROMPTS.md, for Adam's
         approval): in her fifties, greying hair pinned up in a bun, reading glasses on a cord, wool waistcoat over a
         rolled-sleeve blouse, long canvas apron with pockets of letters and a pencil, satchel strap, postal-blue
         neckerchief, calf-length skirt, laced boots.
  rowan  Rowan Finch, village elder (designed the same way): older man, kind but cautious face, neat white beard, soft
         knitted cap, long striped knitted shawl over a simple cream tunic, grey-green trousers, walking stick carved
         with a windmill.
  elara  Elara Greenborough (art_source/characters/Elara Greenborough Turnaround.jpeg), the Orchard Vale grower (D-10):
         dark curly hair with a long braid, hazel eyes; cream button shirt with rolled sleeves, high-waisted green
         trousers rolled above laced dark boots, belt with seed pouches, leather bag across the body.

  blender --background --python build_villager.py -- <Unreal/Tools/blender/kieran folder> <output folder> <tessa|elara>
Writes <Name>_Master.blend and preview renders to the output folder.
"""
import math
import os
import random
import sys

ARGS = sys.argv[sys.argv.index("--") + 1:]
KIERAN_TOOLS, OUT, WHO = ARGS[0], ARGS[1], ARGS[2]
os.makedirs(os.path.join(OUT, "renders"), exist_ok=True)
sys.argv = [sys.argv[0], "--", "body"]
sys.path.insert(0, KIERAN_TOOLS)
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
import build_kieran as bk  # noqa: E402
import dress_kieran as dk  # noqa: E402

CAST = {
    "tessa": dict(name="Tessa", export="Tessa_Reed", seed=5,
                  pheno={"gender": 0.0, "age": 0.4, "muscle": 0.5, "weight": 0.4, "height": 0.58, "proportions": 0.7, "cupsize": 0.4, "firmness": 0.6},
                  race={"african": 0.45, "asian": 0.0, "caucasian": 0.55}, eyes="green_eye.png", brows="eyebrow006.mhclo",
                  targets={"l-eye-scale-incr": 0.35, "r-eye-scale-incr": 0.35, "mouth-angles-up": 0.4, "nose-scale-horiz-decr": 0.2},
                  palette={"skin": "#9C6A4C", "hair": "#561A19", "tunic": "#E8DFC9", "jacket": "#3F6248", "jacket_dark": "#304C38",
                           "trousers": "#8A5B30", "trousers_dark": "#73491F", "boots": "#6B4A31", "boot_dark": "#53382A", "sole": "#2A1F17",
                           "belt": "#5A3B25", "brass": "#A88645", "steel": "#A9AEB0", "bag": "#B39E78", "bag_dark": "#8E7A57",
                           "gloves": "#8A5E35", "bead_a": "#3E6FA8", "bead_b": "#C84B3B", "cuff": "#DCD2BA"}),
    "elara": dict(name="Elara", export="Elara_Greenborough", seed=9,
                  pheno={"gender": 0.0, "age": 0.45, "muscle": 0.55, "weight": 0.45, "height": 0.54, "proportions": 0.65, "cupsize": 0.5, "firmness": 0.6},
                  race={"african": 0.85, "asian": 0.0, "caucasian": 0.15}, eyes="brownlight_eye.png", brows="eyebrow006.mhclo",
                  targets={"l-eye-scale-incr": 0.25, "r-eye-scale-incr": 0.25, "mouth-angles-up": 0.2},
                  palette={"skin": "#7A4E33", "hair": "#1F1915", "shirt": "#E6DDC8", "cuff": "#DCD2BA", "trousers": "#5F7444",
                           "trousers_dark": "#4E6237", "boots": "#3E2C22", "boot_dark": "#2C1F18", "sole": "#1E1612", "belt": "#4A3222",
                           "brass": "#A88645", "steel": "#A9AEB0", "bag": "#7A4F30", "bag_dark": "#63402A", "pouch": "#9A7752",
                           "button": "#C9BFA8", "lace": "#2A1E16"}),
    "maren": dict(name="Maren", export="Maren_Holt", seed=13,
                  pheno={"gender": 0.0, "age": 0.72, "muscle": 0.5, "weight": 0.58, "height": 0.56, "proportions": 0.55, "cupsize": 0.5, "firmness": 0.4},
                  race={"african": 0.2, "asian": 0.0, "caucasian": 0.8}, eyes="grey_eye.png", brows="eyebrow006.mhclo",
                  targets={"mouth-angles-down": 0.15},
                  palette={"skin": "#B98468", "hair": "#8A7E74", "shirt": "#E9E0CB", "cuff": "#DDD3BC", "waistcoat": "#7C5636",
                           "waistcoat_dark": "#5E3F26", "apron": "#BBA780", "apron_dark": "#9C8862", "skirt": "#5B4B3E", "postal": "#3E6A9A",
                           "boots": "#4E3626", "boot_dark": "#3A281C", "sole": "#211812", "belt": "#4E3523", "brass": "#A88645", "steel": "#A9AEB0",
                           "bag": "#7A5234", "bag_dark": "#5E3E26", "letter": "#F1EAD8", "lens": "#9FC6D6", "lace": "#2A1E16", "pencil": "#C9A640"}),
    "rowan": dict(name="Rowan", export="Rowan_Finch", seed=17,
                  pheno={"gender": 1.0, "age": 0.9, "muscle": 0.42, "weight": 0.48, "height": 0.52, "proportions": 0.5},
                  race={"african": 0.1, "asian": 0.0, "caucasian": 0.9}, eyes="brownlight_eye.png", brows="eyebrow001.mhclo",
                  targets={"mouth-angles-up": 0.2},
                  palette={"skin": "#C08F72", "hair": "#E4E1DA", "beard": "#E9E6DF", "tunic": "#E3DAC2", "trousers": "#626B54",
                           "trousers_dark": "#4F5743", "shawl": "#6F8456", "shawl_band": "#E1D5B5", "shawl_dark": "#566A42", "cap": "#5F7148",
                           "boots": "#5A402B", "boot_dark": "#43301F", "sole": "#211812", "belt": "#4E3523", "stick": "#8A6A45",
                           "stick_dark": "#6B4F32", "brass": "#A88645", "steel": "#A9AEB0", "cuff": "#DCD2BA", "lace": "#2A1E16"}),
}
C = CAST[WHO]
NAME = C["name"]
dk.PAL.update(C["palette"])
dk.KIND.update({"waistcoat": "wool", "waistcoat_dark": "wool", "apron": "cloth", "apron_dark": "cloth", "skirt": "wool", "postal": "cloth",
                "letter": "paper", "pencil": "paint", "beard": "hair", "shawl": "wool", "shawl_band": "wool", "shawl_dark": "wool", "cap": "wool",
                "stick": "cloth", "stick_dark": "cloth"})
dk.KIND.update({"tunic": "linen", "jacket": "cloth", "trousers_dark": "cloth", "bag": "cloth", "bag_dark": "leather", "gloves": "leather",
                "bead_a": "paint", "bead_b": "paint", "pouch": "cloth", "lace": "cloth"})
_orig_mat = dk.mat


def mat(key):
    m = _orig_mat(key)
    if not m.name.startswith("M_%s_" % NAME):
        m.name = "M_%s_%s" % (NAME, key)
    return m


dk.mat = mat
random.seed(C["seed"])
MPFB_DATA = os.path.join(os.environ["APPDATA"], "Blender Foundation", "Blender", "5.2", "extensions", ".user", "blender_org", "mpfb", "data")


# ------------------------------------------------------------------ body
def build_body():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    HS = bk.mpfb()
    info = HS._create_default_human_info_dict()
    info["phenotype"].update(C["pheno"])
    info["phenotype"]["race"] = C["race"]
    info.update({"eyes": "high-poly.mhclo", "eyebrows": C["brows"], "eyelashes": "mindfront_eyelashes_01.mhclo",
                 "teeth": "teeth_base.mhclo", "skin_mhmat": "middleage_african_female.mhmat", "skin_material_type": "ENHANCED_SSS",
                 "rig": "game_engine", "name": NAME})
    info["targets"] = [{"target": t, "value": v} for t, v in C["targets"].items()]
    st = HS.get_default_deserialization_settings()
    st["load_clothes"] = False
    st["subdiv_levels"] = 0
    try:
        body = HS.deserialize_from_dict(info, st)
    except Exception as e:
        print("LS_VILLAGER target problem:", e, flush=True)
        info["targets"] = []
        body = HS.deserialize_from_dict(info, st)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rig.name = NAME + "_Rig"
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for side, s in (("l", 1), ("r", -1)):
        for bone, target in (("upperarm", (s * 0.22, 0.02, -1.0)), ("lowerarm", (s * 0.14, -0.08, -1.0)),
                             ("thigh", (s * 0.06, 0.0, -1.0)), ("calf", (s * 0.04, 0.02, -1.0))):
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
    return bpy.data.objects.get(NAME + ".body") or body, rig


# ------------------------------------------------------------------ helpers
def skin_weights_to(o, groups):
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


def metaball_mesh(name, elements, key, rig, bone, resolution=0.007, threshold=0.3):
    mb = bpy.data.metaballs.new(name + "_mass")
    mb.resolution = mb.render_resolution = resolution
    mb.threshold = threshold
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


def skirt(name, key, rig, cls, body, z_top, z_bottom, ease, flare, open_front=0.0, rings=8, segs=28, hip_z=0.0):
    """A tube of cloth from z_top down to z_bottom around the hips/thighs (tunic and jacket tails), optionally open at
    the front (radians of the opening). Skinned to the pelvis and, lower down, a little to each thigh."""
    c, rx, ry = dk.ring_at(body, cls, z_top, ("spine", "thigh_l", "thigh_r"), ease)
    verts, faces = [], []
    a0 = -math.pi / 2 + open_front / 2
    span = 2 * math.pi - open_front
    for j in range(rings + 1):
        t = j / rings
        z = z_top - (z_top - z_bottom) * t
        k = 1.0 + flare * t
        for i in range(segs + 1):
            a = a0 + span * i / segs
            verts.append((c.x + math.cos(a) * rx * k, c.y + math.sin(a) * ry * k * (1.0 + 0.1 * t), z))
    for j in range(rings):
        for i in range(segs):
            a = j * (segs + 1) + i
            faces.append((a, a + 1, a + segs + 2, a + segs + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.materials.append(mat(key))
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    dk.fold_bands(scale=0.05, strength=0.004)(o)
    s = o.modifiers.new("thick", "SOLIDIFY"); s.thickness, s.offset = 0.004, 1.0
    sub = o.modifiers.new("sub", "SUBSURF"); sub.levels = 1
    skin_weights_to(o, [("pelvis", lambda co: 1.0),
                        ("thigh_l", lambda co: max(0.0, co.x) * 6.0 * max(0.0, (hip_z - co.z) / 0.2)),
                        ("thigh_r", lambda co: max(0.0, -co.x) * 6.0 * max(0.0, (hip_z - co.z) / 0.2))])
    skinned(o, rig)
    dk.hem_piping(o, key, 0.003)
    return o


def boots(body, rig, cls, seg, from_t, laces):
    src = dk.SRC["body"]
    dk.garment(body, rig, cls, NAME + "_boots", "boots", lambda c, co: (c[0].startswith("shin") and c[1] > from_t) or (c[0].startswith("foot") and co.z > 0.07),
               lambda c, co: 0.022, 0.006, smooth=2)
    for s in "lr":
        fv = [src.vertices[i].co.copy() for i, c in cls.items() if c[0] == "foot_" + s or (c[0] == "shin_" + s and c[1] > 0.85)]
        bmh = bmesh.new()
        for co in fv:
            bmh.verts.new(co + Vector((0, -0.004, 0)))
        bmesh.ops.convex_hull(bmh, input=bmh.verts)
        me = bpy.data.meshes.new(NAME + "_bootfoot_" + s)
        bmh.to_mesh(me)
        bmh.free()
        bf = bpy.data.objects.new(NAME + "_bootfoot_" + s, me)
        bpy.context.scene.collection.objects.link(bf)
        me.materials.append(mat("boots"))
        sm = bf.modifiers.new("sub", "SUBSURF"); sm.levels = 1
        dk.attach(bf, rig, "foot_" + s)
        zmin = min(v.co.z for v in me.vertices)
        cx = sum(v.co.x for v in me.vertices) / len(me.vertices)
        cyy = sum(v.co.y for v in me.vertices) / len(me.vertices)
        ylen = max(v.co.y for v in me.vertices) - min(v.co.y for v in me.vertices)
        dk.box(NAME + "_sole_" + s, (cx, cyy, zmin + 0.01), (0.045, ylen / 2 * 0.9, 0.01), "sole", 0.4, parent=rig, bone="foot_" + s)
        z = dk.pt(seg, "shin_" + s, from_t + 0.02).z
        c, rx, ry = dk.ring_at(body, cls, z, ("shin_" + s,), 0.026)
        dk.ring_band(NAME + "_boot_cuff_" + s, c, rx, ry, 0.026, 0.007, "boot_dark", parent=rig, bone="calf_" + s)
        if laces:
            for k in range(6):
                zz = dk.pt(seg, "shin_" + s, from_t + 0.08 + k * 0.05).z
                cc, rx2, ry2 = dk.ring_at(body, cls, zz, ("shin_" + s,), 0.026)
                dk.box(NAME + "_lace_%s%d" % (s, k), (cc.x, cc.y - ry2 - 0.002, zz), (0.014, 0.002, 0.0025), "lace", 0.2, parent=rig, bone="calf_" + s)
    dk.COVERED.update(i for i, c in cls.items() if c[0].startswith("foot"))


def rolled_cuff(body, rig, cls, seg, s, t, key, ease):
    a, b = seg["farm_" + s]
    c, rx, ry = dk.ring_at(body, cls, dk.pt(seg, "farm_" + s, t).z, ("farm_" + s,), ease)
    q = Vector((0, 0, 1)).rotation_difference((b - a).normalized())
    dk.ring_band("%s_rolled_sleeve_%s" % (NAME, s), dk.pt(seg, "farm_" + s, t), rx, ry, 0.04, 0.009, key, parent=rig, bone="lowerarm_" + s,
                 tilt=q.to_euler())


def crossbody(body, rig, cls, seg, neck_z, hip_z, sy, key_strap, key_bag, key_dark):
    """A strap from the left shoulder across the chest to a bag on the right hip (as both sheets show)."""
    lsh = dk.pt(seg, "uarm_l", 0.0)
    pts_front, pts_back = [], []
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        z = neck_z - 0.02 - (neck_z - 0.02 - (hip_z + 0.05)) * t
        x = lsh.x * 0.7 * (1 - t) + (-0.17) * t
        c, rx, ry = dk.ring_at(body, cls, z, ("spine",), 0.03)
        pts_front.append(Vector((x, c.y - ry * math.sqrt(max(0.0, 1 - min(1.0, (x - c.x) ** 2 / max(rx * rx, 1e-6)))) - 0.014, z)))
        pts_back.append(Vector((x, c.y + ry * math.sqrt(max(0.0, 1 - min(1.0, (x - c.x) ** 2 / max(rx * rx, 1e-6)))) + 0.014, z)))
    dk.strap(NAME + "_bag_strap", pts_front, 0.028, 0.004, key_strap, parent=rig, bone="spine_03")
    dk.strap(NAME + "_bag_strap_back", pts_back, 0.028, 0.004, key_strap, parent=rig, bone="spine_03")
    c, rx, ry = dk.ring_at(body, cls, hip_z, ("spine", "thigh_r"), 0.03)
    bag_c = (c.x - rx - 0.03, c.y, hip_z - 0.02)
    dk.box(NAME + "_bag", bag_c, (0.032, 0.085, 0.075), key_bag, 0.8, parent=rig, bone="pelvis")
    dk.box(NAME + "_bag_flap", (bag_c[0] - 0.034, bag_c[1], bag_c[2] + 0.03), (0.005, 0.082, 0.045), key_dark, 0.6, parent=rig, bone="pelvis")
    dk.box(NAME + "_bag_buckle", (bag_c[0] - 0.04, bag_c[1], bag_c[2] + 0.0), (0.003, 0.01, 0.008), "brass", 0.3, parent=rig, bone="pelvis")


def curly_hair(body, rig, B, length, volume, braid=False):
    """Curly hair: a volume of curls grown from the scalp, falling to `length` below the crown, and small tight coils on
    the outside for texture; optionally a long braid down the back."""
    me = body.data
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    scalp = body.vertex_groups.get("scalp")
    sidx = [v.index for v in me.vertices if scalp and any(g.group == scalp.index and g.weight > 0.4 for g in v.groups)]
    face_y = min(v.co.y for v in me.vertices if abs(v.co.z - (h0.z + hl * 0.3)) < 0.02 and abs(v.co.x) < 0.02)
    els, surface = [], []
    for i in sidx:
        v = me.vertices[i]
        n = (v.normal + Vector((0, 0, 0.2))).normalized()
        up = (v.co.z - h0.z) / hl
        front = v.co.y < face_y + 0.05 and up < 0.75
        depth = volume * (0.6 + 0.4 * up)
        for k in range(2):
            e = v.co + n * depth * random.uniform(0.3, 1.0)
            els.append((e, random.uniform(0.018, 0.026)))
            surface.append((e, n))
        if not front and length > 0:                       # hair falls down the back and sides
            drop = length * (0.4 + 0.6 * max(0.0, 1 - up)) * random.uniform(0.7, 1.0)
            out = Vector((v.co.x * 0.3, max(0.0, v.co.y - h0.y) * 0.4 + 0.01, 0)).normalized() if abs(v.co.x) + abs(v.co.y - h0.y) > 1e-4 else Vector((0, 1, 0))
            for s in range(1, 6):
                t = s / 5
                p = v.co + n * depth + out * volume * 0.8 * t + Vector((0, 0, -drop * t))
                els.append((p, random.uniform(0.02, 0.028) * (1 - 0.25 * t)))
                if s == 5 or random.random() < 0.3:
                    surface.append((p, (n + out).normalized()))
    hm = metaball_mesh(NAME + "_hair", els, "hair", rig, "head", resolution=0.0065)
    cu = bpy.data.curves.new(NAME + "_hair_coils", "CURVE")
    cu.dimensions, cu.bevel_resolution, cu.resolution_u, cu.bevel_depth = "3D", 0, 3, 1.0
    random.shuffle(surface)
    for co, n in surface[:700]:
        a_ = n.orthogonal().normalized(); b_ = n.cross(a_)
        L, r, th, ph = random.uniform(0.012, 0.022), random.uniform(0.006, 0.009), random.uniform(0.004, 0.006), random.uniform(0, 6.28)
        sp = cu.splines.new("NURBS")
        sp.points.add(7)
        for j in range(8):
            t = j / 7
            ang = ph + t * 1.5 * 2 * math.pi
            q = co + n * (0.008 + L * t * 0.5) + Vector((0, 0, -L * t)) + (a_ * math.cos(ang) + b_ * math.sin(ang)) * r
            sp.points[j].co = (q.x, q.y, q.z, 1)
            sp.points[j].radius = th * (1 - 0.4 * t)
        sp.use_endpoint_u, sp.order_u = True, 4
    co_ = bpy.data.objects.new(NAME + "_hair_coils", cu)
    bpy.context.scene.collection.objects.link(co_)
    cu.materials.append(mat("hair"))
    dk.attach(co_, rig, "head")
    if braid:
        back_y = max(me.vertices[i].co.y for i in sidx)
        top = Vector((0, back_y + 0.01, h0.z + hl * 0.35))
        bels = []
        for k in range(14):                                 # alternating plaits, tapering down the back
            t = k / 13
            p = top + Vector((0.012 * (1 if k % 2 else -1) * (1 - 0.5 * t), 0.03 * t, -0.34 * t))
            bels.append((p, 0.03 * (1 - 0.45 * t)))
        br = metaball_mesh(NAME + "_braid", bels, "hair", rig, "head", resolution=0.006)
        skin_weights_to(br, [("head", lambda co: max(0.0, (co.z - (top.z - 0.12)) / 0.12)),
                             ("spine_03", lambda co: max(0.0, ((top.z - 0.08) - co.z) / 0.12) + 0.01)])
        mw = br.matrix_world.copy()
        br.parent = None
        br.matrix_world = mw
        skinned(br, rig)
        dk.ring_band(NAME + "_braid_tie", top + Vector((0, 0.03, -0.34)), 0.013, 0.013, 0.012, 0.004, "belt", parent=rig, bone="spine_03")
    # hair-coloured scalp under the curls
    on = set(sidx)
    body.data.materials.append(mat("hair"))
    slot = len(body.data.materials) - 1
    for p in body.data.polygons:
        if sum(1 for i in p.vertices if i in on) >= 3:
            p.material_index = slot


def base(body, rig):
    seg, B = dk.segments(rig)
    cls = dk.classify(body, seg)
    dk.SRC["body"] = body.data.copy()
    body.data.materials.clear()
    body.data.materials.append(mat("skin"))
    dk.paint_skin(body, B)
    eye = os.path.join(MPFB_DATA, "eyes", "materials", C["eyes"])
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
            o.data.materials.append(mat("hair"))
    return seg, B, cls


def finish(body):
    bm = bmesh.new()
    bm.from_mesh(body.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if all(v.index in dk.COVERED for v in f.verts)], context="FACES_ONLY")
    bm.to_mesh(body.data)
    bm.free()


# ------------------------------------------------------------------ Tessa
def dress_tessa(body, rig):
    seg, B, cls = base(body, rig)
    G = lambda *a, **k: dk.garment(body, rig, cls, *a, **k)   # noqa: E731
    hip_z = seg["thigh_l"][0].z
    neck_z = seg["neck"][0].z
    waist_z = hip_z + 0.1
    sy = seg["spine"][1].y
    # Long cream tunic: body to the hips, then a tail to mid-thigh.
    G(NAME + "_tunic", "tunic", lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.04) or (c[0] == "neck" and c[1] < 0.15) or
      (c[0].startswith("uarm") and c[1] < 0.5), lambda c, co: 0.008, 0.003, folds=dk.fold_bands(strength=0.003), smooth=4)
    skirt(NAME + "_tunic_tail", "tunic", rig, cls, body, hip_z + 0.02, hip_z - 0.22, 0.04, 0.2, hip_z=hip_z)
    # Open green jacket, sleeves rolled to the forearm, tails to the hip.
    def jacket_pick(c, co):
        if c[0] == "spine" and co.z > hip_z - 0.02:
            return not (abs(co.x) < 0.05 and co.y < sy - 0.015)
        if c[0] == "neck" and c[1] < 0.2 and co.y > sy - 0.03:
            return True
        return c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.4)
    jacket = G(NAME + "_jacket", "jacket", jacket_pick, lambda c, co: 0.016 if c[0] == "spine" else 0.012, 0.004,
               folds=dk.fold_bands(strength=0.003), hide=False, smooth=5)
    dk.hem_piping(jacket, "jacket_dark", 0.003)
    skirt(NAME + "_jacket_tail", "jacket", rig, cls, body, hip_z + 0.04, hip_z - 0.12, 0.058, 0.14, open_front=0.9, hip_z=hip_z)
    for s in "lr":
        rolled_cuff(body, rig, cls, seg, s, 0.4, "jacket", 0.016)
    for sx in (-1, 1):                                       # lapels
        dk.box("%s_lapel_%d" % (NAME, sx), (sx * 0.06, sy - 0.07, neck_z - 0.04), (0.028, 0.005, 0.045), "jacket", 0.5,
               rot=(math.radians(-8), 0, sx * math.radians(-18)), parent=rig, bone="spine_03")
    # Loose brown trousers bunched over the boots.
    G(NAME + "_trousers", "trousers", lambda c, co: c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < 0.72) or
      (c[0] == "spine" and co.z < hip_z - 0.03), lambda c, co: 0.022 if c[0].startswith("thigh") else (0.03 if c[0].startswith("shin") else 0.006),
      0.004, folds=dk.fold_bands(scale=0.03, strength=0.006), smooth_group=("crotch", lambda co: abs(co.x) < 0.07 and hip_z - 0.15 < co.z < hip_z - 0.02, 8))
    for s in "lr":
        z = dk.pt(seg, "shin_" + s, 0.66).z
        c, rx, ry = dk.ring_at(body, cls, z, ("shin_" + s,), 0.034)
        dk.ring_band("%s_trouser_gather_%s" % (NAME, s), c, rx, ry, 0.05, 0.012, "trousers_dark", parent=rig, bone="calf_" + s)
    boots(body, rig, cls, seg, 0.62, laces=False)
    # Belt, gloves, bracelet, satchel across the body.
    c, rx, ry = dk.ring_at(body, cls, waist_z, ("spine",), 0.03)
    dk.ring_band(NAME + "_belt", c, rx, ry, 0.03, 0.007, "belt", parent=rig, bone="pelvis")
    dk.box(NAME + "_belt_buckle", (0, c.y - ry - 0.008, waist_z), (0.02, 0.003, 0.016), "steel", 0.3, parent=rig, bone="pelvis")
    gx = c.x + rx * 0.75
    for k in range(2):
        dk.box("%s_glove_%d" % (NAME, k), (gx + 0.01 * k, c.y - ry * 0.6 - 0.01, waist_z - 0.07 - 0.01 * k), (0.03, 0.008, 0.06), "gloves", 0.7,
               rot=(0, math.radians(8 + 10 * k), 0), parent=rig, bone="pelvis")
    wz = dk.pt(seg, "farm_r", 0.92).z
    cc, rx2, ry2 = dk.ring_at(body, cls, wz, ("farm_r", "hand_r"), 0.006)
    for k in range(10):                                      # beaded bracelet
        a = k * math.pi / 5
        dk.box("%s_bead_%d" % (NAME, k), (cc.x + math.cos(a) * rx2, cc.y + math.sin(a) * ry2, wz), (0.004, 0.004, 0.004),
               "bead_a" if k % 2 else "bead_b", 0.5, parent=rig, bone="lowerarm_r")
    crossbody(body, rig, cls, seg, neck_z, hip_z, sy, "bag_dark", "bag", "bag_dark")
    finish(body)
    curly_hair(body, rig, B, length=0.16, volume=0.05)


# ------------------------------------------------------------------ Elara
def dress_elara(body, rig):
    seg, B, cls = base(body, rig)
    G = lambda *a, **k: dk.garment(body, rig, cls, *a, **k)   # noqa: E731
    hip_z = seg["thigh_l"][0].z
    neck_z = seg["neck"][0].z
    waist_z = hip_z + 0.12
    sy = seg["spine"][1].y
    # Cream button shirt tucked in, sleeves rolled above the elbow.
    shirt = G(NAME + "_shirt", "shirt", lambda c, co: (c[0] == "spine" and co.z > waist_z - 0.03) or (c[0] == "neck" and c[1] < 0.2) or
              c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.1), lambda c, co: 0.01, 0.003,
              folds=dk.fold_bands(strength=0.003), smooth=1)
    dk.hem_piping(shirt, "cuff", 0.003)
    for s in "lr":
        rolled_cuff(body, rig, cls, seg, s, 0.08, "cuff", 0.014)
    for sx in (-1, 1):                                       # collar points
        dk.box("%s_collar_%d" % (NAME, sx), (sx * 0.045, sy - 0.05, neck_z - 0.005), (0.03, 0.004, 0.022), "shirt", 0.5,
               rot=(math.radians(-25), 0, sx * math.radians(-35)), parent=rig, bone="spine_03")
    for k in range(5):
        z = neck_z - 0.07 - k * 0.055
        c, rx, ry = dk.ring_at(body, cls, z, ("spine",), 0.012)
        dk.cyl("%s_button_%d" % (NAME, k), (0, c.y - ry - 0.002, z), 0.0045, 0.003, "button", rot=(math.radians(90), 0, 0), verts=12,
               parent=rig, bone="spine_03")
    # High-waisted green trousers rolled above the boots.
    G(NAME + "_trousers", "trousers", lambda c, co: c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < 0.6) or
      (c[0] == "spine" and co.z < waist_z + 0.02), lambda c, co: 0.013 if c[0].startswith("thigh") else (0.022 if c[0].startswith("shin") else 0.012),
      0.004, folds=dk.fold_bands(scale=0.032, strength=0.005), smooth_group=("crotch", lambda co: abs(co.x) < 0.07 and hip_z - 0.15 < co.z < hip_z - 0.02, 8))
    for s in "lr":
        z = dk.pt(seg, "shin_" + s, 0.58).z
        c, rx, ry = dk.ring_at(body, cls, z, ("shin_" + s,), 0.034)
        dk.ring_band("%s_trouser_roll_%s" % (NAME, s), c, rx, ry, 0.045, 0.012, "trousers_dark", parent=rig, bone="calf_" + s)
    boots(body, rig, cls, seg, 0.64, laces=True)
    # Belt with seed pouches; leather bag across the body.
    c, rx, ry = dk.ring_at(body, cls, waist_z, ("spine",), 0.026)
    dk.ring_band(NAME + "_belt", c, rx, ry, 0.03, 0.007, "belt", parent=rig, bone="pelvis")
    dk.box(NAME + "_belt_buckle", (0, c.y - ry - 0.008, waist_z), (0.02, 0.003, 0.016), "steel", 0.3, parent=rig, bone="pelvis")
    for k, ox in enumerate((0.0, 0.05)):
        px = c.x + rx * 0.8 + ox * 0.3
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.035, location=(px, c.y - ry * 0.55 - 0.02 - ox * 0.2, waist_z - 0.06 - 0.01 * k))
        p = bpy.context.active_object; p.name = "%s_pouch_%d" % (NAME, k)
        p.scale = (0.9, 0.7, 1.15)
        p.data.materials.append(mat("pouch"))
        bpy.ops.object.shade_smooth()
        dk.attach(p, rig, "pelvis")
    crossbody(body, rig, cls, seg, neck_z, hip_z, sy, "bag_dark", "bag", "bag_dark")
    finish(body)
    curly_hair(body, rig, B, length=0.05, volume=0.035, braid=True)


# ------------------------------------------------------------------ shared: beards, caps, pinned-up hair
def face_profile(body, B):
    me = body.data
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    prof = [v for v in me.vertices if abs(v.co.x) < 0.01 and h0.z - hl * 0.6 < v.co.z < h0.z + hl * 0.9]
    nose = min(prof, key=lambda v: v.co.y)
    front = [v for v in prof if v.co.y < nose.co.y + 0.04 and v.co.z < nose.co.z]
    chin_z = min(v.co.z for v in front)
    mouth_z = nose.co.z - (nose.co.z - chin_z) * 0.42
    return nose.co.z, nose.co.y, mouth_z, chin_z


def beard(body, rig, B, depth_chin, key="beard"):
    """A neat beard and moustache placed from the measured profile (as Bram's, trimmed shorter)."""
    me = body.data
    nose_z, nose_y, mouth_z, chin_z = face_profile(body, B)
    els = []
    for v in me.vertices:
        co = v.co
        if co.y > nose_y + 0.09 or co.z > nose_z - 0.014 or co.z < chin_z - 0.03:
            continue
        side = abs(co.x)
        if side > 0.072 or (side < 0.03 and mouth_z - 0.012 < co.z < mouth_z + 0.014) or (side < 0.05 and co.z > mouth_z + 0.014):
            continue
        n = v.normal.normalized()
        if n.z > 0.6:
            continue
        below = max(0.0, mouth_z - co.z) / max(mouth_z - chin_z + 0.03, 0.01)
        els.append((co + n * (0.005 + depth_chin * min(1.0, below)) + Vector((0, 0, -0.006 * below)), random.uniform(0.011, 0.014)))
    for sx in (-1, 1):
        for k in range(8):
            t = k / 7
            els.append((Vector((sx * (0.004 + 0.03 * t), nose_y + 0.012 + 0.016 * t, mouth_z + 0.015 - 0.026 * t * t)), 0.011 - 0.003 * t))
    m = metaball_mesh(NAME + "_beard", els, key, rig, "head", resolution=0.005)
    dk.fold_bands(scale=0.006, strength=0.0018, name="wavy")(m)


def close_cap_hair(body, rig, B, key, depth=0.008):
    me = body.data
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    scalp = body.vertex_groups.get("scalp")
    sidx = [v.index for v in me.vertices if scalp and any(g.group == scalp.index and g.weight > 0.4 for g in v.groups)]
    els = []
    for i in sidx:
        v = me.vertices[i]
        up = (v.co.z - h0.z) / hl
        els.append((v.co + v.normal.normalized() * (depth + 0.008 * max(0.0, up - 0.4)), random.uniform(0.019, 0.023)))
    m = metaball_mesh(NAME + "_hair", els, key, rig, "head", resolution=0.008)
    dk.fold_bands(scale=0.008, strength=0.002, name="combed")(m)
    on = set(sidx)
    body.data.materials.append(mat(key))
    slot = len(body.data.materials) - 1
    for p in body.data.polygons:
        if sum(1 for i in p.vertices if i in on) >= 3:
            p.material_index = slot
    return sidx


# ------------------------------------------------------------------ Maren
def dress_maren(body, rig):
    seg, B, cls = base(body, rig)
    G = lambda *a, **k: dk.garment(body, rig, cls, *a, **k)   # noqa: E731
    hip_z = seg["thigh_l"][0].z
    neck_z = seg["neck"][0].z
    chest_z = neck_z - 0.17
    waist_z = hip_z + 0.12
    knee_z = seg["shin_l"][0].z
    sy = seg["spine"][1].y
    # Cream blouse, sleeves rolled to the forearm.
    G(NAME + "_shirt", "shirt", lambda c, co: (c[0] == "spine" and co.z > waist_z - 0.05) or (c[0] == "neck" and c[1] < 0.22) or
      c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.3), lambda c, co: 0.009, 0.003, folds=dk.fold_bands(strength=0.003), smooth=2)
    for s in "lr":
        rolled_cuff(body, rig, cls, seg, s, 0.28, "cuff", 0.014)
    # Wool waistcoat, buttoned down the front.
    vest = G(NAME + "_waistcoat", "waistcoat", lambda c, co: c[0] == "spine" and waist_z - 0.06 < co.z < neck_z - 0.04 and
             not (abs(co.x) < 0.035 and co.y < sy - 0.02 and co.z > chest_z + 0.04), lambda c, co: 0.019, 0.004,
             folds=dk.fold_bands(scale=0.05, strength=0.002), hide=False, smooth=14)
    dk.hem_piping(vest, "waistcoat_dark", 0.0035)
    for k in range(4):
        z = chest_z + 0.02 - k * 0.045
        c, rx, ry = dk.ring_at(body, cls, z, ("spine",), 0.02)
        dk.cyl("%s_vest_button_%d" % (NAME, k), (0, c.y - ry - 0.003, z), 0.006, 0.004, "brass", rot=(math.radians(90), 0, 0), verts=12,
               parent=rig, bone="spine_02")
    # Postal-blue neckerchief.
    nk = dk.pt(seg, "neck", 0.3)
    dk.ring_band(NAME + "_neckerchief", Vector((nk.x, nk.y - 0.004, nk.z - 0.02)), 0.06, 0.064, 0.016, 0.005, "postal", parent=rig, bone="neck_01")
    dk.box(NAME + "_neckerchief_knot", (0, nk.y - 0.068, nk.z - 0.05), (0.014, 0.006, 0.016), "postal", 0.8, rot=(0, math.radians(45), 0), parent=rig, bone="spine_03")
    dk.box(NAME + "_neckerchief_tail", (0.004, nk.y - 0.07, nk.z - 0.085), (0.012, 0.004, 0.03), "postal", 0.6, rot=(0, math.radians(8), 0), parent=rig, bone="spine_03")
    # Calf-length wool skirt over the legs, long canvas apron in front.
    skirt(NAME + "_skirt", "skirt", rig, cls, body, waist_z - 0.02, knee_z - 0.2, 0.034, 0.75, rings=12, hip_z=hip_z)
    dk.COVERED.update(i for i, c in cls.items() if c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < 0.55))
    c, rx, ry = dk.ring_at(body, cls, waist_z - 0.02, ("spine",), 0.03)
    apron = skirt(NAME + "_apron", "apron", rig, cls, body, waist_z - 0.01, knee_z - 0.12, 0.036, 0.5, open_front=0.0, rings=10, hip_z=hip_z)
    bm = bmesh.new(); bm.from_mesh(apron.data)                       # keep only the front of the tube: an apron, not a skirt
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v.co.y > c.y - ry * 0.25], context="VERTS")
    bm.to_mesh(apron.data); bm.free()
    for k, sx in enumerate((-1, 1)):                                  # pockets with letters and a pencil
        pz = hip_z - 0.06
        py = c.y - ry - 0.06
        dk.box("%s_apron_pocket_%d" % (NAME, k), (sx * 0.1, py, pz), (0.07, 0.006, 0.065), "apron_dark", 0.3, parent=rig, bone="pelvis")
        for j in range(3):
            dk.box("%s_letter_%d_%d" % (NAME, k, j), (sx * 0.1 + (j - 1) * 0.022, py - 0.004, pz + 0.07 + 0.008 * j), (0.022, 0.002, 0.03), "letter", 0.2,
                   rot=(0, math.radians((j - 1) * 8), 0), parent=rig, bone="pelvis")
    dk.cyl(NAME + "_pencil", (0.13, c.y - ry - 0.068, hip_z + 0.0), 0.004, 0.11, "pencil", verts=6, rot=(0, math.radians(12), 0), parent=rig, bone="pelvis")
    dk.ring_band(NAME + "_apron_tie", c, rx + 0.006, ry + 0.006, 0.02, 0.004, "apron_dark", parent=rig, bone="pelvis")
    boots(body, rig, cls, seg, 0.68, laces=True)
    crossbody(body, rig, cls, seg, neck_z, hip_z, sy, "bag_dark", "bag", "bag_dark")
    # Reading glasses on a cord.
    gz = chest_z + 0.03
    c2, rx2, ry2 = dk.ring_at(body, cls, gz, ("spine",), 0.02)
    gy = c2.y - ry2 - 0.03
    for sx in (-1, 1):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.016, minor_radius=0.0025, location=(sx * 0.02, gy, gz), rotation=(math.radians(80), 0, 0),
                                         major_segments=16, minor_segments=4)
        r = bpy.context.active_object; r.name = "%s_glasses_rim_%d" % (NAME, sx)
        r.data.materials.append(mat("brass")); dk.attach(r, rig, "spine_03")
        dk.cyl("%s_glasses_lens_%d" % (NAME, sx), (sx * 0.02, gy + 0.001, gz), 0.014, 0.002, "lens", rot=(math.radians(80), 0, 0), verts=16, parent=rig, bone="spine_03")
    dk.strap(NAME + "_glasses_cord", [Vector((0.034, gy, gz)), Vector((0.06, gy + 0.01, gz + 0.06)), Vector((0.07, sy - 0.04, neck_z + 0.01)),
                                       Vector((0.0, sy + 0.07, neck_z + 0.02)), Vector((-0.07, sy - 0.04, neck_z + 0.01)),
                                       Vector((-0.06, gy + 0.01, gz + 0.06)), Vector((-0.034, gy, gz))], 0.003, 0.002, "lace", parent=rig, bone="spine_03")
    finish(body)
    # Greying hair pinned up in a bun.
    sidx = close_cap_hair(body, rig, B, "hair", depth=0.01)
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    back_y = max(body.data.vertices[i].co.y for i in sidx)
    bun = Vector((0, back_y + 0.01, h0.z + hl * 0.78))
    els = [(bun + Vector((math.cos(a) * 0.024, math.sin(a) * 0.012, math.sin(a * 2) * 0.006)), 0.03) for a in [k * math.pi / 4 for k in range(8)]]
    els.append((bun + Vector((0, 0.012, 0)), 0.035))
    b = metaball_mesh(NAME + "_bun", els, "hair", rig, "head", resolution=0.005)
    dk.fold_bands(scale=0.005, strength=0.0018, name="twist")(b)
    dk.cyl(NAME + "_hairpin", (0.01, bun.y + 0.02, bun.z + 0.02), 0.0025, 0.08, "brass", verts=6, rot=(math.radians(60), math.radians(30), 0), parent=rig, bone="head")


# ------------------------------------------------------------------ Rowan
def dress_rowan(body, rig):
    seg, B, cls = base(body, rig)
    G = lambda *a, **k: dk.garment(body, rig, cls, *a, **k)   # noqa: E731
    hip_z = seg["thigh_l"][0].z
    neck_z = seg["neck"][0].z
    waist_z = hip_z + 0.11
    sy = seg["spine"][1].y
    # Simple cream tunic to mid-thigh, long sleeves.
    G(NAME + "_tunic", "tunic", lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.04) or (c[0] == "neck" and c[1] < 0.2) or
      c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.85), lambda c, co: 0.012, 0.003, folds=dk.fold_bands(strength=0.003), smooth=3)
    skirt(NAME + "_tunic_tail", "tunic", rig, cls, body, hip_z + 0.01, hip_z - 0.2, 0.034, 0.25, hip_z=hip_z)
    for s in "lr":
        rolled_cuff(body, rig, cls, seg, s, 0.84, "cuff", 0.016)
    G(NAME + "_trousers", "trousers", lambda c, co: c[0].startswith("thigh") or (c[0].startswith("shin") and c[1] < 0.7) or
      (c[0] == "spine" and co.z < hip_z - 0.03), lambda c, co: 0.016 if c[0].startswith("thigh") else (0.02 if c[0].startswith("shin") else 0.006),
      0.004, folds=dk.fold_bands(scale=0.03, strength=0.004), smooth_group=("crotch", lambda co: abs(co.x) < 0.07 and hip_z - 0.15 < co.z < hip_z - 0.02, 8))
    boots(body, rig, cls, seg, 0.66, laces=False)
    c, rx, ry = dk.ring_at(body, cls, waist_z - 0.02, ("spine",), 0.026)
    dk.ring_band(NAME + "_sash", c, rx, ry, 0.035, 0.008, "belt", parent=rig, bone="pelvis")
    # The long knitted shawl: over the shoulders and hanging down the front in two striped panels to the thighs.
    shawl = G(NAME + "_shawl", "shawl", lambda c, co: (c[0] == "spine" and co.z > neck_z - 0.2 and (co.y > sy - 0.02 or abs(co.x) > 0.09)) or
              (c[0] == "neck" and c[1] < 0.3 and co.y > sy - 0.04) or (c[0].startswith("uarm") and c[1] < 0.2), lambda c, co: 0.017, 0.006,
              folds=dk.fold_bands(scale=0.012, strength=0.003, name="knit"), hide=False, smooth=6)
    dk.hem_piping(shawl, "shawl_dark", 0.005)
    for sx in (-1, 1):
        top = neck_z - 0.03
        x0 = sx * 0.085
        y = sy - 0.1
        for k in range(9):                                            # striped panel, knitted bands
            z = top - k * 0.06
            cc, rxx, ryy = dk.ring_at(body, cls, max(z, hip_z + 0.02), ("spine",), 0.03)
            y = min(cc.y - ryy * math.sqrt(max(0.0, 1 - (x0 / max(rxx, 0.01)) ** 2)) - 0.012, cc.y - 0.02)
            dk.box("%s_shawl_panel_%d_%d" % (NAME, sx, k), (x0 + sx * 0.003 * k, y - 0.004 * max(0, k - 5), z - 0.03), (0.04, 0.007, 0.034),
                   "shawl_band" if k % 3 == 1 else "shawl", 0.12, parent=rig, bone="spine_03" if k < 4 else "pelvis")
        for t in range(5):                                            # fringe
            dk.cyl("%s_fringe_%d_%d" % (NAME, sx, t), (x0 + sx * 0.024 - 0.03 + t * 0.015, y - 0.02, top - 9 * 0.06 - 0.02), 0.003, 0.05, "shawl_band",
                   verts=5, parent=rig, bone="pelvis")
    # Walking stick in the right hand, carved with a little windmill at the top.
    hand = dk.pt(seg, "hand_r", 0.45)
    ground = min(v.co.z for v in dk.SRC["body"].vertices)
    foot = Vector((hand.x + 0.02, hand.y - 0.1, ground))
    top = hand + Vector((0, -0.01, 0.1))
    mid = (foot + top) / 2
    d = top - foot
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.014, depth=d.length, location=mid)
    st = bpy.context.active_object; st.name = NAME + "_stick"
    st.rotation_mode = "QUATERNION"; st.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d.normalized())
    st.data.materials.append(mat("stick"))
    dk.attach(st, rig, "hand_r")
    dk.cyl(NAME + "_stick_knob", tuple(top + Vector((0, 0, 0.02))), 0.022, 0.04, "stick_dark", verts=10, parent=rig, bone="hand_r")
    for k in range(4):                                                # windmill sails carved on the knob
        a = k * math.pi / 2 + 0.3
        dk.box("%s_stick_sail_%d" % (NAME, k), (top.x + math.cos(a) * 0.03, top.y - 0.024, top.z + 0.04 + math.sin(a) * 0.03), (0.007, 0.003, 0.024),
               "stick_dark", 0.3, rot=(0, -a + math.pi / 2, 0), parent=rig, bone="hand_r")
    finish(body)
    # Short white hair under a soft knitted cap, neat white beard.
    sidx = close_cap_hair(body, rig, B, "hair", depth=0.006)
    h0, h1 = B["head"]
    hl = (h1 - h0).length
    els = []
    for i in sidx:
        v = body.data.vertices[i]
        if (v.co.z - h0.z) / hl > 0.62:
            els.append((v.co + v.normal.normalized() * 0.024 + Vector((0, 0.008, 0.008)), 0.032))
    cap = metaball_mesh(NAME + "_cap", els, "cap", rig, "head", resolution=0.008)
    dk.fold_bands(scale=0.01, strength=0.002, name="knit")(cap)
    beard(body, rig, B, 0.012)


# ------------------------------------------------------------------ previews (same lights as Kieran's sheet)
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
    rig = bpy.data.objects[NAME + "_Rig"]
    for nm, loc, size, energy, col in (("Key", (-2.0, -3.0, 3.2), 2.5, 900, (1.0, 0.95, 0.88)), ("Fill", (3.0, -2.2, 1.4), 3.0, 350, (0.88, 0.92, 1.0)),
                                        ("Rim", (0.8, 3.2, 2.8), 1.5, 700, (1.0, 0.92, 0.8))):
        ld = bpy.data.lights.new("Look_" + nm, "AREA"); ld.size, ld.energy, ld.color = size, energy, col
        o = bpy.data.objects.new("Look_" + nm, ld); sc.collection.objects.link(o); o.location = loc
        c = o.constraints.new("TRACK_TO"); c.target = rig
    cam = bpy.data.objects.new("LookCam", bpy.data.cameras.new("LookCam")); sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type in ("MESH", "CURVE") for c in o.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    for nm, yaw, res, frame in ((NAME + "_Front", 0, (800, 1200), None), (NAME + "_ThreeQuarter", 40, (800, 1200), None),
                                (NAME + "_Side", 90, (800, 1200), None), (NAME + "_Rear", 180, (800, 1200), None), (NAME + "_Face", 25, (800, 800), 0.42)):
        sc.render.resolution_x, sc.render.resolution_y = res
        a = math.radians(yaw)
        cam.data.ortho_scale = frame if frame else (zmax - zmin) * 1.06
        cz = zmax - 0.17 if frame else (zmax + zmin) / 2
        cam.location = (10 * math.sin(a), -10 * math.cos(a), cz)
        cam.rotation_euler = (math.radians(90), 0, a)
        sc.camera = cam
        sc.render.filepath = os.path.join(OUT, "renders", nm + ".png")
        bpy.ops.render.render(write_still=True)


body, rig = build_body()
z = [(body.matrix_world @ v.co).z for v in body.data.vertices]
print("LS_VILLAGER %s height %.3f m" % (NAME, max(z) - min(z)), flush=True)
{"tessa": dress_tessa, "elara": dress_elara, "maren": dress_maren, "rowan": dress_rowan}[WHO](body, rig)
render_views()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "%s_Master.blend" % C["export"]))
print("LS_VILLAGER_OK", NAME, flush=True)
