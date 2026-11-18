# Kieran: character fidelity overhaul, pass 2

This is Adam's second, deeper pass under all six phases of `CHARACTER_FIDELITY_DIRECTIVE.md`.

**Comparisons** in `Unity/Screenshots/KieranFidelity/`:
- `compare_pass2_*.png`: pass 1 against pass 2, in Unity under neutral grey light with post-processing off (`-LSCharacterLab`), same camera and pose. Raw shots are in `after/` (pass 1) and `pass2/`.
- `compare_pass2_geometry_face_hands.png`: geometry only (Blender, flat grey, no textures), so the shape changes can be judged apart from any shading.

## Geometry changes (the mesh itself)
| Area | Change | Game mesh | High-poly (baked to normal/AO) |
|---|---|---|---|
| **Face** | Subdivided once over the face (9.4k → 28k body faces with the hands), then sculpted by script from landmarks measured on Kieran's own head. **Eyes:** thicker margins on both lids, an upper-lid crease and fold, a soft lower lid, a caruncle dip at the inner corner. **Nose:** a defined bridge and tip, alar wings with the groove round them, nostril openings. **Mouth:** a raised vermilion border with a cupid's bow, philtrum columns and groove, a pressed lip line and corners, upper/lower lip fullness, a mentolabial fold. **Cheekbones.** | the larger forms (wider falloffs) | all of it, plus sharpening of the whole face |
| **Ears** | The helix and antihelix deepened by sharpening the ear's own forms | moderate | strong |
| **Hands** | Subdivided once. Knuckles over every finger joint, fuller finger pads, joint creases on the palm side. **Nail plates:** new geometry, thin and domed, one per finger and thumb, skinned to the fingertip bones. Knuckles are also raised on the gloves. | knuckles, pads, nails | plus creases |
| **Hair** | Finer clumps: 2,378 clumps of 9,508 coils, against 1,100/5,463 in pass 1, with a narrower coil radius and pitch. The game shell is remeshed at 1.9 mm and kept at 22k triangles, so each bump is about one curl. Plus **721 edge curl cards**: small alpha-cut cards of coiled strands standing out of the shell, for a soft outline. They are geometry in their own material; the farthest LOD drops them. | shell + cards | 2.46M-triangle coils |
| **Clothing edges** | **Rolled hems** (new tubes) along every open edge of the jacket (front opening, waist, sleeve ends), shirt and trousers. Cuffs (sleeve, trouser, boot) about 50% thicker with rounder bevels. Collar, lapel and flap edges crisper (bevel 1.2 mm, 2 segments). | yes | yes, plus stitching |
| **Props** | The budget for goggles, compass, buckles, eyelets and buttons raised from 23% to 43% of their modelled triangles. The goggle rims are round again. | yes | |

**Triangles:** LOD0 152,765 (pass 1: 84,831), LOD1 76,365, LOD2 32,912.

## Shading changes
- **Hair cards:** URP Lit with alpha clip, both sides, smoothness 0.12. The strand texture is painted by script in Kieran's hair browns.
- **Nails:** smoothness 0.42 (natural nail, not glossy). Everything else keeps pass 1's values: skin 0.38, cloth 0.06–0.10, hair 0.10, leather about 0.3, brass/steel about 0.5.
- **Nothing glossier.** No rim, sheen, wetness or bloom was added.
- **Materials are matched by name** in the importer, not by slot. This fixed the hair cards first showing the colour atlas.

## Verification (2026-11-18, UHD 630, 1920×1080, Low)
- **Frame rate:** 30.0 fps running and 30.0 fps gliding at the cap. Uncapped headroom is 59.9 fps (morning) and 54.5 fps (sunset); pass 1 was 59.3 and 54.4.
- **Tests:** EditMode 27/27, PlayMode 10/10, story bot 74/74.
- **Unchanged:** skeleton (53 bones), Humanoid avatar, Mixamo Animator, glider and IK, prefab.

## Assets modified
- **Game files:**
  - `Assets/Art/Characters/Kieran/Model/`: `Kieran_Thorn_GameReady.fbx`, `T_Kieran_BaseColor/Normal/MetalAOSmooth/Mask.png`, new `T_Kieran_HairStrands.png`;
  - new `Assets/Art/Characters/Kieran/M_Kieran_HairCards.mat`;
  - `Kieran.prefab`, `Brindle.unity`.
- **Tools:**
  - new `Unity/Tools/blender/kieran/kieran_face.py` (face and hand sculpt, nails) and `kieran_pass2.py` (pass-2 steps);
  - changed `kieran_hifi.py` and `export_kieran_hifi.py`;
  - changed `Assets/Editor/KieranSetup.cs` (hair-card material, remap by name).

## Still limits of scripted Blender work
- **The face is sculpted by measured, scripted displacement.** It defines the lids, lips, nose, ears and cheekbones on MakeHuman's anatomy. It is not freehand sculpting: proportions and expression are the base model's, and an artist with a tablet would still do better on subtle asymmetry, the eye shape and youthfulness. In close-ups the eyes still read darker than the turnaround's bright brown eyes.
- **The hair is a remeshed shell with curl cards,** not individual strands or a groom. That's the realistic ceiling at 30 fps on a UHD 630.
- **The fingers are mostly hidden** by the fingerless gloves in the default pose, so the hand work shows best in close-ups and the geometry sheet.
