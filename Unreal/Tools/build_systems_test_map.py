"""Builds the greybox systems test map /Game/LastSkyfarer/Maps/Test/L_SystemsTest.

Run headless from the repo root:
  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script="<abs path>/Unreal/Tools/build_systems_test_map.py" -unattended -nullrhi

Layout (cm, Z up): Island A (start) with a ramp up to a cliff; Island B (landing area) 300 m east and
40 m lower; a visible current between them, two updrafts, one hidden current that Piko reveals.
Falling below -200 m returns Kieran to the last safe ledge (ALSPlayerCharacter.RecoveryZ).
"""
import unreal

MAP = "/Game/LastSkyfarer/Maps/Test/L_SystemsTest"
CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
PLANE = unreal.load_asset("/Engine/BasicShapes/Plane.Plane")

level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    unreal.EditorAssetLibrary.delete_asset(MAP)
level_subsystem.new_level(MAP)


def block(label, center, size_m, rot=(0, 0, 0), collision=True):
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*center), unreal.Rotator(*rot))
    a.set_actor_label(label)
    comp = a.static_mesh_component
    comp.set_static_mesh(CUBE)
    a.set_actor_scale3d(unreal.Vector(*size_m))  # the engine cube is 1 m
    if not collision:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def wind(label, kind, points, strength, radius=600.0, hidden=False):
    a = actors.spawn_actor_from_class(unreal.WindVolume, unreal.Vector(*points[0]), unreal.Rotator(0, 0, 0))
    a.set_actor_label(label)
    a.set_editor_property("wind_type", kind)
    a.set_editor_property("strength", strength)
    a.set_editor_property("radius", radius)
    a.set_editor_property("starts_hidden", hidden)
    spline = a.get_component_by_class(unreal.SplineComponent)
    spline.clear_spline_points(False)
    for p in points:
        spline.add_spline_point(unreal.Vector(*p), unreal.SplineCoordinateSpace.WORLD, False)
    spline.update_spline()
    a.rebuild_visual()
    return a


# Lighting
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 5000), unreal.Rotator(-35, 0, 40))
sun.set_actor_label("Sun")
sun.light_component.set_editor_property("atmosphere_sun_light", True)
actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)).set_actor_label("SkyAtmosphere")
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 3000))
sky.set_actor_label("SkyLight")
sky.light_component.set_editor_property("real_time_capture", True)
actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -2000)).set_actor_label("Fog")

# Island A: 60 x 60 m, top at Z = 0
block("IslandA", (0, 0, -1000), (60, 60, 20))
# Cliff on the east side of A: top at 15 m, east face at X = 25 m
block("IslandA_Cliff", (2000, 0, 750), (10, 20, 15))
# Ramp up the west side of the cliff (30 m at 30 degrees)
block("IslandA_Ramp", (200, 0, 750), (30, 6, 0.5), rot=(30, 0, 0))
# Ledge to jump to from the cliff
block("IslandA_Ledge", (2000, 1600, 1200), (4, 3, 0.5))

# Island B (landing area): 300 m east, top 40 m lower
block("IslandB_Landing", (30000, 0, -5000), (40, 40, 20))
block("IslandB_Marker", (30000, 0, -3950), (6, 6, 0.1))

# Cloud sea visual (no collision); recovery triggers at -200 m
sea = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(15000, 0, -15000), unreal.Rotator(0, 0, 0))
sea.set_actor_label("CloudSea_Visual")
sea.static_mesh_component.set_static_mesh(PLANE)
sea.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
sea.set_actor_scale3d(unreal.Vector(1000, 1000, 1))

# Wind
wind("Current_AtoB", unreal.WindVolumeType.CURRENT, [(4000, 0, 500), (14000, 500, 400), (24000, 0, 300)], 14.0, 700.0)
wind("Updraft_Cliff", unreal.WindVolumeType.UPDRAFT, [(4500, 2500, -3000), (4500, 2500, 3000)], 7.0, 500.0)
wind("Updraft_IslandB", unreal.WindVolumeType.UPDRAFT, [(25500, -2500, -6000), (25500, -2500, 0)], 6.0, 500.0)
wind("Hidden_Current", unreal.WindVolumeType.CURRENT, [(4000, -3000, 1200), (12000, -4500, 1600), (20000, -3000, 1800)], 12.0, 600.0, hidden=True)

# Player start on island A
start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-1500, 0, 120), unreal.Rotator(0, 0, 0))
start.set_actor_label("PlayerStart")

world = unreal.EditorLevelLibrary.get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", unreal.LSTestGameMode.static_class())

level_subsystem.save_current_level()
unreal.log("LS_BUILD_MAP_OK " + MAP)
