"""Re-exports Kieran's game-ready model for Unity from the Blender master, using the Unreal-era pipeline
(Unreal/Tools/blender/kieran/finalize_kieran.py, read-only reference) with Unity fixes applied on the fly:

  * hem piping takes its skin weights from the garment it trims, not the nearest body surface, so the thin trim lines
    on the jacket and sleeves no longer stretch towards the hands and legs when he moves;
  * thin trim (hem piping, seams, straps) is kept as simple four-sided tubes and left out of the triangle-budget
    decimation, which had collapsed it into loose slivers that looked like stretched lines;
  * a hair / skin / eye mask is baked in the atlas layout (T_<Name>_Mask.png) for the character shader;
  * outputs go to Unity/SourceArt/Characters/Kieran/export (the Unreal export folder is left untouched);
  * the slow preview renders and the turnaround QA sheet are skipped.

  blender --background "<repo with LFS>/Unreal/SourceArt/Characters/Kieran/Kieran_Thorn_Master.blend" --python export_kieran_unity.py -- <Unreal finalize_kieran.py> <out dir>
"""
import os
import sys

args = sys.argv[sys.argv.index("--") + 1:]
SRC, OUT = args[0], args[1]
os.makedirs(OUT, exist_ok=True)
code = open(SRC, encoding="utf-8").read()


def patch(old, new):
    global code
    if old not in code:
        raise SystemExit("LS_PATCH missing: " + old[:60])
    code = code.replace(old, new, 1)


patch('REND = os.path.join(KDIR, "renders")', 'REND = os.path.join(%r, "renders")' % OUT)
patch('EXP = os.path.join(KDIR, "export")', 'EXP = %r' % OUT)
patch('def render(name, yaw, res=(800, 1200), pad=1.06):\n', 'def render(name, yaw, res=(800, 1200), pad=1.06):\n    return ""\n')
patch("        dt.object = body\n", "        dt.object = src   # Unity fix: the garment's own weights\n")
patch('bpy.ops.wm.save_as_mainfile(filepath=os.path.join(KDIR, "Kieran_Thorn_GameReady_scene.blend"), copy=True)',
      'bpy.ops.wm.save_as_mainfile(filepath=os.path.join(%r, "Kieran_Thorn_GameReady_scene.blend"), copy=True)' % OUT)
patch('curve_objs = [o for o in sc.objects if o.type == "CURVE"]\n',
      'for o in sc.objects:   # Unity fix: thin trim stays a clean tube\n'
      '    if o.type == "CURVE" and (o.name.endswith("_hem") or o.get("weights_from") or "strap" in o.name):\n'
      '        o.data.bevel_resolution = 0\n'
      '        o["thin"] = 1\n'
      'curve_objs = [o for o in sc.objects if o.type == "CURVE"]\n')
patch('"_hem": 600,', '"_hem": 2400,')
patch('prot = sum(tri_count(o) for o in game_parts if any(k in o.name for k in PROTECT))',
      'prot = sum(tri_count(o) for o in game_parts if any(k in o.name for k in PROTECT) or o.get("thin"))')
patch('rest = [o for o in game_parts if not any(k in o.name for k in PROTECT)]',
      'rest = [o for o in game_parts if not any(k in o.name for k in PROTECT) and not o.get("thin")]')
patch('REPORT["atlas"] = atlas.filepath_raw\n', 'REPORT["atlas"] = atlas.filepath_raw\n# Unity polish pass 3: a mask in the same layout for the character shader (R hair, G skin, B eyes).\nmask_img = bpy.data.images.new("T_Mask", 2048, 2048, alpha=False)\ndef _mask_colour(m):\n    n = m.name.lower()\n    if any(k in n for k in ("hair", "beard", "eyebrow", "eyelash", "coils", "braid", "bun", "ponytail")):\n        return (1.0, 0.0, 0.0, 1.0)\n    if any(k in n for k in ("eye", "cornea", "high-poly", "iris", "pupil")):\n        return (0.0, 0.0, 1.0, 1.0)\n    if any(k in n for k in ("skin", "teeth", "tongue", ".body")):\n        return (0.0, 1.0, 0.0, 1.0)\n    return (0.0, 0.0, 0.0, 1.0)\nfor m in game.data.materials:\n    if not m or not m.use_nodes:\n        continue\n    nt = m.node_tree\n    for n in nt.nodes:\n        if n.type == "TEX_IMAGE" and n.image == atlas:\n            n.image = mask_img\n    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None)\n    if out:\n        b = nt.nodes.new("ShaderNodeBsdfPrincipled")\n        b.inputs["Base Color"].default_value = _mask_colour(m)\n        nt.links.new(b.outputs[0], out.inputs["Surface"])\nbpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True, target="IMAGE_TEXTURES")\nmask_img.filepath_raw = os.path.splitext(atlas.filepath_raw)[0].replace("BaseColor", "Mask") + ".png"\nmask_img.file_format = "PNG"\nmask_img.save()\nprint("LS_MASK", mask_img.filepath_raw, flush=True)\n')
patch('hair = bpy.data.objects.get("Kieran_hair_coils")', 'for _o in [o for o in sc.objects if o.name.endswith(("_hair_coils", "_strands"))]:\n    bpy.data.objects.remove(_o, do_unlink=True)   # Unity pass 3: decimation shattered these; the shader draws strands\nhair = bpy.data.objects.get("Kieran_hair_coils")')
patch('atlas = bpy.data.images.new("T_Kieran_BaseColor", 2048, 2048, alpha=False)', 'atlas = bpy.data.images.new("T_Kieran_BaseColor", 4096, 4096, alpha=False)   # Unity pass 3: sharper eyes and faces')
code = code.split("# ------------------------------------------------------------------ 4b. QA sheet")[0]
exec(compile(code, SRC, "exec"), {"__name__": "__main__", "__file__": SRC})
print("LS_UNITY_EXPORT_OK", OUT, flush=True)
