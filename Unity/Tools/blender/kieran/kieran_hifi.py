"""Kieran fidelity overhaul (Phase 2/3): the high-poly build and the bakes, run inside the game export.

Called from export_kieran_hifi.py, which runs the Unity export of the Unreal-era finalize script with these steps
patched in. Everything here is geometry built in Blender from Kieran's own master; nothing is downloaded.

  * hair: ~800 clumps of tight coils (real helical tubes) grown from the master's hair volume. The game hair is a
    clump-shaped shell remeshed from those clumps, so the silhouette carries the curls and their normals and occlusion
    are baked onto it;
  * clothing: folds concentrated where the garments bend (elbows, knees, armpits, hips, waist) in the game mesh as
    well as the high-poly, finer creases in the high-poly only, double top-stitching along every seam and hem, single
    stitching round every pocket, flap, collar and cuff, and the fabric weave and leather grain from the materials;
  * skin: the body subdivided twice with a fine pore relief, and the face and hands given more texture space;
  * bakes onto the game mesh: tangent-space normal, ambient occlusion, and a packed mask (R metallic, G occlusion,
    A smoothness) for URP Lit.
"""
import bisect
import itertools
import math
import os
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector, bvhtree, noise

HP_NAME = "Kieran_HighPoly"


def hp_collection():
    c = bpy.data.collections.get(HP_NAME)
    if not c:
        c = bpy.data.collections.new(HP_NAME)   # not linked to the scene: the game copy never sees these objects
    return c


def add_hp(name, me, mats=None):
    o = bpy.data.objects.new(name, me)
    hp_collection().objects.link(o)
    if mats is not None and not me.materials:
        for m in mats:
            me.materials.append(m)
    return o


