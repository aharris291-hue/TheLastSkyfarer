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


# ------------------------------------------------------------------ art pass 1: painterly materials by name
# (Tools/build_materials.py makes them; STYLE_GUIDE: grass green, wheat gold, terracotta roofs, warm stone.)
MATS = "/Game/LastSkyfarer/Materials/Instances/"
_mat_cache = {}
# First match wins; each entry is (text the label contains, material instance).
MATERIAL_RULES = [
    ("Island_Underside", "MI_CliffRock"), ("MistIsland", "MI_CliffRock"), ("CloudSea", "MI_CloudSea"), ("CloudPuff", "MI_CloudPuff"),
    ("Island_Top", "MI_IslandGround"), ("Square_Paving", "MI_PathStone"), ("Path_", "MI_PathDirt"),
    ("Square_Fountain", "MI_Stone"), ("Market_Stall", "MI_Wood"),
    ("EliasWorkshop_Roof", "MI_RoofBlue"), ("ObservationTower_Top", "MI_RoofBlue"), ("WindsongTavern_Roof", "MI_RoofGreen"),
    ("_Roof", "MI_RoofTerracotta"), ("_Cap", "MI_RoofTerracotta"),
    ("PostHouse", "MI_Plaster"), ("WindsongTavern", "MI_Plaster"), ("Home_", "MI_Plaster"), ("EliasWorkshop", "MI_Plaster"),
    ("_Trunk", "MI_Wood"), ("Crate", "MI_Wood"), ("FencePost", "MI_Wood"),
    ("Orchard_", "MI_FoliageBlossom"), ("_Canopy", "MI_Foliage"),
    ("_Tower", "MI_Stone"), ("_Sail", "MI_Sailcloth"), ("Whispermill_Wheat", "MI_Wheat"),
    ("Crate", "MI_Wood"), ("Mill_Platform", "MI_Wood"), ("_Rail", "MI_Wood"), ("FencePost", "MI_Wood"),
    ("CloudEdge_Terrace", "MI_Stone"), ("FlowerBed", "MI_FlowerBed"),
    ("Ramp", "MI_PathDirt"), ("Landing", "MI_PathDirt"), ("ClimbFace", "MI_CliffRock"), ("UpperCliffs_Rock", "MI_CliffRock"),
    ("Lookout", "MI_CliffRock"), ("Skywatch_Deck", "MI_Wood"), ("Telescope", "MI_Brass"), ("ObservationTower", "MI_Stone"),
    ("LaunchLip", "MI_Stone"), ("Skywatch_Hill", "MI_IslandGround"), ("UpperCliffs_Plateau", "MI_IslandGround"),
    ("Bluff_Plateau", "MI_IslandGround"), ("FloatingIsle", "MI_IslandGround"), ("FloatingRock", "MI_IslandGround"), ("SkyRock", "MI_IslandGround"),
    ("Workshop_Floor", "MI_WoodFloor"), ("Workshop_Wall", "MI_Plaster"), ("Workshop_Ceiling", "MI_Plaster"),
    ("Workshop_", "MI_Wood"), ("Compartment_Glider", "MI_Sailcloth"), ("Compartment_Compass", "MI_Brass"), ("Compartment_", "MI_Wood"),
]


def material(name):
    if name not in _mat_cache:
        _mat_cache[name] = unreal.load_asset(MATS + name)
    return _mat_cache[name]


def material_for(label):
    for key, mi in MATERIAL_RULES:
        if key in label:
            return material(mi)
    return material("MI_Stone")


def shape(label, mesh, center, size, yaw=0.0, pitch=0.0, roll=0.0, climbable=False, collision=True, folder="Greybox"):
    """size in metres; engine basic shapes are 1 m across."""
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, v(*center), rot(pitch, yaw, roll))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    comp = a.static_mesh_component
    comp.set_static_mesh(mesh)
    comp.set_material(0, material_for(label))
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


KIT = "/Game/LastSkyfarer/Environments/Brindle/Meshes/"
# (mesh name prefix, max draw distance in metres, casts shadows)
KIT_CULL = [
    ("SM_GrassPatch", 110, False), ("SM_FlowerBed", 160, False), ("SM_Planter", 140, False), ("SM_HangingLantern", 60, False),
    ("SM_LanternPost", 180, False), ("SM_Bench", 160, True), ("SM_Chest", 140, True), ("SM_Fence", 220, True),
    ("SM_MarketStall", 260, True), ("SM_NoticeBoard", 200, True), ("SM_Rock", 450, True), ("SM_Tree", 650, True),
    ("SM_Workbench", 60, True), ("SM_Bookshelf", 60, True), ("SM_Armillary", 60, True), ("SM_SketchBoard", 60, False),
    ("SM_PortraitFrame", 60, False),
]


