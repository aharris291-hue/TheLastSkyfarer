# Save System Specification

## Location

`user://saves/` which on Windows is `%APPDATA%\Godot\app_userdata\The Last Skyfarer\saves\`. Files: `slot1.json`, `slot2.json`, `slot3.json`, `auto.json`, each possibly with a `.bak`.

## When the game saves

- Manually from the pause menu into slots 1 to 3.
- Autosave at story beats (`autosave` action in quest and dialogue data) and on scene change.
- Settings are separate, in `user://settings.cfg`.

## Format (version 1)

```json
{
  "version": 1,
  "flags": {"opening_done": true},
  "inventory": {"parcel_tessa": 1},
  "quests": {"morning_deliveries": {"state": "active", "objectives": {"report": 1}}},
  "tracked_quest": "morning_deliveries",
  "journal": ["note_wind"],
  "discovered": ["post_house"],
  "time_of_day": "day",
  "chapter": 1,
  "playtime": 512.4,
  "scene_path": "res://scenes/world/windrest.tscn",
  "player_position": [6000, 900],
  "meta": {"slot": "slot1", "saved_at": "...", "unix": 0, "chapter": 1, "location": "Windrest", "playtime": 512.4, "game_version": "0.1.0-demo"}
}
```

## Crash safety

1. Write the JSON to `<slot>.json.tmp`.
2. Read it back and confirm it parses and has `version` and `flags`.
3. Move the existing `<slot>.json` to `<slot>.json.bak`.
4. Rename the `.tmp` into place.

On load, if the main file is missing or does not parse, the `.bak` is used. A save from a newer version loads with a warning. Unknown keys are ignored, missing keys take defaults, so later versions can add fields without breaking old saves.

## Tested

`tests/test_runner.gd` covers round-trip save and load, all slots, the .bak fallback with a deliberately corrupted file, the slot list metadata and restoring position and scene.
