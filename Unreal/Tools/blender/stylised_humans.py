"""Stylised character drafts: an MPFB base pushed toward stylised proportions, chunky hand-made clothes with piped
hems, sculpted hair clumps and painterly toon materials, rendered in EEVEE to turnaround sheets for Adam's approval.

Adam asked for a stylised AAA look (2026-11-16). Designs follow his turnarounds; nothing goes into the game until
he approves.

  blender --background --python stylised_humans.py -- <output folder> [kieran]
"""
import math
import os
import random
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import character_drafts as cd   # noqa: E402
import realistic_drafts as rd   # noqa: E402
import realistic_humans as rh   # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [os.getcwd()]
OUT = ARGS[0]
WHICH = ARGS[1:] or ["kieran"]
os.makedirs(OUT, exist_ok=True)
cd.OUT = rd.OUT = rh.OUT = OUT
hexrgb = cd.hexrgb
SHEEN = {}   # hex -> extra sheen/gloss for leather and brass


# ------------------------------------------------------------------ painterly toon material
def toon_mat(hexcol):
    name = "T_" + hexcol
    m = bpy.data.materials.get(name)
    if m:
        return m
    col = hexrgb(hexcol)
    kind = rd.KIND.get(hexcol, "plain")
    m, nt, out = rd.node_mat(name)
    L = nt.links
    gloss = {"brass": 0.25, "steel": 0.3, "leather": 0.55, "glass": 0.05, "glow": 0.3}.get(kind, 0.75)
    b = rd.principled(nt, col, gloss, 1.0 if kind in ("brass", "steel") else 0.0)
    # soft painterly variation in the base colour
    n = rd.noise(nt, 3.5, 3.0, 0.5)
    r = rd.ramp_between(nt, n.outputs["Fac"], rd.darker(col, 0.95), (min(col[0] * 1.04, 1), min(col[1] * 1.04, 1), min(col[2] * 1.04, 1), 1))
    L.new(r.outputs["Color"], b.inputs["Base Color"])
    s2r = nt.nodes.new("ShaderNodeShaderToRGB")
    L.new(b.outputs["BSDF"], s2r.inputs["Shader"])
    # light into three soft bands, shadows tinted warm-violet rather than black
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "EASE"
    e = ramp.color_ramp.elements
    e[0].position, e[0].color = 0.05, (0.42, 0.36, 0.45, 1)
    e[1].position, e[1].color = 0.55, (1.0, 0.97, 0.92, 1)
    mid = e.new(0.22)
    mid.color = (0.72, 0.66, 0.68, 1)
    bw = nt.nodes.new("ShaderNodeRGBToBW")
    L.new(s2r.outputs["Color"], bw.inputs["Color"])
    L.new(bw.outputs["Val"], ramp.inputs["Fac"])
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs[0].default_value = 1.0
    L.new(r.outputs["Color"], mul.inputs[6])
    L.new(ramp.outputs["Color"], mul.inputs[7])
    # warm rim light
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.25
    rim = nt.nodes.new("ShaderNodeValToRGB")
    rim.color_ramp.elements[0].position = 0.55
    rim.color_ramp.elements[0].color = (0, 0, 0, 1)
    rim.color_ramp.elements[1].position = 0.8
    rim.color_ramp.elements[1].color = (0.35, 0.28, 0.18, 1)
    L.new(lw.outputs["Facing"], rim.inputs["Fac"])
    add = nt.nodes.new("ShaderNodeMix")
    add.data_type = "RGBA"
    add.blend_type = "ADD"
    add.inputs[0].default_value = 1.0
    L.new(mul.outputs[2], add.inputs[6])
    L.new(rim.outputs["Color"], add.inputs[7])
    em = nt.nodes.new("ShaderNodeEmission")
    L.new(add.outputs[2], em.inputs["Color"])
    if kind in ("brass", "steel", "glass"):   # a small real highlight on metal and glass
        g = nt.nodes.new("ShaderNodeBsdfGlossy")
        g.inputs["Roughness"].default_value = gloss
        g.inputs["Color"].default_value = (0.18, 0.16, 0.12, 1)
        mx = nt.nodes.new("ShaderNodeAddShader")
        L.new(em.outputs["Emission"], mx.inputs[0])
        L.new(g.outputs["BSDF"], mx.inputs[1])
        L.new(mx.outputs["Shader"], out.inputs["Surface"])
    elif kind == "glow":
        em.inputs["Strength"].default_value = 3.0
        em.inputs["Color"].default_value = col
        L.new(em.outputs["Emission"], out.inputs["Surface"])
    else:
        L.new(em.outputs["Emission"], out.inputs["Surface"])
    return m