def stable_hash(text):
    """Like hash(), but the same in every run, so the map comes out identical each time."""
    return sum((i + 1) * ord(ch) for i, ch in enumerate(text))


def kit(label, mesh_name, center, yaw=0.0, scale=(1.0, 1.0, 1.0), folder="Art/Windrest", spin=None, override=None):
    """Places a Windrest kit piece (Tools/import_windrest_kit.py). Visual only: no collision."""
    cls = unreal.LSSpinningMesh if spin is not None else unreal.StaticMeshActor
    a = actors.spawn_actor_from_class(cls, v(*center), rot(yaw=yaw))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    comp = a.get_editor_property("mesh") if spin is not None else a.static_mesh_component
    comp.set_static_mesh(unreal.load_asset(KIT + mesh_name))
    comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    if override:
        comp.set_material(0, material(override))
    # Small props stop drawing (and grass stops casting shadows) at a distance, which keeps the village view at
    # 30 fps on integrated graphics; big landmarks always draw.
    for prefix, metres, shadow in KIT_CULL:
        if mesh_name.startswith(prefix):
            comp.set_editor_property("ld_max_draw_distance", metres * M)
            comp.set_cast_shadow(shadow)
            break
    a.set_actor_scale3d(unreal.Vector(*scale))
    if spin is not None:
        a.set_editor_property("speed", spin)
    return always_loaded(a)


def hide(a):
    """Keeps a greybox shape for collision but stops drawing it (the art piece shows instead)."""
    a.set_actor_hidden_in_game(True)
    return a


def house(label, center, size, yaw=0.0, folder="Greybox/Village"):
    x, y, w, d, h = center[0], center[1], size[0], size[1], size[2]
    base = center[2] if len(center) > 2 else 0.0
    hide(box(label, (x, y, base + h / 2), (w, d, h), yaw=yaw, folder=folder))
    # Art pass 1: a Windrest cottage (8 x 8 m, 6 m walls) scaled to the greybox footprint.
    variant = "SM_Cottage_Blue" if "Elias" in label else "SM_Cottage_B" if ("Tavern" in label or label.endswith(("1", "4", "6"))) else "SM_Cottage_A"
    kit(label + "_Art", variant, (x, y, base), yaw=yaw, scale=(w / 8.0, d / 8.0, h / 6.0))


def tree(label, center, folder="Greybox/Trees"):
    x, y = center[0], center[1]
    base = center[2] if len(center) > 2 else 0.0
    hide(shape(label + "_Trunk", CYL, (x, y, base + 1.5), (0.6, 0.6, 3.0), folder=folder))
    hide(shape(label + "_Canopy", SPHERE, (x, y, base + 4.5), (5.0, 5.0, 4.0), folder=folder))
    blossom = label.startswith("Orchard")
    s = 0.85 + ((stable_hash(label) % 7) * 0.05)
    kit(label + "_Art", "SM_Tree_Blossom" if blossom else "SM_Tree_Round", (x, y, base), yaw=(stable_hash(label) % 360), scale=(s, s, s))


def windmill(label, center, folder="Greybox/Whispermill"):
    x, y = center
    hide(shape(label + "_Tower", CYL, (x, y, 9.0), (6.0, 6.0, 18.0), folder=folder))
    hide(shape(label + "_Cap", CONE, (x, y, 19.5), (7.0, 7.0, 3.0), folder=folder))
    # Art pass 1: stone tower with turning sails facing east, so they read from the village and the Bluff.
    s = 1.1
    kit(label + "_Art", "SM_Windmill_Tower", (x, y, 0), yaw=180, scale=(s, s, s))
    kit(label + "_Sails", "SM_Windmill_Sails", (x, y + 3.6 * s, 17.0 * s), yaw=180, scale=(s, s, s), spin=22.0 + (stable_hash(label) % 5) * 3)


def struct_set(obj, names, value):
    for n in names:
        try:
            obj.set_editor_property(n, value)
            return
        except Exception:
            pass
    raise RuntimeError("no property %s on %s" % (names, obj))


def action(kind, arg):
    act = unreal.LSStoryAction()
    act.set_editor_property("type", kind)
    act.set_editor_property("arg", arg)
    return act