# ------------------------------------------------------------------ materials: relief the normal bake picks up
def _principled(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m and m.use_nodes else None


def add_relief(mat, kind):
    """Adds a fine bump to a material (weave, leather grain or skin pores) if it has none. Used by the normal bake only."""
    b = _principled(mat)
    if not b or b.inputs["Normal"].is_linked or mat.get("ls_relief"):
        return
    nt = mat.node_tree
    tc = nt.nodes.new("ShaderNodeTexCoord")
    bump = nt.nodes.new("ShaderNodeBump")
    if kind == "weave":
        w1 = nt.nodes.new("ShaderNodeTexWave"); w1.wave_type = "BANDS"; w1.bands_direction = "X"; w1.inputs["Scale"].default_value = 260
        w2 = nt.nodes.new("ShaderNodeTexWave"); w2.wave_type = "BANDS"; w2.bands_direction = "Z"; w2.inputs["Scale"].default_value = 260
        for w in (w1, w2):
            w.inputs["Distortion"].default_value = 0.4
            nt.links.new(tc.outputs["Object"], w.inputs["Vector"])
        mul = nt.nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"
        nt.links.new(w1.outputs["Fac"], mul.inputs[0]); nt.links.new(w2.outputs["Fac"], mul.inputs[1])
        nt.links.new(mul.outputs[0], bump.inputs["Height"])
        bump.inputs["Strength"].default_value = 0.25
        bump.inputs["Distance"].default_value = 0.0004
    else:
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 900 if kind == "pores" else 420
        nz.inputs["Detail"].default_value = 3
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
        bump.inputs["Strength"].default_value = 0.08 if kind == "pores" else 0.25
        bump.inputs["Distance"].default_value = 0.0003
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mat["ls_relief"] = 1


def soften_ramps(keep=0.3):
    """The master's materials paint their colour through a noise ramp. Under physically based light that variation
    reads as dirt, so each ramp is pulled most of the way to its mean colour (a subtle variation stays)."""
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        for n in m.node_tree.nodes:
            if n.type == "VALTORGB":
                els = n.color_ramp.elements
                mean = [sum(e.color[i] for e in els) / len(els) for i in range(3)]
                for e in els:
                    e.color = tuple(mean[i] + (e.color[i] - mean[i]) * keep for i in range(3)) + (e.color[3],)
    hair = bpy.data.materials.get("M_Kieran_hair")
    if hair and hair.use_nodes:   # a very dark brown rather than near-black, so the clumps' forms read in shade
        for n in hair.node_tree.nodes:
            if n.type == "VALTORGB":
                cols = [(0.030, 0.021, 0.015), (0.034, 0.024, 0.017)]
                for e, c in zip(n.color_ramp.elements, cols):
                    e.color = c + (1.0,)


def add_all_relief():
    soften_ramps()
    for m in bpy.data.materials:
        n = m.name.lower()
        if any(k in n for k in ("jacket", "shirt", "trousers", "scarf", "cuff")):
            add_relief(m, "weave")
        elif any(k in n for k in ("boot", "belt", "satchel", "gloves")):
            add_relief(m, "leather")
        elif "skin" in n:
            add_relief(m, "pores")


# ------------------------------------------------------------------ geometry helpers
def tube(bm, pts, radius_fn, sides, colour=None, col_layer=None):
    """A closed-ended tube along a polyline, parallel-transport frames, radius varying along it."""
    if len(pts) < 2:
        return
    t0 = (pts[1] - pts[0]).normalized()
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    u = t0.cross(ref).normalized()
    rings = []
    prev_t = t0
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        axis = prev_t.cross(t)
        if axis.length > 1e-6:
            u = Matrix.Rotation(prev_t.angle(t), 3, axis.normalized()) @ u
        prev_t = t
        v = t.cross(u)
        r = radius_fn(i / (len(pts) - 1))
        rings.append([bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * r)
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    faces = []
    for a, b in zip(rings, rings[1:]):
        for k in range(sides):
            faces.append(bm.faces.new((a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k])))
    faces.append(bm.faces.new(list(reversed(rings[0]))))
    faces.append(bm.faces.new(rings[-1]))
    if colour is not None and col_layer is not None:
        for f in faces:
            for loop in f.loops:
                loop[col_layer] = colour


def bm_to_mesh(bm, name):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


# ------------------------------------------------------------------ hair: coil clumps
def build_hair(seed=11):
    """Replaces the smooth hair mass with a clump-shaped shell and adds the coil clumps to the high-poly."""
    hair = bpy.data.objects["Kieran_hair"]
    mw = hair.matrix_world.copy()
    src = bmesh.new()
    src.from_mesh(hair.data)
    src.transform(mw)
    bmesh.ops.triangulate(src, faces=src.faces)
    src.normal_update()
    src.faces.ensure_lookup_table()
    areas = [f.calc_area() for f in src.faces]
    cum = list(itertools.accumulate(areas))
    total = cum[-1]
    rnd = random.Random(seed)
    head_c = Vector((0.0, -0.045, 1.70))

    # Even spread of clump roots (rejection sampling on a 1.1 cm spacing).
    roots, grid = [], {}
    cell = 0.011
    tries = 0
    while tries < 40000 and len(roots) < 1100:
        tries += 1
        f = src.faces[min(bisect.bisect(cum, rnd.random() * total), len(src.faces) - 1)]
        a, b, c = (v.co for v in f.verts)
        r1, r2 = rnd.random(), rnd.random()
        if r1 + r2 > 1:
            r1, r2 = 1 - r1, 1 - r2
        p = a + (b - a) * r1 + (c - a) * r2
        n = f.normal.copy()
        if n.dot(p - head_c) < 0:          # inner side of the shell (if it has one)
            continue
        key = tuple(int(math.floor(x / cell)) for x in p)
        if any((q - p).length < cell for k in itertools.product((-1, 0, 1), repeat=3)
               for q in grid.get((key[0] + k[0], key[1] + k[1], key[2] + k[2]), ())):
            continue
        grid.setdefault(key, []).append(p)
        roots.append((p, n))
    src.free()

    hp = bmesh.new()
    col = hp.loops.layers.color.new("Col")
    env = bmesh.new()
    base_dark = Vector((0.032, 0.022, 0.015))
    coils = 0
    for p, n in roots:
        side = max(0.0, -n.z) + 0.3 * (1 - abs(n.z))      # sides and nape hang a little
        tang = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
        tang = (tang - n * tang.dot(n)).normalized()
        axis = (n * 0.85 + tang * 0.35 + Vector((0, 0, -1)) * 0.25 * side).normalized()
        length = rnd.uniform(0.018, 0.03) * (1.1 if n.z > 0.5 else 0.9)
        base = p - n * 0.013
        u = axis.cross(Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))).normalized()
        v = axis.cross(u)
        clump_r = rnd.uniform(0.0042, 0.0058)
        tone = rnd.uniform(0.8, 1.35)
        hand = 1 if rnd.random() < 0.5 else -1
        # Envelope for the game shell: an ellipsoid round the clump.
        mid = base + axis * length * 0.55
        ico = bmesh.ops.create_icosphere(env, subdivisions=1, radius=1.0)
        sm = Matrix((u * (clump_r + 0.0045), v * (clump_r + 0.0045), axis * length * 0.5)).transposed().to_4x4()
        bmesh.ops.transform(env, matrix=Matrix.Translation(mid) @ sm, verts=ico["verts"])
        for k in range(rnd.randint(4, 6)):
            off_a = rnd.uniform(0, 2 * math.pi)
            off_r = clump_r * math.sqrt(rnd.random()) * 0.8
            start = base + (u * math.cos(off_a) + v * math.sin(off_a)) * off_r
            hr = rnd.uniform(0.0026, 0.0036)
            pitch = rnd.uniform(0.0065, 0.008)
            phase = rnd.uniform(0, 2 * math.pi)
            L = length * rnd.uniform(0.8, 1.1)
            steps = max(8, int(L / 0.0011))
            pts = []
            for i in range(steps + 1):
                t = L * i / steps
                ang = phase + hand * 2 * math.pi * t / pitch
                droop = Vector((0, 0, -1)) * side * 0.35 * L * (t / L) ** 2
                rr = hr * (1.0 - 0.25 * t / L)
                pts.append(start + axis * t + (u * math.cos(ang) + v * math.sin(ang)) * rr + droop)
            tr = rnd.uniform(0.0011, 0.0015)
            c = base_dark * tone * rnd.uniform(0.9, 1.1)
            tube(hp, pts, lambda s, tr=tr: tr * (1.0 - 0.45 * s * s), 6, (c.x, c.y, c.z, 1.0), col)
            coils += 1
    hp_me = bm_to_mesh(hp, "Kieran_hair_coils_HP")
    hair_mat = bpy.data.materials.get("M_Kieran_hair")
    hp_mat = bpy.data.materials.new("M_Kieran_hair_HP")
    hp_mat.use_nodes = True
    nt = hp_mat.node_tree
    bsdf = _principled(hp_mat)
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.6
    hp_me.materials.append(hp_mat)
    add_hp("Kieran_hair_coils_HP", hp_me)

    # The game shell: the clump envelopes and the original volume pulled in 4 mm, remeshed together, smoothed and
    # reduced. It keeps the clumps in its silhouette.
    inner = bmesh.new()
    inner.from_mesh(hair.data)
    inner.transform(mw)
    inner.normal_update()
    for vtx in inner.verts:
        vtx.co -= vtx.normal * 0.004
    tmp_me = bpy.data.meshes.new("hair_inner")
    inner.to_mesh(tmp_me)
    inner.free()
    env_me = bpy.data.meshes.new("hair_env")
    env.to_mesh(env_me)
    env.free()
    shell = bpy.data.objects.new("hair_shell_tmp", env_me)
    bpy.context.scene.collection.objects.link(shell)
    inner_o = bpy.data.objects.new("hair_inner_tmp", tmp_me)
    bpy.context.scene.collection.objects.link(inner_o)
    for o in bpy.context.scene.objects:
        o.select_set(False)
    shell.select_set(True)
    inner_o.select_set(True)
    bpy.context.view_layer.objects.active = shell
    bpy.ops.object.join()
    rm = shell.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = 0.0028
    smo = shell.modifiers.new("smooth", "SMOOTH")
    smo.factor = 0.6
    smo.iterations = 3
    dec = shell.modifiers.new("dec", "DECIMATE")
    dg = bpy.context.evaluated_depsgraph_get()
    n_full = len(shell.evaluated_get(dg).data.polygons) * 2
    dec.ratio = min(1.0, 14000 / max(1, n_full))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    game_me = bpy.data.meshes.new_from_object(shell.evaluated_get(dg))
    game_me.transform(mw.inverted())
    for poly in game_me.polygons:
        poly.use_smooth = True
    game_me.materials.clear()
    if hair_mat:
        shell_mat = hair_mat.copy()
        shell_mat.name = "M_Kieran_hair_shell"     # tells the shell apart from the scalp (which shares the hair colour)
        game_me.materials.append(shell_mat)
    old = hair.data
    hair.data = game_me
    bpy.data.meshes.remove(old)
    bpy.data.objects.remove(shell, do_unlink=True)   # (the inner volume was joined into it)
    for o in [o for o in bpy.context.scene.objects if o.name.endswith("_hair_coils")]:
        bpy.data.objects.remove(o, do_unlink=True)   # the master's guide coils: replaced by the clumps
    body = bpy.data.objects.get("Kieran.body")
    if body:
        sb = bmesh.new()
        sb.from_mesh(game_me)
        sb.transform(mw)
        tree = bvhtree.BVHTree.FromBMesh(sb)
        sb.free()
        names = [m.name if m else "" for m in body.data.materials]
        hi = names.index("M_Kieran_hair") if "M_Kieran_hair" in names else -1
        si = names.index("M_Kieran_skin") if "M_Kieran_skin" in names else -1
        moved = 0
        if hi >= 0 and si >= 0:
            bmw = body.matrix_world
            for poly in body.data.polygons:
                if poly.material_index == hi:
                    c = bmw @ poly.center
                    nw = (bmw.to_3x3() @ poly.normal).normalized()
                    hit = tree.ray_cast(c + nw * 0.0005, nw, 0.07)[0]   # covered if the shell lies right above it
                    if hit is None:
                        poly.material_index = si
                        moved += 1
        print("LS_HIFI scalp faces outside the hair now skin: %d" % moved, flush=True)
    game_me.calc_loop_triangles()
    print("LS_HIFI hair: %d clumps, %d coils, high-poly %d tris, game shell %d tris"
          % (len(roots), coils, len(hp_me.polygons) * 2, len(game_me.loop_triangles)), flush=True)


