"""Bakes ambient occlusion (R) and worn edges (G) into the vertex colours of every Windrest kit piece, for Unity's
painterly shader (polish pass 1). The kit has no UVs (the shader paints in world space), so large faces are first
split into a finer grid to give the shading somewhere to live. Pieces that stand on the ground are baked over a
ground plane, so their bases darken where they meet it. Orientation, scale and material slots are unchanged.

  blender --background --factory-startup --python bake_kit_vertex_ao.py -- <source FBX folder> <output folder>
Source: Unreal/SourceArt/Meshes/Windrest (read only). Output: Unity/LastSkyfarer/Assets/Art/Windrest/Meshes.
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

SRC, OUT = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(OUT, exist_ok=True)
NO_GROUND = ("SM_HangingLantern", "SM_FloatingIsle", "SM_Windmill_Sails", "SM_WindRibbon", "SM_Deck", "SM_PortraitFrame", "SM_SketchBoard")
SKIP = ("SM_WindRibbon",)                        # a flat ribbon card: nothing to shade
MAX_EDGE = 0.6                                   # metres; finer grid for the shading on big faces


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.cycles.device = "CPU"
    world = bpy.data.worlds.new("W")
    sc.world = world
    world.light_settings.distance = 1.6         # AO reach, metres


def refine(o):
    """Split big faces into a grid (no UVs to preserve) so per-vertex shading has resolution."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    for _ in range(5):
        long_edges = [e for e in bm.edges if e.calc_length() > MAX_EDGE]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bm.to_mesh(o.data)
    bm.free()


def edge_wear(o):
    """0..1 per vertex: how convex the surface is there (outer edges and corners catch light and wear)."""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    wear = [0.0] * len(bm.verts)
    for v in bm.verts:
        if not v.link_edges:
            continue
        s = 0.0
        for e in v.link_edges:
            d = (e.other_vert(v).co - v.co)
            if d.length > 1e-6:
                s += d.normalized().dot(v.normal)
        s /= len(v.link_edges)
        wear[v.index] = max(0.0, min(1.0, -s * 3.0))
    bm.free()
    return wear


def process(path):
    name = os.path.splitext(os.path.basename(path))[0]
    reset()
    bpy.ops.import_scene.fbx(filepath=path, axis_forward="-Y", axis_up="Z")
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    before = len(o.data.vertices)
    if name not in SKIP:
        refine(o)
    wear = edge_wear(o)
    col = o.data.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    o.data.color_attributes.active_color = col
    if name not in SKIP:
        ground = None
        zmin = min((o.matrix_world @ v.co).z for v in o.data.vertices)
        if name not in NO_GROUND and zmin > -0.35:
            bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, max(0.0, zmin)))
            ground = bpy.context.active_object
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
        if ground:
            bpy.data.objects.remove(ground, do_unlink=True)
    for i, d in enumerate(col.data):
        ao = d.color[0] if name not in SKIP else 1.0
        ao = 0.25 + 0.75 * ao                   # never fully black: painted, soft corners
        d.color = (ao, wear[i], 0.0, 1.0)
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    out = os.path.join(OUT, name + ".fbx")
    bpy.ops.export_scene.fbx(filepath=out, use_selection=True, apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                             axis_forward="-Y", axis_up="Z", mesh_smooth_type="FACE", add_leaf_bones=False, bake_anim=False,
                             colors_type="LINEAR")
    print("LS_KIT_AO %s %d -> %d vertices" % (name, before, len(o.data.vertices)), flush=True)


for f in sorted(os.listdir(SRC)):
    if f.lower().endswith(".fbx"):
        process(os.path.join(SRC, f))
print("LS_KIT_AO_DONE", flush=True)
