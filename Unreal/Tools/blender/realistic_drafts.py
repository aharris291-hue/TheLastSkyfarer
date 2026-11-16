"""Realistic design drafts (Cycles): real materials, fur and lighting, rendered to turnaround sheets for Adam's approval.

Props reuse the shapes from character_drafts.py with physically based wood, brass, sailcloth and leather; Piko is
rebuilt as one organic furred body following Adam's turnaround. Nothing goes into the game until Adam approves.

  blender --background --factory-startup --python realistic_drafts.py -- <output folder> [piko glider compass]
"""
import math
import os
import random
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import character_drafts as cd  # noqa: E402

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [os.getcwd()]
OUT = ARGS[0]
WHICH = ARGS[1:] or ["piko", "glider", "compass"]
SAMPLES = int(os.environ.get("LS_SAMPLES", "128"))
if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
cd.OUT = OUT

hexrgb = cd.hexrgb
KIND = {}          # hex colour -> material kind, set per subject
PRE_RENDER = []    # extra detail added just before a sheet renders


# ------------------------------------------------------------------ materials
def node_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    return m, nt, nt.nodes.get("Material Output")


def principled(nt, col, rough=0.6, metal=0.0):
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = col
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return b


def noise(nt, scale, detail=6.0, rough=0.6):
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    return n


def bump(nt, height_socket, strength, distance=0.01):
    b = nt.nodes.new("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = distance
    nt.links.new(height_socket, b.inputs["Height"])
    return b


def ramp_between(nt, fac_socket, c1, c2, p1=0.3, p2=0.7):
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = p1
    r.color_ramp.elements[0].color = c1
    r.color_ramp.elements[1].position = p2
    r.color_ramp.elements[1].color = c2
    nt.links.new(fac_socket, r.inputs["Fac"])
    return r


def darker(c, k):
    return (c[0] * k, c[1] * k, c[2] * k, 1.0)


def real_mat(hexcol):
    kind = KIND.get(hexcol, "plain")
    name = "R_%s_%s" % (kind, hexcol)
    m = bpy.data.materials.get(name)
    if m:
        return m
    col = hexrgb(hexcol)
    m, nt, out = node_mat(name)
    L = nt.links
    if kind == "wood":
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1.0, 1.0, 14.0)
        L.new(tc.outputs["Object"], mp.inputs["Vector"])
        w = nt.nodes.new("ShaderNodeTexWave")
        w.wave_type = "RINGS"
        w.inputs["Scale"].default_value = 6.0
        w.inputs["Distortion"].default_value = 7.0
        w.inputs["Detail"].default_value = 4.0
        L.new(mp.outputs["Vector"], w.inputs["Vector"])
        r = ramp_between(nt, w.outputs["Fac"], darker(col, 0.62), col, 0.2, 0.8)
        b = principled(nt, col, 0.55)
        L.new(r.outputs["Color"], b.inputs["Base Color"])
        L.new(bump(nt, w.outputs["Fac"], 0.15).outputs["Normal"], b.inputs["Normal"])
        b.inputs["Coat Weight"].default_value = 0.15
    elif kind in ("brass", "steel"):
        n = noise(nt, 40.0, 8.0, 0.7)
        ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
        ao.inputs["Distance"].default_value = 0.05
        mix = nt.nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[6].default_value = darker(col, 0.35)     # tarnish in crevices
        mix.inputs[7].default_value = col
        L.new(ao.outputs["AO"], mix.inputs[0])
        rr = ramp_between(nt, n.outputs["Fac"], (0.22, 0.22, 0.22, 1), (0.45, 0.45, 0.45, 1))
        b = principled(nt, col, 0.3, 1.0)
        L.new(mix.outputs[2], b.inputs["Base Color"])
        L.new(rr.outputs["Color"], b.inputs["Roughness"])
        L.new(bump(nt, n.outputs["Fac"], 0.04).outputs["Normal"], b.inputs["Normal"])
    elif kind in ("cloth", "linen", "wool", "cloth_heavy"):
        tc = nt.nodes.new("ShaderNodeTexCoord")
        weave = nt.nodes.new("ShaderNodeTexBrick")
        weave.inputs["Scale"].default_value = {"wool": 90.0, "cloth_heavy": 150.0}.get(kind, 260.0)
        weave.inputs["Mortar Size"].default_value = 0.08
        L.new(tc.outputs["Object"], weave.inputs["Vector"])
        n = noise(nt, 6.0, 4.0)
        r = ramp_between(nt, n.outputs["Fac"], darker(col, 0.86), col)
        b = principled(nt, col, 0.85)
        b.inputs["Sheen Weight"].default_value = 0.6 if kind == "wool" else 0.3
        L.new(r.outputs["Color"], b.inputs["Base Color"])
        L.new(bump(nt, weave.outputs["Fac"], 0.08).outputs["Normal"], b.inputs["Normal"])
        if kind == "cloth":   # sailcloth lets light through
            t = nt.nodes.new("ShaderNodeBsdfTranslucent")
            t.inputs["Color"].default_value = col
            mx = nt.nodes.new("ShaderNodeMixShader")
            mx.inputs[0].default_value = 0.3
            L.new(b.outputs["BSDF"], mx.inputs[1])
            L.new(t.outputs["BSDF"], mx.inputs[2])
            L.new(mx.outputs["Shader"], out.inputs["Surface"])
            return m
    elif kind == "leather":
        v = nt.nodes.new("ShaderNodeTexVoronoi")
        v.inputs["Scale"].default_value = 180.0
        n = noise(nt, 8.0)
        r = ramp_between(nt, n.outputs["Fac"], darker(col, 0.7), col)
        b = principled(nt, col, 0.5)
        L.new(r.outputs["Color"], b.inputs["Base Color"])
        L.new(bump(nt, v.outputs["Distance"], 0.12).outputs["Normal"], b.inputs["Normal"])
    elif kind == "glow":
        b = principled(nt, col, 0.3)
        b.inputs["Emission Color"].default_value = col
        b.inputs["Emission Strength"].default_value = 3.0
    elif kind == "paint":     # faded route markings
        b = principled(nt, col, 0.8)
        b.inputs["Alpha"].default_value = 0.65
    elif kind == "glass":
        b = principled(nt, col, 0.05)
        b.inputs["Transmission Weight"].default_value = 1.0
        b.inputs["Roughness"].default_value = 0.0
    else:
        n = noise(nt, 12.0)
        b = principled(nt, col, 0.6)
        L.new(bump(nt, n.outputs["Fac"], 0.05).outputs["Normal"], b.inputs["Normal"])
    L.new(b.outputs["BSDF"], out.inputs["Surface"])
    return m


