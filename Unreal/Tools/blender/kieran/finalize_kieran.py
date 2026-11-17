"""Kieran Thorn, final stage: deformation tests, game-ready export, re-import check and five-view QA sheet.

Opens Kieran_Thorn_Master.blend (the editable master is never modified by this script), then:
  1. poses the rig (arms raised, elbows bent, torso twist, walking stride, knees bent, head turn) and renders each;
  2. builds a game copy: curves to meshes, rigid parts skinned to their bone, light subdivision, one armature;
  3. exports Kieran_Thorn_GameReady.glb and .fbx, re-imports the GLB into an empty scene and checks it;
  4. renders the five reference angles and lays them under the matching drawings from Adam's sheet.

  blender --background <Kieran_Thorn_Master.blend> --python finalize_kieran.py
"""
import json
import math
import os
import sys

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
KDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SourceArt", "Characters", "Kieran"))
REND = os.path.join(KDIR, "renders")
EXP = os.path.join(KDIR, "export")
os.makedirs(EXP, exist_ok=True)
REPORT = {}
rig = bpy.data.objects["Kieran_Rig"]
sc = bpy.context.scene
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -1.6
for l in bpy.data.lights:   # neutral white light, so the comparison judges the materials, not the lamp colour
    l.color = (1.0, 1.0, 1.0)


def render(name, yaw, res=(800, 1200), pad=1.06):
    sc.render.resolution_x, sc.render.resolution_y = res
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for o in sc.objects:
        if o.type in ("MESH", "CURVE") and not o.hide_render:
            ev = o.evaluated_get(dg)
            pts += [ev.matrix_world @ Vector(c) for c in ev.bound_box]
    zmin, zmax = min(p.z for p in pts), max(p.z for p in pts)
    span = max(zmax - zmin, max(p.x for p in pts) - min(p.x for p in pts), 1.0)
    cam = bpy.data.objects.get("LookCam")
    cam.data.ortho_scale = span * pad
    a = math.radians(yaw)
    cam.location = (10 * math.sin(a), -10 * math.cos(a), (zmax + zmin) / 2)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.camera = cam
    sc.render.filepath = os.path.join(REND, name + ".png")
    bpy.ops.render.render(write_still=True)
    return sc.render.filepath


# ------------------------------------------------------------------ 1. deformation tests
def pose(rots):
    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0, 0, 0)
    for bone, axis, deg in rots:
        pb = rig.pose.bones[bone]
        e = list(pb.rotation_euler)
        e["XYZ".index(axis)] += math.radians(deg)
        pb.rotation_euler = e
    bpy.context.view_layer.update()


def world_rotate(bone, axis_world, deg):
    """Rotate a pose bone about a world axis through its head (rig bones have arbitrary rolls)."""
    pb = rig.pose.bones[bone]
    head = pb.head.copy()
    R = Matrix.Rotation(math.radians(deg), 4, Vector(axis_world))
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


POSES = {
    "pose_arms_raised": [("upperarm_l", (0, 1, 0), -80), ("upperarm_r", (0, 1, 0), 80)],
    "pose_elbows_bent": [("lowerarm_l", (1, 0, 0), -95), ("lowerarm_r", (1, 0, 0), -95)],
    "pose_torso_twist": [("spine_02", (0, 0, 1), 20), ("spine_03", (0, 0, 1), 15)],
    "pose_walk": [("thigh_l", (1, 0, 0), -28), ("calf_l", (1, 0, 0), 30), ("thigh_r", (1, 0, 0), 20),
                  ("upperarm_l", (1, 0, 0), -18), ("upperarm_r", (1, 0, 0), 22)],
    "pose_knees_bent": [("thigh_l", (1, 0, 0), -45), ("thigh_r", (1, 0, 0), -45), ("calf_l", (1, 0, 0), 80), ("calf_r", (1, 0, 0), 80),
                        ("pelvis", (0, 0, 1), 0)],
    "pose_head_turn": [("head", (0, 0, 1), 35), ("neck_01", (0, 0, 1), 10)],
}
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="POSE")
for name, ops in POSES.items():
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    for bone, axis, deg in ops:
        world_rotate(bone, axis, deg)
    render(name, 30, res=(700, 900), pad=1.1)
    print("LS_POSE", name, flush=True)
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.ops.object.mode_set(mode="OBJECT")
bpy.context.view_layer.update()