def rule(conditions, conversation, repeat=False, set_flag=None, event=None):
    r = unreal.LSInteractionRule()
    struct_set(r, ["if", "if_", "If"], conditions)
    struct_set(r, ["conversation"], conversation)
    struct_set(r, ["repeat", "b_repeat"], repeat)
    acts = []
    if set_flag:
        acts.append(action(unreal.LSActionType.SET_FLAG, set_flag))
    if event:
        acts.append(action(unreal.LSActionType.EVENT, event))
    if acts:
        struct_set(r, ["do", "do_", "Do"], acts)
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


def inspect(label, center, size, prompt, rules, mesh=CUBE, folder="Story/Inspect", yaw=0.0, available_if=None):
    a = actors.spawn_actor_from_class(unreal.LSInspectable, v(*center), rot(yaw=yaw))
    a.set_actor_label(label)
    a.set_folder_path(folder)
    a.get_editor_property("mesh").set_static_mesh(mesh)
    a.get_editor_property("mesh").set_material(0, material(
        "MI_Sailcloth" if ("Glider" in label or "Maps" in label or "Sketches" in label or "Notes" in label)
        else "MI_Brass" if "Instruments" in label else "MI_Stone" if "Fountain" in label else "MI_Wood"))
    a.set_actor_scale3d(unreal.Vector(*size))
    talk = a.get_editor_property("interactable")
    talk.set_editor_property("prompt", unreal.Text(prompt))
    talk.set_editor_property("rules", rules)
    if available_if:
        talk.set_editor_property("available_if", available_if)
    return always_loaded(a)


def lamp(label, center, radius=12.0, folder="Greybox/Workshop"):
    a = actors.spawn_actor_from_class(unreal.PointLight, v(*center), rot())
    a.set_actor_label(label)
    a.set_folder_path(folder)
    a.root_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    light = a.light_component
    light.set_light_color(unreal.LinearColor(1.0, 0.68, 0.38, 1.0))
    light.set_intensity(40.0)
    light.set_attenuation_radius(radius * M)
    return always_loaded(a)


def transform(center, yaw=0.0):
    return unreal.Transform(location=v(*center), rotation=rot(yaw=yaw), scale=unreal.Vector(1, 1, 1))


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
# Soft cloud puffs hugging the island's rocky underside (cheap mist: opaque, no volumetrics).
for i in range(28):
    ang = i * (2 * math.pi / 28) + (i % 3) * 0.07
    r = 0.78 + (i % 4) * 0.05
    shape("CloudPuff_%02d" % i, SPHERE, (math.cos(ang) * 575 * r, math.sin(ang) * 700 * r, -70 - (i % 5) * 22),
          (150 + (i % 3) * 50, 170 + (i % 4) * 40, 45 + (i % 2) * 20), yaw=math.degrees(ang), collision=False, folder="Greybox/Mist")

# ------------------------------------------------------------------ Windrest Village (centre)
shape("Square_Paving", CYL, (0, 0, 0.05), (44, 44, 0.1), folder="Greybox/Village")
hide(shape("Square_Fountain_Basin", CYL, (0, 0, 0.6), (7, 7, 1.2), folder="Greybox/Village"))
hide(shape("Square_Fountain_Column", CYL, (0, 0, 2.2), (1.2, 1.2, 3.2), folder="Greybox/Village"))
for i, (x, y) in enumerate(((14, -10), (14, 10), (-14, -10), (-14, 10))):
    hide(box("Market_Stall_%d" % i, (x, y, 1.3), (4, 3, 2.6), folder="Greybox/Village"))
    # Art pass 1: a striped market stall, counter facing the fountain.
    kit("Market_Stall_%d_Art" % i, "SM_MarketStall", (x, y, 0), yaw=math.degrees(math.atan2(-x, y)))
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
    hide(shape("Orchard_FencePost_%d" % i, CYL, (x, -686, 0.6), (0.25, 0.25, 1.2), folder="Greybox/Orchard"))
# Art pass 1: a wooden fence along the orchard's rim.
for i, x in enumerate(range(-88, 92, 4)):
    kit("Orchard_Fence_%d" % i, "SM_Fence_4m", (x, -686, 0), yaw=(i % 3) - 1)

# Lantern posts around Central Square, and rocks breaking up the island's edges and plateau feet.
for i in range(6):
    ang = i * math.pi / 3 + 0.3
    kit("Square_Lantern_%d" % i, "SM_LanternPost", (math.cos(ang) * 24, math.sin(ang) * 24, 0), yaw=math.degrees(ang) + 180)
for i in range(6):
    ang = i * math.pi / 3 + 0.82
    kit("Square_Planter_%d" % i, "SM_Planter", (math.cos(ang) * 20, math.sin(ang) * 20, 0), yaw=math.degrees(ang) + 90)
