"""Imports the synthesised sounds (Tools/blender/synth_sounds.py, Unreal/SourceArt/Audio) into /Game/LastSkyfarer/Audio and
sets up the mixing groundwork: sound classes (Master > Music, SFX, Ambience, Dialogue, UI), matching submixes, the
settings sound mix the volume sliders drive, and attenuation for the placed ambience. Re-running replaces everything.

  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script=<abs path> -unattended -nullrhi
"""
import os

import unreal

ROOT = "/Game/LastSkyfarer/Audio"
PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJECT, "SourceArt", "Audio")
tools = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary


def fresh_asset(name, folder, cls, factory):
    path = folder + "/" + name
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    return tools.create_asset(name, folder, cls, factory)


# ------------------------------------------------------------------ classes and submixes
classes = {}
master = fresh_asset("SC_Master", ROOT + "/Mix", unreal.SoundClass, unreal.SoundClassFactory())
classes["Master"] = master
for name in ("Music", "SFX", "Ambience", "Dialogue", "UI"):
    sc = fresh_asset("SC_" + name, ROOT + "/Mix", unreal.SoundClass, unreal.SoundClassFactory())
    sc.set_editor_property("parent_class", master)
    classes[name] = sc
    EAL.save_loaded_asset(sc)
master.set_editor_property("child_classes", [classes[n] for n in ("Music", "SFX", "Ambience", "Dialogue", "UI")])
EAL.save_loaded_asset(master)

submixes = {}
for name in ("Music", "SFX", "Ambience", "Dialogue", "UI"):
    sm = fresh_asset("SMX_" + name, ROOT + "/Mix", unreal.SoundSubmix, unreal.SoundSubmixFactory())
    submixes[name] = sm
    EAL.save_loaded_asset(sm)

mix = fresh_asset("SMix_Settings", ROOT + "/Mix", unreal.SoundMix, unreal.SoundMixFactory())
EAL.save_loaded_asset(mix)


def attenuation(name, inner_m, falloff_m):
    a = fresh_asset(name, ROOT + "/Mix", unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
    s = a.get_editor_property("attenuation")
    s.set_editor_property("attenuation_shape_extents", unreal.Vector(inner_m * 100, 0, 0))
    s.set_editor_property("falloff_distance", falloff_m * 100)
    a.set_editor_property("attenuation", s)
    EAL.save_loaded_asset(a)


attenuation("ATT_Ambience", 40, 140)
attenuation("ATT_Windmill", 12, 140)
attenuation("ATT_Room", 9, 8)

# ------------------------------------------------------------------ sounds
GROUPS = [("wind_", "Wind", "SFX"), ("glide", "Glide", "SFX"), ("step_", "Footsteps", "SFX"), ("windmill", "World", "SFX"),
          ("village", "Ambience", "Ambience"), ("workshop", "Ambience", "Ambience"), ("ui_", "UI", "UI")]
tasks = []
for f in sorted(os.listdir(SRC)):
    if not f.endswith(".wav"):
        continue
    folder = next(g[1] for g in GROUPS if f.startswith(g[0]))
    t = unreal.AssetImportTask()
    t.filename = os.path.join(SRC, f)
    t.destination_path = ROOT + "/" + folder
    t.replace_existing = True
    t.automated = True
    t.save = True
    tasks.append(t)
tools.import_asset_tasks(tasks)

count = 0
for t in tasks:
    base = os.path.splitext(os.path.basename(t.filename))[0]
    group = next(g for g in GROUPS if base.startswith(g[0]))
    w = unreal.load_asset(t.destination_path + "/" + base)
    if not w:
        raise RuntimeError("import failed: " + base)
    w.set_editor_property("looping", base.endswith("_loop"))
    w.set_editor_property("sound_class_object", classes[group[2]])
    w.set_editor_property("sound_submix_object", submixes[group[2]])
    EAL.save_loaded_asset(w)
    count += 1
unreal.log("LS_IMPORT_AUDIO_OK %d sounds" % count)