# ------------------------------------------------------------------ 4a. final five-view renders of the master
VIEWS = (("Kieran_Front", 0), ("Kieran_ThreeQuarterFront", 40), ("Kieran_Side", 90), ("Kieran_ThreeQuarterRear", 140), ("Kieran_Rear", 180))
for name, yaw in VIEWS:
    render(name, yaw)
    print("LS_VIEW", name, flush=True)

# ------------------------------------------------------------------ 2. game copy
for o in sc.objects:
    o.select_set(False)
# hair: lighter coil tubes for real time
hair = bpy.data.objects.get("Kieran_hair_coils")
if hair:
    hair.data.bevel_resolution = 0
    hair.data.resolution_u = 2
curve_objs = [o for o in sc.objects if o.type == "CURVE"]
for o in curve_objs:
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    bpy.ops.object.convert(target="MESH")
    o.select_set(False)
dg = bpy.context.evaluated_depsgraph_get()
game_parts = []
for o in list(sc.objects):
    if o.type != "MESH" or o.name.startswith("Look"):
        continue
    for m in o.modifiers:
        if m.type == "SUBSURF":
            m.levels = 0 if not o.name.startswith(("Kieran_jacket", "Kieran_trousers", "Kieran_shirt")) else 1
    bone = o.parent_bone if o.parent_type == "BONE" else None
    has_arm = any(m.type == "ARMATURE" for m in o.modifiers)
    # bake every non-armature modifier into the mesh
    arm_mods = [m for m in o.modifiers if m.type == "ARMATURE"]
    for m in arm_mods:
        m.show_viewport = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    mw = o.matrix_world.copy()
    o.modifiers.clear()
    o.parent = None
    o.matrix_world = mw
    o.data = me
    if bone:   # rigid part: skin it 100% to its bone
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        vg = o.vertex_groups.new(name=bone)
        vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    elif not has_arm and not o.vertex_groups:   # stray part: follow the pelvis
        vg = o.vertex_groups.new(name="pelvis")
        vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    game_parts.append(o)
# real-time budget: each part decimated to its own share, so the face and hands keep their detail
BUDGET = {"Kieran_hair": 9000, "Kieran_jacket": 6000, "Kieran_trousers": 4000, "Kieran_shirt": 2500, "Kieran_boots": 2000,
          "Kieran_bootfoot": 1200, "Kieran_sole": 500, "Kieran_gloves": 1500, "_hem": 600, "Kieran_scarf": 1200,
          "Kieran_satchel_strap": 300, "Kieran.mindfront_eyelashes": 1500, "Kieran.eyebrow": 1500}
for o in game_parts:
    key = next((k for k in BUDGET if k in o.name), None)
    if not key:
        continue
    o.data.calc_loop_triangles()
    n = len(o.data.loop_triangles)
    if n > BUDGET[key]:
        dm = o.modifiers.new("budget", "DECIMATE")
        dm.ratio = BUDGET[key] / n
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="budget")
# then share what is left of a 45k-triangle budget among everything except the face (skin, eyes, brows, lashes)
TARGET = 45000
PROTECT = ("Kieran.body", "high-poly", "eyebrow", "eyelash")
def tri_count(o):
    o.data.calc_loop_triangles()
    return len(o.data.loop_triangles)
for o in game_parts:
    if "teeth" in o.name and tri_count(o) > 1500:
        dm = o.modifiers.new("budget", "DECIMATE")
        dm.ratio = 1500 / tri_count(o)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="budget")
prot = sum(tri_count(o) for o in game_parts if any(k in o.name for k in PROTECT))
rest = [o for o in game_parts if not any(k in o.name for k in PROTECT)]
rest_n = sum(tri_count(o) for o in rest)
ratio = max(0.1, min(1.0, (TARGET - prot) / max(1, rest_n)))
print("LS_BUDGET protected %d, rest %d, ratio %.3f" % (prot, rest_n, ratio), flush=True)
if ratio < 1.0:
    for o in rest:
        if tri_count(o) < 60:
            continue
        dm = o.modifiers.new("budget", "DECIMATE")
        dm.ratio = ratio
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.modifier_apply(modifier="budget")
# hem piping curves were converted without weights: copy weights from the garment they trim
body = bpy.data.objects["Kieran.body"]
for o in game_parts:
    src_name = o.get("weights_from")
    if o.name.endswith("_hem") or src_name:
        src = bpy.data.objects.get(src_name or o.name[:-4]) or body
        for vg in list(o.vertex_groups):
            o.vertex_groups.remove(vg)
        dt = o.modifiers.new("dt", "DATA_TRANSFER")
        dt.object = body
        dt.use_vert_data = True
        dt.data_types_verts = {"VGROUP_WEIGHTS"}
        dt.vert_mapping = "POLYINTERP_NEAREST"
        dt.layers_vgroup_select_src = "ALL"
        dt.layers_vgroup_select_dst = "NAME"
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.datalayout_transfer(modifier="dt")
        bpy.ops.object.modifier_apply(modifier="dt")