rd.real_mat = toon_mat
cd.mat = toon_mat


def restyle_skin(body, hexcol):
    """Swap MPFB's photographic skin for a clean painted tone with warm cheeks."""
    body.data.materials.clear()
    rd.KIND[hexcol] = "skin"
    body.data.materials.append(toon_mat(hexcol))


def scalp_cap(body, hexcol):
    """Paint the scalp in the hair colour so no skin shows between the curl clumps."""
    vg = body.vertex_groups.get("scalp")
    if not vg:
        return
    on = {v.index for v in body.data.vertices if any(g.group == vg.index and g.weight > 0.3 for g in v.groups)}
    body.data.materials.append(toon_mat(hexcol))
    slot = len(body.data.materials) - 1
    for p in body.data.polygons:
        if all(i in on for i in p.vertices):
            p.material_index = slot


# ------------------------------------------------------------------ stylised proportions
def stylise(body, seg, head_scale=1.12, hand_scale=1.06):
    """Larger head (and everything on it) and slightly larger hands, blended smoothly at the neck and wrists."""
    h0, h1 = seg["head"]
    pivot = h0 + (h1 - h0) * 0.05
    neck_lo = seg["neck"][0].z
    span = max(h0.z - neck_lo, 0.02)

    def head_w(co):
        if co.z >= h0.z:
            return 1.0
        if co.z <= neck_lo:
            return 0.0
        return ((co.z - neck_lo) / span) ** 2

    heads = [o for o in bpy.data.objects if o.type == "MESH" and o != body]
    for v in body.data.vertices:
        w = head_w(v.co)
        if w > 0:
            v.co = pivot + (v.co - pivot) * (1 + (head_scale - 1) * w)
    for o in heads:   # eyes, brows, lashes, teeth sit on the head: scale with it
        mw = o.matrix_world
        inv = mw.inverted()
        for v in o.data.vertices:
            wco = mw @ v.co
            v.co = inv @ (pivot + (wco - pivot) * head_scale)
    for s in "LR":
        w0 = seg["hand" + s][0]
        for v in body.data.vertices:
            d = (v.co - w0).length
            if d < 0.2:
                c = rh.classify_one(v.co, seg)
                if c.startswith("hand"):
                    v.co = w0 + (v.co - w0) * hand_scale
    body.data.update()


def classify_one(co, seg):
    best = None
    for k, (a, b) in seg.items():
        ab = b - a
        t = max(0.0, min(1.0, (co - a).dot(ab) / max(ab.length_squared, 1e-9)))
        d = (co - (a + ab * t)).length
        if best is None or d < best[1]:
            best = (k, d)
    return best[0]


rh.classify_one = classify_one


