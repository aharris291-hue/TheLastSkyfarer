"""TEST ONLY: import the draft Kieran into /Game/LastSkyfarer/TestOnly/Kieran and retarget the mannequin's idle, walk,
jog and fall (glide stand-in) animations onto him, for an in-game performance check. Nothing here is referenced by the
shipped maps; the TestOnly folder is never cooked unless a test build asks for it.

  UnrealEditor-Cmd.exe LastSkyfarer.uproject -run=pythonscript -script=import_kieran_test.py
"""
import os

import unreal

REPO = os.path.dirname(os.path.abspath(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).rstrip("/\\"))
EXP = os.path.join(REPO, "Unreal", "SourceArt", "Characters", "Kieran", "export")
DST = "/Game/LastSkyfarer/TestOnly/Kieran"
AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary


def get_or_create(name, cls, factory):
    path = DST + "/" + name
    a = unreal.load_asset(path) if EAL.does_asset_exist(path) else None
    return a or AT.create_asset(name, DST, cls, factory)


def log(*a):
    unreal.log("LS_KIERAN " + " ".join(str(x) for x in a))


for path in (DST,):
    if EAL.does_directory_exist(path):
        EAL.delete_directory(path)
    EAL.make_directory(path)

# 1. texture and a simple material that shows the baked painted atlas
t = unreal.AssetImportTask()
t.filename = os.path.join(EXP, "T_Kieran_BaseColor.png")
t.destination_path = DST
t.automated, t.save, t.replace_existing = True, True, True
AT.import_asset_tasks([t])
tex = unreal.load_asset(DST + "/T_Kieran_BaseColor")
tex.set_editor_property("never_stream", True)                # keep full detail: a streamed atlas averages to flat grey
tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_CHARACTER)
EAL.save_loaded_asset(tex)
MEL = unreal.MaterialEditingLibrary


def make_mat(name, metallic, rough):
    """Fresh material every run (earlier runs stacked nodes into one asset): baked texture to base colour,
    with a little self-light so he never drops to a black silhouette in shade."""
    path = DST + "/" + name
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    m = AT.create_asset(name, DST, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("used_with_skeletal_mesh", True)   # without this the cooked game falls back to the grey default
    s_ = MEL.create_material_expression(m, unreal.MaterialExpressionTextureSample, -600, 0)
    s_.set_editor_property("texture", tex)
    MEL.connect_material_property(s_, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    lift = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 200)
    lift.set_editor_property("const_b", 0.04)
    MEL.connect_material_expressions(s_, "RGB", lift, "A")
    MEL.connect_material_property(lift, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    for prop, val, y in ((unreal.MaterialProperty.MP_METALLIC, metallic, 300), (unreal.MaterialProperty.MP_ROUGHNESS, rough, 400)):
        c = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, y)
        c.set_editor_property("r", val)
        MEL.connect_material_property(c, "", prop)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    return m


m_main = make_mat("M_KieranPaint", 0.0, 0.7)
m_metal = make_mat("M_KieranPaint_Metal", 1.0, 0.35)

# 2. the skeletal mesh with its own skeleton
opts = unreal.FbxImportUI()
opts.import_mesh = True
opts.import_as_skeletal = True
opts.import_materials = False
opts.import_textures = False
opts.import_animations = False
opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
t = unreal.AssetImportTask()
t.filename = os.path.join(EXP, "Kieran_Thorn_GameReady.fbx")
t.destination_path = DST
t.destination_name = "SK_KieranTest"
t.options = opts
t.automated, t.save, t.replace_existing = True, True, True
AT.import_asset_tasks([t])
mesh = unreal.load_asset(DST + "/SK_KieranTest")
log("mesh", mesh, "skeleton", mesh.skeleton if mesh else None)
new = []
for sm in mesh.get_editor_property("materials"):
    mi = m_metal if "Metal" in str(sm.material_slot_name) else m_main
    new.append(unreal.SkeletalMaterial(material_interface=mi, material_slot_name=sm.material_slot_name))
mesh.set_editor_property("materials", new)
EAL.save_loaded_asset(mesh)
log("slots", [(str(x.material_slot_name), x.material_interface.get_name()) for x in mesh.get_editor_property("materials")])

# 3. IK rigs and a retargeter from the UE5 mannequin to Kieran
src_mesh = unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple") or unreal.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple")
if src_mesh is None:
    for p in EAL.list_assets("/Game/Characters/Mannequins/Meshes", recursive=True):
        a = unreal.load_asset(p)
        if isinstance(a, unreal.SkeletalMesh):
            src_mesh = a
            break
log("source mesh", src_mesh)


def ik_rig(name, skm):
    rig = get_or_create(name, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(skm)
    ok = c.apply_auto_generated_retarget_definition()
    log(name, "auto retarget definition", ok, "chains", [ch.chain_name for ch in c.get_retarget_chains()])
    EAL.save_loaded_asset(rig)
    return rig


rig_src = ik_rig("IK_MannyTest", src_mesh)
rig_dst = ik_rig("IK_KieranTest", mesh)
rtg = get_or_create("RTG_Manny_to_KieranTest", unreal.IKRetargeter, unreal.IKRetargetFactory())
rc = unreal.IKRetargeterController.get_controller(rtg)
rc.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, rig_src)
rc.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, rig_dst)
try:
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
except Exception as e:
    log("auto_map_chains", e)
for fn in ("auto_align_all_bones",):
    try:
        getattr(rc, fn)(unreal.RetargetSourceOrTarget.TARGET)
        log(fn, "ok")
    except Exception as e:
        log(fn, "skipped", e)
EAL.save_loaded_asset(rtg)

anims = [unreal.load_asset(p) for p in ("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle",
                                        "/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd",
                                        "/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd",
                                        "/Game/Characters/Mannequins/Anims/Unarmed/Jump/MM_Fall_Loop")]
anims = [EAL.find_asset_data(a.get_path_name().split(".")[0]) for a in anims if a]
out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(assets_to_retarget=anims, source_mesh=src_mesh, target_mesh=mesh,
                                                             ik_retarget_asset=rtg, search="", replace="", prefix="", suffix="_Kieran",
                                                             target_path=DST)
log("retargeted", [str(a.asset_name) for a in out] if out else out)
for a in out or []:
    obj = a.get_asset()
    if obj:
        EAL.save_loaded_asset(obj)
log("done", EAL.list_assets(DST))
