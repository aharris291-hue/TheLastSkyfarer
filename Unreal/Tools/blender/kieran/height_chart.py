"""Render Kieran beside a 1.73 m (5 ft 8 in) scale bar with 10 cm ticks, front and side.

  blender --background <Kieran_Thorn_Master.blend> --python height_chart.py
"""
import math
import os

import bpy
from mathutils import Vector

KDIR = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "SourceArt", "Characters", "Kieran"))
sc = bpy.context.scene
sc.view_settings.view_transform = "Standard"
sc.view_settings.exposure = -1.6


def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*rgb, 1)
    return m


body = bpy.data.objects["Kieran.body"]
zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
height = max(zs) - min(zs)
dark, light = mat("bar_dark", (0.05, 0.05, 0.05)), mat("bar_light", (0.9, 0.9, 0.9))
x0 = 0.42
for k in range(18):   # alternating 10 cm blocks up to 1.7 m, then the last 3 cm
    z0 = k * 0.1
    z1 = min(z0 + 0.1, 1.73)
    if z0 >= 1.73:
        break
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x0, 0, (z0 + z1) / 2))
    o = bpy.context.active_object
    o.scale = (0.03, 0.03, z1 - z0)
    o.data.materials.append(dark if k % 2 == 0 else light)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0.0, 0, 1.73))
top = bpy.context.active_object
top.scale = (0.9, 0.004, 0.003)
top.data.materials.append(mat("bar_red", (0.8, 0.1, 0.05)))
for txt, z in (("1.73 m / 5 ft 8 in", 1.75), ("Kieran, measured %.2f m barefoot" % height, 1.84)):
    bpy.ops.object.text_add(location=(-0.42, -0.05, z), rotation=(math.radians(90), 0, 0))
    t = bpy.context.active_object
    t.data.body = txt
    t.data.size = 0.05
    t.data.materials.append(light)
cam = bpy.data.objects.get("LookCam")
sc.camera = cam
cam.data.ortho_scale = 2.05
sc.render.resolution_x, sc.render.resolution_y = 1000, 1100
for name, yaw in (("Kieran_HeightChart_Front", 0), ("Kieran_HeightChart_Side", 90)):
    a = math.radians(yaw)
    cam.location = (10 * math.sin(a), -10 * math.cos(a), 0.95)
    cam.rotation_euler = (math.radians(90), 0, a)
    sc.render.filepath = os.path.join(KDIR, "renders", name + ".png")
    bpy.ops.render.render(write_still=True)
    print("LS_CHART", sc.render.filepath, flush=True)
