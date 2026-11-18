"""Renders a quick Workbench preview of the exported Windrest kit (for checking shapes, not final look).

  blender --background --factory-startup --python preview_kit.py -- <kit folder> <output.png>
"""
import math
import os
import sys

import bpy

args = sys.argv[sys.argv.index("--") + 1:]
KIT, OUT = args[0], args[1]
COLORS = {"MI_Stone": (0.62, 0.52, 0.40), "MI_Plaster": (0.86, 0.78, 0.62), "MI_Wood": (0.33, 0.20, 0.11),
          "MI_RoofTerracotta": (0.62, 0.20, 0.08), "MI_RoofGreen": (0.18, 0.36, 0.13), "MI_RoofBlue": (0.10, 0.25, 0.50),
          "MI_FlowerBed": (0.85, 0.30, 0.45), "MI_Brass": (0.60, 0.42, 0.10), "MI_Foliage": (0.20, 0.40, 0.10),
          "MI_FoliageBlossom": (0.75, 0.45, 0.55), "MI_Sailcloth": (0.85, 0.80, 0.65), "MI_CliffRock": (0.35, 0.29, 0.25)}

bpy.ops.wm.read_factory_settings(use_empty=True)
files = sorted(f for f in os.listdir(KIT) if f.endswith(".fbx"))
x = 0.0
for f in files:
    bpy.ops.import_scene.fbx(filepath=os.path.join(KIT, f))
    for o in bpy.context.selected_objects:
        o.location.x = x
        for s in o.material_slots:
            if s.material:
                s.material.diffuse_color = (*COLORS.get(s.material.name.split(".")[0], (0.5, 0.5, 0.5)), 1)
    x += 11.0
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
bpy.context.scene.collection.objects.link(cam)
cam.location = (x / 2 - 5, -95, 30)
cam.rotation_euler = (math.radians(72), 0, 0)
cam.data.lens = 20
bpy.context.scene.camera = cam
sc = bpy.context.scene
sc.render.engine = "BLENDER_WORKBENCH"
sc.display.shading.color_type = "MATERIAL"
sc.display.shading.light = "STUDIO"
sc.display.shading.show_shadows = True
sc.render.resolution_x, sc.render.resolution_y = 1600, 700
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)
print("LS_PREVIEW_OK " + OUT)
