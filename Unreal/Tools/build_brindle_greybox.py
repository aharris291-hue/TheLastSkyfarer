"""Builds the Brindle Isle greybox: /Game/LastSkyfarer/Maps/Brindle/L_Brindle (World Partition).

Run headless (the path must not contain spaces; copy the script somewhere first if needed):
  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script=<abs path to this file> -unattended -nullrhi

Layout follows Adam's Windrest Village map (art_source/maps/Windrest Village_ Brindle Isle Map.png):
north is +X, east is +Y, Central Square at the origin. Units below are metres (converted to cm).
  Whispermill Fields  north-west      Skywatch Point     north (hill)
  Cloud Edge          north rim, west of Skywatch (D-25)
  Orchard Vale        west            Upper Cliffs       north-east (plateau, opening at sunrise)
                                      Old Cartographer's Bluff  east rim (workshop, tower, glide east)
  Post House          north-east of the square; Windsong Tavern south-east; village homes south.
The island is about 1.4 km east-west and 1.15 km north-south. Greybox only: engine shapes, no final art.
Delete Content/LastSkyfarer/Maps/Brindle/L_Brindle.umap (and its __ExternalActors__ folder) before re-running.
"""
import math
import unreal

MAP = "/Game/LastSkyfarer/Maps/Brindle/L_Brindle"
CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
CYL = unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
CONE = unreal.load_asset("/Engine/BasicShapes/Cone.Cone")
SPHERE = unreal.load_asset("/Engine/BasicShapes/Sphere.Sphere")
PLANE = unreal.load_asset("/Engine/BasicShapes/Plane.Plane")

level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

M = 100.0  # cm per metre


def v(x, y, z=0.0):
    return unreal.Vector(x * M, y * M, z * M)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    """unreal.Rotator takes (roll, pitch, yaw) positionally; always build it by name."""
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def always_loaded(a):
    # Greybox landmarks must be visible from across the island, so nothing streams out.
    try:
        a.set_editor_property("is_spatially_loaded", False)
    except Exception:
        pass
    return a


def shape(label, mesh, center, size, yaw=0.0, pitch=0.0, roll=0.0, climbable=False, collision=True, folder="Greybox"):
    """size in metres; engine basic shapes are 1 m across."""
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, v(*center), rot(pitch, yaw, roll))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    comp = a.static_mesh_component
    comp.set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(*size))
    if not collision:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if climbable:
        a.tags = ["Climbable"]
    return always_loaded(a)


def box(label, center, size, **kw):
    return shape(label, CUBE, center, size, **kw)


def ramp(label, start, end, width, thickness=1.0, folder="Greybox/Paths"):
    """A sloped walkway from start (x, y, z) to end, in metres."""
    dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
    run = math.hypot(dx, dy)
    length = math.hypot(run, dz)
    yaw = math.degrees(math.atan2(dy, dx))
    pitch = math.degrees(math.atan2(dz, run))
    center = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, (start[2] + end[2]) / 2 - thickness / 2)
    return box(label, center, (length, width, thickness), yaw=yaw, pitch=pitch, folder=folder)


def path(label, a, b, width=4.0):
    """Flat dirt path on the ground between two points."""
    return ramp(label, (a[0], a[1], 0.05), (b[0], b[1], 0.05), width, 0.1)


def house(label, center, size, yaw=0.0, folder="Greybox/Village"):
    x, y, w, d, h = center[0], center[1], size[0], size[1], size[2]
    base = center[2] if len(center) > 2 else 0.0
    box(label, (x, y, base + h / 2), (w, d, h), yaw=yaw, folder=folder)
    # Pitched roof: a box rotated 45 degrees, squashed.
    box(label + "_Roof", (x, y, base + h + 1.2), (w * 1.05, d * 0.75, d * 0.75), yaw=yaw, roll=45, folder=folder)


def tree(label, center, folder="Greybox/Trees"):
    x, y = center[0], center[1]
    base = center[2] if len(center) > 2 else 0.0
    shape(label + "_Trunk", CYL, (x, y, base + 1.5), (0.6, 0.6, 3.0), folder=folder)
    shape(label + "_Canopy", SPHERE, (x, y, base + 4.5), (5.0, 5.0, 4.0), folder=folder)


