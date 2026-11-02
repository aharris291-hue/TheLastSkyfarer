"""Builds the greybox systems test map /Game/LastSkyfarer/Maps/Test/L_SystemsTest.

Run headless from the repo root:
  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script="<abs path>/Unreal/Tools/build_systems_test_map.py" -unattended -nullrhi

Layout (cm, Z up): Island A (start) with a ramp up to a cliff; Island B (landing area) 300 m east and
40 m lower; a visible current between them, two updrafts, one hidden current that Piko reveals.
Falling below -200 m returns Kieran to the last safe ledge (ALSPlayerCharacter.RecoveryZ).
"""
import unreal


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    """unreal.Rotator takes (roll, pitch, yaw) positionally; always build it by name."""
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)

MAP = "/Game/LastSkyfarer/Maps/Test/L_SystemsTest"
CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
PLANE = unreal.load_asset("/Engine/BasicShapes/Plane.Plane")

level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

# The map is regenerated from scratch. Delete Content/LastSkyfarer/Maps/Test/L_SystemsTest.umap first
# if the asset registry still holds it (delete_asset can fail in a commandlet).
if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    unreal.EditorAssetLibrary.delete_asset(MAP)
if not level_subsystem.new_level(MAP):
    raise RuntimeError("Could not create %s; delete the old .umap file and run again" % MAP)


def block(label, center, size_m, pitch=0.0, collision=True):
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*center), rot(pitch=pitch))
    a.set_actor_label(label)
    comp = a.static_mesh_component
    comp.set_static_mesh(CUBE)
    a.set_actor_scale3d(unreal.Vector(*size_m))  # the engine cube is 1 m
    if not collision:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    return a


def wind(label, kind, points, strength, radius=600.0, hidden=False):
    a = actors.spawn_actor_from_class(unreal.WindVolume, unreal.Vector(*points[0]), rot())
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
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 5000), rot(pitch=-28, yaw=60))
sun.set_actor_label("Sun")
sun.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)  # the time-of-day director rotates it
sun.light_component.set_editor_property("atmosphere_sun_light", True)
actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0)).set_actor_label("SkyAtmosphere")
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 3000))
sky.set_actor_label("SkyLight")
sky.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property("real_time_capture", True)
actors.spawn_actor_from_class(unreal.ExponentialHeightFog, unreal.Vector(0, 0, -2000)).set_actor_label("Fog")

# Island A: 60 x 60 m, top at Z = 0
block("IslandA", (0, 0, -1000), (60, 60, 20))
# Cliff on the east side of A: top at 15 m, east face at X = 25 m
block("IslandA_Cliff", (2000, 0, 750), (10, 20, 15))
# Ramp up the west side of the cliff (30 m at 30 degrees)
block("IslandA_Ramp", (200, 0, 750), (30, 6, 0.5), pitch=30)
# Ledge to jump to from the cliff
block("IslandA_Ledge", (2000, 1600, 1200), (4, 3, 0.5))

# Island B (landing area): 300 m east, top 40 m lower
block("IslandB_Landing", (30000, 0, -5000), (40, 40, 20))
block("IslandB_Marker", (30000, 0, -3950), (6, 6, 0.1))

# Cloud sea visual (no collision); recovery triggers at -200 m
sea = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(15000, 0, -15000), rot())
sea.set_actor_label("CloudSea_Visual")
sea.static_mesh_component.set_static_mesh(PLANE)
sea.static_mesh_component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
sea.set_actor_scale3d(unreal.Vector(1000, 1000, 1))

# Wind
wind("Current_AtoB", unreal.WindVolumeType.CURRENT, [(4000, 0, 500), (14000, 500, 400), (24000, 0, 300)], 14.0, 700.0)
wind("Updraft_Cliff", unreal.WindVolumeType.UPDRAFT, [(4500, 2500, -3000), (4500, 2500, 3000)], 7.0, 500.0)
wind("Updraft_IslandB", unreal.WindVolumeType.UPDRAFT, [(25500, -2500, -6000), (25500, -2500, 0)], 6.0, 500.0)
wind("Hidden_Current", unreal.WindVolumeType.CURRENT, [(4000, -3000, 1200), (12000, -4500, 1600), (20000, -3000, 1800)], 12.0, 600.0, hidden=True)


# Story test content (cloud's interaction classes): the opening plays on spawn, Maren gives the
# delivery briefing, an Elias note can be picked up, and the Upper Cliffs location is discovered.
def struct_set(obj, names, value):
    for n in names:
        try:
            obj.set_editor_property(n, value)
            return
        except Exception:
            pass
    raise RuntimeError("no property %s on %s" % (names, obj))


def rule(conditions, conversation, repeat=False):
    r = unreal.LSInteractionRule()
    struct_set(r, ["if", "if_", "If"], conditions)
    struct_set(r, ["conversation"], conversation)
    struct_set(r, ["repeat", "b_repeat"], repeat)
    return r


opening = actors.spawn_actor_from_class(unreal.LSStoryTrigger, unreal.Vector(-1500, 0, 150), rot())
opening.set_actor_label("Trigger_Opening")
opening.set_editor_property("once_flag", "opening_seen")
opening.set_editor_property("conversation", "opening")

maren = actors.spawn_actor_from_class(unreal.LSStoryNPC, unreal.Vector(-700, 350, 100), rot(yaw=180))
maren.set_actor_label("NPC_Maren_Test")
maren.set_editor_property("speaker_id", "maren")
talk = maren.get_editor_property("interactable")
talk.set_editor_property("prompt", unreal.Text("Talk to Maren"))
talk.set_editor_property("rules", [
    rule(["quest:morning_deliveries:active", "!obj:morning_deliveries:report"], "maren_intro"),
    rule([], "maren_waiting", True),
])

note = actors.spawn_actor_from_class(unreal.LSJournalPickup, unreal.Vector(-1000, -500, 60), rot())
note.set_actor_label("Pickup_EliasNote_Wind")
note.set_editor_property("journal_id", "note_wind")

cliffs = actors.spawn_actor_from_class(unreal.LSLocationVolume, unreal.Vector(2000, 0, 2000), rot())
cliffs.set_actor_label("Location_UpperCliffs")
cliffs.set_editor_property("location_id", "upper_cliffs")

# Player start on island A
start = actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(-1500, 0, 120), rot())
start.set_actor_label("PlayerStart")

world = unreal.EditorLevelLibrary.get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", unreal.LSTestGameMode.static_class())

if not level_subsystem.save_current_level():
    raise RuntimeError("Could not save " + MAP)
unreal.log("LS_BUILD_MAP_OK " + MAP)
