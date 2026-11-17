# Kieran Thorn: 3D build, technical spec and QA report

This is a draft for Adam's approval. Nothing here is imported into Unreal yet. The work follows `docs/unreal/KIERAN_PRODUCTION_DIRECTIVE.md`, and Adam's five-view turnaround (`art_source/characters/Kieran Thorn Turnaround Sheet.png`) is the only reference used.

## Files

| File | What it is |
|---|---|
| `Kieran_Thorn_Master.blend` | Editable master with all external textures packed in. Separate objects for the body, every garment, the hair and each accessory, with the 53-bone rig. I re-opened it after packing to check it: 126 objects, 53 bones, 5 images packed, none missing. |
| `Kieran_Thorn_GameReady_scene.blend` | The joined, game-budget version, set up in a scene. |
| `export/Kieran_Thorn_GameReady.glb` and `.fbx`, `export/T_Kieran_BaseColor.png` | Game exports with one baked 2048 colour atlas and 2 materials (cloth/skin and metal). I re-imported the GLB into an empty scene to check it: 1 skinned mesh, 1 armature with 53 bones, 44,966 triangles. |
| `export/export_report.json` | The numbers above, as written by the export script. |
| `renders/Kieran_Front.png`, `_ThreeQuarterFront`, `_Side`, `_ThreeQuarterRear`, `_Rear` | The five reference angles. |
| `renders/Kieran_QA_vs_turnaround.png` | The five renders laid over the five drawings for comparison. |
| `renders/pose_*.png` | Deformation tests: arms raised, elbows bent, torso twist, walk, knees bent, head turn. |
| `reference/turnaround_measurements.json`, `reference/palette_sampled.json` | Silhouette measurements and colours taken from the sheet. |
| Scripts in `Unreal/Tools/blender/kieran/` | `measure_reference.py`, `build_kieran.py` (body), `dress_kieran.py` (face, hair, clothes, accessories, materials), `finalize_kieran.py` (poses, game build, export, QA sheet). Rebuild from the repo with `dress_kieran.py -- full params_v4.json`, then run `finalize_kieran.py` on the master. |

## How it was built

- **Body.** The base is MPFB (MakeHuman), whose output is CC0, with the CC0 young_african_male skin pack. It's a lean teenage build: weight 0.3, age about 16, slimmer torso and thighs. The face is set by targets: larger eyes, a gentle smile, a softer chin and fuller cheeks. The skeleton is the Unreal-named `game_engine` rig: pelvis, spine_01-03, clavicles, upperarm and lowerarm, hands and fingers, thighs, calves, feet and balls, neck and head. The relaxed stance from the drawings is baked in as the rest pose.
- **Matching the sheet.** I separated the five drawings automatically, measured their silhouettes, and rendered the model's front and side silhouettes to compare against them, normalised from chin to soles. The chin sits at 16% of the height on both the drawing and the model. Average width difference is 2.5% (front) and 2.2% (side) of the chin-to-sole height. By region, front then side:
  - shoulders +3.4% / +1.5%
  - chest and arms -1.3% / -1.0%
  - hips -0.2% / -2.4%
  - thighs +3.6% / +0.4%
  - knees and calves +2.5% / +0.4%
  - boots -5.7% / -4.9%
  
  These figures come from the model build just before the final colour tweak, which changed colours only, not shapes.
- **Clothes.** Every garment is cut from the body surface, given a small region-by-region ease, real thickness and finished hems, and carries the body's skin weights so it deforms with the rig:
  - cream henley with buttons
  - olive jacket: open front, back collar and lapels, chest pockets with flaps and buttons, sleeve pockets, sleeves rolled to mid-forearm with cream cuffs
  - grey-olive trousers with rolled cuffs
  - belt with buckle
  - laced leather boots: smooth leather toe, sole, folded cuff, laces and eyelets
  - fingerless gloves
  - sky-blue double-wrap scarf with soft tails
- **Accessories, each skinned to its bone.**
  - Goggles: brass rims and cups, pale-blue lenses, rivets, bridge, leather strap.
  - Satchel: on his left hip, strap over his right shoulder running across the front and the back, flap and buckle.
  - Compass: on his right hip, with case, bezel, dial, eight cardinal marks, needle and bail.
- **Hair.** About 3,000 coiled curl clumps grown from the scalp: fuller on top and at the front, tidy at the nape, over a hair-coloured scalp.
- **Colours.** Sampled from the sheet. Materials are hand-painted style PBR: soft colour variation, weave or grain bump, restrained metal.

## Real-time budget (Adam's UHD 630)

- **Triangles.** The master is about 740k triangles, most of it hair. The game version is about 46k. Hair, clothes and props were reduced by a budget that keeps the face, eyes, brows and lashes at full detail.
- **Draw calls.** There are 25 material slots on one mesh. That should be fine for one hero character, but it's more draw calls than ideal (see below).
- **Bones.** 53.

## Deformation tests

All six poses render without mesh collapse. The clothing, cuffs, boots and accessories follow the rig. Two notes: the knees-bent test lifts the feet (there's no root motion, so he floats), and the walk test is a single stride pose.

## Refinement pass 2 (done)

- **Hair** is now a soft, chunky mass of fused curl clusters (metaballs) with small coils on the surface. It's tall on top and close at the sides, like the drawings.
- **Face** has a gentler smile, and the skin has hand-painted touches as vertex colour: warm cheeks and nose, deeper lips, soft shadow round the eyes.
- **Boots** are chunkier, with lug-tread soles and criss-cross laces on the boot face.
- **Satchel** is a soft, rounded messenger bag with a curved flap and two buckle straps. It now hangs clear of his hand.
- **Jacket** has a back yoke and back seams. The trousers have back patch pockets and side seams. The arms hang a little more relaxed.
- **Game textures:** all colours are baked into one 2048 atlas, so 25 materials became 2.

## Honest gaps (what still falls short of the drawings)

1. **Hair.** It's now a soft clustered mass, but its outline is still a little smaller and lumpier than the drawing's rounded curls.
2. **Face.** The expression is closer to neutral than the drawing's gentle smile, and the skin is a flat painted tone with no hand-painted texture yet.
3. **Boots.** They measure about 5% narrower than the drawing and lack its chunky lug soles, toe cap and bold criss-cross lacing.
4. **Satchel.** It's boxy; the drawing shows a soft, rounded messenger bag with buckle straps.
5. **Jacket.** No back yoke seams, epaulettes or stitching yet.
6. **Trousers.** No pockets, and the folds are subtle.
7. **Pose.** The arms hang straighter than in the drawings. The stance is a rest pose, not the drawings' relaxed attitude.
8. **Textures.** The colours are baked into one atlas, but the UV packing is loose (many small islands), so some of the 2048 texture is wasted. A tidier unwrap would give sharper texture detail.
9. **Skeleton.** It uses Unreal-style bone names, but it is not the full UE5 Manny hierarchy (no spine_04/05 or IK bones). Using the mannequin's animations will need an IK Retargeter.
10. **Not in Unreal yet.** It hasn't been tested at 30 fps in-game. That happens after Adam approves the design.
