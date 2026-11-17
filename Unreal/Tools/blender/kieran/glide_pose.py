"""Kieran's glide pose, after Adam's reference (2026-11-17): prone and nearly horizontal under the wing, face-down with the
head raised to look ahead, both arms reaching forward and down to grip the control bar in front of and below the
shoulders, legs trailing straight back together with the feet a little below the hips.

Built on the centimetre game rig (Kieran_Thorn_GameReady_scene.blend) and exported as a short looping FBX animation for
Unreal. A reference crossbar and wing outline (from the Ancient Glider draft) are added for the preview renders only.

  blender --background Kieran_Thorn_GameReady_scene.blend --python glide_pose.py
"""
import math
import os

import bpy
from mathutils import Matrix, Vector

KDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SourceArt", "Characters", "Kieran"))
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
sc = bpy.context.scene
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="POSE")
PB = rig.pose.bones


def world(p):
    return rig.matrix_world @ p


def rotate(bone, axis, deg, pivot=None):
    pb = PB[bone]
    head = pivot if pivot is not None else pb.head.copy()
    R = Matrix.Rotation(math.radians(deg), 4, Vector(axis))
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


def aim(bone, direction):
    """Point a bone (head -> tail) along a direction in armature space, turning about its head."""
    pb = PB[bone]
    cur = (pb.tail - pb.head).normalized()
    q = cur.rotation_difference(Vector(direction).normalized())
    head = pb.head.copy()
    pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ pb.matrix
    bpy.context.view_layer.update()


def reach(side, target):
    """Two-bone reach: aim upper arm and forearm so the wrist lands on target (law of cosines, elbow bends outward)."""
    ua, la = PB["upperarm_" + side], PB["lowerarm_" + side]
    s = ua.head.copy()
    l1 = (la.head - ua.head).length
    l2 = (PB["hand_" + side].head - la.head).length
    d = target - s
    dist = min(d.length, (l1 + l2) * 0.999)
    a = math.acos(max(-1.0, min(1.0, (l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist))))
    out = Vector((1 if side == "l" else -1, 0, 0))
    bend = d.cross(out).cross(d).normalized()          # elbows point outward-ish
    elbow_dir = (d.normalized() * math.cos(a) - bend * math.sin(a)).normalized()
    aim("upperarm_" + side, elbow_dir)
    aim("lowerarm_" + side, target - PB["lowerarm_" + side].head)


def build_pose(sway=0.0):
    for pb in PB:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    hip = PB["pelvis"].head.copy()
    # 1. tip the whole body forward ~82 degrees about the hips: prone, head toward -Y (forward)
    rotate("pelvis", (1, 0, 0), 82)
    # 2. head raised to look ahead, neck lifting with it
    rotate("neck_01", (1, 0, 0), -30)
    rotate("head", (1, 0, 0), -28)
    # 3. legs together and trailing straight back, knees just soft, feet a little lower than the hips
    for s in "lr":
        rotate("thigh_" + s, (0, 0, 1), 4 if s == "l" else -4)
        rotate("thigh_" + s, (1, 0, 0), -6 + sway)
        rotate("calf_" + s, (1, 0, 0), 10)
        rotate("foot_" + s, (1, 0, 0), 30)          # toes pointed back
    # 4. hands to the control bar: in front of and below the shoulders
    sh_l, sh_r = PB["upperarm_l"].head.copy(), PB["upperarm_r"].head.copy()
    mid = (sh_l + sh_r) / 2
    bar_y = mid.y - 30.0      # 30 cm ahead of the shoulders
    bar_z = mid.z - 38.0      # 38 cm below them
    half = 26.0               # a shoulder-width grip on the bar
    # wrists sit just behind and above the bar so the palms close over it
    targets = {"l": Vector((half, bar_y + 5.0, bar_z + 6.0)), "r": Vector((-half, bar_y + 5.0, bar_z + 6.0))}
    for s in "lr":
        reach(s, targets[s])
        aim("hand_" + s, Vector((0, -0.75, -0.65)))
        for f in ("index", "middle", "ring", "pinky"):     # fingers curl round the bar
            for k in "123":
                n = "%s_0%s_%s" % (f, k, s)
                if n in PB:
                    rotate(n, (1, 0, 0), -38)
        for k in "23":
            n = "thumb_0%s_%s" % (k, s)
            if n in PB:
                rotate(n, (1, 0, 0), -25)
    return Vector((0, bar_y, bar_z)), half


