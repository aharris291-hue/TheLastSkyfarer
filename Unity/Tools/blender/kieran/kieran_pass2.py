"""Kieran fidelity pass 2: the steps added on top of kieran_hifi.py (all our own geometry, made in Blender).

  * face and hands: the game mesh is subdivided once over the face and hands and given the larger sculpted forms;
    the high-poly gets all of them (kieran_face.py);
  * nails: thin domed plates on each fingertip, skinned to the fingertip bones;
  * hems: a rolled hem along every open edge of the jacket, shirt and trousers (front opening, cuffs, waist, legs);
  * cuffs thicker, collar and lapel edges crisper;
  * edge curls: small alpha-cut cards of coiled strands round the hair, so its outline is soft rather than a hard
    shell. They use their own material and strand texture, painted here.
"""
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Vector

import kieran_face as KF

STATE = {}


def prepare(sc, rig):
    """At the start of the game copy (master still untouched): landmarks, nails, hems and trim changes."""
    STATE["L"] = KF.landmarks()
    STATE["rig"] = rig
    body = bpy.data.objects["Kieran.body"]
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg))
    me.transform(body.matrix_world)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    nail_mat = bpy.data.materials.new("M_Kieran_nails")
    nail_mat.use_nodes = True
    b = next(n for n in nail_mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.20, 0.12, 0.09, 1.0)
    b.inputs["Roughness"].default_value = 0.55
    nails_me = KF.build_nails(bm, rig, nail_mat)
    bm.free()
    bpy.data.meshes.remove(me)
    nails = bpy.data.objects.new("Kieran_nails", nails_me)
    sc.collection.objects.link(nails)
    # each plate follows its fingertip bone
    F = KF.hand_frames(rig)
    tips = [(s, f) for s in ("l", "r") for f in KF.FINGERS + ("thumb",)]
    groups = {}
    for s, f in tips:
        groups[(s, f)] = nails.vertex_groups.new(name="%s_03_%s" % (f, s))
    for v in nails_me.vertices:
        best = min(tips, key=lambda t: (v.co - (rig.matrix_world @ rig.data.bones["%s_03_%s" % (t[1], t[0])].tail_local)).length)
        groups[best].add([v.index], 1.0, "REPLACE")
    build_hems(sc)
    adjust_trims(sc)


def build_hems(sc):
    """A rolled hem along each open edge of the main garments, in the garment's own material."""
    dg = bpy.context.evaluated_depsgraph_get()
    for name in ("Kieran_jacket", "Kieran_shirt", "Kieran_trousers"):
        o = bpy.data.objects.get(name)
        if not o:
            continue
        sol = [m for m in o.modifiers if m.type == "SOLIDIFY"]
        arm = [m for m in o.modifiers if m.type == "ARMATURE"]
        for m in sol + arm:
            m.show_viewport = False
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        for m in sol + arm:
            m.show_viewport = True
        me.transform(o.matrix_world)
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.normal_update()
        bpy.data.meshes.remove(me)
        out = bmesh.new()
        seen = set()
        loops = 0
        for e0 in [e for e in bm.edges if e.is_boundary]:
            if e0.index in seen:
                continue
            chain = [e0.verts[0]]
            cur_e, cur_v = e0, e0.verts[1]
            seen.add(e0.index)
            while cur_v is not chain[0] and len(chain) < 5000:
                chain.append(cur_v)
                nxt = [e for e in cur_v.link_edges if e.is_boundary and e is not cur_e and e.index not in seen]
                if not nxt:
                    break
                cur_e = nxt[0]
                seen.add(cur_e.index)
                cur_v = cur_e.other_vert(cur_v)
            closed = cur_v is chain[0]
            # resample every 9 mm, sit the roll on the outside of the cloth, its edge flush with the cloth's edge
            pts = []
            acc = 0.0
            for a, b in zip(chain, chain[1:] + ([chain[0]] if closed else [])):
                seg = (b.co - a.co).length
                n_sub = max(1, int(seg / 0.009))
                for k in range(n_sub):
                    t = k / n_sub
                    nrm = (a.normal * (1 - t) + b.normal * t).normalized()
                    pts.append(a.co.lerp(b.co, t) + nrm * 0.0016)
            if closed and pts:
                pts.append(pts[0])
            if len(pts) < 4:
                continue
            KF_tube(out, pts, 0.0024, 5)
            loops += 1
        bm.free()
        hm = bpy.data.meshes.new(name + "_hemroll")
        out.to_mesh(hm)
        out.free()
        for p in hm.polygons:
            p.use_smooth = True
        for m in o.data.materials:
            hm.materials.append(m)
            break
        h = bpy.data.objects.new(name + "_hemroll", hm)
        h["thin"] = 1
        sc.collection.objects.link(h)
        hm.calc_loop_triangles()
        print("LS_PASS2 hems on %s: %d edges, %d tris" % (name, loops, len(hm.loop_triangles)), flush=True)


