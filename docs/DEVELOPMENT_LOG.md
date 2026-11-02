# Development Log

## 2026-11-02 (change of direction: Unreal Engine 5.8, 3D)

Adam moved The Last Skyfarer from the 2D Godot demo to a 3D game in Unreal Engine 5.8. `docs/UNREAL_PRODUCTION_PROMPT.md` is now the production brief, and the Godot demo is archived reference (its dialogue, quests, layout and lessons are reused; its code and sprites are not).

- Created `Unreal/LastSkyfarer.uproject` from the UE 5.8.4 Third Person C++ template. The template's classes were renamed to LastSkyfarer, with redirects so the template's assets still find them. Added `Unreal/.gitignore`.
- Added Git LFS rules for `*.uasset`, `*.umap`, `*.fbx`, `*.wav`, `*.png`, `*.tga`, `*.exr`, `*.psd` and `*.blend`. Existing PNGs already in Git stay as normal blobs; history was not rewritten.
- Generating project files works. The first C++ build stops because this PC has no .NET Framework SDK; it needs the .NET Framework 4.8.1 SDK from Visual Studio Installer.
- Checked connections: ElevenLabs works (voices, Voice Design, TTS, sound effects, music). The Unreal MCP is not connected yet; UE 5.8 includes an experimental Unreal MCP plugin that still needs enabling and registering.
- Phase 1 started: Canon Summary, Open Decisions and Decision Log in `docs/unreal/`. The Master Project Bible PDF on file is truncated at section 26.
- Stopped the earlier Firefly/Blender test work for the 2D build before anything was committed.
- Commit 7606874 holds 851 files, 753 of them in LFS (about 140 MB).
- Adam approved all Open Decision recommendations ("go"); see docs/unreal/DECISION_LOG.md. Source PDFs copied to docs/source/.
- Later on 2026-11-02: the .NET Framework SDK was installed and the project compiles and opens. Enabled the Unreal MCP and EditorToolset plugins and registered the MCP server with Claude Code on Adam's PC; a read-only actor query works (commit b9be051). Another, empty project (Documents\Unreal Projects\TheLastSkyfarer) had an editor open whose Live Coding blocked builds; it was force-closed after a save prompt did not resolve, losing only an unsaved untitled level. A config backup zip was kept.
- Drafted Bible sections 26-32 (D-20), the Phase 2 style guide, technical plan and Firefly prompt batch 1.
- Phase 3 started (Adam's "go"). Narrative data: `Unreal/Tools/convert_godot_data.py` turns the Godot dialogue, quests, journal, items, speakers and locations into 7 JSON files in `Unreal/Content/LastSkyfarer/Data` (opening line now says Upper Cliffs, per D-15; canon lines untouched). `Unreal/Tools/validate_narrative.py` checks references and canon lines and simulates a Milestone A run: passes (35 conversations, 114 lines, 4 quests).
- C++ Narrative module written in `Source/LastSkyfarer/Narrative/`: data types and loader, `ULSStorySubsystem` (flags, items, quests with Godot rules, journal and collectibles, story events, time of day, chapters, dialogue runner, atomic saves with .bak recovery) and automation tests `LastSkyfarer.Narrative.*`. **Not compiled yet**: written in the cloud, needs a build on Adam's PC. The device session that was building the player, glider and Piko stopped with an error before doing any work.

- Phase 3 part 2 (cloud, not compiled yet): interaction (`World/Interaction`: interactable rules ported from the Godot demo, interactor for Kieran, story triggers, location volumes, journal pickups, NPCs) and the restoration framework (`World/Restoration`: six stages stored as story flags, Beacon actor, ring puzzle with no fail state), plus tests `LastSkyfarer.World.*`. Glider tuning approved as D-24.

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
