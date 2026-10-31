# Project Audit Report

Date: 2026-10-31. Scope: every file Adam attached to the project (`/mnt/project-files/The Last Skyfarer/`), plus the zips and `slice_sprites.py`.

## What was supplied

| Kind | Files | Used in the demo |
|---|---|---|
| Story | `The Last Skyfarer.pdf` (script), `The Last Skyfarer- Master Project Bible.pdf` | Yes. Chapters 1 to 3, characters, tone, places |
| Kieran | Turnaround, Actions, Action frames, Emotions, with-Staff turnaround | Yes. Sprites from Action frames, portraits from Emotions |
| Piko | Piko Turnaround, Keiran/Piko with Staff | Yes. Side view, in-world and portrait |
| Windrest cast | Tessa Reed, Elias Thorn (Final Years) | Yes |
| Other characters | 25 more turnarounds (Bram, Elara, Joren, Arlen, Doran, Selka, Varek, Verena, Raxis, Soren, Lysette, Cassian, Thalen, Sage Alder, Rhea, Kael, Aeolus, guardians, etc.) | Bram and Elara as stand-ins only (see Conflicts) |
| Places | Windrest Village map, Brindle Isle atlas, World Above the Clouds map, Fantasy Atlas, Eight Realms platformer asset atlas | Yes. Atlas for environment props, maps for journal and level layout |
| Other | 2 Gemini images, Skyfarer Staff, images.zip, images2.zip, thelastskyfarer.zip, GameSprites/, Character/ | Gemini image used for title key art, others reviewed |

Originals were never modified. Copies of every source image used are kept untouched in `art_source/`. All derived art is produced by `tools/sprite_pipeline.py` and can be regenerated.

## Conflicts between sources (not resolved silently)

1. **Opening location.** The script opens on the Upper Cliffs; the bible describes Kieran starting his day leaving the workshop. The demo opens at the workshop door at sunrise and passes the Upper Cliffs during deliveries.
2. **Piko's first appearance.** The script introduces Piko in Chapter 3 after the first launch. The demo meets Piko on the morning of the launch, just before the glide, so the companion and sensing can be shown. A decision card was posted; the demo currently follows the script order *within* the day but Piko appears before the launch. Needs Adam's call.
3. **Piko's first words.** The two documents give two different versions. Piko does not speak in the demo (chirps only), so nothing was chosen.
4. **Master Bible is truncated** at section 26. Anything after that is unknown.
5. **Maren Holt** (postmistress, quest giver) has no art. A clearly labelled silhouette ("art pending") is used.
6. **"Tavern Keeper" and "Flower Grower"** have no named art. Bram Holloway and Elara Greenborough turnarounds were used as stand-ins. They are undocumented in the story files, so this is a casting proposal, not lore.
7. **No glider art exists.** Kieran's glide frames are his jump poses with no glider; the glider prop in the workshop is a placeholder.
8. **Environment art** is cut from the platformer atlas and upscaled 4x; several houses repeat. Fine for a demo, not final.
9. **Combat** is described in the bible but there is no combat art for enemies in the Windrest arc, so the demo has no combat. Inputs for attack and dodge are reserved.

## Risks

- AI-generated source art (the Gemini images, the atlases) has unclear licensing for commercial release. See ASSET_LICENSES.md.
- The Windows build was exported but could not be run on Windows from this environment.