for i in range(4):
    ang = i * math.pi / 2 + math.pi / 4
    bx, by = math.cos(ang) * 9.5, math.sin(ang) * 9.5
    kit("Square_Bench_%d" % i, "SM_Bench", (bx, by, 0), yaw=math.degrees(math.atan2(-bx, by)) + 180)
# Benches on the Cloud Edge terrace, looking out north over the cloud sea.
for i, y in enumerate((-118, -82)):
    kit("CloudEdge_Bench_%d" % i, "SM_Bench", (556, y, 1.0), yaw=90)
# Meadow grass that sways: around the village, the orchard, Cloud Edge's approach and the Upper Cliffs.
GRASS = [(60, -60), (-60, -70), (70, 130), (-120, -150), (140, -120), (180, 60), (-40, 230), (110, 230), (-230, -60),
         (-260, 120), (40, -250), (-60, -300), (60, -460), (-70, -520), (30, -600), (-110, -440), (430, -150), (470, -60),
         (380, -200), (230, -80), (300, 120), (160, 330), (-150, 330)]
for i, (x, y) in enumerate(GRASS):
    kit("Grass_%02d" % i, "SM_GrassPatch", (x, y, 0), yaw=i * 61, folder="Art/Grass")
for i, (x, y) in enumerate(((290, 300), (320, 360), (270, 350))):
    kit("Grass_Cliffs_%d" % i, "SM_GrassPatch", (x, y, 15.0), yaw=i * 77, scale=(0.6, 0.6, 1.0), folder="Art/Grass")
ROCK_SPOTS = [(560, 160), (540, 260), (470, -560), (420, -600), (-520, -350), (-560, 120), (-480, 380), (-300, 600),
              (200, 640), (260, 520), (240, 240), (360, 230), (240, 420), (-10, 520), (130, 520), (140, 690),
              (400, 90), (520, 0), (420, -30), (-200, -650), (120, -660), (300, -640)]
for i, (x, y) in enumerate(ROCK_SPOTS):
    s = 1.6 + (i % 4) * 0.8
    kit("Rock_%02d" % i, "SM_Rock_%d" % (i % 3), (x, y, -0.4), yaw=i * 47, scale=(s, s * 0.8, s * 0.7), folder="Art/Rocks")
# Rocks every few metres around the whole rim, so the island's edge reads as natural, not a cut.
for i in range(36):
    ang = i * 2 * math.pi / 36 + 0.05 * (i % 3)
    s = 2.0 + (i % 5) * 0.7
    kit("RimRock_%02d" % i, "SM_Rock_%d" % (i % 3), (math.cos(ang) * 575 * 0.985, math.sin(ang) * 700 * 0.985, -0.6), yaw=i * 61, scale=(s, s * 0.9, s * 0.6), folder="Art/Rocks")

# ------------------------------------------------------------------ Cloud Edge (north rim, D-25)
# A flower terrace on the north rim, west of Skywatch Point, looking out over the cloud sea.
hide(box("CloudEdge_Terrace", (545, -100, 0.5), (40, 60, 1), folder="Greybox/CloudEdge"))
kit("CloudEdge_Terrace_Art", "SM_Plateau", (545, -100, 0), scale=(40, 60, 1), folder="Art/CloudEdge", override="MI_PathStone")
for i, y in enumerate(range(-126, -72, 4)):
    kit("CloudEdge_Fence_%d" % i, "SM_Fence_4m", (566, y, 1.0), yaw=90, folder="Art/CloudEdge")
for i, y in enumerate((-125, -110, -90, -75)):
    hide(box("CloudEdge_FlowerBed_%d" % i, (535, y, 1.2), (3, 6, 0.4), folder="Greybox/CloudEdge"))
    kit("CloudEdge_FlowerBed_%d_Art" % i, "SM_FlowerBed", (535, y, 1.0), yaw=90)
for i, y in enumerate(range(-127, -70, 6)):
    hide(shape("CloudEdge_Rail_%d" % i, CYL, (566, y, 1.5), (0.3, 0.3, 2), folder="Greybox/CloudEdge"))