def KF_tube(bm, pts, r, sides):
    from kieran_hifi import tube
    tube(bm, pts, lambda s: r, sides)


def adjust_trims(sc):
    """Cuffs about half as thick again; collar and lapel edges crisper (narrower bevels, no rounding)."""
    for o in sc.objects:
        if o.type != "MESH":
            continue
        n = o.name
        if "cuff" in n:
            for m in o.modifiers:
                if m.type == "SOLIDIFY":
                    m.thickness *= 1.5
                if m.type == "BEVEL":
                    m.segments = 3
        if any(k in n for k in ("collar", "lapel", "chest_flap", "sleeve_flap")):
            for m in o.modifiers:
                if m.type == "BEVEL":
                    m.width = min(m.width, 0.0012)
                    m.segments = 2
    print("LS_PASS2 trims adjusted", flush=True)


def _region_faces(bm, o, names, front_only=False):
    groups = [o.vertex_groups[n].index for n in names if n in o.vertex_groups]
    dl = bm.verts.layers.deform.active
    if not groups or not dl:
        return []
    mw = o.matrix_world
    out = []
    for f in bm.faces:
        if all(sum(v[dl].get(i, 0.0) for i in groups) > 0.5 for v in f.verts):
            if front_only and (mw @ f.calc_center_median()).y > -0.02:
                continue
            out.append(f)
    return out


def game_body(o, me):
    """The game body: one subdivision over the face and the hands, then the larger sculpted forms."""
    if not o.name.startswith("Kieran.body"):
        if o.name.startswith("Kieran_gloves"):
            _sculpt_world(o, me, lambda bm: KF.sculpt_hands(bm, STATE["rig"], False))
        return
    bm = bmesh.new()
    bm.from_mesh(me)
    hand_names = [g.name for g in o.vertex_groups if g.name.startswith(("hand_", "thumb_", "index_", "middle_", "ring_", "pinky_"))]
    faces = _region_faces(bm, o, ["head"], front_only=True) + _region_faces(bm, o, hand_names)
    edges = list({e for f in faces for e in f.edges})
    n0 = len(bm.faces)
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True, smooth=1.0)
    bm.to_mesh(me)
    bm.free()
    print("LS_PASS2 game face/hands subdivided: %d -> %d faces" % (n0, len(me.polygons)), flush=True)

    def sculpt(bm):
        KF.sculpt_face(bm, STATE["L"], False)
        KF.sculpt_hands(bm, STATE["rig"], False)
    _sculpt_world(o, me, sculpt)


def _sculpt_world(o, me, fn):
    mw = o.matrix_world
    me.transform(mw)
    bm = bmesh.new()
    bm.from_mesh(me)
    fn(bm)
    bm.to_mesh(me)
    bm.free()
    me.transform(mw.inverted())


def hp_body(name, me_world):
    """The high-poly body (already in world space): every sculpted form, fine detail included."""
    bm = bmesh.new()
    bm.from_mesh(me_world)
    if name.startswith("Kieran.body"):
        KF.sculpt_face(bm, STATE["L"], True)
        KF.sculpt_hands(bm, STATE["rig"], True)
    elif name.startswith("Kieran_gloves"):
        KF.sculpt_hands(bm, STATE["rig"], True)
    else:
        bm.free()
        return
    bm.to_mesh(me_world)
    bm.free()
    print("LS_PASS2 high-poly sculpted: %s" % name, flush=True)