# join into one skinned mesh with material slots, under the rig
for o in sc.objects:
    o.select_set(False)
for o in game_parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = body
bpy.ops.object.join()
game = bpy.context.active_object
game.name = "Kieran_GameReady"
# drop unused helper groups and unused materials
bpy.ops.object.material_slot_remove_unused()
bone_names = {b.name for b in rig.data.bones}
for vg in list(game.vertex_groups):
    if vg.name not in bone_names:
        game.vertex_groups.remove(vg)
# --- bake every material's colour into one 2048 atlas so the game mesh needs only two materials
metal_names = {m.name for m in game.data.materials if m and ("brass" in m.name or "steel" in m.name or "button" in m.name)}
render_uv = game.data.uv_layers.active.name if game.data.uv_layers.active else None
atlas_uv = game.data.uv_layers.new(name="atlas")
game.data.uv_layers.active = atlas_uv
for u in game.data.uv_layers:
    u.active_render = (u.name == render_uv)
bpy.context.view_layer.objects.active = game
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.002, scale_to_bounds=True)
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(rotate=True, margin=0.0015)
bpy.ops.object.mode_set(mode="OBJECT")
atlas = bpy.data.images.new("T_Kieran_BaseColor", 2048, 2048, alpha=False)
for m in game.data.materials:
    if not m or not m.use_nodes:
        continue
    n = m.node_tree.nodes.new("ShaderNodeTexImage")
    n.image = atlas
    uvn = m.node_tree.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "atlas"
    m.node_tree.links.new(uvn.outputs["UV"], n.inputs["Vector"])
    m.node_tree.nodes.active = n
sc.render.engine = "CYCLES"
sc.cycles.samples = 4
sc.cycles.device = "CPU"
for o in sc.objects:
    o.select_set(o == game)
bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True, target="IMAGE_TEXTURES")
atlas.filepath_raw = os.path.join(EXP, "T_Kieran_BaseColor.png")
atlas.file_format = "PNG"
atlas.save()
REPORT["atlas"] = atlas.filepath_raw
# replace the many authored materials with two that sample the atlas
def atlas_mat(name, metallic, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = atlas
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = "atlas"
    nt.links.new(uvn.outputs["UV"], t.inputs["Vector"])
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m
m_main = atlas_mat("M_Kieran", 0.0, 0.7)
m_metal = atlas_mat("M_Kieran_Metal", 1.0, 0.35)
old = [m.name if m else "" for m in game.data.materials]
idx_map = [1 if name in metal_names else 0 for name in old]
for p in game.data.polygons:
    p.material_index = idx_map[p.material_index] if p.material_index < len(idx_map) else 0
game.data.materials.clear()
game.data.materials.append(m_main)
game.data.materials.append(m_metal)
for u in list(game.data.uv_layers):     # the atlas becomes the only UV map
    if u.name != "atlas":
        game.data.uv_layers.remove(u)
game.parent = rig
arm = game.modifiers.new("Armature", "ARMATURE")
arm.object = rig
me = game.data
me.calc_loop_triangles()
REPORT["game_triangles"] = len(me.loop_triangles)
REPORT["game_vertices"] = len(me.vertices)
REPORT["materials"] = len(me.materials)
REPORT["bones"] = len(rig.data.bones)
print("LS_GAME", json.dumps(REPORT), flush=True)

# ------------------------------------------------------------------ 3. export and re-import
for o in sc.objects:
    o.select_set(o in (game, rig))
glb = os.path.join(EXP, "Kieran_Thorn_GameReady.glb")
fbx = os.path.join(EXP, "Kieran_Thorn_GameReady.fbx")
bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_format="GLB", export_skins=True, export_animations=False,
                          export_apply=False)