# ------------------------------------------------------------------ Skywatch Point (north hill, 25 m)
hide(box("Skywatch_Hill", (470, 40, 12.5), (60, 60, 25), folder="Greybox/Skywatch"))
kit("Skywatch_Hill_Art", "SM_Plateau", (470, 40, 0), scale=(60, 60, 25), folder="Art/Landforms")
ramp("Skywatch_Ramp_1", (400, 0, 0), (430, 0, 12), 5, folder="Greybox/Skywatch")
box("Skywatch_Landing", (434, -2, 11.5), (8, 8, 1), folder="Greybox/Skywatch")
ramp("Skywatch_Ramp_2", (434, 6, 12), (441, 30, 25), 5, folder="Greybox/Skywatch")
# A climbable face on the south side (tagged Climbable).
box("Skywatch_ClimbFace", (439.6, 60, 12.5), (0.8, 10, 25), climbable=True, folder="Greybox/Skywatch")
box("Skywatch_Deck", (480, 40, 25.3), (20, 20, 0.6), folder="Greybox/Skywatch")
shape("Skywatch_Telescope", CYL, (486, 46, 27), (0.8, 0.8, 3), pitch=-35, folder="Greybox/Skywatch")
# A floating rock off the deck (jump across) with one of Elias's notes.
hide(box("Skywatch_FloatingRock", (512, 40, 24.0), (5, 5, 2), folder="Greybox/Skywatch"))
kit("Skywatch_FloatingRock_Art", "SM_FloatingIsle", (512, 40, 25.0), scale=(5.5, 5.5, 5), folder="Art/Sky")

# ------------------------------------------------------------------ Upper Cliffs (north-east plateau, 15 m)
hide(box("UpperCliffs_Plateau", (300, 330, 7.5), (120, 140, 15), folder="Greybox/UpperCliffs"))
kit("UpperCliffs_Plateau_Art", "SM_Plateau", (300, 330, 0), scale=(120, 140, 15), folder="Art/Landforms")
ramp("UpperCliffs_Ramp", (230, 270, 0), (250, 280, 15), 6, folder="Greybox/UpperCliffs")
for i, (x, y) in enumerate(((320, 300), (340, 360), (280, 380), (330, 330))):
    hide(box("UpperCliffs_Rock_%d" % i, (x, y, 16.5), (4, 3, 3), yaw=i * 30, folder="Greybox/UpperCliffs"))
    kit("UpperCliffs_Rock_%d_Art" % i, "SM_Rock_%d" % (i % 3), (x, y, 14.6), yaw=i * 30, scale=(1.5, 1.5, 2.2), folder="Art/Rocks")
# A 1.6 m ledge to mantle onto the lookout rock.
hide(box("UpperCliffs_Lookout", (350, 380, 15.8), (8, 8, 1.6), folder="Greybox/UpperCliffs"))
kit("UpperCliffs_Lookout_Art", "SM_Plateau", (350, 380, 15.0), scale=(8, 8, 1.6), folder="Art/Landforms", override="MI_CliffRock")

# ------------------------------------------------------------------ Old Cartographer's Bluff (east rim, 20 m)
hide(box("Bluff_Plateau", (60, 600, 10), (140, 160, 20), folder="Greybox/Bluff"))
kit("Bluff_Plateau_Art", "SM_Plateau", (60, 600, 0), scale=(140, 160, 20), folder="Art/Landforms")
ramp("Bluff_Ramp", (40, 480, 0), (45, 525, 20), 6, folder="Greybox/Bluff")
house("EliasWorkshop", (80, 600, 20), (14, 10, 7), folder="Greybox/Bluff")
hide(shape("ObservationTower", CYL, (130, 640, 35), (6, 6, 30), folder="Greybox/Bluff"))
hide(shape("ObservationTower_Top", CONE, (130, 640, 51.5), (7, 7, 3), folder="Greybox/Bluff"))
kit("ObservationTower_Art", "SM_ObservationTower", (130, 640, 20), folder="Art/Bluff")
# A low launch lip (15 cm, walkable) marks the glide edge.
hide(box("Bluff_LaunchLip", (60, 676, 20.0), (20, 6, 0.3), folder="Greybox/Bluff"))
# The glider launch: a plank deck at the Bluff edge, lanterns and crates by the workshop.
kit("Bluff_LaunchDeck", "SM_LaunchDeck", (60, 676, 20.15), folder="Art/Bluff")
for i, (x, y) in enumerate(((70, 590), (88, 590), (48, 650))):
    kit("Bluff_Lantern_%d" % i, "SM_LanternPost", (x, y, 20), yaw=i * 90, folder="Art/Bluff")
for i, (x, y) in enumerate(((94, 596), (95, 599), (40, 640))):
    kit("Bluff_Chest_%d" % i, "SM_Chest", (x, y, 20), yaw=i * 40, scale=(0.9, 0.9, 0.9), folder="Art/Bluff")