# ------------------------------------------------------------------ edge curl cards
def strand_texture(path, size=512, seed=5):
    """Coiled strands on transparency, in Kieran's hair browns (straight alpha, colour bled into the clear parts)."""
    rnd = random.Random(seed)
    img = np.zeros((size, size, 4), np.float32)
    base = np.array([0.030, 0.021, 0.015])
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32) / size
    alpha = np.zeros((size, size), np.float32)
    tone = np.zeros((size, size), np.float32)
    for column in range(4):                              # four card designs side by side
        x0, x1 = column / 4, (column + 1) / 4
        for k in range(9):
            cx = x0 + (x1 - x0) * rnd.uniform(0.25, 0.75)
            amp = (x1 - x0) * rnd.uniform(0.12, 0.22)
            pitch = rnd.uniform(0.07, 0.11)
            ph = rnd.uniform(0, 2 * math.pi)
            width = rnd.uniform(0.006, 0.010)
            top = rnd.uniform(0.55, 0.98)
            t = rnd.uniform(0.8, 1.25)
            sx = cx + amp * np.sin(2 * math.pi * yy / pitch + ph) * (0.6 + 0.4 * yy)
            d = np.abs(xx - sx) / width
            m = np.clip(1.4 - d, 0, 1) * (yy < top) * (xx >= x0) * (xx < x1)
            m *= np.clip((top - yy) / 0.05, 0, 1)        # tapered tips
            alpha = np.maximum(alpha, m)
            tone = np.where(m > 0.5, t, tone)
    tone = np.where(tone == 0, 1.0, tone)
    for c in range(3):
        img[..., c] = base[c] * tone
    img[..., 3] = alpha
    im = bpy.data.images.new("T_Kieran_HairStrands", size, size, alpha=True)
    im.colorspace_settings.name = "sRGB"
    im.alpha_mode = "STRAIGHT"
    srgb = np.where(img[..., :3] <= 0.0031308, img[..., :3] * 12.92, 1.055 * np.power(img[..., :3], 1 / 2.4) - 0.055)
    img[..., :3] = srgb
    im.pixels[:] = img.ravel()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("LS_PASS2 strand texture", path, flush=True)


def add_edge_cards(game, sites, rig, count=900, seed=9):
    """Small alpha-cut curl cards standing out of the hair shell (material slot 2), skinned to the head."""
    rnd = random.Random(seed)
    mat = bpy.data.materials.new("M_Kieran_HairCards")
    game.data.materials.append(mat)
    mi = len(game.data.materials) - 1
    bm = bmesh.new()
    bm.from_mesh(game.data)
    dl = bm.verts.layers.deform.verify()
    uv = bm.loops.layers.uv.active
    hi = game.vertex_groups["head"].index
    imw = game.matrix_world.inverted()
    picks = rnd.sample(sites, min(count, len(sites)))
    made = 0
    for p, n in picks:
        if n.z < -0.6:
            continue
        tang = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        tang = (tang - n * tang.dot(n)).normalized()
        side = max(0.0, -n.z) + 0.3 * (1 - abs(n.z))
        d = (n * 0.8 + tang * 0.45 + Vector((0, 0, -1)) * 0.3 * side).normalized()
        s = d.cross(n)
        if s.length < 1e-3:
            s = tang.cross(n)
        s.normalize()
        length = rnd.uniform(0.016, 0.026)
        width = rnd.uniform(0.010, 0.014)
        base = p - n * 0.002
        col = rnd.randrange(4)
        u0, u1 = col / 4 + 0.005, (col + 1) / 4 - 0.005
        rows = []
        for i, t in enumerate((0.0, 0.5, 1.0)):
            c = base + d * length * t + Vector((0, 0, -1)) * 0.004 * side * t * t
            row = []
            for j, w in enumerate((-0.5, 0.5)):
                v = bm.verts.new(imw @ (c + s * width * w))
                v[dl][hi] = 1.0
                row.append((v, (u0 if j == 0 else u1, t)))
            rows.append(row)
        for a in range(2):
            quad = [rows[a][0], rows[a][1], rows[a + 1][1], rows[a + 1][0]]
            f = bm.faces.new([q[0] for q in quad])
            f.material_index = mi
            f.smooth = True
            for loop, q in zip(f.loops, quad):
                loop[uv].uv = q[1]
        made += 1
    bm.to_mesh(game.data)
    bm.free()
    print("LS_PASS2 edge curl cards: %d" % made, flush=True)
