"""Builds the painterly master materials and their instances (STYLE_GUIDE section 5) in /Game/LastSkyfarer/Materials.

  M_Painterly_Surface  two paint colours mixed by a world-aligned brush-noise texture, a separate colour on
                       upward faces (grass on top of rock), darker low down, a little paint grain.
  M_Painterly_Foliage  the same, plus a gentle wind sway (world position offset).
  M_CloudSea           slowly drifting lilac-and-white cloud tops; lit, with a soft glow so it never goes grey.
All three are opaque and texture-light, so they stay cheap on Low. Re-running replaces the assets.

Run headless (the path must not contain spaces; copy the script somewhere first if needed):
  UnrealEditor-Cmd.exe Unreal/LastSkyfarer.uproject -run=pythonscript -script=<abs path> -unattended -nullrhi
The brush texture comes from Tools/blender/make_brush_noise.py (Unreal/SourceArt/Textures/T_BrushNoise.png).
"""
import os

import unreal

ROOT = "/Game/LastSkyfarer/Materials"
MEL = unreal.MaterialEditingLibrary
assets = unreal.AssetToolsHelpers.get_asset_tools()
PROJECT = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())
NOISE_SRC = os.path.join(PROJECT, "SourceArt", "Textures", "T_BrushNoise.png")


def hex_color(h, a=1.0):
    """'#rrggbb' (sRGB, as in the style guide) to a linear colour."""
    def lin(v):
        v /= 255.0
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return unreal.LinearColor(lin(int(h[1:3], 16)), lin(int(h[3:5], 16)), lin(int(h[5:7], 16)), a)


def fresh(path):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)


# ------------------------------------------------------------------ the brush texture
task = unreal.AssetImportTask()
task.filename = NOISE_SRC
task.destination_path = ROOT + "/Textures"
task.destination_name = "T_BrushNoise"
task.replace_existing = True
task.automated = True
task.save = True
assets.import_asset_tasks([task])
noise = unreal.load_asset(ROOT + "/Textures/T_BrushNoise")
noise.set_editor_property("srgb", False)
noise.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
unreal.EditorAssetLibrary.save_loaded_asset(noise)


# ------------------------------------------------------------------ graph helpers
class Graph:
    def __init__(self, mat):
        self.m = mat
        self.x = -1600

    def node(self, cls, y=0, **props):
        self.x += 40
        n = MEL.create_material_expression(self.m, cls, self.x, y)
        for k, v in props.items():
            n.set_editor_property(k, v)
        return n

    def link(self, a, b, pin="", out=""):
        MEL.connect_material_expressions(a, out, b, pin)
        return b

    def scalar(self, name, value, y=0):
        return self.node(unreal.MaterialExpressionScalarParameter, y, parameter_name=name, default_value=value)

    def color(self, name, value, y=0):
        return self.node(unreal.MaterialExpressionVectorParameter, y, parameter_name=name, default_value=value)

    def const(self, value, y=0):
        return self.node(unreal.MaterialExpressionConstant, y, r=value)

    def op(self, cls, a, b, y=0):
        n = self.node(cls, y)
        self.link(a, n, "A")
        self.link(b, n, "B")
        return n

    def mul(self, a, b, y=0):
        return self.op(unreal.MaterialExpressionMultiply, a, b, y)

    def add(self, a, b, y=0):
        return self.op(unreal.MaterialExpressionAdd, a, b, y)

    def sub(self, a, b, y=0):
        return self.op(unreal.MaterialExpressionSubtract, a, b, y)

    def div(self, a, b, y=0):
        return self.op(unreal.MaterialExpressionDivide, a, b, y)

    def lerp(self, a, b, alpha, y=0):
        n = self.node(unreal.MaterialExpressionLinearInterpolate, y)
        self.link(a, n, "A")
        self.link(b, n, "B")
        self.link(alpha, n, "Alpha")
        return n

    def mask(self, src, r=False, g=False, b=False, y=0):
        n = self.node(unreal.MaterialExpressionComponentMask, y, r=r, g=g, b=b, a=False)
        self.link(src, n)
        return n

    def saturate(self, src, y=0):
        n = self.node(unreal.MaterialExpressionSaturate, y)
        self.link(src, n)
        return n