for i, x in enumerate(range(-6, 128, 4)):
    if 30 <= x <= 54:
        continue  # leave the top of the ramp open
    kit("Bluff_Fence_S_%d" % i, "SM_Fence_4m", (x, 522, 20), yaw=(i % 3) - 1, folder="Art/Bluff")

# Blocks the Bluff edge until Kieran has the glider (windrest.gd edge_wall); hidden, collision only.
edge_wall = box("Bluff_EdgeWall", (60, 681.5, 23), (140, 1, 6), folder="Greybox/Bluff")
edge_wall.set_actor_hidden_in_game(True)

# ------------------------------------------------------------------ Into the Clouds: the sky route east (Ch. 3)
# Small floating islands along the impossible current, then the island in the mist where the wind refuses to go.
hide(box("FloatingIsle_East", (60, 920, -5), (30, 30, 6), folder="Greybox/Sky"))
kit("FloatingIsle_East_Art", "SM_FloatingIsle", (60, 920, -2), scale=(32, 32, 18), folder="Art/Sky")
hide(box("FloatingIsle_Mid", (60, 1180, -15), (40, 40, 8), folder="Greybox/Sky"))
kit("FloatingIsle_Mid_Art", "SM_FloatingIsle", (60, 1180, -11), scale=(42, 42, 24), folder="Art/Sky")
hide(box("FloatingIsle_Small", (40, 1420, -20), (20, 20, 6), folder="Greybox/Sky"))
kit("FloatingIsle_Small_Art", "SM_FloatingIsle", (40, 1420, -17), scale=(22, 22, 14), folder="Art/Sky")
for i, (x, y, z, s) in enumerate(((20, 800, 30, 4), (110, 1050, 25, 3), (0, 1300, 35, 5), (120, 1480, 20, 4))):
    hide(box("SkyRock_%d" % i, (x, y, z), (s, s, s * 0.8), yaw=i * 37, folder="Greybox/Sky"))
    kit("SkyRock_%d_Art" % i, "SM_FloatingIsle", (x, y, z + s * 0.4), yaw=i * 37, scale=(s * 1.3, s * 1.3, s * 2.2), folder="Art/Sky")
# The island in the mist: a dark silhouette beyond the fog (STYLE_GUIDE colour script 6).
shape("MistIsland_Top", CYL, (60, 1900, -10), (320, 380, 30), collision=False, folder="Greybox/Sky")
shape("MistIsland_Underside", CONE, (60, 1900, -60), (300, 360, 80), roll=180, collision=False, folder="Greybox/Sky")
shape("MistIsland_Spire", CYL, (40, 1880, 30), (12, 12, 60), collision=False, folder="Greybox/Sky")
# Where the wind refuses to go: an invisible wall past the fog trigger.
fog_wall = box("Sky_FogWall", (60, 1620, 0), (600, 2, 400), folder="Greybox/Sky")
fog_wall.set_actor_hidden_in_game(True)

# ------------------------------------------------------------------ Elias's workshop interior (Ch. 2)
# Greybox room far west of the island, out of sight; the doors teleport Kieran in and out.
IX, IY = 0.0, -3000.0
box("Workshop_Floor", (IX, IY, -0.2), (14, 10, 0.4), folder="Greybox/Workshop")
box("Workshop_Ceiling", (IX, IY, 4.3), (14.8, 10.8, 0.4), folder="Greybox/Workshop")
box("Workshop_Wall_N", (IX + 7.2, IY, 2.0), (0.4, 10.8, 4.4), folder="Greybox/Workshop")
box("Workshop_Wall_S", (IX - 7.2, IY, 2.0), (0.4, 10.8, 4.4), folder="Greybox/Workshop")
box("Workshop_Wall_E", (IX, IY + 5.2, 2.0), (14.8, 0.4, 4.4), folder="Greybox/Workshop")
box("Workshop_Wall_W", (IX, IY - 5.2, 2.0), (14.8, 0.4, 4.4), folder="Greybox/Workshop")
for i, x in enumerate((-4.5, 0.0, 4.5)):
    box("Workshop_Beam_%d" % i, (IX + x, IY, 3.9), (0.4, 10, 0.4), folder="Greybox/Workshop")
