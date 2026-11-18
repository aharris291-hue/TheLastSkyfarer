"""Kieran fidelity pass 2: scripted sculpting of the face and hands, applied in world space to a subdivided head.

Every form is a displacement along the surface normal, defined from landmarks measured on Kieran's own master (the
eyes, the teeth, the nose tip, the mouth line, the ears, the finger bones), so the same field shapes the game mesh
(the larger forms) and the high-poly (all of it, baked into the normal map). Nothing is imported or downloaded.

  * eyes: a thickened margin on both lids, the upper-lid crease and a soft lower-lid swell;
  * nose: a defined bridge, the alar wings and the groove round them, and nostril openings underneath;
  * mouth: the vermilion border as a fine raised edge (with a cupid's bow), the philtrum columns, the lip line and
    the corners pressed in;
  * cheekbones and the jaw line; the ears' helix and antihelix by sharpening their existing forms;
  * hands: knuckles over each finger joint, finger pads, and nail plates (the nails are separate geometry).
"""
import math

import bmesh
import bpy
from mathutils import Vector, kdtree


def g(x, s):
    return math.exp(-0.5 * (x / s) ** 2)


# ------------------------------------------------------------------ landmarks
def landmarks():
    dg = bpy.context.evaluated_depsgraph_get()

    def wverts(name):
        o = bpy.data.objects[name]
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        pts = [o.matrix_world @ v.co for v in me.vertices]
        ev.to_mesh_clear()
        return pts

    L = {}
    eyes = wverts("Kieran.high-poly")
    L["eyes"] = []
    for side in (1, -1):
        p = [q for q in eyes if q.x * side > 0]
        c = sum(p, Vector()) / len(p)
        front = min(q.y for q in p)
        L["eyes"].append(Vector((c.x, front + 0.0125, c.z)))      # eyeball centre (12.5 mm radius)
    L["eye_r"] = 0.0125
    body = wverts("Kieran.body")
    head = [q for q in body if q.z > 1.45]
    L["tip"] = min((q for q in head if abs(q.x) < 0.01 and 1.55 < q.z < 1.68), key=lambda q: q.y)
    teeth = wverts("Kieran.teeth_base")
    tz0, tz1 = min(q.z for q in teeth), max(q.z for q in teeth)
    # mouth line: on the centre-line profile between the nose and the chin, the deepest point between the two lips
    prof = {}
    for q in head:
        if abs(q.x) < 0.004 and tz0 - 0.01 < q.z < L["tip"].z - 0.012:
            k = int(q.z / 0.001)
            prof[k] = min(prof.get(k, 1.0), q.y)
    ks = sorted(prof)
    upper = min((k for k in ks if k * 0.001 > (tz0 + tz1) / 2 - 0.004), key=lambda k: prof[k])
    lower = min((k for k in ks if k * 0.001 < upper * 0.001 - 0.006), key=lambda k: prof[k])
    L["mouth_z"] = (upper + lower) * 0.0005 + 0.0005   # the closed lips meet a little above halfway
    L["upper_lip"] = Vector((0.0, prof[upper], upper * 0.001))
    L["lower_lip"] = Vector((0.0, prof[lower], lower * 0.001))
    L["mouth_w"] = max(q.x for q in teeth) * 0.95
    L["ears"] = []
    for side in (1, -1):
        e = max((q for q in head if 1.54 < q.z < 1.67), key=lambda q: q.x * side)
        L["ears"].append(e)
    L["head_c"] = Vector((0.0, -0.06, 1.62))
    print("LS_FACE landmarks: tip %s, mouth z %.4f (upper lip %.4f, lower %.4f), eyes %s"
          % (tuple(round(x, 4) for x in L["tip"]), L["mouth_z"], L["upper_lip"].z, L["lower_lip"].z,
             [tuple(round(x, 4) for x in e) for e in L["eyes"]]), flush=True)
    return L


