"""Kieran Thorn: build the game character in Blender from Adam's turnaround, stage by stage.

Body: MPFB (MakeHuman, CC0 output) with the Unreal-style "game_engine" rig, shaped by targets until its front and
side silhouettes match the widths measured from Adam's turnaround (measure_reference.py). The pose is baked as the
rest pose, so the exported skeleton stands like the drawings.

  blender --background --python build_kieran.py -- <stage> [params.json]
  stages: body (build + silhouette check)
"""
import json
import math
import os
import sys

import addon_utils
import bpy
import numpy as np
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
KDIR = os.path.join(REPO, "Unreal", "SourceArt", "Characters", "Kieran")
REF = json.load(open(os.path.join(KDIR, "reference", "turnaround_measurements.json")))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["body"]
STAGE = ARGS[0]
PARAMS = json.load(open(ARGS[1])) if len(ARGS) > 1 else {}


def mpfb():
    addon_utils.enable("bl_ext.blender_org.mpfb")
    from bl_ext.blender_org.mpfb.services.humanservice import HumanService
    return HumanService


# ------------------------------------------------------------------ body
DEFAULT = {
    "pheno": {"gender": 1.0, "age": 0.28, "muscle": 0.5, "weight": 0.3, "height": 0.55, "proportions": 0.75, "cupsize": 0.5, "firmness": 0.5},
    "targets": {"l-eye-scale-incr": 0.5, "r-eye-scale-incr": 0.5},
    "arm_out": 0.2, "forearm_out": 0.12, "leg_out": 0.09,
}


def build_body(p):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    HS = mpfb()
    info = HS._create_default_human_info_dict()
    info["phenotype"].update(p["pheno"])
    info["phenotype"]["race"] = {"african": 1.0, "asian": 0.0, "caucasian": 0.0}
    info.update({"eyes": "high-poly.mhclo", "eyebrows": "eyebrow010.mhclo", "eyelashes": "mindfront_eyelashes_01.mhclo",
                 "teeth": "teeth_base.mhclo", "skin_mhmat": "young_african_male.mhmat", "skin_material_type": "ENHANCED_SSS",
                 "rig": "game_engine", "name": "Kieran"})
    info["targets"] = [{"target": t, "value": v} for t, v in p["targets"].items()]
    st = HS.get_default_deserialization_settings()
    st["load_clothes"] = False
    st["subdiv_levels"] = 0
    body = HS.deserialize_from_dict(info, st)
    rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    rig.name = "Kieran_Rig"
    # Pose like the turnaround: arms hanging a little out from the sides, feet apart
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="POSE")
    for side, s in (("l", 1), ("r", -1)):
        for bone, target in (("upperarm", (s * p["arm_out"], 0.02, -1.0)), ("lowerarm", (s * p["forearm_out"], -0.08, -1.0)),
                             ("thigh", (s * p["leg_out"], 0.0, -1.0)), ("calf", (s * p["leg_out"] * 0.6, 0.02, -1.0))):
            pb = rig.pose.bones["%s_%s" % (bone, side)]
            head = pb.head.copy()
            q = (pb.tail - pb.head).normalized().rotation_difference(Vector(target).normalized())
            pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
            bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode="OBJECT")
    # Bake pose and targets into plain meshes, then make that pose the rig's rest pose
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    baked = {}
    for o in meshes:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        baked[o] = me
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
        for poly in o.data.polygons:
            poly.use_smooth = True
    return bpy.data.objects.get("Kieran.body") or body, rig


