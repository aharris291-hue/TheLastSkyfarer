# Development Log

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