# ------------------------------------------------------------------ polish pieces
def hems(o, offset, radius, hexcol):
    """Piping along every open edge of a garment: hems, cuffs and the jacket front read as finished clothing."""
    me = o.data
    me.calc_loop_triangles()
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    edges = [e for e in bm.edges if e.is_boundary]
    seen = set()
    cu = bpy.data.curves.new(o.name + "_hem", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    for e0 in edges:
        if e0 in seen:
            continue
        loop = [e0.verts[0], e0.verts[1]]
        seen.add(e0)
        cur = e0.verts[1]
        while True:
            nxt = [e for e in cur.link_edges if e.is_boundary and e not in seen]
            if not nxt:
                break
            seen.add(nxt[0])
            cur = nxt[0].other_vert(cur)
            if cur == loop[0]:
                break
            loop.append(cur)
        perim = sum((loop[i].co - loop[i - 1].co).length for i in range(len(loop)))
        if len(loop) < 4 or perim < 0.3:   # skip tiny holes (e.g. where fingers brushed the cloth)
            continue
        sp = cu.splines.new("POLY")
        sp.points.add(len(loop) - 1)
        for i, v in enumerate(loop):
            p = v.co + v.normal * (offset + radius * 0.5)
            sp.points[i].co = (p.x, p.y, p.z, 1)
        sp.use_cyclic_u = cur == loop[0] or (loop[-1].co - loop[0].co).length < 0.02
    bm.free()
    h = bpy.data.objects.new(o.name + "_hem", cu)
    bpy.context.scene.collection.objects.link(h)
    cu.materials.append(toon_mat(hexcol))
    return h


def curl_clumps(body, seg, hexcol, count=420, length=(0.03, 0.055), radius=0.0085, seed=7):
    """Sculpted coils of hair grown from the scalp: stylised natural curls."""
    vg = body.vertex_groups.get("scalp")
    idx = [v.index for v in body.data.vertices if vg and any(g.group == vg.index and g.weight > 0.5 for g in v.groups)]
    random.seed(seed)
    random.shuffle(idx)
    h0, h1 = seg["head"]
    cu = bpy.data.curves.new("curls", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 3
    cu.resolution_u = 6
    body.data.update()
    for i in idx[:count]:
        v = body.data.vertices[i]
        n = (v.normal + Vector((0, 0, 0.6))).normalized()
        a = n.orthogonal().normalized()
        b = n.cross(a)
        L = random.uniform(*length)
        turns = random.uniform(1.2, 2.0)
        r = random.uniform(0.006, 0.01)
        ph = random.uniform(0, 2 * math.pi)
        pts = []
        for k in range(14):
            t = k / 13
            ang = ph + t * turns * 2 * math.pi
            p = v.co + n * (L * t) + (a * math.cos(ang) + b * math.sin(ang)) * r * min(1, t * 3)
            pts.append(p)
        sp = cu.splines.new("NURBS")
        sp.points.add(len(pts) - 1)
        for k, p in enumerate(pts):
            sp.points[k].co = (p.x, p.y, p.z, 1)
            sp.points[k].radius = 1.0 - 0.6 * (k / 13)
        sp.use_endpoint_u = True
        sp.order_u = 4
    o = bpy.data.objects.new("curls", cu)
    bpy.context.scene.collection.objects.link(o)
    cu.materials.append(toon_mat(hexcol))
    return o


# ------------------------------------------------------------------ EEVEE turnaround sheet
def render_sheet_eevee(name, height, palette, width=None, views_def=cd.VIEWS):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = int(os.environ.get("LS_SAMPLES", "64"))
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    sc.render.resolution_x, sc.render.resolution_y = 640, 900
    w = sc.world or bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = hexrgb("#EFE6D2")
    w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
    root = bpy.data.objects.new("root", None)
    sc.collection.objects.link(root)
    for o in list(sc.objects):
        if o != root and o.parent is None and o.type in ("MESH", "CURVE", "CURVES"):
            o.parent = root
    s = max(height, width or 0)
    tz = height * 0.5
    rd.light("key", (-1.6 * s, -2.2 * s, tz + 1.6 * s), s * 1.5, 900 * s * s, (1.0, 0.94, 0.85))
    rd.light("fill", (2.2 * s, -1.6 * s, tz + 0.4 * s), s * 2.0, 250 * s * s, (0.85, 0.9, 1.0))
    rd.light("rim", (0.6 * s, 2.4 * s, tz + 1.8 * s), s * 1.0, 700 * s * s, (1.0, 0.9, 0.75))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(height, (width or 0) * 900 / 640) * 1.15
    sc.camera = cam
    views = []
    for label, yaw, elev in views_def:
        e = math.radians(elev)
        cam.location = (0, -s * 4 * math.cos(e), tz + s * 4 * math.sin(e))
        cam.rotation_euler = (math.radians(90) - e, 0, 0)
        root.rotation_euler = (0, 0, math.radians(yaw))
        path = os.path.join(OUT, "_%s_%s.png" % (name, label))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        img = bpy.data.images.load(path)
        views.append(np.array(img.pixels[:]).reshape(900, 640, 4))
        bpy.data.images.remove(img)
        os.remove(path)
    sheet = np.concatenate(views, axis=1)
    strip = np.ones((140, sheet.shape[1], 4))
    strip[:, :, :3] = np.array(cd.srgb("#E6DAC0"))
    for i, h in enumerate(palette):
        strip[30:110, 40 + i * 150:150 + i * 150, :3] = np.array(cd.srgb(h))
    sheet = np.concatenate([strip, sheet], axis=0)
    out = bpy.data.images.new(name, sheet.shape[1], sheet.shape[0], alpha=True)
    out.pixels.foreach_set(sheet.astype(np.float32).ravel())
    out.filepath_raw = os.path.join(OUT, name + "_turnaround.png")
    out.file_format = "PNG"
    out.save()
    print("LS_SHEET " + out.filepath_raw, flush=True)


# ------------------------------------------------------------------ Kieran Thorn, stylised
def kieran():
    SKIN, HAIR, JACKET, SCARF, SHIRT, PANTS = "#6E4630", "#1A1412", "#5C6E4F", "#4B9FE1", "#E9E1CC", "#6B6A55"
    LEATHER, BOOT, BRASS, GLOVE, SOCK, SOLE = "#8B5A2B", "#6B4426", "#C79A3B", "#3E2C22", "#E6DCC6", "#2E211A"
    K = rd.KIND
    K.clear()
    K.update({LEATHER: "leather", BOOT: "leather", BRASS: "brass", GLOVE: "leather", SOLE: "leather", "#8FD0EE": "glass",
              "#7FD3FF": "glow"})
    body, bones = rh.make_human(
        "Kieran", {"gender": 1.0, "age": 0.3, "muscle": 0.55, "weight": 0.42, "height": 0.6, "proportions": 0.7},
        {"african": 1.0, "asian": 0.0, "caucasian": 0.0},
        {"eyes": "high-poly.mhclo", "eyebrows": "eyebrow010.mhclo", "eyelashes": "mindfront_eyelashes_01.mhclo", "teeth": "teeth_base.mhclo"},
        "young_african_male.mhmat",
        targets={"l-eye-scale-incr": 1.0, "r-eye-scale-incr": 1.0})
    seg = rh.segments(bones)
    stylise(body, seg)
    cls = rh.classify(body, seg)
    hip_z, neck_z = seg["thighL"][0].z, seg["neck"][0].z
    rh.CLS[body.name], rh.HIP[body.name] = cls, hip_z
    restyle_skin(body, SKIN)
    scalp_cap(body, HAIR)
    for o in bpy.data.objects:     # brows and lashes in a clean dark tone
        if "eyebrow" in o.name or "eyelash" in o.name:
            o.data.materials.clear()
            o.data.materials.append(toon_mat("#120C0A"))
    G = rh.garment
    sh = G(body, cls, "shirt", SHIRT, lambda c, co: (c[0] == "spine" and co.z > hip_z - 0.12) or (c[0] == "neck" and c[1] < 0.3)
           or c[0].startswith("uarm"), 0.008, 0.004, folds=0.0, smooth=3)
    jk = G(body, cls, "jacket", JACKET, lambda c, co: ((c[0] == "spine" and co.z > hip_z - 0.1 and not (abs(co.x) < 0.05 and co.y < -0.02))
                                                       or c[0].startswith("uarm") or (c[0].startswith("farm") and c[1] < 0.45)),
           0.03, 0.008, folds=0.0, hide_skin=False, smooth=4)
    hems(jk, 0.03, 0.008, "#4D5D42")
    for s in "LR":
        a, b = seg["farm" + s]
        rh.band(rh.pt(seg, "farm" + s, 0.45), 0.06, b - a, 0.055, 0.016, SHIRT)
    sy = seg["spine"][1].y
    for sx in (-1, 1):
        y = rh.front_y(body, neck_z - 0.17, 0.15) - 0.035
        cd.box((sx * 0.085, y, neck_z - 0.17), (0.048, 0.01, 0.052), JACKET, 0.35)
        cd.box((sx * 0.085, y - 0.008, neck_z - 0.125), (0.05, 0.012, 0.02), "#4D5D42", 0.4)
        cd.sph((sx * 0.085, y - 0.02, neck_z - 0.128), (0.007, 0.004, 0.007), BRASS)
        c = cd.box((sx * 0.07, sy - 0.075, neck_z - 0.005), (0.06, 0.014, 0.045), JACKET, 0.4)
        c.rotation_euler = (math.radians(-35), 0, sx * math.radians(25))
    hands = [rh.pt(seg, "hand" + s, t) for s in "LR" for t in (0.0, 0.35, 0.7, 1.0)]

    def near_hand(co):   # fingers hang by the thighs: keep them out of the trousers
        return min((co - h).length for h in hands) < 0.075
    tr = G(body, cls, "trousers", PANTS, lambda c, co: (c[0].startswith("thigh") and not near_hand(co)) or (c[0].startswith("shin") and c[1] < 0.6)
           or (c[0] == "spine" and co.z < hip_z + 0.1), 0.04, 0.006, folds=0.0, smooth=4)
    hems(tr, 0.04, 0.008, "#5C5B48")
    rh.belt(body, hip_z + 0.05, LEATHER, off=0.045, width=0.05)
    bt = G(body, cls, "boots", BOOT, lambda c, co: c[0].startswith("foot") or (c[0].startswith("shin") and c[1] > 0.45),
           0.02, 0.008, folds=0.0, smooth=3)
    for s in "LR":
        pts = [v.co for v in rh.SRC[body.name].vertices if cls[v.index][0] == "foot" + s or (cls[v.index][0] == "shin" + s and v.co.z < 0.06)]
        xs, ys = [p.x for p in pts], [p.y for p in pts]
        cd.box(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2 - 0.008, 0.014),
               ((max(xs) - min(xs)) / 2 + 0.014, (max(ys) - min(ys)) / 2 + 0.006, 0.014), SOLE, 0.4)
        a, b = seg["shin" + s]
        rh.band(rh.pt(seg, "shin" + s, 0.56), 0.072, b - a, 0.06, 0.018, SOCK)
        for k in range(4):
            p0 = rh.pt(seg, "shin" + s, 0.64 + k * 0.08)
            cd.box((p0.x, p0.y - 0.07, p0.z), (0.024, 0.004, 0.004), SOCK, 0.3)
    G(body, cls, "gloves", GLOVE, lambda c, co: (c[0].startswith("hand") and c[1] < 0.62) or (c[0].startswith("farm") and c[1] > 0.9),
      0.004, 0.003, folds=0.0)
    nz = neck_z + 0.03
    ny = seg["neck"][0].y
    rh.band(Vector((0, ny, nz)), 0.08, (0, 0, 1), 0.075, 0.035, SCARF, scale=(1.12, 1.06, 1))
    rh.band(Vector((0.01, ny - 0.01, nz - 0.045)), 0.09, (0.15, -0.25, 1), 0.06, 0.03, SCARF, scale=(1.12, 1.05, 1))
    rh.strap([(0.05, ny - 0.09, nz - 0.03), (0.075, ny - 0.11, nz - 0.1), (0.085, ny - 0.115, nz - 0.18)], 0.075, 0.018, SCARF)
    rh.strap([(0.035, ny - 0.095, nz - 0.035), (0.05, ny - 0.12, nz - 0.08), (0.055, ny - 0.13, nz - 0.13)], 0.065, 0.018, SCARF)
    h0, h1 = seg["head"]
    hl = (h1 - h0).length
    hz, hy = h0.z + hl * 0.68, h0.y
    rh.band(Vector((0, hy, hz)), 0.112, (0, 0.25, 1), 0.028, 0.007, LEATHER, scale=(1.0, 1.12, 1.0))
    for sx in (-1, 1):
        rh.band(Vector((sx * 0.04, hy - 0.118, hz + 0.012)), 0.032, (0, -1, 0.35), 0.024, 0.01, BRASS)
        cd.sph((sx * 0.04, hy - 0.126, hz + 0.014), (0.03, 0.01, 0.03), "#8FD0EE")
    lsh = seg["uarmL"][0]
    rhip = Vector((-0.18, seg["spine"][0].y - 0.02, hip_z - 0.03))
    rh.strap([(lsh.x - 0.04, lsh.y - 0.07, lsh.z + 0.02), (0.0, lsh.y - 0.17, lsh.z - 0.2), (rhip.x + 0.02, rhip.y - 0.14, rhip.z + 0.12),
              (rhip.x - 0.02, rhip.y - 0.06, rhip.z + 0.07)], 0.04, 0.007, LEATHER)
    cd.box((rhip.x - 0.02, rhip.y, rhip.z), (0.09, 0.05, 0.085), LEATHER, 0.35)
    cd.box((rhip.x - 0.02, rhip.y - 0.05, rhip.z + 0.025), (0.093, 0.012, 0.065), "#7A4E25", 0.35)
    cd.box((rhip.x - 0.02, rhip.y - 0.064, rhip.z + 0.0), (0.012, 0.004, 0.025), BRASS, 0.3)
    cz, fy = hip_z - 0.02, rh.front_y(body, hip_z - 0.02, 0.2)
    cd.cyl((0.13, fy - 0.06, cz), 0.042, 0.016, BRASS, rot=(math.radians(90), 0, 0), verts=40)
    cd.cyl((0.13, fy - 0.069, cz), 0.034, 0.004, "#EFE6CF", rot=(math.radians(90), 0, 0))
    cd.limb((0.13, fy - 0.073, cz - 0.004), (0.13, fy - 0.073, cz + 0.028), 0.004, 0.001, "#7FD3FF")
    curl_clumps(body, seg, HAIR)
    render_sheet_eevee("Kieran_stylised", 1.85, [SKIN, HAIR, JACKET, SCARF, SHIRT, PANTS, LEATHER, BOOT, BRASS, GLOVE])


if __name__ == "__main__":
    for w in WHICH:
        {"kieran": kieran}[w]()
    print("LS_STYLISED_OK", flush=True)