# ------------------------------------------------------------------ clothing folds
FOLD_JOINTS = [("upperarm_l", "lowerarm_l"), ("upperarm_r", "lowerarm_r"), ("thigh_l", "calf_l"), ("thigh_r", "calf_r"),
               ("spine_03", "upperarm_l"), ("spine_03", "upperarm_r"), ("pelvis", "thigh_l"), ("pelvis", "thigh_r"),
               ("spine_01", "pelvis"), ("lowerarm_l", "hand_l"), ("lowerarm_r", "hand_r")]
GARMENTS = ("Kieran_jacket", "Kieran_shirt", "Kieran_trousers")


def fold_mesh(o, me, rig, fine):
    """Displaces a garment's evaluated mesh outward in irregular ring folds where two of its bones meet; with fine=True
    adds the smaller creases the high-poly carries. Only outward, so the cloth never sinks into the body."""
    if not o.name.startswith(GARMENTS):
        return
    groups = {g.name: g.index for g in o.vertex_groups}
    bones = rig.data.bones
    mw = o.matrix_world
    imw = mw.inverted()
    pairs = [(a, b) for a, b in FOLD_JOINTS if a in groups and b in groups]
    for vtx in me.vertices:
        w = {g.group: g.weight for g in vtx.groups}
        p = mw @ vtx.co
        disp = 0.0
        for a, b in pairs:
            wa, wb = w.get(groups[a], 0.0), w.get(groups[b], 0.0)
            m = min(1.0, 4.0 * wa * wb)
            if m < 0.02:
                continue
            bone = bones[b]
            joint = rig.matrix_world @ bone.head_local
            ax = (rig.matrix_world.to_3x3() @ (bone.tail_local - bone.head_local)).normalized()
            s = (p - joint).dot(ax)
            ph = noise.noise(p * 18.0) * 2.2 + noise.noise(p * 7.0) * 1.5
            wave = 0.5 + 0.5 * math.sin(2 * math.pi * s / 0.026 + ph)
            disp += m * 0.0032 * wave ** 2
            if fine:
                wave2 = 0.5 + 0.5 * math.sin(2 * math.pi * s / 0.011 + ph * 1.7)
                disp += m * 0.0011 * wave2 ** 3
        if fine:   # general drape: soft, low creases everywhere
            disp += 0.0006 * max(0.0, noise.noise(p * Vector((9.0, 9.0, 2.5))))
        if disp > 0:
            vtx.co = imw @ (p + (mw.to_3x3() @ vtx.normal).normalized() * disp)


