# The Last Skyfarer: Unity rebuild plan

Adam approved this on 2026-11-17 ("yes, switch to Unity" and rebuild the entire game from the ground up). It is logged as D-30.

## Ground rules

- **Engine:** Unity 6 (6000.6.9f1, already installed) with URP and C#.
- **Location:** project at `Unity/LastSkyfarer`, in a repo clone on D: (`D:\TheLastSkyfarer\repo`), because C: is nearly full.
- **Reference only:** the Godot files and the `Unreal/` folder. Never edit, move or delete them.
- **Sources of truth:** the Bible, CANON_SUMMARY, GDD, VERTICAL_SLICE and STYLE_GUIDE. All other rules from `docs/UNREAL_PRODUCTION_PROMPT.md` still apply, except the engine. That covers the Bible winning over the script, the approval rules, free tools only, the ElevenLabs and Firefly rules, the manifest and decision log, and .zip builds.
- **Target PC:** Adam's UHD 630 with 12 GB of RAM. The Low preset must hold 30 fps.
- **Licences:** only our own work, CC0 assets, or assets whose licence allows Unity. Unreal-only content (the UE mannequin and its animations, starter content, and any UE-only Fab licences) is not copied over.

## Rebuilt from the ground up

| Step | What | Brought over from earlier work |
|---|---|---|
| U0 | Project setup: URP, Low quality level, git/LFS, text serialisation | none |
| U1 | Core systems in C#: third-person movement and camera, glider and wind volumes, climb/mantle, Input System (keyboard and gamepad), save/Continue, settings | GDD, TECH_PLAN, glider tuning notes |
| U2 | Story systems: dialogue, quests and flags, read from the existing narrative JSON. Automated tests (Unity Test Framework) and the story bot | narrative JSON, validators |
| U3 | Brindle Isle / Windrest greybox level, then the painterly URP materials, lighting, and day, sunset and night | Windrest kit and props (our own), D-27 art direction |
| U4 | Kieran: model, painted material, animations, horizontal glide pose | Kieran Blender build (our own) |
| U5 | Music and sound | the eight music pieces and the sound effects (our own) |
| U6 | UI: menus, dialogue box, compass, and parchment style when approved | UI layouts |
| U7 | Piko companion, Orchard Vale and the 4 quests, to reach Milestone A scope | VERTICAL_SLICE |
| A | **Milestone A build (.zip):** story bot passes, crash stress passes, 30 fps on Low. Needs Adam's approval | none |

After Milestone A comes Milestone B (the Act I vertical slice), then Acts II–V, each with Adam's approval.

## Open questions for Adam (asked when they come up)

- **Kieran's animations:** the Unreal ones came from Epic's mannequin and can't be used in Unity. The options are animations made in Blender (free, no download), or Unity's free Starter Assets animations (a download, which needs his typed approval).