hide(box("Workshop_Bookshelf_W", (IX - 3, IY - 4.7, 1.4), (4, 0.6, 2.8), folder="Greybox/Workshop"))
kit("Workshop_Bookshelf_W_Art", "SM_Bookshelf", (IX - 3, IY - 4.75, 0), yaw=180, folder="Art/Workshop")
hide(box("Workshop_Bookshelf_E", (IX + 5, IY + 4.7, 1.4), (3, 0.6, 2.8), folder="Greybox/Workshop"))
kit("Workshop_Bookshelf_E_Art", "SM_Bookshelf", (IX + 5, IY + 4.75, 0), scale=(0.75, 1, 1), folder="Art/Workshop")
hide(box("Workshop_Desk", (IX + 3, IY, 0.45), (2.2, 3.2, 0.9), folder="Greybox/Workshop"))
kit("Workshop_Workbench", "SM_Workbench", (IX + 3, IY, 0), folder="Art/Workshop")
hide(box("Workshop_Chest", (IX + 5.8, IY + 2.5, 0.4), (1.0, 1.6, 0.8), folder="Greybox/Workshop"))
kit("Workshop_Chest_Art", "SM_Chest", (IX + 5.8, IY + 2.5, 0), folder="Art/Workshop")
kit("Workshop_SketchBoard", "SM_SketchBoard", (IX + 3, IY + 4.95, 1.8), folder="Art/Workshop")
kit("Workshop_Portrait", "SM_PortraitFrame", (IX - 3, IY + 4.95, 2.0), folder="Art/Workshop")
kit("Workshop_Armillary", "SM_Armillary", (IX + 5.5, IY - 3.5, 0), folder="Art/Workshop")
for i, (x, y) in enumerate(((IX - 4, IY - 3), (IX + 4, IY + 3), (IX + 3, IY - 1.2))):
    kit("Workshop_HangingLantern_%d" % i, "SM_HangingLantern", (x, y, 4.1), folder="Art/Workshop")
lamp("Workshop_Lantern_A", (IX - 4, IY - 3, 3.0))
lamp("Workshop_Lantern_B", (IX + 4, IY + 3, 3.0))
lamp("Workshop_Lantern_Desk", (IX + 3, IY, 1.6), radius=6.0)

inspect("Inspect_WorkshopDoor_Inside", (IX - 6.9, IY, 1.2), (0.2, 1.6, 2.4), "Go outside", [
    rule(["compass_active"], "", event="leave"),
    rule([], "workshop_leave_night", True),
], folder="Story/Workshop")
inspect("Inspect_Maps", (IX + 3, IY, 0.95), (1.8, 2.6, 0.05), "Study the maps", [
    rule(["!searched_maps"], "inspect_maps"),
], folder="Story/Workshop")
inspect("Inspect_Sketches", (IX + 3, IY + 4.9, 1.8), (2.0, 0.1, 1.4), "Look at the sketches", [
    rule(["!searched_sketches"], "inspect_sketches"),
], folder="Story/Workshop")
inspect("Inspect_Notes", (IX - 3, IY - 4.3, 1.2), (3.6, 0.2, 2.2), "Read the weather logs", [
    rule(["!searched_notes"], "inspect_notes"),
    rule([], "inspect_shelf", True),
], folder="Story/Workshop")
inspect("Inspect_Portrait", (IX - 3, IY + 4.9, 2.0), (1.0, 0.1, 1.3), "Look at the portrait", [
    rule([], "inspect_portrait", True),
], folder="Story/Workshop")
inspect("Inspect_Instruments", (IX + 5.5, IY - 3.5, 0.8), (1.2, 1.2, 1.2), "Examine the instruments", [
    rule([], "inspect_instruments", True),
], mesh=SPHERE, folder="Story/Workshop")
inspect("Inspect_Floorboard", (IX, IY + 1.5, 0.03), (1.6, 1.0, 0.06), "Lift the floorboard", [
    rule(["!compartment_open"], "compartment"),
    rule(["compartment_open", "!compass_active"], "final_entry"),
], folder="Story/Workshop", available_if=["obj:hidden_workshop:search"])
compartment_props = [
    shape("Compartment_Hole", CUBE, (IX, IY + 1.5, 0.07), (1.4, 0.8, 0.02), collision=False, folder="Story/Workshop"),
    shape("Compartment_Glider", CUBE, (IX - 0.2, IY + 1.5, 0.12), (0.5, 2.6, 0.06), collision=False, folder="Story/Workshop"),
    shape("Compartment_Compass", CYL, (IX + 0.45, IY + 1.3, 0.15), (0.25, 0.25, 0.06), collision=False, folder="Story/Workshop"),
]

# ------------------------------------------------------------------ Into the Clouds: the glider at the Bluff edge
glider = inspect("Inspect_Glider", (48, 664, 20.6), (2.2, 5.0, 0.15), "Approach", [
    rule(["compass_active", "!piko_joined"], "piko_meeting"),
], folder="Story/Bluff", available_if=["compass_active"])