def windmill(label, center, folder="Greybox/Whispermill"):
    x, y = center
    shape(label + "_Tower", CYL, (x, y, 9.0), (6.0, 6.0, 18.0), folder=folder)
    shape(label + "_Cap", CONE, (x, y, 19.5), (7.0, 7.0, 3.0), folder=folder)
    # Sails face east, so they read from the village and the Bluff.
    for i, r in enumerate((45.0, 135.0)):
        box(label + "_Sail%d" % i, (x, y + 3.6, 17.0), (0.5, 22.0, 1.6), roll=r, collision=False, folder=folder)


def struct_set(obj, names, value):
    for n in names:
        try:
            obj.set_editor_property(n, value)
            return
        except Exception:
            pass
    raise RuntimeError("no property %s on %s" % (names, obj))


def rule(conditions, conversation, repeat=False, set_flag=None):
    r = unreal.LSInteractionRule()
    struct_set(r, ["if", "if_", "If"], conditions)
    struct_set(r, ["conversation"], conversation)
    struct_set(r, ["repeat", "b_repeat"], repeat)
    if set_flag:
        act = unreal.LSStoryAction()
        act.set_editor_property("type", unreal.LSActionType.SET_FLAG)
        act.set_editor_property("arg", set_flag)
        struct_set(r, ["do", "do_", "Do"], [act])
    return r


def npc(label, speaker, center, yaw, prompt, rules):
    a = actors.spawn_actor_from_class(unreal.LSStoryNPC, v(center[0], center[1], center[2] + 1.0), rot(yaw=yaw))
    a.set_actor_label(label)
    a.set_folder_path("Story/NPCs")
    a.set_editor_property("speaker_id", speaker)
    talk = a.get_editor_property("interactable")
    talk.set_editor_property("prompt", unreal.Text(prompt))
    talk.set_editor_property("rules", rules)
    return always_loaded(a)


def inspect(label, center, size, prompt, rules, mesh=CUBE, folder="Story/Inspect", yaw=0.0):
    a = actors.spawn_actor_from_class(unreal.LSInspectable, v(*center), rot(yaw=yaw))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    a.get_editor_property("mesh").set_static_mesh(mesh)
    a.set_actor_scale3d(unreal.Vector(*size))
    talk = a.get_editor_property("interactable")
    talk.set_editor_property("prompt", unreal.Text(prompt))
    talk.set_editor_property("rules", rules)
    return always_loaded(a)


def trigger(label, center, extent, once_flag, conversation, conditions=None):
    a = actors.spawn_actor_from_class(unreal.LSStoryTrigger, v(*center), rot())
    a.set_actor_label(label)
    a.set_folder_path("Story/Triggers")
    a.set_editor_property("once_flag", once_flag)
    a.set_editor_property("conversation", conversation)
    if conditions:
        a.set_editor_property("conditions", conditions)
    a.get_editor_property("box").set_box_extent(v(*extent))
    return always_loaded(a)


def location(loc_id, center, extent):
    a = actors.spawn_actor_from_class(unreal.LSLocationVolume, v(*center), rot())
    a.set_actor_label("Location_" + loc_id)
    a.set_folder_path("Story/Locations")
    a.set_editor_property("location_id", loc_id)
    a.get_editor_property("box").set_box_extent(v(*extent))
    always_loaded(a)
    marker("Landmark_" + loc_id, (center[0], center[1], center[2]), unreal.LSMapMarkerKind.LANDMARK, location_id=loc_id)
    return a


def marker(label, center, kind, location_id=None, quest=None, objective=None):
    a = actors.spawn_actor_from_class(unreal.LSMapMarkerActor, v(*center), rot())
    a.set_actor_label(label)
    a.set_folder_path("Story/MapMarkers")
    m = a.get_editor_property("marker")
    m.set_editor_property("kind", kind)
    if location_id:
        m.set_editor_property("location_id", location_id)
    if quest:
        m.set_editor_property("quest_id", quest)
        m.set_editor_property("objective_id", objective)
    return always_loaded(a)


def objective(quest, obj, center):
    return marker("Objective_%s_%s" % (quest, obj), center, unreal.LSMapMarkerKind.OBJECTIVE, quest=quest, objective=obj)


