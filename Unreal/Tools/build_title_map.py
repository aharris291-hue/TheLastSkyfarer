"""Builds the placeholder title screen map: /Game/LastSkyfarer/Maps/Title/L_Title.

A dawn sky with Brindle Isle floating over the cloud sea, seen by one camera; the title menu (ULSTitleWidget)
is drawn over it by ALSTitleGameMode. Greybox only.

Run headless (the path must not contain spaces; copy the script somewhere first if needed):
  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script=<abs path to this file> -unattended -nullrhi
"""
import unreal

MAP = "/Game/LastSkyfarer/Maps/Title/L_Title"
CYL = unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
CONE = unreal.load_asset("/Engine/BasicShapes/Cone.Cone")
CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
PLANE = unreal.load_asset("/Engine/BasicShapes/Plane.Plane")

level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
M = 100.0


def v(x, y, z=0.0):
    return unreal.Vector(x * M, y * M, z * M)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    """unreal.Rotator takes (roll, pitch, yaw) positionally; always build it by name."""
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def shape(label, mesh, center, size, roll=0.0, yaw=0.0):
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, v(*center), rot(yaw=yaw, roll=roll))
    a.set_actor_label(label)
    a.static_mesh_component.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(*size))
    return a


# Delete Content/LastSkyfarer/Maps/Title/L_Title.umap before re-running.
if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    unreal.EditorAssetLibrary.delete_asset(MAP)
if not level_subsystem.new_level(MAP):
    raise RuntimeError("Could not create %s; delete the old map file and run again" % MAP)

# Dawn: pale gold horizon over a lilac cloud sea (STYLE_GUIDE colour script 5).
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, v(0, 0, 300), rot(pitch=-6, yaw=100))
sun.set_actor_label("Sun")
sun.light_component.set_editor_property("atmosphere_sun_light", True)
sun.light_component.set_light_color(unreal.LinearColor(1.0, 0.78, 0.62, 1.0))
sun.light_component.set_intensity(4.0)
actors.spawn_actor_from_class(unreal.SkyAtmosphere, v(0, 0, 0)).set_actor_label("SkyAtmosphere")
sky = actors.spawn_actor_from_class(unreal.SkyLight, v(0, 0, 200))
sky.set_actor_label("SkyLight")
sky.light_component.set_editor_property("real_time_capture", True)
fog = actors.spawn_actor_from_class(unreal.ExponentialHeightFog, v(0, 0, -100))
fog.set_actor_label("Fog")
fog.component.set_fog_inscattering_color(unreal.LinearColor(0.78, 0.68, 0.88, 1.0))
fog.component.set_fog_density(0.02)
actors.spawn_actor_from_class(unreal.VolumetricCloud, v(0, 0, 0)).set_actor_label("VolumetricCloud")

# Brindle Isle in the distance: top, rocky underside, the Bluff, Skywatch hill, a windmill and the tower.
shape("Isle_Top", CYL, (0, 0, -20), (1150, 1400, 40))
shape("Isle_Underside", CONE, (0, 0, -120), (1050, 1300, 160), roll=180)
shape("Isle_Bluff", CUBE, (60, 600, 10), (140, 160, 20))
shape("Isle_Skywatch", CUBE, (470, 40, 12.5), (60, 60, 25))
shape("Isle_Tower", CYL, (130, 640, 35), (6, 6, 30))
shape("Isle_Windmill", CYL, (300, -280, 9), (6, 6, 18))
shape("Isle_Small", CUBE, (60, 920, -5), (30, 30, 6))
shape("CloudSea", PLANE, (0, 0, -260), (8000, 8000, 1))

cam = actors.spawn_actor_from_class(unreal.CameraActor, v(-1500, 1700, 120), rot(pitch=-4, yaw=-58))
cam.set_actor_label("TitleCamera")
cam.camera_component.set_editor_property("field_of_view", 60.0)

world = unreal.EditorLevelLibrary.get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", unreal.LSTitleGameMode.static_class())

if not level_subsystem.save_current_level():
    raise RuntimeError("Could not save " + MAP)
unreal.log("LS_BUILD_MAP_OK " + MAP)
