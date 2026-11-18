# Kieran: character fidelity overhaul, result (Phases 2–6)

**Before/after:** neutral light, post-processing off, same camera and pose. The images are in `Unity/Screenshots/KieranFidelity/`:
- `before/` and `after/` hold the raw shots;
- `compare_*.png` puts each pair side by side.

They were captured with `LastSkyfarer.exe -LSCharacterLab`: a flat grey studio with one white key light and a flat grey ambient. There is no sky, fog or bloom, and the post stack is off.

## What changed, and whether it is geometry or shading

| Change | Kind | Where |
|---|---|---|
| **Hair:** 1,100 clumps of tight coils (5,463 helical strands, 1.29M triangles) grown over Kieran's own hair volume. The game hair is a new 14k-triangle shell remeshed from those clumps, so the silhouette is made of curls. It replaces the 9k smooth lump and the alpha hair cards. | **Geometry** (game mesh), plus a normal and AO bake from the coils | `kieran_hifi.py: build_hair` |
| **Clothing folds:** irregular ring folds where the jacket, shirt and trousers bend (elbows, knees, armpits, hips, waist, wrists), in the game mesh. Finer creases and drape exist in the high-poly only. | **Geometry**, plus normal | `fold_mesh` |
| **Subdivision:** the scarf, satchel, gloves and boots keep a level of subdivision instead of being flattened to their cages. The hero budget rises from 45k to about 85k triangles at LOD0. | **Geometry** | export patch |
| **Stitching:** 3,536 stitches. Double top-stitching runs along every seam and hem. Single stitching runs round the pockets, flaps, lapels and collar, and 4 mm in from the cuff and collar-band edges. | High-poly **geometry**, baked to normal + AO | `build_stitches` |
| **Fabric weave, leather grain and skin pores:** relief in the high-poly's materials. | Baked to the **normal map** (surface detail, not silhouette) | `add_all_relief` |
| **Face and hands:** about 4× the texture area on the face and about 2× on the hands. Body detail is baked from a twice-subdivided body. | Texture budget, plus normal | `prioritise_uvs` |
| **Eyes:** the MPFB iris, eyebrow and teeth textures are relinked; their broken paths had been baking blanks. The cornea "wet" caps and lid lines are removed. | Texture fix, layers removed | `fix_mpfb_paths`, `KieranSetup` |
| **Nape:** scalp polygons not under the hair are now skin, so there is no stair-stepped scalp edge. | Material assignment on the mesh | `build_hair` |
| **Skinning:** trim that was never attached to the skeleton (the sleeve seams) was pinned to the pelvis and drew lines from the shoulders when he moved. It now takes its weights from its garment. | Rig data | export patch 4c |
| **Materials:** URP Lit (physically based) with a normal map, plus one packed map: metallic R, occlusion G, smoothness A. | **Shading** | `KieranSetup` |
| **Smoothness, from the map only:** skin 0.38, lips 0.45, hair 0.10, cloth 0.06–0.10, leather 0.28–0.32, brass/steel 0.45–0.52. There is no rim light, sheen lobe, catchlight, wetness or extra bloom. The old toon shader's rim light and hair sheen are gone from Kieran. | **Shading** (less gloss than before) | `kieran_hifi.py: SMOOTH` |
| **Colour noise:** the master's painted colour noise is pulled 70% towards each colour's mean, because under physical light it read as dirt. The hair is a very dark brown rather than near-black, so its forms read. | Base colour | `soften_ramps` |
| **Ambient occlusion:** contact occlusion from the game mesh, plus the curls' own occlusion in the hair. | Baked map | `bake_maps` |
| **LODs:** LOD1 at 50% and LOD2 at 22%, same rig and maps. Switch heights are 22% and 7% of the screen. | Geometry | `make_lods` |
| **SSAO on Low and PC:** interleaved-gradient sampling with the bilateral blur. The old setting left blotches on smooth skin and cloth under URP Lit. Same radius and intensity. | Rendering setting (all scenes) | `RenderingSetup.cs` |

**Kept as they were:**
- the skeleton (53 bones), the Humanoid avatar, the Mixamo Animator and its states;
- the glider and its hand IK;
- the prefab path and references, the controller and collision.

## Assets modified
- `Unity/LastSkyfarer/Assets/Art/Characters/Kieran/Model/`:
  - `Kieran_Thorn_GameReady.fbx` (new mesh with LOD0–2);
  - `T_Kieran_BaseColor.png`;
  - `T_Kieran_Normal.png` (new);
  - `T_Kieran_MetalAOSmooth.png` (new);
  - `T_Kieran_Mask.png`.
- `M_Kieran.mat` and `M_Kieran_Metal.mat` (now URP Lit), `Assets/Prefabs/Kieran.prefab`, `Assets/Scenes/Brindle.unity`.
- Removed: `Kieran_HairCards.asset`, `Kieran_Cornea.asset`, `Kieran_WetLine.asset`.
- **New tools:**
  - `Unity/Tools/blender/kieran/kieran_hifi.py` and `export_kieran_hifi.py`;
  - `Assets/Scripts/Dev/CharacterLab.cs` (`-LSCharacterLab`).
- **Changed tools:** `Assets/Editor/KieranSetup.cs`, `Assets/Editor/RenderingSetup.cs` (SSAO), `Assets/Scripts/World/BrindleLevel.cs` (lab flag).
- **Not touched:** the master `Kieran_Thorn_Master.blend` and the Unreal scripts (read only), Adam's artwork and the Mixamo originals.

## Verification (2026-11-18, UHD 630, 1920×1080)
- **Low quality:** 30.0 fps running and 30.0 fps gliding at the 30 cap. Uncapped headroom is 59.3 fps (square, morning) and 54.4 fps (sunset), against 57.5/53.0 before.
- **Tests:** EditMode 27/27, PlayMode 10/10 (including the glider-grip tests), story bot 74/74.
- **Mesh:** LOD0 84,831 triangles / 47,926 vertices, LOD1 42,414, LOD2 18,623. 53 bones, Humanoid avatar valid (52 mapped).
- **Maps:** 4096 base colour, normal and metallic/AO/smoothness.
- **The before `8_hand` shot** is badly framed: the camera sat behind the stowed glider. The after shot uses the corrected angle.

## Honest limits
- **No hand sculpting.** The face's anatomy is MPFB's (MakeHuman's), refined by subdivision and baked detail. It is not hand-sculpted with a tablet: the eyelids, lips, nose and ears are the base model's forms. A character artist sculpting the face would still lift it further.
- **The hair is a mesh shell with baked curls,** not strands. Close up, the shell's bumps are larger than single curls. Strand or groom hair at 30 fps on a UHD 630 isn't possible.
- **No subsurface scattering for skin** in URP, so the skin is natural and matte, not translucent.
- **Small props** (goggles, compass, eyelets, buckles) are reduced to about 23% of their modelled triangles to fit the budget.