# ------------------------------------------------------------------ stitching
def _polyline(points, step):
    out = [points[0]]
    acc = 0.0
    for a, b in zip(points, points[1:]):
        seg = (b - a).length
        while acc + seg >= step:
            t = (step - acc) / seg
            a = a + (b - a) * t
            seg = (b - a).length
            out.append(a)
            acc = 0.0
        acc += seg
    return out


def stitch_row(bm, pts, offset_fn=None, dash=0.003, gap=0.0018, radius=0.00055):
    """Short stitches along a path (each a tiny tube), optionally offset sideways by offset_fn(point, tangent)."""
    path = _polyline(pts, 0.0005)
    if len(path) < 3:
        return 0
    n = 0
    period = int(round((dash + gap) / 0.0005))
    run = int(round(dash / 0.0005))
    for i in range(0, len(path) - run - 1, period):
        seg = path[i:i + run + 1]
        if offset_fn:
            t = (seg[-1] - seg[0]).normalized()
            seg = [q + offset_fn(q, t) for q in seg]
        tube(bm, [seg[0], seg[len(seg) // 2], seg[-1]], lambda s: radius * (0.7 + 0.3 * math.sin(math.pi * s)), 4)
        n += 1
    return n


def seam_points(o):
    """World-space points of a seam curve (before it is turned into a mesh)."""
    pts = []
    mw = o.matrix_world
    for s in o.data.splines:
        if s.type == "BEZIER":
            bp = s.bezier_points
            for a, b in zip(bp, bp[1:]):
                for k in range(12):
                    t = k / 12
                    p = ((1 - t) ** 3) * a.co + 3 * ((1 - t) ** 2) * t * a.handle_right + 3 * (1 - t) * t * t * b.handle_left + t ** 3 * b.co
                    pts.append(mw @ p)
            pts.append(mw @ bp[-1].co)
        else:
            pts += [mw @ p.co.xyz for p in s.points]
    return pts


def build_stitches(sc):
    bm = bmesh.new()
    count = 0
    # Double top-stitching either side of every seam and hem curve.
    for o in [o for o in sc.objects if o.type == "CURVE" and ("seam" in o.name or "yoke" in o.name or o.name.endswith("_hem"))]:
        pts = seam_points(o)
        if len(pts) < 2:
            continue
        for side in (-1, 1):
            def off(q, t, side=side):
                out = Vector((q.x, q.y, 0.0))
                out = out.normalized() if out.length > 1e-4 else Vector((0, -1, 0))
                return t.cross(out).normalized() * 0.0024 * side
            count += stitch_row(bm, pts, off)
    # Panels (pockets, flaps, lapels, collars): a stitch line 3 mm inside the edge of the outward face.
    for o in [o for o in sc.objects if o.type == "MESH" and any(k in o.name for k in ("pocket", "flap", "lapel", "collar_-1", "collar_1"))
              and not o.name.startswith("Kieran_satchel")]:
        mw = o.matrix_world
        me = o.data
        centre = mw @ (sum((v.co for v in me.vertices), Vector()) / len(me.vertices))
        out = Vector((centre.x, centre.y + 0.03, 0.0)).normalized()
        best = max(me.polygons, key=lambda f: f.area * (1.0 + max(0.0, (mw.to_3x3() @ f.normal).normalized().dot(out))))
        nrm = (mw.to_3x3() @ best.normal).normalized()
        if nrm.dot(out) < 0:
            continue
        corners = [mw @ me.vertices[i].co for i in best.vertices]
        c = sum(corners, Vector()) / len(corners)
        loop = [q + (c - q).normalized() * 0.003 + nrm * 0.0006 for q in corners]
        count += stitch_row(bm, loop + [loop[0]])
    # Rings (cuffs, collar band): stitch 4 mm in from each open edge of the strip.
    for o in [o for o in sc.objects if o.type == "MESH" and ("cuff" in o.name or o.name == "Kieran_collar_back")]:
        b2 = bmesh.new()
        b2.from_mesh(o.data)
        b2.transform(o.matrix_world)
        b2.edges.ensure_lookup_table()
        boundary = [e for e in b2.edges if e.is_boundary]
        seen = set()
        for e0 in boundary:
            if e0.index in seen:
                continue
            # walk the loop
            loop_v = [e0.verts[0]]
            cur_e, cur_v = e0, e0.verts[1]
            seen.add(e0.index)
            while cur_v != loop_v[0] and len(loop_v) < 2000:
                loop_v.append(cur_v)
                nxt = [e for e in cur_v.link_edges if e.is_boundary and e is not cur_e and e.index not in seen]
                if not nxt:
                    break
                cur_e = nxt[0]
                seen.add(cur_e.index)
                cur_v = cur_e.other_vert(cur_v)
            pts = []
            for v in loop_v:
                inner = [e.other_vert(v) for e in v.link_edges if not e.is_boundary]
                d = (inner[0].co - v.co).normalized() if inner else Vector()
                pts.append(v.co + d * 0.004)
            if len(pts) > 3:
                count += stitch_row(bm, pts + [pts[0]])
        b2.free()
    me = bm_to_mesh(bm, "Kieran_stitches_HP")
    cuff = bpy.data.materials.get("M_Kieran_cuff")
    if cuff:
        me.materials.append(cuff)
    add_hp("Kieran_stitches_HP", me)
    print("LS_HIFI stitches: %d" % count, flush=True)


# ------------------------------------------------------------------ high-poly copies of each game part
def hp_copy(o, rig):
    """Called in the game-copy loop after the game part is evaluated and before its modifiers are cleared: makes its
    high-poly twin, subdivided one level more than the game part (at least twice for skin, gloves and boots), with
    the finer creases on the garments."""
    subs = [m for m in o.modifiers if m.type == "SUBSURF"]
    if subs:
        for m in subs:
            m.levels = max(2, m.levels + 1)
            m.render_levels = m.levels
    else:
        m = o.modifiers.new("hp_subsurf", "SUBSURF")
        m.levels = 2 if o.name.startswith(("Kieran.body", "Kieran_gloves", "Kieran_boots", "Kieran_scarf", "Kieran_satchel")) else 1
        m.render_levels = m.levels
        arm = [i for i, x in enumerate(o.modifiers) if x.type == "ARMATURE"]
        if arm:
            o.modifiers.move(len(o.modifiers) - 1, arm[0])
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    fold_mesh(o, me, rig, True)
    me.transform(o.matrix_world)
    hp = add_hp(o.name + "_HP", me)
    return hp


# ------------------------------------------------------------------ texture space for the face and hands
def prioritise_uvs(game, scale_head=2.0, scale_hands=1.45):
    vg = {g.name: g.index for g in game.vertex_groups}
    head_ids = [vg[n] for n in ("head", "neck_01") if n in vg]
    hand_ids = [i for n, i in vg.items() if n.startswith(("hand_", "thumb_", "index_", "middle_", "ring_", "pinky_"))]
    bm = bmesh.from_edit_mesh(game.data)
    uv = bm.loops.layers.uv.active
    dl = bm.verts.layers.deform.active
    if not uv or not dl:
        return
    for ids, s in ((head_ids, scale_head), (hand_ids, scale_hands)):
        faces = [f for f in bm.faces if all(sum(v[dl].get(i, 0.0) for i in ids) > 0.5 for v in f.verts)]
        if not faces:
            continue
        loops = [l for f in faces for l in f.loops]
        c = sum((l[uv].uv for l in loops), Vector((0.0, 0.0))) / len(loops)
        for l in loops:
            l[uv].uv = c + (l[uv].uv - c) * s
        print("LS_HIFI uv priority x%.2f on %d faces" % (s, len(faces)), flush=True)
    bmesh.update_edit_mesh(game.data)


# ------------------------------------------------------------------ bakes
SMOOTH = [("skin", 0.0, 0.38), ("lip", 0.0, 0.45), ("hair", 0.0, 0.1), ("eyebrow", 0.0, 0.15), ("eyelash", 0.0, 0.15),
          ("high-poly", 0.0, 0.62), ("teeth", 0.0, 0.45), ("jacket", 0.0, 0.1), ("shirt", 0.0, 0.08), ("trousers", 0.0, 0.1),
          ("scarf", 0.0, 0.06), ("cuff", 0.0, 0.1), ("gloves", 0.0, 0.3), ("boot", 0.0, 0.28), ("sole", 0.0, 0.18),
          ("belt", 0.0, 0.32), ("satchel", 0.0, 0.3), ("brass", 1.0, 0.5), ("button", 1.0, 0.45), ("steel", 1.0, 0.52),
          ("needle", 0.0, 0.4), ("dial", 0.0, 0.3), ("lens", 0.0, 0.75)]


def _smooth_for(name):
    n = name.lower()
    for k, metal, sm in SMOOTH:
        if k in n:
            return metal, sm
    return 0.0, 0.15


def bake_maps(sc, game, out_dir, size, name="Kieran"):
    """Normal and AO from the high-poly onto the game mesh's atlas UVs, then the metallic/smoothness pass from the
    game mesh's own materials, packed with the AO into one mask."""
    coll = hp_collection()
    sc.collection.children.link(coll)
    hp_objs = list(coll.objects)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    bk = sc.render.bake
    bk.margin = 8
    bk.use_selected_to_active = True
    bk.cage_extrusion = 0.006
    bk.max_ray_distance = 0.016

    def new_img(tag, colour, data=True, alpha=False):
        img = bpy.data.images.new("T_%s_%s" % (name, tag), size, size, alpha=alpha, float_buffer=False)
        img.generated_color = colour
        if data:
            img.colorspace_settings.name = "Non-Color"
        return img

    def target(img):
        for m in game.data.materials:
            if not m or not m.use_nodes:
                continue
            nt = m.node_tree
            n = nt.nodes.get("ls_bake") or nt.nodes.new("ShaderNodeTexImage")
            n.name = "ls_bake"
            n.image = img
            uvn = nt.nodes.get("ls_bake_uv") or nt.nodes.new("ShaderNodeUVMap")
            uvn.name = "ls_bake_uv"
            uvn.uv_map = "atlas"
            nt.links.new(uvn.outputs["UV"], n.inputs["Vector"])
            nt.nodes.active = n

    def select_for_bake():
        for o in sc.objects:
            o.select_set(o in hp_objs or o == game)
        bpy.context.view_layer.objects.active = game

    # 1. normal (tangent space, OpenGL / +Y like Unity)
    nimg = new_img("Normal", (0.5, 0.5, 1.0, 1.0))
    target(nimg)
    select_for_bake()
    sc.cycles.samples = 4
    bk.normal_space = "TANGENT"
    bk.normal_r, bk.normal_g, bk.normal_b = "POS_X", "POS_Y", "POS_Z"
    bpy.ops.object.bake(type="NORMAL", use_selected_to_active=True, cage_extrusion=0.006, max_ray_distance=0.016, margin=8)
    nimg.filepath_raw = os.path.join(out_dir, "T_%s_Normal.png" % name)
    nimg.file_format = "PNG"
    nimg.save()
    print("LS_HIFI baked normal", flush=True)

    # 2a. contact occlusion from the game mesh itself (collar on the neck, hair over the brow, arms by the body):
    #     an ordinary image bake, the high-poly hidden.
    lpimg = new_img("AO_Contact", (1.0, 1.0, 1.0, 1.0))
    target(lpimg)
    for o in hp_objs:
        o.hide_render = True
    for o in sc.objects:
        o.select_set(o == game)
    bpy.context.view_layer.objects.active = game
    if sc.world:
        sc.world.light_settings.distance = 0.06
    sc.cycles.samples = 32
    bpy.ops.object.bake(type="AO", use_selected_to_active=False, margin=8)
    for o in hp_objs:
        o.hide_render = False
    print("LS_HIFI baked contact AO", flush=True)
    # 2b. the curls' own occlusion. The game mesh would shadow the high-poly beneath it, so this is baked on the
    #     high-poly alone (into its vertices, the game mesh hidden), then carried across like the normals. It is kept
    #     for the hair only: on smooth skin and cloth, per-vertex occlusion turned blotchy.
    game.hide_render = True
    for o in sc.objects:
        o.select_set(o in hp_objs)
    bpy.context.view_layer.objects.active = hp_objs[0]
    for o in hp_objs:
        ca = o.data.color_attributes.get("ls_ao") or o.data.color_attributes.new("ls_ao", "FLOAT_COLOR", "POINT")
        o.data.color_attributes.active_color = ca
    if sc.world:
        sc.world.light_settings.distance = 0.05
    sc.cycles.samples = 24
    bk.target = "VERTEX_COLORS"
    bpy.ops.object.bake(type="AO", use_selected_to_active=False, target="VERTEX_COLORS")
    bk.target = "IMAGE_TEXTURES"
    game.hide_render = False
    ao_mat = bpy.data.materials.new("ls_ao_emit")
    ao_mat.use_nodes = True
    nt = ao_mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    vc = nt.nodes.new("ShaderNodeVertexColor"); vc.layer_name = "ls_ao"
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(vc.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    for o in hp_objs:
        o.data.materials.clear()
        o.data.materials.append(ao_mat)
    aimg = new_img("AO", (1.0, 1.0, 1.0, 1.0))
    target(aimg)
    select_for_bake()
    sc.cycles.samples = 1
    bpy.ops.object.bake(type="EMIT", use_selected_to_active=True, cage_extrusion=0.006, max_ray_distance=0.016, margin=8)
    print("LS_HIFI baked AO", flush=True)

    # 3. metallic and smoothness from each material (emission), with a gentle variation so nothing is uniform
    simg = new_img("Smooth", (0.0, 0.0, 0.0, 1.0))
    target(simg)
    saved = {}
    for m in game.data.materials:
        if not m or not m.use_nodes:
            continue
        nt = m.node_tree
        out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" and n.is_active_output), None) or \
            next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if not out:
            continue
        saved[m.name] = [l.from_socket for l in out.inputs["Surface"].links]
        metal, sm = _smooth_for(m.name)
        em = nt.nodes.new("ShaderNodeEmission")
        nz = nt.nodes.new("ShaderNodeTexNoise")
        nz.inputs["Scale"].default_value = 60.0
        tc = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        mr = nt.nodes.new("ShaderNodeMapRange")
        mr.inputs["To Min"].default_value = sm * 0.82
        mr.inputs["To Max"].default_value = sm * 1.12
        nt.links.new(nz.outputs["Fac"], mr.inputs["Value"])
        cmb = nt.nodes.new("ShaderNodeCombineColor")
        cmb.inputs["Red"].default_value = metal
        cmb.inputs["Green"].default_value = 1.0 if "hair_shell" in m.name else 0.0   # where the curls' occlusion applies
        nt.links.new(mr.outputs["Result"], cmb.inputs["Blue"])
        nt.links.new(cmb.outputs["Color"], em.inputs["Color"])
        nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
        m["ls_tmp_emit"] = em.name
    for o in sc.objects:
        o.select_set(o == game)
    bpy.context.view_layer.objects.active = game
    sc.cycles.samples = 1
    bpy.ops.object.bake(type="EMIT", use_selected_to_active=False, margin=8)
    for m in game.data.materials:
        if m and m.name in saved:
            out = next((n for n in m.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
            for l in list(out.inputs["Surface"].links):
                m.node_tree.links.remove(l)
            for s in saved[m.name]:
                m.node_tree.links.new(s, out.inputs["Surface"])
    print("LS_HIFI baked smoothness", flush=True)

    # 4. pack: R metallic, G occlusion, B unused, A smoothness (URP Lit's metallic map + occlusion map)
    ao_hp = np.array(aimg.pixels[:], dtype=np.float32).reshape(-1, 4)
    ao_lp = np.array(lpimg.pixels[:], dtype=np.float32).reshape(-1, 4)
    sp = np.array(simg.pixels[:], dtype=np.float32).reshape(-1, 4)
    hair = sp[:, 1:2]
    ao = ao_lp * (1.0 - hair) + ao_lp * ao_hp * hair
    aimg.pixels[:] = np.concatenate([ao[:, :3], np.ones((ao.shape[0], 1), np.float32)], axis=1).ravel()
    pack = np.zeros_like(ao)
    pack[:, 0] = sp[:, 0]
    pack[:, 1] = np.clip(0.4 + 0.6 * ao[:, 0], 0, 1)       # never fully black: the cavities still take some light
    pack[:, 2] = 0.0
    pack[:, 3] = sp[:, 2]
    mimg = bpy.data.images.new("T_%s_MaskPBR" % name, size, size, alpha=True)
    mimg.colorspace_settings.name = "Non-Color"
    mimg.alpha_mode = "STRAIGHT"
    mimg.pixels[:] = pack.ravel()
    mimg.filepath_raw = os.path.join(out_dir, "T_%s_MetalAOSmooth.png" % name)
    mimg.file_format = "PNG"
    mimg.save()
    aimg.filepath_raw = os.path.join(out_dir, "T_%s_AO.png" % name)
    aimg.file_format = "PNG"
    aimg.save()
    # remove the bake helpers so the export materials are untouched
    for m in game.data.materials:
        if m and m.use_nodes:
            for k in ("ls_bake", "ls_bake_uv"):
                n = m.node_tree.nodes.get(k)
                if n:
                    m.node_tree.nodes.remove(n)
        for n in m.node_tree.nodes if (m and m.use_nodes) else []:
            if n.type == "TEX_IMAGE" and n.image and n.image.name.startswith("T_%s_BaseColor" % name):
                m.node_tree.nodes.active = n
    sc.collection.children.unlink(coll)
    bk.use_selected_to_active = False
    sc.cycles.samples = 4
    for o in sc.objects:
        o.select_set(o == game)
    bpy.context.view_layer.objects.active = game
    print("LS_HIFI maps saved", flush=True)


def fill_empty_weights(game, bone_names):
    """Vertices with no skin weight stay at the bind pose in Unity and stretch into lines as soon as he moves (thin
    trim on the sleeves did this): give each one the weights of its nearest weighted vertex."""
    from mathutils import kdtree
    groups = {g.index: g.name for g in game.vertex_groups}
    me = game.data
    weighted, empty = [], []
    for v in me.vertices:
        w = [(g.group, g.weight) for g in v.groups if groups.get(g.group) in bone_names and g.weight > 0.0]
        (weighted if sum(x[1] for x in w) > 0.01 else empty).append((v.index, w))
    if not empty or not weighted:
        print("LS_HIFI unweighted vertices: %d" % len(empty), flush=True)
        return
    kd = kdtree.KDTree(len(weighted))
    for i, (vi, _) in enumerate(weighted):
        kd.insert(me.vertices[vi].co, i)
    kd.balance()
    for vi, _ in empty:
        _, i, _ = kd.find(me.vertices[vi].co)
        for gi, wt in weighted[i][1]:
            game.vertex_groups[gi].add([vi], wt, "REPLACE")
    print("LS_HIFI unweighted vertices fixed: %d" % len(empty), flush=True)


def thin_strands(o, keep):
    """Removes all but an even fraction of an object's loose parts (eyelash strands)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.verts.ensure_lookup_table()
    seen, parts = set(), []
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], []
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y.index not in seen:
                    seen.add(y.index)
                    stack.append(y)
        parts.append(comp)
    drop = [v for i, comp in enumerate(parts) if (i * keep) % 1.0 >= keep for v in comp]
    bmesh.ops.delete(bm, geom=drop, context="VERTS")
    bm.to_mesh(o.data)
    bm.free()
    o.data.calc_loop_triangles()
    print("LS_HIFI %s: kept %d of %d strands, %d tris" % (o.name, len(parts) - int(round(len(parts) * (1 - keep))), len(parts), len(o.data.loop_triangles)), flush=True)


def hair_uvs(game):
    """The hair shell's remeshed surface would shatter into thousands of tiny islands under smart projection: give it
    one spherical projection round the head instead (split only at the back), at the same texel density as the rest."""
    mi = next((i for i, m in enumerate(game.data.materials) if m and m.name == "M_Kieran_hair_shell"), None)
    bm = bmesh.from_edit_mesh(game.data)
    uv = bm.loops.layers.uv.active
    faces = [f for f in bm.faces if f.material_index == mi]
    if mi is None or not uv or not faces:
        return
    centre = sum((v.co for f in faces for v in f.verts), Vector()) / sum(len(f.verts) for f in faces)
    old_area = sum(abs(_uv_area(f, uv)) for f in faces)
    for f in faces:
        us = []
        for l in f.loops:
            d = (l.vert.co - centre).normalized()
            u = 0.5 + math.atan2(d.x, -d.y) / (2 * math.pi)
            v = 0.5 + math.asin(max(-1.0, min(1.0, d.z))) / math.pi
            us.append([u, v])
        umin = min(x[0] for x in us)
        for x in us:
            if x[0] - umin > 0.5:
                x[0] -= 1.0
        for l, x in zip(f.loops, us):
            l[uv].uv = Vector(x)
    new_area = sum(abs(_uv_area(f, uv)) for f in faces)
    k = math.sqrt(old_area / max(new_area, 1e-12))
    for f in faces:
        for l in f.loops:
            l[uv].uv = l[uv].uv * k
    bmesh.update_edit_mesh(game.data)
    print("LS_HIFI hair uv: %d faces, one projection" % len(faces), flush=True)


def _uv_area(f, uv):
    pts = [l[uv].uv for l in f.loops]
    return 0.5 * sum(pts[i].x * pts[(i + 1) % len(pts)].y - pts[(i + 1) % len(pts)].x * pts[i].y for i in range(len(pts)))


def make_lods(game, rig, ratios=(0.5, 0.22)):
    """LOD1 and LOD2: decimated copies sharing the atlas and maps, skinned to the same rig."""
    game.name = "Kieran_GameReady_LOD0"
    lods = [game]
    for i, r in enumerate(ratios, 1):
        o = game.copy()
        o.data = game.data.copy()
        o.name = "Kieran_GameReady_LOD%d" % i
        game.users_collection[0].objects.link(o)
        for m in [m for m in o.modifiers if m.type == "ARMATURE"]:
            m.show_viewport = False
        d = o.modifiers.new("lod", "DECIMATE")
        d.ratio = r
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="lod")
        for m in [m for m in o.modifiers if m.type == "ARMATURE"]:
            m.show_viewport = True
        o.data.calc_loop_triangles()
        print("LS_HIFI LOD%d %d tris" % (i, len(o.data.loop_triangles)), flush=True)
        lods.append(o)
    return lods


def fix_mpfb_paths():
    """The master's MPFB textures use paths relative to the machine they were made on; point them at the installed add-on."""
    roots = [os.path.join(os.environ.get("APPDATA", ""), "Blender Foundation", "Blender", "5.2", "extensions", d, "blender_org", "mpfb", "data")
             for d in (".user", "")]
    for img in bpy.data.images:
        if not img.filepath or os.path.exists(bpy.path.abspath(img.filepath)):
            continue
        tail = img.filepath.replace("\\", "/").split("/mpfb/data/")[-1]
        for r in roots:
            p = os.path.join(r, *tail.split("/"))
            if os.path.exists(p):
                img.filepath = p
                img.reload()
                print("LS_HIFI relinked", img.name, flush=True)
                break