# ------------------------------------------------------------------ wind (gliding lines)
wind("Updraft_BluffEdge", unreal.WindVolumeType.UPDRAFT, [(20, 715, -60), (20, 715, 25)], 6.0, 8.0)
wind("Updraft_CloudEdge", unreal.WindVolumeType.UPDRAFT, [(590, -100, -60), (590, -100, 15)], 6.0, 8.0)
# Off the Cloud Edge rail: ride the updraft, then a current along the north rim towards Skywatch Point.
wind("Current_NorthRim", unreal.WindVolumeType.CURRENT, [(595, -95, 14), (605, 0, 12), (585, 110, 8)], 10.0, 10.0)
# The impossible current: hidden until the compass awakens, then it carries Kieran east from the Bluff (Ch. 3).
route = wind("ImpossibleCurrent", unreal.WindVolumeType.CURRENT,
             [(60, 690, 17), (60, 900, 15), (60, 1150, 13), (60, 1400, 11), (60, 1570, 10)], 14.0, 14.0, hidden=True)
route.tags = ["impossible_route"]
# The hidden updraft Piko reveals on the way (revealed_wind_1 in the Godot level).
hidden_updraft = wind("Hidden_Updraft_1", unreal.WindVolumeType.UPDRAFT, [(60, 1090, -60), (60, 1090, 22)], 5.0, 10.0, hidden=True)
hidden_updraft.tags = ["revealed_wind_1"]
wind("Updraft_Isle_Mid", unreal.WindVolumeType.UPDRAFT, [(80, 1180, -40), (80, 1180, 15)], 6.0, 8.0)

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

hide(inspect("Inspect_BulletinBoard", (10, -18, 1.5), (0.3, 3, 2.5), "Read", [rule([], "board", True)]))
kit("Square_NoticeBoard", "SM_NoticeBoard", (10, -18, 0), yaw=-90)
hide(inspect("Inspect_Fountain", (0, 0, 2.2), (7.5, 7.5, 0.1), "Look", [rule([], "fountain", True)], mesh=CYL))
kit("Square_Fountain_Art", "SM_Fountain", (0, 0, 0))
inspect("Inspect_Windmill", (296, -276, 2), (1, 1, 1), "Look", [rule([], "windmill", True)])
inspect("Inspect_WorkshopDoor", (75, 594.8, 21.5), (2, 0.3, 3), "Enter workshop", [
    rule(["!deed_received"], "workshop_locked_ch1", True),
    rule(["!has_glider"], "", event="enter_workshop"),
], folder="Story/Inspect")

trigger("Trigger_EdgeWarning", (558, -100, 2), (6, 20, 4), "seen_edge_warning", "edge_warning")
trigger("Trigger_SkywatchHint", (390, 10, 2), (8, 8, 4), "seen_skywatch_hint", "skywatch_hint", ["item:parcel_tessa"])
# The Bluff edge (windrest.gd): a warning until Piko joins, then "ready to launch" at the lip.
trigger("Trigger_BluffEdgeWarning", (60, 676, 21.5), (20, 3, 3), "seen_bluff_edge_warning", "edge_warning", ["!piko_joined"])
trigger("Trigger_LaunchReady", (60, 676, 21.5), (20, 3, 3), "seen_launch_ready", "launch_ready", ["piko_joined"])
# The fog where the wind refuses to go (Ch. 3 ends here).
trigger("Trigger_Fog", (60, 1545, 10), (200, 8, 200), "reached_fog", "wind_refuses", ["piko_joined"])

# The level's story director (sunset, workshop, compass, next morning, Piko, fog, demo end).
story = actors.spawn_actor_from_class(unreal.LSBrindleStory, v(0, 0, 50), rot())
story.set_actor_label("BrindleStory")
story.set_folder_path("Story")
story.set_editor_property("interior_spawn", transform((IX - 5.5, IY, 1.0), yaw=0))
story.set_editor_property("door_spawn", transform((75, 590.5, 21.2), yaw=-90))
story.set_editor_property("end_view", transform((60, 1500, 22), yaw=90))
story.set_editor_property("piko_perch", v(48, 664, 21.4))
story.set_editor_property("glider_prop", glider)
story.set_editor_property("edge_wall", edge_wall)
story.set_editor_property("compartment_props", compartment_props)
always_loaded(story)

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

# Greybox inspect meshes now covered by art (interaction finds them by position, so hiding is safe).
for a in actors.get_all_level_actors():
    if a.get_actor_label() in ("Inspect_Maps", "Inspect_Sketches", "Inspect_Notes", "Inspect_Portrait", "Inspect_Instruments"):
        hide(a)

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
