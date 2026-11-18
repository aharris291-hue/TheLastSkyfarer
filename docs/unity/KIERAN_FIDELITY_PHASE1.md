# Kieran: character fidelity overhaul, Phase 1 findings

This is the inspection that the character fidelity directive asks for (`CHARACTER_FIDELITY_DIRECTIVE.md`). Nothing was changed before it was written. "Before" pictures are in neutral light, with post-processing off, in `Unity/Screenshots/KieranFidelity/before/` (captured with `-LSCharacterLab`).

## Project
- **Engine:** Unity 6000.6.9f1, Universal Render Pipeline (URP). Low quality uses its own renderer with SSAO. The PC target is an Intel UHD 630, which must hold 30 fps on Low at 1920×1080.
- **Kieran's pipeline:**
  - His body is the MPFB (MakeHuman) base mesh. Clothes and props are built by script in Blender: `Unreal/Tools/blender/kieran/build_kieran.py` and `dress_kieran.py`. The master file is `Kieran_Thorn_Master.blend`.
  - `finalize_kieran.py` turns the master into the game mesh. `Unity/Tools/blender/kieran/export_kieran_unity.py` runs it for Unity, with fixes.
  - In Unity, `KieranSetup.cs` builds the prefab: Humanoid avatar, Mixamo animator, glider and IK.
- **Rig:** 53 bones. Humanoid avatar. Mixamo clips retargeted. Kept as-is.

## What the game mesh is today
| Part | Master (triangles, modifiers) | In the game |
|---|---|---|
| Body (skin, face, hands) | 18,740 tris, MPFB topology, no subdivision | Kept at full density. The whole face is about 3–4k tris. |
| Hair | 33,336-tri smooth mass plus 117 coil curves | Mass decimated to 9,000 tris, which gives faceted dark lumps. The coils were removed because decimation shattered them. On top of that, about 1,450 alpha hair cards from the earlier character pass, which read as shards. |
| Jacket, shirt, trousers | 2.4–3.9k tris, smooth plus displace, solidify, subsurf 1 | Decimated by the 45k budget. No folds beyond a light displace. |
| Collar, lapels, pockets, flaps | 12-tri boxes with a bevel | Flat slabs: no roll, no stitching, no edge thickness. |
| Seams, hems | Thin curves (1.2–3.5 mm) | Four-sided tubes. They barely register. |
| Gloves, boots, belt, satchel | Low shells, solidify, subsurf 1 | Decimated. The boots are a remesh blob. |
| **Total** | | **44,863 tris, 29,583 verts, 2 materials** |

## Textures and shading today
- **One 4096 base-colour atlas:**
  - Smart-project UVs at uniform density, so the face gets the same texel density as the trousers.
  - No normal map, no AO map, no roughness/smoothness map. Every surface is flat apart from its vertex normals.
  - The master's materials do contain fabric weave bumps, but these were lost because only colour was baked.
- **Broken texture links in the master:** the MPFB eye, eyebrow and teeth textures use relative paths that only resolve from the original machine. From the current clone they are missing, so the bake used fallbacks.
- **Shader:** `LastSkyfarer/StylisedCharacter`, a custom toon-ramp shader with:
  - rim light, a hair "shine" lobe, a skin "scatter" lift and eye catchlights;
  - a single smoothness and specular value per material, not per surface.
  - The rim light and highlight lobes are what make him read as glossy plastic in neutral light.
- **Extra layers from the earlier pass:** cornea caps and a "wet line" on each eye. The directive's Phase 4 rules out wetness.

## Real limitations
1. **Geometry detail is thrown away rather than missing.** The master has more detail than the game mesh (subdivision levels, fabric bumps, coils), but the export decimates it and bakes only colour. Fix: build a high-poly and bake **normal + AO** from it onto the game mesh. That is the standard AA pipeline, and Blender can do it here.
2. **The hair has no clump structure.** A decimated smooth mass cannot read as curls. Fix: build real coil clumps as geometry, which is the high-poly. Make the game hair a clump-shaped low-poly shell derived from those coils, then bake their normals and AO onto it. Delete the alpha cards.
3. **Clothing construction details are slabs.** Fix:
   - thicker rolled collar, cuffs and pocket edges in the game mesh;
   - folds concentrated at the joints (elbows, knees, armpits, waist) in the high-poly;
   - stitch rows along every seam, pocket and hem, baked into the normal and AO maps.
4. **Material response is a single value per material.** Fix: an authored map that varies across the surface. Pack metallic in R, AO in G and smoothness in A, matching URP's Lit layout. Use URP Lit, which is physically based and already in the project's pipeline. Drop the rim, sheen and catchlight extras.
5. **Texel budget.** Fix: give the face and hands larger UV islands, so the face gets about four times the texel area.
6. **What can't honestly be done here:**
   - **No hand sculpting.** I work through Blender scripts, so the face's anatomical forms (eyelid creases, lip edges, nostrils, ear folds) come from MPFB's anatomy, refined by subdivision and baked crease detail. They are not hand-sculpted the way a character artist would sculpt with a tablet.
   - **No mesh skin-scattering.** URP has no skin subsurface scattering, so skin will be natural and matte, not translucent.
   - **No strand-level hair.** Strand rendering or grooms at 30 fps on a UHD 630 are out of reach. The clump mesh plus baked maps is the realistic ceiling here.

## Plan (Kieran only, then report before the others)
- **Game mesh:** keep the rig, avatar, animator, prefab and glider IK. Budget about 60–65k triangles for Kieran at LOD0, plus a LOD1 at about 50% and a LOD2 at about 20%. (Outcome: 85k at LOD0, because the hair shell, eyelashes and garments needed more. Low still holds 30 fps; see the result.)
- **New maps:** normal (tangent space, baked from the high-poly), and an ORM-style mask (metallic R, AO G, smoothness A). Base colour is re-baked at 4096 with face and hand priority.
- **Shading:** URP Lit with low smoothness. Skin about 0.35–0.42, cloth 0.08–0.18, leather about 0.3, brass about 0.5. No rim, no gloss boost, no bloom change.
- **Verification:** before/after in the neutral lab (post off), a fps check on Low, the EditMode/PlayMode tests and the story bot.