def note(journal_id, center):
    a = actors.spawn_actor_from_class(unreal.LSJournalPickup, v(*center), rot())
    a.set_actor_label("Note_" + journal_id)
    a.set_folder_path("Story/EliasNotes")
    a.set_editor_property("journal_id", journal_id)
    return always_loaded(a)


def wind(label, kind, points, strength, radius, hidden=False):
    a = actors.spawn_actor_from_class(unreal.WindVolume, v(*points[0]), rot())
    a.set_actor_label(label)
    a.set_folder_path("Wind")
    a.set_editor_property("wind_type", kind)
    a.set_editor_property("strength", strength)
    a.set_editor_property("radius", radius * M)
    a.set_editor_property("starts_hidden", hidden)
    spline = a.get_component_by_class(unreal.SplineComponent)
    spline.clear_spline_points(False)
    for p in points:
        spline.add_spline_point(v(*p), unreal.SplineCoordinateSpace.WORLD, False)
    spline.update_spline()
    a.rebuild_visual()
    return always_loaded(a)


# ------------------------------------------------------------------ level
if unreal.EditorAssetLibrary.does_asset_exist(MAP):
    unreal.EditorAssetLibrary.delete_asset(MAP)
created = False
try:
    created = level_subsystem.new_level(MAP, True)  # World Partition
except TypeError:
    created = level_subsystem.new_level(MAP)
if not created:
    raise RuntimeError("Could not create %s; delete the old map files and run again" % MAP)

# ------------------------------------------------------------------ sky and light
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, v(0, 0, 300), rot(pitch=-28, yaw=60))
sun.set_actor_label("Sun")
sun.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
sun.light_component.set_editor_property("atmosphere_sun_light", True)
always_loaded(sun)
always_loaded(actors.spawn_actor_from_class(unreal.SkyAtmosphere, v(0, 0, 0))).set_actor_label("SkyAtmosphere")
sky = actors.spawn_actor_from_class(unreal.SkyLight, v(0, 0, 200))
sky.set_actor_label("SkyLight")
sky.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property("real_time_capture", True)
always_loaded(sky)
always_loaded(actors.spawn_actor_from_class(unreal.ExponentialHeightFog, v(0, 0, -100))).set_actor_label("Fog")
always_loaded(actors.spawn_actor_from_class(unreal.VolumetricCloud, v(0, 0, 0))).set_actor_label("VolumetricCloud")

# ------------------------------------------------------------------ the island
# Top: an ellipse 1150 m (N-S) by 1400 m (E-W), surface at Z = 0.
shape("Island_Top", CYL, (0, 0, -20), (1150, 1400, 40), folder="Greybox/Island")
# Rocky underside, so it reads as a floating island from the air.
shape("Island_Underside", CONE, (0, 0, -120), (1050, 1300, 160), roll=180, folder="Greybox/Island")
# Cloud sea far below (visual only). Falling below -200 m returns Kieran to his last safe ledge.
shape("CloudSea_Visual", PLANE, (0, 0, -260), (6000, 6000, 1), collision=False, folder="Greybox/Island")

# ------------------------------------------------------------------ Windrest Village (centre)
shape("Square_Paving", CYL, (0, 0, 0.05), (44, 44, 0.1), folder="Greybox/Village")
shape("Square_Fountain_Basin", CYL, (0, 0, 0.6), (7, 7, 1.2), folder="Greybox/Village")
shape("Square_Fountain_Column", CYL, (0, 0, 2.2), (1.2, 1.2, 3.2), folder="Greybox/Village")
for i, (x, y) in enumerate(((14, -10), (14, 10), (-14, -10), (-14, 10))):
    box("Market_Stall_%d" % i, (x, y, 1.3), (4, 3, 2.6), folder="Greybox/Village")
house("PostHouse", (55, 70), (16, 12, 8))
house("WindsongTavern", (-70, 120), (20, 14, 9))
for i, (x, y) in enumerate(((-110, -40), (-130, 30), (-160, 90), (-120, 165), (-180, -25), (-205, 60), (-90, -95), (-215, 140))):
    house("Home_%d" % i, (x, y), (8, 8, 6), yaw=(i * 23) % 40 - 20)

