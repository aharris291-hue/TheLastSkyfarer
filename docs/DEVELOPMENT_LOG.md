# Development Log

## 2026-10-31 (visual fixes after Adam's first playtest)

Adam reported blurry, faded sprites, Kieran's feet vanishing on jump, seams in the scenery, static backgrounds and glitchy NPCs. Causes and fixes:

- **Blurry art.** Kieran's animation frames on the source sheet are only about 100 px tall and the props came from a 384 px wide atlas panel, then were stretched 2x to 6x in-game. Added `tools/esrgan_upscale.py` (Real-ESRGAN anime model, run locally on CPU) and `tools/hd_pipeline.py`, which upscale the untouched sources 4x and rebuild every game sprite from them.
- **Faded, see-through Kieran.** The old cut-out blurred the alpha edge by about 3 px on a 100 px figure, so a large share of his pixels were half transparent. The new cut-out follows the ink outline at 4x and keeps the body fully opaque (a test now checks this).
- **Feet cut off on jump.** The jump crop ended at the cell border, but the boots hang below it. The crop now runs to y=294 and the grid line is painted out; every animation shares one canvas with the feet on the same baseline.
- **Seams and white gaps.** Houses and windmills floated above the ground with sky showing underneath, the hills faded to transparent before reaching the island, and some props carried white background pockets or neighbouring objects (the bush cut beside the windmill). Props now sit on the ground, the hills are solid behind the island, white pockets are removed, and the island underside uses tiled stonework instead of a grey gradient.
- **Glitchy NPCs.** NPC textures were about 640 px tall and drawn at 190 px with no mipmaps, which shimmers. They are now pre-sized with high-quality filtering. Villagers also glance at Kieran when he is near.
- **Static scenery.** Windmill sails turn (tower and rotor are now separate), trees and banners sway (shader), clouds drift, distant islands bob, and leaves and petals blow through the village.
- Workshop props rebuilt the same way.

## 2026-10-31

- Audited all supplied files; wrote AUDIT_REPORT.md.
- Set up Godot 4.3 project: autoloads for settings, game state, saves, audio, scene routing, dialogue and HUD. Data-driven JSON for quests, dialogue, items, journal, locations and speakers.
- Built `tools/sprite_pipeline.py`: cuts Kieran's animation rows (idle 5, walk 6, run 6, jump 4, glide 3) from the action-frame sheet, portraits from the emotions sheet, Piko from his turnaround, NPC bodies, environment props from the platformer atlas, a seamless ground tile, and the journal maps. Untouched copies of sources go to `art_source/`.
- Built `tools/audio_synth.py` for placeholder music and sound.
- Implemented Kieran (movement and glide), Piko (spring follow, sensing), Windrest and the workshop, four quests and the end card.
- Bugs found and fixed while testing:
  - `Sky` class name clashed with a native class; renamed `SkyLayer`.
  - Updraft `hidden` clashed with an Area2D member; renamed `concealed`.
  - Glide ended when an updraft pushed Kieran upward; velocity now only gates starting a glide.
  - Piko could not sense the hidden updraft because its origin is at the bottom; added `sense_position()`.
  - First Skywatch step was 236 px against a 224 px maximum jump; added a crate step.
  - Prompt panel too tall; journal and title labels wrapped one word per line; fixed.
- Exported Windows build. Test suite at 331/331.