# Unreal works in centimetres: rescale this game copy so 1 Blender unit = 1 cm and the skeleton imports 1:1
# (otherwise the root bone carries a 100x scale that retargeted animations ignore and the mesh collapses)
rig.name = "Armature"   # Unreal drops a top node named Armature
sc.unit_settings.scale_length = 0.01
for o in (rig, game):
    o.select_set(True)
bpy.context.view_layer.objects.active = rig
game.parent = None
rig.scale = (100, 100, 100)
game.scale = (100, 100, 100)
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
game.parent = rig
bpy.ops.export_scene.fbx(filepath=fbx, use_selection=True, add_leaf_bones=False, bake_anim=False, mesh_smooth_type="FACE",
                         armature_nodetype="NULL", primary_bone_axis="Y", secondary_bone_axis="X",
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0)
REPORT["glb_bytes"] = os.path.getsize(glb)
REPORT["fbx_bytes"] = os.path.getsize(fbx)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KDIR, "Kieran_Thorn_GameReady_scene.blend"), copy=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=glb)
meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.name != "Icosphere"]   # Icosphere = importer bone shape
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
tris = 0
for o in meshes:
    o.data.calc_loop_triangles()
    tris += len(o.data.loop_triangles)
REPORT["reimport"] = {"meshes": len(meshes), "armatures": len(arms), "bones": len(arms[0].data.bones) if arms else 0, "triangles": tris,
                      "skinned": all(any(m.type == "ARMATURE" for m in o.modifiers) for o in meshes if o.name.startswith("Kieran"))}
print("LS_REIMPORT", json.dumps(REPORT["reimport"]), flush=True)
json.dump(REPORT, open(os.path.join(EXP, "export_report.json"), "w"), indent=1)

# ------------------------------------------------------------------ 4b. QA sheet: drawings above, renders below
ref = json.load(open(os.path.join(KDIR, "reference", "turnaround_measurements.json")))
src = bpy.data.images.load(os.path.join(KDIR, "..", "..", "..", "..", "art_source", "characters", "Kieran Thorn Turnaround Sheet.png"))
w, h = src.size
sheet_px = np.array(src.pixels[:]).reshape(h, w, 4)[::-1]
cell_w, cell_h = 360, 600
rows = []
top = np.ones((cell_h, cell_w * 5, 4))
bot = np.ones((cell_h, cell_w * 5, 4))
order = ["front", "three_quarter_front", "side", "three_quarter_rear", "rear"]


def fit(img, cw, ch):
    ih, iw = img.shape[:2]
    s = min(cw / iw, ch / ih)
    nw, nh = max(1, int(iw * s)), max(1, int(ih * s))
    ys = (np.arange(nh) / s).astype(int).clip(0, ih - 1)
    xs = (np.arange(nw) / s).astype(int).clip(0, iw - 1)
    out = np.ones((ch, cw, 4))
    out[(ch - nh) // 2:(ch - nh) // 2 + nh, (cw - nw) // 2:(cw - nw) // 2 + nw] = img[ys][:, xs]
    return out


for i, key in enumerate(order):
    f = ref["figures"][key]
    crop = sheet_px[f["top"]:f["bottom"] + 1, f["x"][0]:f["x"][1]]
    top[:, i * cell_w:(i + 1) * cell_w] = fit(crop, cell_w, cell_h)
    r = bpy.data.images.load(os.path.join(REND, VIEWS[i][0] + ".png"))
    rw, rh = r.size
    rp = np.array(r.pixels[:]).reshape(rh, rw, 4)[::-1]
    lumr = rp[:, :, :3].mean(axis=2)
    bg = np.median(rp[2:12, 2:12, :3].reshape(-1, 3), axis=0)
    msk = np.abs(rp[:, :, :3] - bg).sum(axis=2) > 0.04
    yy, xx = np.where(msk)
    rp = rp[yy.min():yy.max() + 1, xx.min():xx.max() + 1]
    bot[:, i * cell_w:(i + 1) * cell_w] = fit(rp, cell_w, cell_h)
qa = np.concatenate([bot, top], axis=0)[::-1]     # image rows bottom-up: drawings on top
out = bpy.data.images.new("QA", qa.shape[1], qa.shape[0], alpha=True)
out.pixels.foreach_set(qa.astype(np.float32).ravel())
out.filepath_raw = os.path.join(REND, "Kieran_QA_vs_turnaround.png")
out.file_format = "PNG"
out.save()
print("LS_QA", out.filepath_raw, flush=True)
print("LS_FINAL_OK", flush=True)