cd.mat = real_mat   # the shape builders in character_drafts now get real materials


# ------------------------------------------------------------------ studio turnaround in Cycles
def light(name, loc, size, energy, col=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.size = size
    ld.energy = energy
    ld.color = col
    o = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    d = -np.array(loc)
    o.rotation_euler = (math.atan2(math.hypot(d[0], d[1]), -d[2]), 0, math.atan2(d[1], d[0]) + math.pi / 2)
    return o


def render_sheet_real(name, height, palette, cam_dist=None, target_z=None, width=None, views_def=cd.VIEWS):
    for fn in PRE_RENDER:
        fn()
    PRE_RENDER.clear()
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 16
    sc.cycles.diffuse_bounces = 8
    sc.cycles.transmission_bounces = 16
    sc.cycles.transparent_max_bounces = 32
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    sc.render.resolution_x, sc.render.resolution_y = 640, 900
    w = sc.world or bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.85, 0.82, 0.76, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    root = bpy.data.objects.new("root", None)
    sc.collection.objects.link(root)
    for o in list(sc.objects):
        if o != root and o.parent is None and o.type in ("MESH", "CURVE", "CURVES", "META"):
            o.parent = root
    s = max(height, width or 0)
    tz = target_z if target_z is not None else height * 0.5
    light("key", (-1.6 * s, -2.2 * s, tz + 1.6 * s), s * 1.2, 800 * s * s, (1.0, 0.95, 0.88))
    light("fill", (2.2 * s, -1.6 * s, tz + 0.4 * s), s * 1.6, 300 * s * s, (0.85, 0.9, 1.0))
    light("rim", (0.6 * s, 2.4 * s, tz + 1.8 * s), s * 0.8, 600 * s * s)
    bpy.ops.mesh.primitive_plane_add(size=s * 8, location=(0, 0, (target_z - height * 0.5) if target_z is not None else 0))
    floor = bpy.context.active_object
    floor.is_shadow_catcher = True
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = max(height, (width or 0) * 900 / 640) * 1.15
    dist = cam_dist or s * 4
    sc.camera = cam
    bg = np.array(cd.srgb("#EFE6D2"))
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
        a = px[:, :, 3:4]
        px[:, :, :3] = px[:, :, :3] * a + bg * (1 - a)     # composite over parchment, keeping the soft floor shadow
        px[:, :, 3] = 1.0
        views.append(px)
        bpy.data.images.remove(img)
        os.remove(path)
        print("LS_VIEW %s %s" % (name, label), flush=True)
    sheet = np.concatenate(views, axis=1)
    strip = np.ones((140, sheet.shape[1], 4))
    strip[:, :, :3] = np.array(cd.srgb("#E6DAC0"))
    for i, h in enumerate(palette):
        x0 = 40 + i * 150
        strip[30:110, x0:x0 + 110, :3] = np.array(cd.srgb(h))
    sheet = np.concatenate([strip, sheet], axis=0)
    outimg = bpy.data.images.new(name, sheet.shape[1], sheet.shape[0], alpha=True)
    outimg.pixels.foreach_set(sheet.astype(np.float32).ravel())
    outimg.filepath_raw = os.path.join(OUT, name + "_turnaround.png")
    outimg.file_format = "PNG"
    outimg.save()
    print("LS_SHEET " + outimg.filepath_raw, flush=True)


cd.render_sheet = render_sheet_real


# ------------------------------------------------------------------ props: same shapes, real materials
def glider():
    KIND.clear()
    KIND.update({"#D2B48A": "wood", "#A9D8F2": "cloth", "#B8893A": "brass", "#6E9FC0": "paint", "#7A6248": "leather"})
    cd.glider()


def compass():
    KIND.clear()
    KIND.update({"#C79A3B": "brass", "#8A6A2A": "brass", "#9A7430": "brass", "#EFE6CF": "linen",
                 "#7FD3FF": "glow", "#7A4E2E": "leather", "#DDE8EC": "glass", "#3A2A1E": "plain"})

    def detail():
        # glass over the dial, degree ticks and N/E/S/W marks, stitching on the strap
        cd.sph((0, -0.1, 0), (0.44, 0.06, 0.44), "#DDE8EC")
        for k in range(72):
            a = k * math.pi / 36
            L = 0.05 if k % 9 == 0 else 0.025
            r0 = 0.41
            cd.limb((r0 * math.sin(a), -0.097, r0 * math.cos(a)), ((r0 - L) * math.sin(a), -0.097, (r0 - L) * math.cos(a)),
                    0.004, 0.004, "#3A2A1E")
        for k in range(8):
            cd.sph((0, -0.012, -0.66 - k * 0.042), (0.004, 0.003, 0.012), "#E6DCC6")
    PRE_RENDER.append(detail)
    cd.compass()


# ------------------------------------------------------------------ Piko: one furred body, glossy eyes, spirit tail
def hair_mat(name, col, tip=None, melanin=None):
    m, nt, out = node_mat(name)
    h = principled(nt, col, 0.55)          # bright, soft fur; the hair BSDF came out too dark for white fur
    h.inputs["Sheen Weight"].default_value = 0.3     # (subsurface on thin strands turned the white fur grey)
    if tip:   # blend toward tip colour along the strand
        info = nt.nodes.new("ShaderNodeHairInfo")
        r = ramp_between(nt, info.outputs["Intercept"], col, tip, 0.55, 0.95)
        nt.links.new(r.outputs["Color"], h.inputs["Base Color"])
    t = nt.nodes.new("ShaderNodeBsdfTranslucent")
    t.inputs["Color"].default_value = col
    mx = nt.nodes.new("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.6
    nt.links.new(h.outputs["BSDF"], mx.inputs[1])
    nt.links.new(t.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    return m


def add_fur(obj, mat, count, length, children=40, clump=0.3, rough=0.02, root=1.0, tip=0.0, short_fn=None):
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("fur", "PARTICLE_SYSTEM")
    if short_fn:   # per-vertex fur length: short fur where short_fn says so (face, paws)
        vg = obj.vertex_groups.new(name="fur_length")
        for v in obj.data.vertices:
            vg.add([v.index], float(short_fn(v.co)), "REPLACE")
        mod.particle_system.vertex_group_length = "fur_length"
        mod.particle_system.vertex_group_density = "fur_length"
    ps = mod.particle_system.settings
    ps.type = "HAIR"
    ps.use_advanced_hair = True
    ps.count = count
    ps.hair_length = length
    ps.hair_step = 5
    ps.child_type = "INTERPOLATED"
    ps.child_percent = 6
    ps.rendered_child_count = children
    ps.child_length = 1.0
    ps.clump_factor = clump
    ps.roughness_2 = rough
    ps.roughness_endpoint = rough * 0.5
    ps.kink = "NO"
    ps.material_slot = mat.name
    ps.root_radius = root
    ps.tip_radius = tip
    ps.radius_scale = 0.0012
    ps.use_close_tip = True
    ps.normal_factor = length      # advanced hair takes its length from the emit speed
    ps.object_align_factor = (0.0, 0.0, -length * 0.7)   # fur lies down and flows downward instead of standing on end
    ps.factor_random = length * 0.15
    ps.use_rotations = True
    ps.phase_factor_random = 0.4
    return ps


def metaball_body(elements, res=0.012):
    mb = bpy.data.metaballs.new("body")
    mb.resolution = res
    mb.render_resolution = res
    o = bpy.data.objects.new("body", mb)
    bpy.context.scene.collection.objects.link(o)
    for kind, loc, radius, size in elements:
        e = mb.elements.new()
        e.type = kind
        e.co = loc
        e.radius = radius
        if kind == "ELLIPSOID":
            e.size_x, e.size_y, e.size_z = size
        e.stiffness = 2.0
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.context.view_layer.update()
    bpy.ops.object.convert(target="MESH")
    return bpy.context.active_object


def piko():
    cd.reset()
    FUR, BLUE, AMBER, MARK = "#FFFFFF", "#87C7FF", "#F4BC42", "#ADEFFF"
    skin, nt, out = node_mat("piko_skin")
    b = principled(nt, hexrgb("#E9E2DA"), 0.6)
    b.inputs["Subsurface Weight"].default_value = 0.3
    nt.links.new(b.outputs["BSDF"], out.inputs["Surface"])
    body = metaball_body([
        ("ELLIPSOID", (0, 0, 0.17), 0.1, (0.85, 0.75, 1.15)),        # body
        ("ELLIPSOID", (0, -0.01, 0.37), 0.1, (1.0, 0.9, 0.9)),       # head
        ("ELLIPSOID", (0, -0.075, 0.35), 0.04, (1.0, 0.7, 0.7)),     # muzzle
        ("ELLIPSOID", (-0.055, -0.05, 0.34), 0.035, (1.0, 0.8, 0.8)),  # cheeks
        ("ELLIPSOID", (0.055, -0.05, 0.34), 0.035, (1.0, 0.8, 0.8)),
        ("ELLIPSOID", (-0.045, -0.025, 0.04), 0.035, (0.9, 1.3, 0.8)),  # feet
        ("ELLIPSOID", (0.045, -0.025, 0.04), 0.035, (0.9, 1.3, 0.8)),
        ("ELLIPSOID", (-0.085, -0.03, 0.2), 0.03, (0.6, 0.8, 1.6)),   # arms
        ("ELLIPSOID", (0.085, -0.03, 0.2), 0.03, (0.6, 0.8, 1.6)),
        ("ELLIPSOID", (-0.09, 0.0, 0.15), 0.045, (0.35, 0.9, 1.4)),   # gliding flaps
        ("ELLIPSOID", (0.09, 0.0, 0.15), 0.045, (0.35, 0.9, 1.4)),
    ])
    body.data.materials.append(skin)
    for p in body.data.polygons:
        p.use_smooth = True
    def face_short(co):
        # short velvety fur on the face and round the eyes, full fluff elsewhere
        d = math.hypot(co.x / 0.09, (co.z - 0.37) / 0.08)
        if co.y < -0.04 and d < 1.0:
            return 0.15 + 0.85 * d ** 3
        if co.z < 0.06:
            return 0.25      # short fur on the soles so Piko stands on the floor
        return 1.0
    add_fur(body, hair_mat("piko_fur", hexrgb(FUR), tip=hexrgb("#FFFFFF")), 9000, 0.016, children=50, clump=0.55, rough=0.002,
            short_fn=face_short)
    # Ears: long and feather-like, short fur fading to blue tips
    for s in (-1, 1):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=1, location=(s * 0.06, 0.0, 0.53), rotation=(0, s * 0.25, 0))
        e = bpy.context.active_object
        e.scale = (0.035, 0.012, 0.13)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        e.data.materials.append(skin)
        for p in e.data.polygons:
            p.use_smooth = True
        add_fur(e, hair_mat("piko_ear%d" % s, hexrgb(FUR)), 1500, 0.008, children=30, clump=0.5, rough=0.001)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=10, radius=1, location=(s * 0.083, 0.0, 0.62), rotation=(0, s * 0.25, 0))
        tipm = bpy.context.active_object
        tipm.scale = (0.027, 0.013, 0.05)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        tipm.data.materials.append(skin)
        add_fur(tipm, hair_mat("piko_tip%d" % s, hexrgb("#9CCFFF")), 500, 0.008, children=30, clump=0.5, rough=0.001)   # blue ear tips
        cd.sph((s * 0.058, -0.011, 0.52), (0.022, 0.004, 0.095), "#EBC9BE", rot=(0, s * 0.25, 0))   # inner ear
    # Eyes: sclera, amber iris, pupil, catchlight under a clear glossy cornea
    KIND.update({"#2A1608": "plain", "#F4BC42": "plain", "#FFFFFF": "glass", "#F2EEE6": "plain"})
    for s_ in (-1, 1):
        x, y, z = s_ * 0.042, -0.095, 0.4
        cd.sph((x, y, z), (0.03, 0.02, 0.033), "#F2EEE6")
        cd.sph((x, y - 0.014, z), (0.024, 0.009, 0.027), AMBER)
        cd.sph((x, y - 0.019, z), (0.013, 0.006, 0.016), "#2A1608")
        cd.sph((x - 0.006, y - 0.024, z + 0.009), (0.004, 0.002, 0.004), "#FFF8E8")
        cd.sph((x, y - 0.006, z), (0.031, 0.02, 0.034), "#FFFFFF")
    cd.sph((0, -0.108, 0.36), (0.009, 0.006, 0.006), "#D49A90")          # nose
    # Spirit tail: layered translucent glowing wisps with golden sparkles
    tail, nt, out = node_mat("piko_tail")
    info = nt.nodes.new("ShaderNodeLayerWeight")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = hexrgb(BLUE)
    em.inputs["Strength"].default_value = 2.5
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(info.outputs["Facing"], mx.inputs[0])
    nt.links.new(em.outputs["Emission"], mx.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
    random.seed(3)
    base = [(0, 0.07, 0.1), (0.05, 0.16, 0.12), (0.16, 0.22, 0.2), (0.28, 0.24, 0.3), (0.38, 0.2, 0.36), (0.46, 0.14, 0.33)]
    for k in range(9):
        off = [(p[0] + random.uniform(-0.02, 0.02) * i, p[1] + random.uniform(-0.02, 0.02) * i, p[2] + random.uniform(-0.025, 0.025) * i)
               for i, p in enumerate(base)]
        off[-1] = (off[-1][0] + random.uniform(0, 0.08), off[-1][1], off[-1][2] + random.uniform(-0.05, 0.05))
        t = cd.tube(off, lambda u, k=k: (0.03 - 0.012 * (k % 3)) * (1 - u) + 0.002, "#87C7FF")
        t.data.materials.clear()
        t.data.materials.append(tail)
    spark, nt, out = node_mat("sparkle")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = hexrgb("#FFD86B")
    em.inputs["Strength"].default_value = 8.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    for _ in range(26):
        u = random.random()
        i = min(int(u * (len(base) - 1)), len(base) - 2)
        f = u * (len(base) - 1) - i
        p = [base[i][j] * (1 - f) + base[i + 1][j] * f + random.uniform(-0.04, 0.04) for j in range(3)]
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.003 + 0.003 * random.random(), location=p)
        bpy.context.active_object.data.materials.append(spark)
    # Faint glowing swirl on the forehead, sitting on top of the fur
    glow, nt, out = node_mat("swirl")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = hexrgb(MARK)
    em.inputs["Strength"].default_value = 3.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    pts = [(0.018 * (1 - a / 12) * math.cos(a), -0.115, 0.43 + 0.018 * (1 - a / 12) * math.sin(a)) for a in np.linspace(0, 12, 16)]
    sw = cd.tube(pts, lambda u: 0.0025, "#ADEFFF")
    sw.data.materials.clear()
    sw.data.materials.append(glow)
    render_sheet_real("Piko", 0.7, [FUR, "#D8DCE2", BLUE, MARK, AMBER, "#E8B7A8"], width=0.85)


if __name__ == "__main__":
    for w in WHICH:
        {"piko": piko, "glider": glider, "compass": compass}[w]()
    print("LS_REAL_OK", flush=True)