def new_material(name):
    path = ROOT + "/Masters/" + name
    fresh(path)
    m = assets.create_asset(name, ROOT + "/Masters", unreal.Material, unreal.MaterialFactoryNew())
    # Packaged games only compile a material for the mesh types it is flagged for (the editor fixes this on the fly).
    m.set_editor_property("used_with_instanced_static_meshes", True)
    return m


def painterly_graph(mat, wind=False):
    """Shared body of the painterly masters; returns the graph."""
    g = Graph(mat)
    wp = g.node(unreal.MaterialExpressionWorldPosition, 0)
    scale = g.mul(g.scalar("BrushScale", 4.0, 60), g.const(100.0, 80))
    p = g.div(wp, scale)
    # Planar UVs from the top, nudged by height so walls do not smear into stripes.
    uv = g.add(g.mask(p, r=True, g=True), g.mul(g.mask(p, b=True), g.const(0.7)))
    tex = g.node(unreal.MaterialExpressionTextureSampleParameter2D, 0, parameter_name="BrushNoise", texture=noise,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    g.link(uv, tex, "UVs")
    paint = g.lerp(g.mask(tex, r=True), g.mask(tex, g=True), g.scalar("StrokeMix", 0.4))
    base = g.lerp(g.color("ColorA", hex_color("#B9A58A")), g.color("ColorB", hex_color("#9C8569")), paint)

    # Upward faces take the top colour (grass on rock, moss on stone).
    up = g.mask(g.node(unreal.MaterialExpressionVertexNormalWS), b=True)
    top_mask = g.mul(g.saturate(g.mul(g.sub(up, g.scalar("TopStart", 0.6)), g.const(5.0))), g.scalar("TopAmount", 0.0))
    top = g.lerp(g.color("TopColorA", hex_color("#7FA548")), g.color("TopColorB", hex_color("#5E8A3A")), paint)
    c1 = g.lerp(base, top, top_mask)

    # Darker low down (cliff undersides), metres in world space.
    z = g.div(g.mask(wp, b=True), g.const(100.0))
    h = g.saturate(g.div(g.sub(z, g.scalar("ShadeBottom", -120.0)), g.scalar("ShadeRange", 120.0)))
    c2 = g.lerp(g.mul(c1, g.scalar("ShadeAmount", 0.65)), c1, h)

    # Fine paint grain.
    grain = g.add(g.const(0.92), g.mul(g.mask(tex, b=True), g.const(0.16)))
    final = g.mul(c2, grain)
    MEL.connect_material_property(final, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(g.scalar("Roughness", 0.85, 300), "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.connect_material_property(g.const(0.25, 340), "", unreal.MaterialProperty.MP_SPECULAR)

    if wind:
        # A gentle sway, phase-shifted across the island so trees do not move in step.
        t = g.mul(g.node(unreal.MaterialExpressionTime, 500), g.scalar("WindSpeed", 1.3, 500))
        phase = g.mul(g.add(g.mask(wp, r=True), g.mask(wp, g=True)), g.const(0.003))
        s = g.node(unreal.MaterialExpressionSine, 500, period=6.283)
        g.link(g.add(t, phase), s)
        dirv = g.node(unreal.MaterialExpressionConstant3Vector, 520, constant=unreal.LinearColor(1.0, 0.6, 0.0, 1.0))
        # More sway higher up the plant, none at its base, so grass and trunks stay rooted.
        above = g.sub(g.mask(wp, b=True), g.mask(g.node(unreal.MaterialExpressionObjectPositionWS, 560), b=True))
        height = g.saturate(g.div(above, g.mul(g.scalar("SwayHeight", 4.0, 580), g.const(100.0))))
        wpo = g.mul(g.mul(g.mul(s, g.scalar("WindAmount", 8.0, 540)), height), dirv)
        MEL.connect_material_property(wpo, "", unreal.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    return g


def cloud_graph(mat):
    g = Graph(mat)
    wp = g.node(unreal.MaterialExpressionWorldPosition)
    p = g.div(g.mask(wp, r=True, g=True), g.mul(g.scalar("CloudScale", 60.0), g.const(100.0)))
    drift = g.mul(g.node(unreal.MaterialExpressionTime), g.scalar("Drift", 0.004))
    tex = g.node(unreal.MaterialExpressionTextureSampleParameter2D, 0, parameter_name="BrushNoise", texture=noise,
                 sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    g.link(g.add(p, drift), tex, "UVs")
    tex2 = g.node(unreal.MaterialExpressionTextureSampleParameter2D, 0, parameter_name="BrushNoise2", texture=noise,
                  sampler_type=unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    g.link(g.sub(g.mul(p, g.const(2.7)), drift), tex2, "UVs")
    puff = g.saturate(g.mul(g.add(g.mask(tex, r=True), g.mask(tex2, r=True)), g.const(0.6)))
    col = g.lerp(g.color("ShadowColor", hex_color("#B9AED6")), g.color("LightColor", hex_color("#FBF6F2")), puff)
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(g.mul(col, g.scalar("Glow", 0.35)), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.connect_material_property(g.const(1.0), "", unreal.MaterialProperty.MP_ROUGHNESS)
    return g


def ribbon_graph(mat):
    """Glowing wind streaks: bright bands flowing along the ribbon (UV x), soft at the edges (UV y). Additive, unlit."""
    g = Graph(mat)
    uvn = g.node(unreal.MaterialExpressionTextureCoordinate)
    u, v = g.mask(uvn, r=True), g.mask(uvn, g=True)
    t = g.mul(g.node(unreal.MaterialExpressionTime), g.scalar("FlowSpeed", 0.8))
    s = g.node(unreal.MaterialExpressionSine, 0, period=1.0)
    g.link(g.sub(u, t), s)
    flow = g.add(g.mul(s, g.const(0.5)), g.const(0.5))
    absn = g.node(unreal.MaterialExpressionAbs)
    g.link(g.sub(g.mul(v, g.const(2.0)), g.const(1.0)), absn)
    edge = g.saturate(g.sub(g.const(1.0), absn))
    ends = g.node(unreal.MaterialExpressionAbs)
    g.link(g.sub(g.mul(u, g.const(2.0)), g.const(1.0)), ends)
    along = g.saturate(g.sub(g.const(1.0), ends))
    glow = g.mul(g.mul(g.mul(flow, edge), along), g.scalar("Intensity", 1.6))
    MEL.connect_material_property(g.mul(g.color("Color", hex_color("#CFEFFF")), glow), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    return g


ribbon = new_material("M_WindRibbon")
ribbon.set_editor_property("blend_mode", unreal.BlendMode.BLEND_ADDITIVE)
ribbon.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
ribbon.set_editor_property("two_sided", True)
ribbon_graph(ribbon)
MEL.recompile_material(ribbon)
unreal.EditorAssetLibrary.save_loaded_asset(ribbon)

surface = new_material("M_Painterly_Surface")
painterly_graph(surface)
foliage = new_material("M_Painterly_Foliage")
painterly_graph(foliage, wind=True)
foliage.set_editor_property("two_sided", True)
cloud = new_material("M_CloudSea")
cloud_graph(cloud)
for m in (surface, foliage, cloud):
    MEL.recompile_material(m)
    unreal.EditorAssetLibrary.save_loaded_asset(m)


# ------------------------------------------------------------------ instances (STYLE_GUIDE: grass green, wheat gold,
# terracotta roofs, warm stone, sky blue; round and warm for Brindle)
def instance(name, parent, colors=None, scalars=None):
    path = ROOT + "/Instances/" + name
    fresh(path)
    mi = assets.create_asset(name, ROOT + "/Instances", unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    for k, v in (colors or {}).items():
        MEL.set_material_instance_vector_parameter_value(mi, k, hex_color(v))
    for k, v in (scalars or {}).items():
        MEL.set_material_instance_scalar_parameter_value(mi, k, v)
    unreal.EditorAssetLibrary.save_loaded_asset(mi)
    return mi


GRASS = {"TopColorA": "#86AE4C", "TopColorB": "#5F8F3C"}
instance("MI_IslandGround", surface, dict(GRASS, ColorA="#A99278", ColorB="#86705B"), {"TopAmount": 1.0, "BrushScale": 9.0})
instance("MI_CliffRock", surface, {"ColorA": "#8E7C6B", "ColorB": "#6E5F55"}, {"BrushScale": 14.0, "ShadeBottom": -200.0, "ShadeRange": 160.0, "ShadeAmount": 0.55})
instance("MI_Stone", surface, dict(GRASS, ColorA="#CDBB9C", ColorB="#AD9877"), {"TopAmount": 0.25, "BrushScale": 2.0})
instance("MI_PathStone", surface, {"ColorA": "#C9B596", "ColorB": "#A8916F"}, {"BrushScale": 1.5, "StrokeMix": 0.2})
instance("MI_PathDirt", surface, {"ColorA": "#B4936A", "ColorB": "#987A55"}, {"BrushScale": 2.5})
instance("MI_Wood", surface, {"ColorA": "#8F6A45", "ColorB": "#6E4E33"}, {"BrushScale": 1.0, "StrokeMix": 0.85})
instance("MI_WoodFloor", surface, {"ColorA": "#9A7650", "ColorB": "#7A5A3C"}, {"BrushScale": 1.2, "StrokeMix": 0.9})
instance("MI_Plaster", surface, {"ColorA": "#EFE3C8", "ColorB": "#DCCBA8"}, {"BrushScale": 2.0, "ShadeAmount": 0.85})
instance("MI_RoofTerracotta", surface, {"ColorA": "#C8693F", "ColorB": "#A9512F"}, {"BrushScale": 1.5, "StrokeMix": 0.7})
instance("MI_RoofBlue", surface, {"ColorA": "#4F86B8", "ColorB": "#3B6A96"}, {"BrushScale": 1.5, "StrokeMix": 0.7})
instance("MI_RoofGreen", surface, {"ColorA": "#6F9A5A", "ColorB": "#557D45"}, {"BrushScale": 1.5, "StrokeMix": 0.7})
instance("MI_Sailcloth", surface, {"ColorA": "#EDE1C6", "ColorB": "#D6C49F"}, {"BrushScale": 3.0, "StrokeMix": 0.8})
instance("MI_Brass", surface, {"ColorA": "#C79A3B", "ColorB": "#A57C2C"}, {"BrushScale": 0.6, "Roughness": 0.45})
instance("MI_Foliage", foliage, {"ColorA": "#6E9C44", "ColorB": "#4E7A33"}, {"BrushScale": 3.0, "ShadeBottom": -10.0, "ShadeRange": 20.0, "ShadeAmount": 0.8})
instance("MI_FoliageBlossom", foliage, {"ColorA": "#8DB255", "ColorB": "#E7A6B8"}, {"BrushScale": 2.0, "StrokeMix": 0.2, "ShadeAmount": 0.85})
instance("MI_Wheat", foliage, {"ColorA": "#E2BE5E", "ColorB": "#C99A3E"}, {"BrushScale": 3.0, "WindAmount": 4.0, "WindSpeed": 1.8, "SwayHeight": 0.3})
instance("MI_Water", surface, {"ColorA": "#7CC3DE", "ColorB": "#4E98BE"}, {"BrushScale": 0.8, "StrokeMix": 0.6, "Roughness": 0.15, "ShadeAmount": 0.9})
instance("MI_Grass", foliage, {"ColorA": "#8DB651", "ColorB": "#5F8F3C"}, {"BrushScale": 1.5, "WindAmount": 6.0, "WindSpeed": 1.6, "ShadeAmount": 0.9, "SwayHeight": 0.8})
instance("MI_FlowerBed", foliage, {"ColorA": "#E77FA0", "ColorB": "#F2C84B"}, {"BrushScale": 0.5, "StrokeMix": 0.1, "WindAmount": 2.0, "SwayHeight": 0.6})
instance("MI_WindRibbon", ribbon)
instance("MI_WindRibbon_Impossible", ribbon, {"Color": "#4BB3FF"}, {"Intensity": 2.2, "FlowSpeed": 1.2})
instance("MI_CloudSea", cloud)
instance("MI_CloudPuff", cloud, {"ShadowColor": "#CFC6E6", "LightColor": "#FFFFFF"}, {"CloudScale": 12.0, "Glow": 0.5})

unreal.log("LS_BUILD_MATERIALS_OK")
