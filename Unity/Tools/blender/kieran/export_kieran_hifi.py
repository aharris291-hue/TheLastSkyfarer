"""Kieran fidelity overhaul: the Unity export (export_kieran_unity.py and its fixes) with the high-poly build and the
bakes from kieran_hifi.py patched in. The master and the Unreal scripts are only read.

  blender --background "<repo>/Unreal/SourceArt/Characters/Kieran/Kieran_Thorn_Master.blend" --python export_kieran_hifi.py -- \
      <Unreal finalize_kieran.py> <out dir> [map size, default 4096]

Outputs in <out dir>: Kieran_Thorn_GameReady.fbx (LOD0-2, same rig), T_Kieran_BaseColor.png (4096 atlas),
T_Kieran_Normal.png, T_Kieran_MetalAOSmooth.png (R metallic, G occlusion, A smoothness), T_Kieran_AO.png,
T_Kieran_Mask.png and the export report.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
args = sys.argv[sys.argv.index("--") + 1:]
SIZE = int(args[2]) if len(args) > 2 else 4096

base = open(os.path.join(HERE, "export_kieran_unity.py"), encoding="utf-8").read()
base = base.split("exec(compile(code")[0]          # all of the Unity export's patches, without running it yet
g = {"__name__": "ls_unity_export", "__file__": os.path.join(HERE, "export_kieran_unity.py")}
exec(compile(base, "export_kieran_unity.py", "exec"), g)
patch = g["patch"]

# 1. Before the game copy: relink the MPFB textures, add the fabric/leather/skin relief, stitch the seams and grow
#    the hair clumps.
patch("# ------------------------------------------------------------------ 2. game copy\n",
      "# ------------------------------------------------------------------ 2. game copy\n"
      "import kieran_hifi as HF\n"
      "HF.fix_mpfb_paths()\n"
      "HF.add_all_relief()\n"
      "HF.build_stitches(sc)\n"
      "HF.build_hair()\n")
# 2. Game-mesh subdivision: the scarf, satchel, gloves and boots keep one level (they were flattened to their cages).
patch('m.levels = 0 if not o.name.startswith(("Kieran_jacket", "Kieran_trousers", "Kieran_shirt")) else 1',
      'm.levels = 1 if o.name.startswith(("Kieran_jacket", "Kieran_trousers", "Kieran_shirt", "Kieran_scarf", "Kieran_satchel", '
      '"Kieran_gloves", "Kieran_boots")) else 0')
# 3. Each game part: folds where it bends, then its high-poly twin (not for the hair shell, brows or lashes).
patch("    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)\n",
      "    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)\n"
      "    HF.fold_mesh(o, me, rig, False)\n"
      "    if not o.name.startswith('Kieran_hair') and not any(k in o.name for k in ('eyebrow', 'eyelash')):\n"
      "        HF.hp_copy(o, rig)\n")
# 4. A larger budget for the hero character: about 62k triangles at LOD0.
patch('BUDGET = {"Kieran_hair": 9000, "Kieran_jacket": 6000, "Kieran_trousers": 4000, "Kieran_shirt": 2500, "Kieran_boots": 2000,',
      'BUDGET = {"Kieran_hair": 14000, "Kieran_jacket": 9000, "Kieran_trousers": 6000, "Kieran_shirt": 3500, "Kieran_boots": 3000,')
patch('"Kieran_bootfoot": 1200, "Kieran_sole": 500, "Kieran_gloves": 1500,', '"Kieran_bootfoot": 1400, "Kieran_sole": 600, "Kieran_gloves": 2600,')
patch('"Kieran_scarf": 1200,', '"Kieran_scarf": 2600,')
patch("TARGET = 45000", "TARGET = 85000")
# the main garments and the hair keep their own budgets above; only the small trims and props share what is left
patch('PROTECT = ("Kieran.body", "high-poly", "eyebrow", "eyelash")',
      'PROTECT = ("Kieran.body", "high-poly", "eyebrow", "eyelash", "Kieran_hair", "Kieran_jacket", "Kieran_trousers", '
      '"Kieran_shirt", "Kieran_boots", "Kieran_scarf", "Kieran_gloves")')
# the eyelashes are thousands of loose strands the decimator cannot reduce: keep 40% of them, evenly
patch("# then share what is left of a 45k-triangle budget",
      "for _o in game_parts:\n"
      "    if 'eyelash' in _o.name:\n"
      "        HF.thin_strands(_o, 0.4)\n"
      "# then share what is left of a 45k-triangle budget")
patch('print("LS_BUDGET protected %d, rest %d, ratio %.3f" % (prot, rest_n, ratio), flush=True)',
      'print("LS_BUDGET protected %d, rest %d, ratio %.3f" % (prot, rest_n, ratio), flush=True)\n'
      'print("LS_BUDGET parts", sorted(((tri_count(o), o.name) for o in game_parts), reverse=True)[:25], flush=True)')
# 4b. No vertex without skin weights (they stretched into lines from the shoulders when he moved).
patch("for vg in list(game.vertex_groups):\n    if vg.name not in bone_names:\n        game.vertex_groups.remove(vg)\n",
      "for vg in list(game.vertex_groups):\n    if vg.name not in bone_names:\n        game.vertex_groups.remove(vg)\n"
      "HF.fill_empty_weights(game, bone_names)\n")
# 4c. Trim that was never attached to the skeleton (sleeve seams and the like) was pinned to the pelvis and stayed
#     behind when the arms moved, drawing lines from the shoulders: it takes its weights from the garment it sits on.
patch('        vg = o.vertex_groups.new(name="pelvis")\n',
      '        o["weights_from"] = "Kieran_jacket" if ("jacket" in o.name or "sleeve" in o.name) else '
      '"Kieran_trousers" if "trouser" in o.name else "Kieran.body"\n'
      '        vg = o.vertex_groups.new(name="pelvis")\n')
# 5. More texture space for the face and hands.
patch("bpy.ops.uv.average_islands_scale()\n", "bpy.ops.uv.average_islands_scale()\nHF.hair_uvs(game)\nHF.prioritise_uvs(game)\n")
# 6. The bakes, straight after the colour atlas and before the mask pass rewires the materials.
patch('REPORT["atlas"] = atlas.filepath_raw\n', 'REPORT["atlas"] = atlas.filepath_raw\nHF.bake_maps(sc, game, EXP, %d)\n' % SIZE)
# 7. LODs, exported together; normals exported as baked (Unity imports them, so the normal map matches).
patch('for o in sc.objects:\n    o.select_set(o in (game, rig))\nglb =',
      'LODS = HF.make_lods(game, rig)\nfor o in sc.objects:\n    o.select_set(o in LODS or o == rig)\nglb =')
patch("for o in (rig, game):\n    o.select_set(True)\n", "for o in [rig] + LODS:\n    o.select_set(True)\n")
patch("game.parent = None\nrig.scale = (100, 100, 100)\ngame.scale = (100, 100, 100)\n"
      "bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)\ngame.parent = rig\n",
      "for _l in LODS:\n    _l.parent = None\n    _l.scale = (100, 100, 100)\nrig.scale = (100, 100, 100)\n"
      "bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)\nfor _l in LODS:\n    _l.parent = rig\n")
patch('mesh_smooth_type="FACE"', 'mesh_smooth_type="OFF"')

code = g["code"]
exec(compile(code, g["SRC"], "exec"), {"__name__": "__main__", "__file__": g["SRC"]})
print("LS_HIFI_EXPORT_OK", g["OUT"], flush=True)
