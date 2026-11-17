"""Re-exports Kieran's game-ready model for Unity from the Blender master, using the Unreal-era pipeline
(Unreal/Tools/blender/kieran/finalize_kieran.py, read-only reference) with Unity fixes applied on the fly:

  * hem piping takes its skin weights from the garment it trims, not the nearest body surface, so the thin trim lines
    on the jacket and sleeves no longer stretch towards the hands and legs when he moves;
  * thin trim (hem piping, seams, straps) is kept as simple four-sided tubes and left out of the triangle-budget
    decimation, which had collapsed it into loose slivers that looked like stretched lines;
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
code = code.split("# ------------------------------------------------------------------ 4b. QA sheet")[0]
exec(compile(code, SRC, "exec"), {"__name__": "__main__", "__file__": SRC})
print("LS_UNITY_EXPORT_OK", OUT, flush=True)