# ------------------------------------------------------------------ silhouette measurement
def silhouette(view, objs=None, res=900):
    """Render a flat white-on-black orthographic silhouette and return the mask (row 0 = top)."""
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (1, 1, 1)
    sh.background_type = "VIEWPORT"
    sh.background_color = (0, 0, 0)
    sh.show_object_outline = False
    sh.show_shadows = False
    sh.show_cavity = False
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x, sc.render.resolution_y = res, res
    hidden = []
    if objs is not None:
        for o in sc.objects:
            if o.type in ("MESH", "CURVE") and o not in objs and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type in ("MESH", "CURVE") and not o.hide_render for c in o.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    cam = bpy.data.objects.get("SilCam") or bpy.data.objects.new("SilCam", bpy.data.cameras.new("SilCam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = (zmax - zmin) * 1.1
    cz = (zmax + zmin) / 2
    if view == "front":
        cam.location, cam.rotation_euler = (0, -10, cz), (math.radians(90), 0, 0)
    else:   # side: Kieran faces -Y, camera on his left (+X) looking at his profile like the sheet
        cam.location, cam.rotation_euler = (10, 0, cz), (math.radians(90), 0, math.radians(90))
    sc.camera = cam
    path = os.path.join(KDIR, "renders", "_sil.png")
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    px = np.array(img.pixels[:]).reshape(res, res, 4)[::-1, :, 0]
    bpy.data.images.remove(img)
    for o in hidden:
        o.hide_render = False
    return px > 0.5


def profile(mask):
    rows = np.where(mask.any(axis=1))[0]
    top, bot = rows[0], rows[-1]
    hgt = bot - top
    prof = []
    for k in range(101):
        xs = np.where(mask[top + int(hgt * k / 100)])[0]
        prof.append((xs[-1] - xs[0]) / hgt if len(xs) else 0.0)
    return np.array(prof)


def chin_index(prof):
    """The narrowest point of the neck between 8% and 26% of the height."""
    return 8 + int(np.argmin(prof[8:26]))


def compare(prof, ref):
    """Compare from the chin down to the soles, both normalised to that span."""
    c1, c2 = chin_index(prof), chin_index(ref)
    xs = np.linspace(0, 1, 60)
    a = np.interp(xs, np.linspace(0, 1, 101 - c1), prof[c1:]) * 100 / (100 - c1)
    b = np.interp(xs, np.linspace(0, 1, 101 - c2), ref[c2:]) * 100 / (100 - c2)
    regions = {"shoulders": (0.02, 0.12), "chest_arms": (0.12, 0.35), "hips_hands": (0.35, 0.52), "thighs": (0.52, 0.7),
               "knees_calves": (0.7, 0.88), "boots": (0.88, 1.0)}
    rep = {}
    for k, (u, v) in regions.items():
        sel = (xs >= u) & (xs < v)
        rep[k] = round(float((a[sel] - b[sel]).mean()), 4)
    return c1, c2, rep, float(np.abs(a - b).mean())


def check_body(tag):
    ref_f = np.array(REF["figures"]["front"]["width_profile"])
    ref_s = np.array(REF["figures"]["side"]["width_profile"])
    for view, ref in (("front", ref_f), ("side", ref_s)):
        prof = profile(silhouette(view))
        c1, c2, rep, err = compare(prof, ref)
        print("LS_SIL %s %s chin(model %d%%, ref %d%%) mean|diff| %.4f  by region (model minus ref, fraction of chin-to-sole height): %s"
              % (tag, view, c1, c2, err, json.dumps(rep)), flush=True)


def render_view(name, yaw, height=None, res=(700, 1000)):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "MATERIAL"
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.93, 0.9, 0.82)
    sh.show_shadows = True
    sh.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = res
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type in ("MESH", "CURVE") and not o.hide_render for c in o.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    cam = bpy.data.objects.get("ViewCam") or bpy.data.objects.new("ViewCam", bpy.data.cameras.new("ViewCam"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = (zmax - zmin) * 1.08
    a = math.radians(yaw)
    cam.location = (10 * math.sin(a), -10 * math.cos(a), (zmax + zmin) / 2)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.camera = cam
    sc.render.filepath = os.path.join(KDIR, "renders", name + ".png")
    bpy.ops.render.render(write_still=True)
    print("LS_RENDER", sc.render.filepath, flush=True)


if __name__ == "__main__":
    p = dict(DEFAULT)
    for k, v in PARAMS.items():
        if isinstance(v, dict) and k in p:
            p[k] = dict(p[k], **v)
        else:
            p[k] = v
    if STAGE == "body":
        body, rig = build_body(p)
        z = [ (body.matrix_world @ v.co).z for v in body.data.vertices]
        print("LS_HEIGHT %.3f m" % (max(z) - min(z)), flush=True)
        check_body("body")
        render_view("stage1_body_front", 0)
        render_view("stage1_body_side", 90)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KDIR, "Kieran_stage1_body.blend"))
    print("LS_STAGE_OK", STAGE, flush=True)