# Paths from the square
path("Path_PostHouse", (0, 0), (50, 62))
path("Path_Tavern", (0, 0), (-62, 112))
path("Path_Homes", (0, 0), (-180, 40))
path("Path_Whispermill", (0, 0), (290, -290))
path("Path_Orchard", (0, 0), (0, -400))
path("Path_OrchardLane", (0, -400), (20, -560))
path("Path_CloudEdge", (330, 45), (525, -100))
path("Path_Skywatch", (50, 62), (400, 40))
path("Path_UpperCliffs", (50, 62), (230, 270))
path("Path_Bluff", (50, 62), (40, 480))

# ------------------------------------------------------------------ Whispermill Fields (north-west)
box("Whispermill_Wheat", (330, -330, 0.15), (170, 210, 0.3), folder="Greybox/Whispermill")
windmill("Windmill_A", (300, -280))
windmill("Windmill_B", (370, -385))
windmill("Windmill_C", (250, -405))
# Crates to mantle up to Elias's note on the mill platform (1.2 m steps).
box("Mill_Crate_1", (300, -268, 0.6), (2, 2, 1.2), folder="Greybox/Whispermill")
box("Mill_Crate_2", (300, -266, 1.8), (2, 2, 1.2), folder="Greybox/Whispermill")
box("Mill_Platform", (300, -262, 3.0), (4, 3, 0.3), folder="Greybox/Whispermill")

# ------------------------------------------------------------------ Orchard Vale (west)
for i in range(5):
    for j in range(4):
        tree("Orchard_%d_%d" % (i, j), (-30 + i * 15, -360 - j * 15))
# The outer orchard runs on to the west rim: looser rows, a lane, crates and a low fence along the edge.
for i in range(4):
    for j in range(5):
        tree("Orchard_Outer_%d_%d" % (i, j), (-45 + i * 20 + (j % 2) * 8, -450 - j * 22))
for i, (x, y) in enumerate(((10, -575), (18, -578), (-20, -570))):
    box("Orchard_Crate_%d" % i, (x, y, 0.5), (1.2, 1.2, 1), yaw=i * 25, folder="Greybox/Orchard")
for i, x in enumerate(range(-90, 100, 12)):
    shape("Orchard_FencePost_%d" % i, CYL, (x, -686, 0.6), (0.25, 0.25, 1.2), folder="Greybox/Orchard")

# ------------------------------------------------------------------ Cloud Edge (north rim, D-25)
# A flower terrace on the north rim, west of Skywatch Point, looking out over the cloud sea.
box("CloudEdge_Terrace", (545, -100, 0.5), (40, 60, 1), folder="Greybox/CloudEdge")
for i, y in enumerate((-125, -110, -90, -75)):
    box("CloudEdge_FlowerBed_%d" % i, (535, y, 1.2), (3, 6, 0.4), folder="Greybox/CloudEdge")
for i, y in enumerate(range(-127, -70, 6)):
    shape("CloudEdge_Rail_%d" % i, CYL, (566, y, 1.5), (0.3, 0.3, 2), folder="Greybox/CloudEdge")

# ------------------------------------------------------------------ Skywatch Point (north hill, 25 m)
box("Skywatch_Hill", (470, 40, 12.5), (60, 60, 25), folder="Greybox/Skywatch")
ramp("Skywatch_Ramp_1", (400, 0, 0), (430, 0, 12), 5, folder="Greybox/Skywatch")
box("Skywatch_Landing", (434, -2, 11.5), (8, 8, 1), folder="Greybox/Skywatch")
ramp("Skywatch_Ramp_2", (434, 6, 12), (441, 30, 25), 5, folder="Greybox/Skywatch")
# A climbable face on the south side (tagged Climbable).
box("Skywatch_ClimbFace", (439.6, 60, 12.5), (0.8, 10, 25), climbable=True, folder="Greybox/Skywatch")
box("Skywatch_Deck", (480, 40, 25.3), (20, 20, 0.6), folder="Greybox/Skywatch")
shape("Skywatch_Telescope", CYL, (486, 46, 27), (0.8, 0.8, 3), pitch=-35, folder="Greybox/Skywatch")
# A floating rock off the deck (jump across) with one of Elias's notes.
box("Skywatch_FloatingRock", (512, 40, 24.0), (5, 5, 2), folder="Greybox/Skywatch")