# ------------------------------------------------------------------ the face field
def face_disp(p, n, L, fine):
    """Displacement (metres, along the normal) at world point p with normal n. fine=False: the forms the game mesh can
    carry; fine=True: everything (the high-poly)."""
    d = 0.0
    if p.z < 1.45 or p.y > -0.03:
        return 0.0
    k = 1.0 if fine else 0.6
    # eyes
    R = L["eye_r"]
    for c in L["eyes"]:
        v = p - c
        r = v.length
        if r > 0.04 or v.y > 0.006:
            continue
        up = v.z
        d += 0.00065 * g(r - (R + 0.0014), 0.0008 if fine else 0.0014) * k                  # lid margins: thickness
        if up > 0.003:
            d -= 0.0008 * g(r - (R + 0.0078), 0.0013) * min(1.0, (up - 0.003) / 0.004)     # upper-lid crease
            d += 0.0004 * g(r - (R + 0.0045), 0.0016) * min(1.0, (up - 0.003) / 0.004)     # the lid above the crease
        if up < -0.003:
            d += 0.0003 * g(r - (R + 0.0035), 0.0013) * min(1.0, (-up - 0.003) / 0.004)   # lower lid (kept young)
        # inner corner (towards the nose): a small caruncle dip
        inner = Vector((c.x - math.copysign(R * 0.95, c.x), c.y - 0.004, c.z - 0.001))
        d -= 0.0006 * g((p - inner).length, 0.0018) * k
    # nose
    T = L["tip"]
    if (p - T).length < 0.05:
        for sx in (1, -1):
            W = T + Vector((sx * 0.0125, 0.011, -0.005))
            rw = (p - W).length
            d += 0.0009 * g(rw, 0.0048)                                                     # alar wing
            if p.z > W.z - 0.003:
                d -= 0.0007 * g(rw - 0.0078, 0.0011 if fine else 0.0018)                    # alar groove
            N = T + Vector((sx * 0.0062, 0.009, -0.0085))
            if n.z < -0.35 and (p - T).length < 0.02:
                d -= 0.0013 * g((p - N).length, 0.0032) * (1.0 if fine else 0.7)            # nostril
        if abs(p.x) < 0.012 and T.z + 0.006 < p.z < L["eyes"][0].z - 0.004:
            d += 0.0004 * g(p.x, 0.0035)                                                    # bridge
        d += 0.0003 * g((p - (T + Vector((0, -0.001, 0.002)))).length, 0.004)               # tip
    # mouth
    z0 = L["mouth_z"]
    w = L["mouth_w"]
    if abs(p.x) < w + 0.012 and z0 - 0.02 < p.z < T.z - 0.006 and p.y < L["upper_lip"].y + 0.022:
        t = min(1.0, abs(p.x) / w)
        bow = -0.0011 * g(p.x, 0.0028) + 0.0005 * g(abs(p.x) - 0.0042, 0.0018)
        z_up = z0 + (0.0072 + bow) * (1 - t * t) ** 0.8
        z_lo = z0 - 0.0085 * (1 - t * t) ** 0.6
        inside = abs(p.x) < w
        if inside:
            d += 0.00042 * g(p.z - z_up, 0.0006 if fine else 0.0011) * k                    # upper vermilion border
            d += 0.00032 * g(p.z - z_lo, 0.0007 if fine else 0.0012) * k                    # lower vermilion border
            d -= 0.0007 * g(p.z - z0, 0.0006 if fine else 0.001) * (1 - t ** 4)            # the lip line
            d += 0.0003 * g(p.z - (z0 + 0.0035 * (1 - t * t)), 0.002) * (1 - t)            # upper lip fullness
            d += 0.0004 * g(p.z - (z0 - 0.0045 * (1 - t * t)), 0.0022) * (1 - t)            # lower lip fullness
        if z_up < p.z < T.z - 0.008:
            d += 0.00035 * g(abs(p.x) - 0.0045, 0.0013) * k                                 # philtrum columns
            d -= 0.00025 * g(p.x, 0.0018) * k                                               # philtrum groove
        for sx in (1, -1):
            C = Vector((sx * w, L["upper_lip"].y + 0.009, z0))
            d -= 0.0012 * g((p - C).length, 0.0022)                                         # corners
        if p.z < z_lo - 0.003 and abs(p.x) < 0.012:
            d -= 0.0005 * g(p.z - (z_lo - 0.0065), 0.002)                                   # mentolabial fold
    # cheekbones
    for sx in (1, -1):
        a = Vector((sx * 0.032, -0.128, 1.588))
        b = Vector((sx * 0.062, -0.085, 1.592))
        ab = b - a
        t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
        d += 0.0009 * g((p - (a + ab * t)).length, 0.009) * (0.5 + 0.5 * t) * max(0.0, -n.y + 0.3)
    return d


def sharpen(bm, mask_fn, amount, iters=3):
    """Unsharp mask on the surface: each vertex moves along its normal by `amount` times its offset from a smoothed
    copy, where mask_fn(p) > 0 (deepens the forms already there: ear folds, jaw line)."""
    pos = {v: v.co.copy() for v in bm.verts}
    sm = dict(pos)
    for _ in range(iters):
        nxt = {}
        for v in bm.verts:
            nb = [e.other_vert(v) for e in v.link_edges]
            nxt[v] = sum((sm[x] for x in nb), Vector()) / len(nb) if nb else sm[v]
        sm = nxt
    for v in bm.verts:
        m = mask_fn(pos[v])
        if m > 0:
            v.co = pos[v] + v.normal * (pos[v] - sm[v]).dot(v.normal) * amount * m


def sculpt_face(bm, L, fine):
    """Applies the face field and the sharpening to a world-space bmesh of the body (or its high-poly twin)."""
    bm.normal_update()
    moves = []
    for v in bm.verts:
        dd = face_disp(v.co, v.normal, L, fine)
        if dd:
            moves.append((v, v.normal * dd))
    for v, m in moves:
        v.co += m
    bm.normal_update()
    ears = L["ears"]

    def ear_mask(p):
        return max(g((p - e).length, 0.022) for e in ears) if abs(p.x) > 0.06 else 0.0

    def face_mask(p):
        if p.z < 1.48 or p.y > -0.06:
            return 0.0
        return g((p - Vector((0, -0.15, 1.57))).length, 0.06)

    sharpen(bm, ear_mask, 1.6 if fine else 0.7)
    if fine:
        sharpen(bm, face_mask, 0.5, iters=2)
    bm.normal_update()


