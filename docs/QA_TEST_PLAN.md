# QA Test Plan

## Automated (run before every commit)

`godot --headless --path . res://tests/test_runner.tscn`. Current result: **331 passed, 0 failed.**

| Suite | Checks |
|---|---|
| Data integrity | Every dialogue, quest, item, journal, location and speaker reference resolves; conditions and actions parse |
| Save system | Round trip, slots, autosave, corrupt main file falls back to .bak, newer-version warning |
| Quests | Start, objective counts, hidden objectives appear on time, completion and rewards |
| Input remap | Remap, persistence, reset |
| Geometry | Every required jump is within Kieran's jump height; glide route reachable |
| Playthrough bot | Plays from New Game to the demo end card through every main beat |

Screenshots: `xvfb-run godot --path . --resolution 1920x1080 res://tests/shot_runner.tscn -- --out=/tmp/shots` produces 14 reference shots.

## Manual (needs a person on Windows)

- [ ] Launch the exe on Windows 10 and 11; window, fullscreen toggle, quit.
- [ ] Play the demo start to finish with keyboard.
- [ ] Play with an Xbox controller; check prompts switch.
- [ ] Listen to all music and sound at default volume for balance.
- [ ] Save, quit, reload each slot; continue from the title screen.
- [ ] Try alt-tab, window resize, 1366x768 and 2560x1440 displays.
- [ ] Read every line of dialogue for typos and tone.

## Known not tested

The exe has never run on Windows. Controller tested only through the input map, not with real hardware. Audio not listened to by a person.
