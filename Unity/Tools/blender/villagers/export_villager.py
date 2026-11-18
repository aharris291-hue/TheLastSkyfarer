"""Game export for a villager built with the Kieran pipeline (build_<name>.py), using the Unreal-era finalize script
(Unreal/Tools/blender/kieran/finalize_kieran.py, read only) with the Unity fixes and the names swapped:
hem piping skinned from its garment, thin trim kept out of decimation, a 32k-triangle budget, no preview renders.

  blender --background <Name_Master.blend> --python export_villager.py -- <finalize_kieran.py> <out dir> <Name> <Export_Name>
e.g.  ... Bram_Holloway_Master.blend ... -- finalize_kieran.py <out> Bram Bram_Holloway
"""
import os
import sys

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT, NAME, EXPORT = args[0], args[1], args[2], args[3]
os.makedirs(OUT, exist_ok=True)
code = open(SRC, encoding="utf-8").read()


def patch(old, new, count=1):
    global code
    if old not in code:
        raise SystemExit("LS_PATCH missing: " + old[:60])
    code = code.replace(old, new, count)


patch('REND = os.path.join(KDIR, "renders")', 'REND = os.path.join(%r, "renders")' % OUT)
patch('EXP = os.path.join(KDIR, "export")', 'EXP = %r' % OUT)
patch('def render(name, yaw, res=(800, 1200), pad=1.06):\n', 'def render(name, yaw, res=(800, 1200), pad=1.06):\n    return ""\n')
patch("        dt.object = body\n", "        dt.object = src\n")
patch('curve_objs = [o for o in sc.objects if o.type == "CURVE"]\n',
      'for o in sc.objects:\n'
      '    if o.type == "CURVE" and (o.name.endswith("_hem") or o.get("weights_from") or "strap" in o.name):\n'
      '        o.data.bevel_resolution = 0\n'
      '        o["thin"] = 1\n'
      'curve_objs = [o for o in sc.objects if o.type == "CURVE"]\n')
patch('prot = sum(tri_count(o) for o in game_parts if any(k in o.name for k in PROTECT))',
      'prot = sum(tri_count(o) for o in game_parts if any(k in o.name for k in PROTECT) or o.get("thin"))')
patch('rest = [o for o in game_parts if not any(k in o.name for k in PROTECT)]',
      'rest = [o for o in game_parts if not any(k in o.name for k in PROTECT) and not o.get("thin")]')
patch('TARGET = 45000', 'TARGET = 32000')
patch('bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KDIR, "Kieran_Thorn_GameReady_scene.blend"), copy=True)',
      'bpy.ops.wm.save_as_mainfile(filepath=os.path.join(%r, "%s_GameReady_scene.blend"), copy=True)' % (OUT, EXPORT))
patch('REPORT["atlas"] = atlas.filepath_raw\n', 'REPORT["atlas"] = atlas.filepath_raw\n# Unity polish pass 3: a mask in the same layout for the character shader (R hair, G skin, B eyes).\nmask_img = bpy.data.images.new("T_Mask", 2048, 2048, alpha=False)\ndef _mask_colour(m):\n    n = m.name.lower()\n    if any(k in n for k in ("hair", "beard", "eyebrow", "eyelash", "coils", "braid", "bun", "ponytail")):\n        return (1.0, 0.0, 0.0, 1.0)\n    if any(k in n for k in ("eye", "cornea", "high-poly", "iris", "pupil")):\n        return (0.0, 0.0, 1.0, 1.0)\n    if any(k in n for k in ("skin", "teeth", "tongue", ".body")):\n        return (0.0, 1.0, 0.0, 1.0)\n    return (0.0, 0.0, 0.0, 1.0)\nfor m in game.data.materials:\n    if not m or not m.use_nodes:\n        continue\n    nt = m.node_tree\n    for n in nt.nodes:\n        if n.type == "TEX_IMAGE" and n.image == atlas:\n            n.image = mask_img\n    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)\n    if out:\n        b = nt.nodes.new("ShaderNodeBsdfPrincipled")\n        b.inputs["Base Color"].default_value = _mask_colour(m)\n        nt.links.new(b.outputs[0], out.inputs["Surface"])\nbpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True, target="IMAGE_TEXTURES")\nmask_img.filepath_raw = os.path.splitext(atlas.filepath_raw)[0].replace("BaseColor", "Mask") + ".png"\nmask_img.file_format = "PNG"\nmask_img.save()\nprint("LS_MASK", mask_img.filepath_raw, flush=True)\n')
patch('hair = bpy.data.objects.get("Kieran_hair_coils")', 'for _o in [o for o in sc.objects if o.name.endswith(("_hair_coils", "_strands"))]:\n    bpy.data.objects.remove(_o, do_unlink=True)   # Unity pass 3: decimation shattered these; the shader draws strands\nhair = bpy.data.objects.get("Kieran_hair_coils")')
patch('atlas = bpy.data.images.new("T_Kieran_BaseColor", 2048, 2048, alpha=False)', 'atlas = bpy.data.images.new("T_Kieran_BaseColor", 4096, 4096, alpha=False)   # Unity pass 3: sharper eyes and faces')
code = code.split("# ------------------------------------------------------------------ 4b. QA sheet")[0]
# names: the rig, the body and the part prefixes
code = code.replace('"Kieran_Rig"', '"%s_Rig"' % NAME).replace('"Kieran.body"', '"%s.body"' % NAME)
code = code.replace('Kieran_Thorn_GameReady', EXPORT + "_GameReady").replace('"Kieran_GameReady"', '"%s_GameReady"' % NAME)
code = code.replace('"Kieran_hair', '"%s_hair' % NAME).replace('"Kieran_', '"%s_' % NAME).replace("startswith(\"Kieran\")", "startswith(\"%s\")" % NAME)
code = code.replace('("Kieran_jacket", "Kieran_trousers", "Kieran_shirt")', '("%s_shirt", "%s_trousers", "%s_apron")' % (NAME, NAME, NAME))
code = code.replace('"T_Kieran_BaseColor.png"', '"T_%s_BaseColor.png"' % NAME)
exec(compile(code, SRC, "exec"), {"__name__": "__main__", "__file__": SRC})
print("LS_VILLAGER_EXPORT_OK", OUT, flush=True)