# ------------------------------------------------------------------ hands
FINGERS = ("index", "middle", "ring", "pinky")


def hand_frames(rig):
    """Per side: the joints of each finger and the back-of-hand direction (away from the palm)."""
    out = {}
    mw = rig.matrix_world
    for s in ("l", "r"):
        B = rig.data.bones
        hand = B["hand_" + s]
        h = mw @ hand.head_local
        mid = mw @ B["middle_01_" + s].head_local
        idx = mw @ B["index_01_" + s].head_local
        pk = mw @ B["pinky_01_" + s].head_local
        thumb = mw @ B["thumb_01_" + s].head_local
        across = (idx - pk).normalized()
        along = (mid - h).normalized()
        back = along.cross(across).normalized()
        # The thumb's root sits towards the palm of the knuckle line; measured on Kieran's rig (rendered both ways),
        # the back of the hand is the side the thumb root is on relative to this cross product, so flip to match.
        if (thumb - (idx + pk) / 2).dot(back) < 0:
            back = -back
        joints = []
        for f in FINGERS + ("thumb",):
            for i in (1, 2, 3):
                b = B["%s_0%d_%s" % (f, i, s)]
                joints.append((f, i, mw @ b.head_local, mw @ b.tail_local))
        out[s] = {"back": back, "joints": joints, "along": along}
    return out


def hand_disp(p, n, frames, fine):
    d = 0.0
    for s, F in frames.items():
        back = F["back"]
        for f, i, head, tail in F["joints"]:
            if (p - head).length > 0.03:
                continue
            nb = n.dot(back)
            # knuckles: a rounded rise over each joint on the back of the hand
            size = 0.0017 if i == 1 else 0.0011
            d += size * g((p - head).length, 0.005 if i == 1 else 0.0038) * max(0.0, nb) ** 0.5
            # finger pads: fuller on the palm side of the last segment
            if i == 3:
                mid = head + (tail - head) * 0.55
                d += 0.0007 * g((p - mid).length, 0.005) * max(0.0, -nb)
                # skin creases at the joints on the palm side
            if fine:
                d -= 0.00035 * g((p - head).length, 0.0016) * max(0.0, -nb) * (1.0 if i > 1 else 0.6)
    return d


def sculpt_hands(bm, rig, fine):
    F = hand_frames(rig)
    bm.normal_update()
    moves = []
    for v in bm.verts:
        dd = hand_disp(v.co, v.normal, F, fine)
        if dd:
            moves.append((v, v.normal * dd))
    for v, m in moves:
        v.co += m
    bm.normal_update()


def build_nails(body_bm, rig, material=None):
    """Nail plates: a thin, slightly domed plate on the back of each fingertip, shaped onto the skin."""
    F = hand_frames(rig)
    kd = kdtree.KDTree(len(body_bm.verts))
    for v in body_bm.verts:
        kd.insert(v.co, v.index)
    kd.balance()
    body_bm.verts.ensure_lookup_table()
    out = bmesh.new()
    made = 0
    for s, fr in F.items():
        back = fr["back"]
        for f, i, head, tail in fr["joints"]:
            if i != 3:
                continue
            axis = (tail - head)
            L = axis.length
            axis.normalize()
            side = axis.cross(back).normalized()
            width = 0.0082 if f != "pinky" else 0.0068
            if f == "thumb":
                width = 0.0095
            length = min(0.011, L * 0.6)
            start = head + axis * (L - length * 1.0)
            rows, cols = 4, 5
            grid = []
            for a in range(rows + 1):
                row = []
                for b in range(cols + 1):
                    u = a / rows
                    vv = b / cols - 0.5
                    q = start + axis * (u * length) + side * (vv * width)
                    # find the skin above this point on the back of the finger
                    best = None
                    for (co, idx, dist) in kd.find_n(q + back * 0.006, 6):
                        vtx = body_bm.verts[idx]
                        if vtx.normal.dot(back) > 0.2 and (best is None or dist < best[1]):
                            best = (vtx, dist)
                    if best is None:
                        base = q + back * 0.004
                    else:
                        base = best[0].co
                    dome = 0.00045 * (1 - (2 * vv) ** 2)
                    row.append(out.verts.new(base + back * (0.0003 + dome)))
                grid.append(row)
            for a in range(rows):
                for b in range(cols):
                    out.faces.new((grid[a][b], grid[a][b + 1], grid[a + 1][b + 1], grid[a + 1][b]))
            made += 1
    bmesh.ops.solidify(out, geom=out.faces[:], thickness=0.0004)
    me = bpy.data.meshes.new("Kieran_nails")
    out.to_mesh(me)
    out.free()
    for poly in me.polygons:
        poly.use_smooth = True
    if material:
        me.materials.append(material)
    print("LS_FACE nails: %d" % made, flush=True)
    return me
