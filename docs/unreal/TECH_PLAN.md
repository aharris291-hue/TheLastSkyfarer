# Technical Plan (Phase 2 draft)

Status: draft for review, 2026-11-02. Project: `Unreal/LastSkyfarer.uproject` (UE 5.8.4, C++).

## 1. Folder structure

```
Unreal/
  Source/LastSkyfarer/        C++ runtime module
    Core/                     game instance, save system, settings
    Player/                   character, camera, traversal, glider
    Companion/                Piko AI, banter
    Narrative/                dialogue, quests, journal, flags
    World/                    restoration and Beacon framework, wind volumes, time of day
    Combat/                   GAS abilities, attributes, enemies
    UI/                       Common UI widgets (C++ bases)
  Content/LastSkyfarer/
    Characters/<Name>/        meshes, materials, animations
    Creatures/<Name>/
    Environments/<Region>/    kits, materials, foliage
    Props/
    VFX/
    Audio/{VO,Music,SFX,Ambience}/
    UI/
    Data/{Dialogue,Quests,Journal,Items,Beacons}/
    Maps/{Brindle,Veilmist,Sky}/
    Materials/Masters/
    Cinematics/
  SourceArt/                  not imported: Firefly images, Blender files, FBX exports
```

Imported marketplace packs stay in their own `Content/<PackName>/` folder until assets are migrated and restyled. Only the assets we actually use get committed (see section 7).

## 2. Naming

`<Prefix>_<Name>_<Variant>`: SM_ static mesh, SK_ skeletal mesh, M_ material, MI_ material instance, T_ texture (with suffix _D, _N, _ORM, _M), BP_ Blueprint, ABP_ animation Blueprint, AM_ montage, NS_ Niagara system, MS_ MetaSound, DT_ DataTable, DA_ data asset, WBP_ widget, L_ level. Dialogue line IDs follow the Godot demo's keys (for example `windrest.maren_intro.03`), so imported data maps one to one.

## 3. Performance budgets (60 FPS on a mid-range PC, High preset)

Reference hardware: RTX 3060 or equivalent, 6-core CPU, 16 GB RAM, 1080p.
| Budget | Target |
|---|---|
| Frame time | 16.6 ms (GPU 14 ms, game thread 10 ms) |
| Draw calls in view | 2,500 or fewer |
| Characters on screen | Kieran, Piko and up to 12 NPCs in the village |
| Texture memory | 3 GB or less streaming pool |
| Lumen | Software ray tracing at High; Medium and Low fall back to lower quality |
| Volumetric clouds | 1.5 ms or less |
| Niagara | 1.0 ms or less in the busiest scene |

Low, Medium, High and Epic scalability presets. Profiled with Unreal Insights at the end of each environment phase.

## 4. World Partition

- One world for the sky, with Brindle Isle and Veilmist Isle as separate island regions, so the glide between them is seamless.
- Grid cells of 128 m with a loading range of 512 m for terrain and props. Large landmarks (windmills, the Observatory, the Beacon) are set to always load as distant HLODs, so they read from anywhere, as the Bible asks.
- Data layers for story states (Beacon off and on, night, the workshop before and after).

## 5. LOD and HLOD

- Nanite for rocks, cliffs and Aerian architecture (rigid meshes). Traditional LODs for foliage with wind and for skeletal meshes.
- HLOD layer 1 per island at 600 m and beyond. Distant islands are painted impostor cards.

## 6. Cloud sea

- Layer 1: a stylized volumetric cloud layer below the islands (soft painted noise, moves slowly).
- Layer 2: a large animated cloud-top mesh with a painterly material for distance.
- Layer 3: billboard cloud puffs near the islands for parallax.
- Falling into the cloud sea triggers recovery (GDD 2.5).

## 7. Asset intake and storage

- Fab and Megascans packs are downloaded to a local cache outside the repo. Only the assets used are migrated into `Content/LastSkyfarer/`, restyled and committed.
- Git LFS stores binary assets. GitHub Free includes about 10 GB of LFS storage and 10 GB of bandwidth a month. Expected use is about 2 to 4 GB for Milestone A and 8 to 15 GB for the slice. We will warn Adam before reaching 8 GB, and recommend setting the GitHub LFS budget to $0 so nothing is charged by surprise.
- `docs/unreal/ASSET_MANIFEST.md` records every asset: source, licence, commercial use confirmed, AI-generated flag for Steam, and status (placeholder or final).

## 8. Save system

UE `USaveGame` subclass serialized to a temp file, then swapped into place, with a `.bak` copy kept. 3 slots plus an autosave. The data saved is listed in GDD section 12. Versioned with a schema number for migrations.

## 9. Tests

- Automation tests (Unreal's automation framework) for data integrity: every dialogue line, quest step, trigger, journal key and voice file resolves.
- Functional tests for the glider (no net energy gain), saves (corrupt-file recovery), and quest flow (a bot plays Milestone A from New Game to the end view, as in the Godot demo).
- Run from the command line on Adam's PC before every milestone build.