# ------------------------------------------------------------------ Upper Cliffs (north-east plateau, 15 m)
box("UpperCliffs_Plateau", (300, 330, 7.5), (120, 140, 15), folder="Greybox/UpperCliffs")
ramp("UpperCliffs_Ramp", (230, 270, 0), (250, 280, 15), 6, folder="Greybox/UpperCliffs")
for i, (x, y) in enumerate(((320, 300), (340, 360), (280, 380), (330, 330))):
    box("UpperCliffs_Rock_%d" % i, (x, y, 16.5), (4, 3, 3), yaw=i * 30, folder="Greybox/UpperCliffs")
# A 1.6 m ledge to mantle onto the lookout rock.
box("UpperCliffs_Lookout", (350, 380, 15.8), (8, 8, 1.6), folder="Greybox/UpperCliffs")

# ------------------------------------------------------------------ Old Cartographer's Bluff (east rim, 20 m)
box("Bluff_Plateau", (60, 600, 10), (140, 160, 20), folder="Greybox/Bluff")
ramp("Bluff_Ramp", (40, 480, 0), (45, 525, 20), 6, folder="Greybox/Bluff")
house("EliasWorkshop", (80, 600, 20), (14, 10, 7), folder="Greybox/Bluff")
shape("ObservationTower", CYL, (130, 640, 35), (6, 6, 30), folder="Greybox/Bluff")
shape("ObservationTower_Top", CONE, (130, 640, 51.5), (7, 7, 3), folder="Greybox/Bluff")
# A low launch lip (15 cm, walkable) marks the glide edge.
box("Bluff_LaunchLip", (60, 676, 20.0), (20, 6, 0.3), folder="Greybox/Bluff")

# A small floating island east of the Bluff: first glide target, with one of Elias's notes.
box("FloatingIsle_East", (60, 920, -5), (30, 30, 6), folder="Greybox/Sky")

# ------------------------------------------------------------------ wind (gliding lines)
wind("Current_BluffEast", unreal.WindVolumeType.CURRENT, [(60, 700, 18), (60, 820, 12), (60, 905, 4)], 12.0, 10.0)
wind("Updraft_BluffEdge", unreal.WindVolumeType.UPDRAFT, [(20, 715, -60), (20, 715, 25)], 6.0, 8.0)
wind("Updraft_CloudEdge", unreal.WindVolumeType.UPDRAFT, [(590, -100, -60), (590, -100, 15)], 6.0, 8.0)
# Off the Cloud Edge rail: ride the updraft, then a current along the north rim towards Skywatch Point.
wind("Current_NorthRim", unreal.WindVolumeType.CURRENT, [(595, -95, 14), (605, 0, 12), (585, 110, 8)], 10.0, 10.0)
wind("Hidden_ImpossibleRoute", unreal.WindVolumeType.CURRENT, [(60, 940, 2), (60, 1300, 0), (60, 1800, -5)], 14.0, 12.0, hidden=True)

# ------------------------------------------------------------------ story: places
location("windrest", (0, 40, 10), (230, 260, 40))
location("post_house", (55, 70, 5), (14, 12, 10))
location("tavern", (-70, 120, 5), (16, 14, 10))
location("whispermill", (330, -330, 10), (110, 130, 30))
location("skywatch", (480, 40, 30), (25, 25, 12))
location("upper_cliffs", (300, 330, 20), (60, 70, 15))
location("bluff", (60, 600, 25), (70, 80, 20))
location("workshop", (80, 600, 24), (9, 7, 6))
location("cloud_edge", (545, -100, 5), (25, 35, 10))
location("central_square", (0, 0, 5), (24, 24, 8))
location("orchard_vale", (0, -470, 8), (75, 130, 15))
location("open_sky", (60, 1100, 0), (200, 200, 100))

# ------------------------------------------------------------------ story: the opening and the people
# D-15: the game opens at sunrise on the Upper Cliffs.
trigger("Trigger_Opening", (320, 320, 17), (8, 8, 4), "opening_seen", "opening")
start = actors.spawn_actor_from_class(unreal.PlayerStart, v(320, 320, 16.2), rot(yaw=60))
start.set_actor_label("PlayerStart_UpperCliffs")
always_loaded(start)