for frame in (1, 2):
    sc.frame_set(frame)
    bar_c, half = build_pose(sway=1.5 if frame == 2 else 0.0)
    for pb in PB:
        pb.rotation_mode = "QUATERNION"
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        pb.keyframe_insert("location", frame=frame)
sc.frame_start, sc.frame_end = 1, 2
bpy.ops.object.mode_set(mode="OBJECT")
rig.animation_data.action.name = "Glide"
for o in sc.objects:
    o.select_set(o == rig)
out = os.path.join(KDIR, "export", "Kieran_Glide.fbx")
bpy.ops.export_scene.fbx(filepath=out, use_selection=True, add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
                         bake_anim_use_nla_strips=False, armature_nodetype="NULL", primary_bone_axis="Y", secondary_bone_axis="X",
                         apply_unit_scale=True, apply_scale_options="FBX_SCALE_NONE", global_scale=1.0, object_types={"ARMATURE"})
print("LS_GLIDE", out, os.path.getsize(out), flush=True)

# ---- checks: hands on the bar, nothing passing through the body
sc.frame_set(1)
bpy.context.view_layer.update()
for s in "lr":
    grip = world(PB["middle_02_" + s].head) if "middle_02_" + s in PB else world(PB["hand_" + s].head)
    target = world(Vector((half if s == "l" else -half, bar_c.y, bar_c.z)))
    print("LS_GRIP %s distance to bar %.1f cm" % (s, (grip - target).length), flush=True)
hz = [world(PB[b].head).z for b in ("pelvis", "spine_03", "neck_01")]
print("LS_LEVEL pelvis/chest/neck heights %s cm (level = similar values)" % [round(z, 1) for z in hz], flush=True)

# ---- reference glider for the previews (not exported): crossbar, uprights and the wing over his back
gm = bpy.data.materials.new("ref_wood")
gm.diffuse_color = (0.55, 0.4, 0.25, 1)
gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.55, 0.4, 0.25, 1)
cm = bpy.data.materials.new("ref_cloth")
cm.use_nodes = True
cm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.66, 0.85, 0.95, 1)
cm.node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.55
cm.blend_method = "BLEND" if hasattr(cm, "blend_method") else None


def rod(a, b, r, m):
    a, b = Vector(a), Vector(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r, depth=(b - a).length, location=(a + b) / 2)
    o = bpy.context.active_object
    o.rotation_euler = Vector((0, 0, 1)).rotation_difference((b - a).normalized()).to_euler()
    o.data.materials.append(m)
    return o


bar = world(bar_c)
apex = Vector((bar.x, bar.y + 25, bar.z + 95))
rod((bar.x - 45, bar.y, bar.z), (bar.x + 45, bar.y, bar.z), 1.6, gm)                       # crossbar
for sx in (-1, 1):
    rod((bar.x + sx * 45, bar.y, bar.z), apex, 1.3, gm)                                     # uprights to the keel
rod((apex.x, apex.y - 120, apex.z + 6), (apex.x, apex.y + 160, apex.z - 6), 2.0, gm)        # keel
bm_verts = [(apex.x, apex.y - 120, apex.z + 8), (apex.x - 230, apex.y + 120, apex.z + 30), (apex.x, apex.y + 160, apex.z),
            (apex.x + 230, apex.y + 120, apex.z + 30)]
me = bpy.data.meshes.new("ref_wing")
me.from_pydata(bm_verts, [], [(0, 1, 2), (0, 2, 3)])
w = bpy.data.objects.new("ref_wing", me)
sc.collection.objects.link(w)
me.materials.append(cm)

# ---- renders
cam = bpy.data.objects.get("LookCam") or bpy.data.objects.new("LookCam", bpy.data.cameras.new("LookCam"))
if cam.name not in sc.collection.objects:
    sc.collection.objects.link(cam)
cam.data.type = "ORTHO"
cam.data.clip_end = 8000
sc.camera = cam
sc.render.resolution_x, sc.render.resolution_y = 1000, 800
centre = world(PB["spine_02"].head)
for name, yaw, elev, scale in (("glide_pose_side", 90, 0, 330), ("glide_pose_threequarter", 35, 20, 360), ("glide_pose_top", 0, 89, 520)):
    a, e = math.radians(yaw), math.radians(elev)
    cam.data.ortho_scale = scale
    cam.location = centre + Vector((1500 * math.sin(a) * math.cos(e), -1500 * math.cos(a) * math.cos(e), 1500 * math.sin(e)))
    cam.rotation_euler = (math.radians(90) - e, 0, a)
    sc.render.filepath = os.path.join(KDIR, "renders", name + ".png")
    bpy.ops.render.render(write_still=True)
    print("LS_RENDER", sc.render.filepath, flush=True)
