# Unity character fidelity overhaul: Adam's standing rules

Adam set these rules on 2026-11-18 at 00:56 UTC for all game characters, starting with Kieran ("follow these rules when designing the game characters start now with Kieran now"). They are copied verbatim below. They sit alongside docs/unreal/KIERAN_PRODUCTION_DIRECTIVE.md, and the turnaround remains the source of truth for Kieran's look.

---

UNITY CHARACTER FIDELITY OVERHAUL — AA GAME QUALITY
You are acting as a senior Unity character technical artist, professional 3D character modeler, and rendering engineer.
I want you to substantially upgrade the visual quality of all existing characters in my Unity game to achieve a modern, professionally produced AA-game standard.
My goal is high-fidelity stylized realism, NOT increased shininess.
I want characters to look more detailed, refined, anatomically believable, sophisticated, and professionally sculpted.

PHASE 1 — Inspect the Existing Character Assets
Before changing anything:

1. Identify the Unity version and active render pipeline (URP, HDRP, or Built-in).
2. Inspect the existing character meshes, prefabs, materials, textures, rigs, and shaders.
3. Determine whether the characters use primitive geometry, procedural meshes, imported 3D models, or other assets.
4. Identify the specific limitations preventing the characters from achieving AA-quality visuals.
5. Determine whether the improvements require geometry changes, new character assets, better textures, revised shading, or a combination.

Do not assume that adjusting materials will solve underlying modeling deficiencies.

PHASE 2 — Upgrade the Actual Character Models
Prioritize improving the 3D models themselves.

* Refine facial topology and anatomical structure.
* Improve eye sockets, eyelids, noses, lips, ears, cheeks, and jawlines.
* Improve body proportions, musculature, hands, fingers, and joint transitions.
* Remove the appearance of simple, primitive, or low-poly construction where it conflicts with the intended art style.
* Add more sophisticated geometric silhouettes and natural transitions between anatomical forms.
* Improve hair volume, sculpted strands or clumps, and silhouette complexity.
* Improve clothing geometry, fabric thickness, folds, collars, cuffs, seams, and other construction details.

Preserve existing character identities, clothing designs, proportions where intentional, and recognizable features.
If the existing models are too simple, replace or remodel the necessary meshes rather than attempting to hide their deficiencies through shading.
Use appropriate modeling tools and asset workflows where available. Do not pretend that changing shader parameters increases mesh detail.

PHASE 3 — Improve Textures and Surface Detail
Introduce professional-quality physically based material textures where supported:

* High-resolution base-color textures.
* Carefully authored normal maps.
* Ambient occlusion maps.
* Material-specific smoothness or roughness maps.
* Subtle skin variation.
* Fabric weave, stitching, and surface imperfections.
* Natural hair color and texture variation.

Detail should be visible at ordinary gameplay camera distances, not only in extreme close-ups.
Avoid excessive procedural noise that makes surfaces appear dirty or artificial.

PHASE 4 — Eliminate the Plastic and Glossy Appearance
This is a mandatory requirement.
Do not increase specular intensity, metallic appearance, clear-coat effects, wetness, bloom, or overall surface glossiness as a substitute for quality.
In Unity, review Smoothness values and any associated texture-map channels. Excessively high smoothness can make characters look like polished plastic.
Skin must have natural, nonmetallic material response, with restrained highlights and appropriate surface variation.
Clothing must look like actual fabric, leather, or other intended materials rather than glossy plastic.
Hair should have controlled highlights without looking metallic or wet.
Use the appropriate physically based shading features for the project's existing render pipeline. Do not change the render pipeline solely to compensate for inadequate character assets.

PHASE 5 — Preserve Functionality
All improvements must integrate correctly into the existing Unity project.

* Preserve existing animations and Animator Controllers.
* Maintain compatible skeletons, rigging, and skin weights.
* Preserve gameplay functionality and scripts.
* Maintain character prefab references.
* Avoid breaking existing scenes.
* Use appropriate levels of detail and texture budgets to maintain gameplay performance.

Do not replace working characters with static models that can no longer animate.

PHASE 6 — Verify the Results
Evaluate upgraded characters under consistent, neutral lighting alongside their original versions.
The improvements must be obvious without enhanced lighting, post-processing, or added gloss.
Verify:

* Better facial anatomy.
* More sophisticated character silhouettes.
* Improved geometry and clothing detail.
* Natural skin and fabric materials.
* Higher-quality hair.
* Improved visual consistency.
* No unnecessary glossy or plastic appearance.
* Working animation and acceptable performance.

Provide a clear before-and-after comparison and explain which actual assets were modified.

CRITICAL REQUIREMENT
I do not want another superficial lighting or material update.
I want the characters themselves to become more sophisticated, detailed, and professionally constructed.
If achieving this quality requires external modeling software, more detailed replacement models, or a character asset creation pipeline, explain that limitation and implement what is genuinely possible with the available tools.
Do not claim to have improved geometry if you only adjusted shaders or materials.
FINAL GOAL: Characters that look like they were created by a professional AA-game character art team, featuring stylized realism, sophisticated modeling, believable anatomy, detailed clothing, and natural materials — WITHOUT artificial shine.
