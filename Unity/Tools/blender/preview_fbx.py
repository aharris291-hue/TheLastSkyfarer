"""Quick look at kit FBX files: imports each one into an empty scene, gives the materials flat colours by name, and
renders a three-quarter front view with soft lighting.

  blender --background --factory-startup --python preview_fbx.py -- <out folder> <a.fbx> [<b.fbx> ...]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ARGS = sys.argv[sys.argv.index("--") + 1:]
OUT, FILES = ARGS[0], ARGS[1:]
COLS = {"MI_Stone": "#CDBB9C", "MI_Plaster": "#EFE3C8", "MI_Wood": "#8F6A45", "MI_RoofTerracotta": "#C8693F", "MI_RoofGreen": "#6F9A5A",
        "MI_RoofBlue": "#4F86B8", "MI_Glass": "#2F4A58", "MI_Brass": "#C79A3B", "MI_FlowerBed": "#E77FA0", "MI_Foliage": "#6E9C44",
        "MI_Cloth_Red": "#C8553D", "MI_FoliageBlossom": "#E7A6B8", "MI_CliffRock": "#8E7C6B"}


def lin(h):
    def c(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return (c(int(h[1:3], 16)), c(int(h[3:5], 16)), c(int(h[5:7], 16)), 1)


for f in FILES:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=f, axis_forward="-Y", axis_up="Z")
    for m in bpy.data.materials:
        m.use_nodes = True
        b = m.node_tree.nodes.get("Principled BSDF")
        key = next((k for k in COLS if m.name.startswith(k)), None)
        if b and key:
            b.inputs["Base Color"].default_value = lin(COLS[key])
            b.inputs["Roughness"].default_value = 0.8
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = 900, 700
    w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.82, 0.9, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3.5; sun.rotation_euler = (math.radians(50), 0, math.radians(-35))
    pts = [o.matrix_world @ Vector(c) for o in sc.objects if o.type == "MESH" for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    centre, size = (lo + hi) / 2, (hi - lo).length
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam)
    cam.location = centre + Vector((size * 0.75, -size * 1.0, size * 0.45))
    d = centre - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, os.path.splitext(os.path.basename(f))[0] + "_preview.png")
    bpy.ops.render.render(write_still=True)
    print("LS_PREVIEW", sc.render.filepath, flush=True)