npc("NPC_Maren", "maren", (47, 62, 0), 225, "Talk to Maren", [
    rule(["!obj:morning_deliveries:report"], "maren_intro"),
    rule(["quest:morning_deliveries:active", "obj:morning_deliveries:tavern", "obj:morning_deliveries:tessa", "obj:morning_deliveries:cliffs"], "maren_return"),
    rule(["quest:morning_deliveries:active"], "maren_waiting", True),
    rule(["quest:morning_deliveries:complete", "!deed_received"], "maren_deed"),
    rule([], "maren_after", True),
])
npc("NPC_Bram", "tavern", (-60, 110, 0), 225, "Talk", [
    rule(["item:parcel_tavern"], "tavern_deliver"),
    rule([], "tavern_after", True),
])
npc("NPC_Tessa", "tessa", (476, 36, 25.6), 200, "Talk to Tessa", [
    rule(["item:parcel_tessa"], "tessa_deliver"),
    rule([], "tessa_after", True),
])
npc("NPC_Elara", "villager", (535, -98, 1), 0, "Talk", [
    rule(["item:parcel_cliffs"], "villager_deliver"),
    rule([], "villager_after", True),
])
# Rowan Finch, the village elder, by the fountain (D-26).
npc("NPC_Rowan", "rowan", (-8, 14, 0), 180, "Talk to Rowan", [
    rule(["deed_received", "!rowan_inheritance_done"], "rowan_inheritance", set_flag="rowan_inheritance_done"),
    rule(["quest:morning_deliveries:active", "!rowan_morning_done", "!deed_received"], "rowan_morning", set_flag="rowan_morning_done"),
    rule([], "rowan_repeat", True),
])

inspect("Inspect_BulletinBoard", (10, -18, 1.5), (0.3, 3, 2.5), "Read", [rule([], "board", True)])
inspect("Inspect_Fountain", (0, 0, 2.2), (7.5, 7.5, 0.1), "Look", [rule([], "fountain", True)], mesh=CYL)
inspect("Inspect_Windmill", (296, -276, 2), (1, 1, 1), "Look", [rule([], "windmill", True)])
inspect("Inspect_WorkshopDoor", (75, 594.8, 21.5), (2, 0.3, 3), "Enter workshop", [
    rule(["!deed_received"], "workshop_locked_ch1", True),
], folder="Story/Inspect")

trigger("Trigger_EdgeWarning", (558, -100, 2), (6, 20, 4), "seen_edge_warning", "edge_warning")
trigger("Trigger_SkywatchHint", (390, 10, 2), (8, 8, 4), "seen_skywatch_hint", "skywatch_hint", ["item:parcel_tessa"])

# Objective markers where the Milestone A objectives happen.
objective("morning_deliveries", "report", (47, 62, 0))
objective("morning_deliveries", "tavern", (-60, 110, 0))
objective("morning_deliveries", "tessa", (476, 36, 26))
objective("morning_deliveries", "cliffs", (535, -98, 1))
objective("morning_deliveries", "return", (47, 62, 0))
objective("hidden_workshop", "enter", (75, 594, 20))
objective("into_the_clouds", "bluff", (60, 676, 20))

# Elias Was Here (part 1): his notes around the island.
note("note_cloud_edge", (550, -112, 1.5))
note("note_wind", (300, -262, 3.6))
note("note_sky_map", (512, 40, 25.5))
note("note_three_decades", (350, 380, 17.1))
note("note_each_island", (60, 920, -1.5))

# ------------------------------------------------------------------ map and game mode
bounds = actors.spawn_actor_from_class(unreal.LSMapBounds, v(0, 0, 0), rot())
bounds.set_actor_label("MapBounds_Brindle")
bounds.set_editor_property("map_title", unreal.Text("Brindle Isle"))
bounds.get_editor_property("bounds").set_box_extent(v(750, 750, 120))
always_loaded(bounds)

world = unreal.EditorLevelLibrary.get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", unreal.LSTestGameMode.static_class())

if not level_subsystem.save_current_level():
    raise RuntimeError("Could not save " + MAP)
unreal.log("LS_BUILD_MAP_OK " + MAP)
