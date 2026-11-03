# Technical Architecture

Godot 4.3, GDScript, Compatibility (OpenGL) renderer. 1920x1080 reference viewport, `canvas_items` stretch with `keep` aspect, so any 16:9 window scales cleanly. Warnings for untyped variables are treated as errors, so code is explicitly typed.

## Folders

| Path | Contents |
|---|---|
| `scenes/` | `.tscn` scenes: player, UI (title, dialogue, HUD), world (windrest, workshop) |
| `scripts/systems/` | Autoload singletons |
| `scripts/player/`, `scripts/companion/` | Kieran and Piko |
| `scripts/world/` | Level base class, builders and interactables |
| `scripts/dialogue/`, `scripts/ui/` | Dialogue runner and menus (menus are built in code from `menu_base.gd`) |
| `data/` | JSON content: quests, items, journal, locations, speakers, `dialogue/*.json` |
| `assets/` | Game-ready art, audio, fonts, theme, shader |
| `art_source/` | Untouched copies of source art (ignored by Godot) |
| `tools/` | Python art and audio pipelines (ignored by Godot) |
| `tests/` | Automated test runner and screenshot runner (excluded from export) |

## Autoloads (load order)

1. **Settings**: audio buses, display, text size and speed, glide mode, input remaps. Persists to `user://settings.cfg`.
2. **GameState**: flags, inventory, quests, journal, discovered places, time of day, chapter. Evaluates condition strings and runs action lists.
3. **SaveManager**: slots, autosave, atomic writes (see SAVE_SYSTEM_SPECIFICATION.md).
4. **AudioManager**: music crossfade, ambience, pooled SFX with pitch variation.
5. **Router**: scene changes with fade and spawn points.
6. **DialogueDB**: loads `data/dialogue/*.json`.
7. **DialogueUI** (scene): typewriter text, portraits, choices.
8. **HUD** (scene): quest tracker, interact prompt, notifications, tutorial hints.

## Content as data

Dialogue nodes, quest objectives and interactions use two small languages:

- **Conditions** (strings, all must pass): `flag`, `!flag`, `item:id`, `quest:id:state`, `obj:quest:objective`, `tod:day|sunset|night`.
- **Actions** (dictionaries): `set`, `clear`, `give`, `take`, `quest_start`, `objective`, `quest_complete`, `journal`, `sfx`, `event`, `time`, `chapter`, `autosave`.

`event` actions call a function on the current level (for example `compass_awakens`), which is how scripted moments hook in. Lines quoted directly from the story documents carry `"canon": true`.

## Levels

`level.gd` is a base class with builder functions (`add_ground`, `add_platform`, `add_npc`, `add_inspect`, `add_updraft`, `add_door`, ...). `windrest.gd` and `workshop.gd` lay out their content in code from those builders, which keeps layouts reviewable in diffs and testable. Each level handles respawn, checkpoints and menus.

## Input

`input_config.gd` registers all actions at startup. Keyboard: A/D or arrows, Space jump and glide, Shift run, E interact, J or Tab journal, M map, Esc or P pause, Q/R journal tabs. Controller: A jump, B run, X interact, Y journal, View map, Menu pause, LB/RB tabs. Prompts switch between keyboard and controller labels based on the last device used.

## Pipelines

- `tools/sprite_pipeline.py` (Python, PIL, numpy): `python3 tools/sprite_pipeline.py [step ...]`. Steps: kieran, portraits, bodies, environment, ground, standins, workshop, upscale, maps.
- `tools/hd_pipeline.py` (run after sprite_pipeline): upscales sources 4x with `tools/esrgan_upscale.py` (needs PyTorch and the model file named in that script; upscales are cached in `tools/cache/`, not committed) and writes the game-size Kieran, NPC, Piko, prop, ground, windmill rotor, workshop and ambient effect textures. Steps: upscale, kieran, bodies, environment, ground, rotor, workshop, fx.
- Ambient motion: `level.gd` `make_prop_sprite()` gives windmills a turning rotor and trees and banners the `assets/shaders/sway.gdshader` material; Windrest adds drifting cloud layers (Parallax2D autoscroll), bobbing far islands and CPUParticles2D leaves.
- `tools/audio_synth.py`: regenerates all placeholder music and SFX (needs ffmpeg for OGG).

## Build

`export_presets.cfg` has a "Windows Desktop" preset that embeds the pack into `builds/windows/TheLastSkyfarer.exe`. Command: `godot --headless --export-release "Windows Desktop" builds/windows/TheLastSkyfarer.exe`.
