# Project Status

Version: 0.1.0-demo. Engine: Godot 4.3 (GDScript, Compatibility renderer). Target: Windows PC, 1920x1080.

## Demo: Windrest Village (awaiting Adam's approval)

| Area | State | Verified by |
|---|---|---|
| Title, new game, continue, load, settings, quit | Done | Test bot, screenshots |
| Kieran movement (walk, run, jump, coyote time, buffer, glide) | Done | Geometry and playthrough tests |
| Piko companion (follow, emotes, senses hidden currents) | Done | Playthrough test |
| Windrest level, 4 named locations, day to sunset to night | Done | Screenshots |
| Elias's workshop (Chapter 2 room) | Done | Playthrough test |
| Quests: Morning Deliveries, The Hidden Workshop, Elias Was Here (5 notes), Into the Clouds | Done | Quest tests |
| Dialogue: 35 conversations, branching choices, portraits | Done | Data integrity tests |
| Challenge: glide route over the edge using a hidden updraft only Piko reveals | Done | Playthrough test |
| Journal (quests, notes, items, map with markers) | Done | Screenshots |
| Saving: 3 slots plus autosave, crash-safe, .bak recovery | Done | Save tests incl. corrupt file |
| Music (3 themes), ambience, 19 sound effects | Done (procedural placeholders) | Heard only in code paths; no human listening test |
| Remappable keyboard and controller controls | Done | Remap tests; controller not tested on hardware |
| Windows export | Built (95 MB exe, pack embedded) | Not run on Windows |

Automated suite: **346 passed, 0 failed** (`tests/test_runner.tscn`), including a bot that plays the whole demo from New Game to the end card.

## Visual fixes (after first playtest)

High-definition sprites, opaque Kieran with unclipped jump frames, grounded props without white gaps, ambient motion and crisp NPCs. Details in DEVELOPMENT_LOG.md. The art is still upscaled from small source sheets: it is much sharper but cannot add detail the sheets never had, and Kieran's walk and run cycles keep the source's 6 frames.

## Placeholder or missing

- Maren Holt art, glider art, Kieran glide frames with a glider.
- Bram and Elara used as stand-in tavern keeper and flower grower.
- Music and sound are synthesised placeholders, not composed tracks.
- No combat.
- Not profiled on real Windows hardware.

## Next (after approval)

See FUTURE_FEATURES.md.
