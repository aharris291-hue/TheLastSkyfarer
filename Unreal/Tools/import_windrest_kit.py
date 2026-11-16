"""Imports the Windrest kit FBX files (Tools/blender/build_windrest_kit.py) into /Game/LastSkyfarer/Environments/Brindle/Meshes
and gives each material slot the painterly instance it is named after. Re-running replaces the meshes.

  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script=<abs path> -unattended -nullrhi
"""
import os

import unreal

DEST = "/Game/LastSkyfarer/Environments/Brindle/Meshes"
MATS = "/Game/LastSkyfarer/Materials/Instances/"
PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
SRC = os.path.join(PROJECT, "SourceArt", "Meshes", "Windrest")

tasks = []
for f in sorted(os.listdir(SRC)):
    if not f.lower().endswith(".fbx"):
        continue
    ui = unreal.FbxImportUI()
    ui.import_mesh = True
    ui.import_as_skeletal = False
    ui.import_materials = False
    ui.import_textures = False
    ui.import_animations = False
    ui.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    sm = ui.static_mesh_import_data
    sm.combine_meshes = True
    sm.auto_generate_collision = False
    sm.generate_lightmap_u_vs = False
    sm.import_uniform_scale = 1.0
    t = unreal.AssetImportTask()
    t.filename = os.path.join(SRC, f)
    t.destination_path = DEST
    t.replace_existing = True
    t.automated = True
    t.save = True
    t.options = ui
    tasks.append(t)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)

for t in tasks:
    name = os.path.splitext(os.path.basename(t.filename))[0]
    mesh = unreal.load_asset(DEST + "/" + name)
    if not mesh:
        raise RuntimeError("import failed: " + name)
    for i, slot in enumerate(mesh.static_materials):
        slot_name = str(slot.material_slot_name)
        mi = unreal.load_asset(MATS + slot_name.split(".")[0])
        if mi:
            mesh.set_material(i, mi)
        else:
            unreal.log_warning("LS_KIT no material for slot " + slot_name + " on " + name)
    # Kit pieces are visual only; the greybox shapes underneath keep the collision gameplay was built on.
    unreal.EditorAssetLibrary.save_loaded_asset(mesh)
    b = mesh.get_bounding_box()
    unreal.log("LS_KIT %s size %.1f x %.1f x %.1f m, %d materials" % (name, (b.max.x - b.min.x) / 100, (b.max.y - b.min.y) / 100,
                                                                       (b.max.z - b.min.z) / 100, len(mesh.static_materials)))
unreal.log("LS_IMPORT_KIT_OK")
