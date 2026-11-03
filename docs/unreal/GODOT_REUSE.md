# What the Unreal build reuses from the Godot demo

The Godot 4.3 demo stays in the repo unchanged as reference. Its code, scenes and 2D sprites are not ported.

| Reuse | Source in the Godot demo | How it carries over |
|---|---|---|
| Dialogue (35 conversations, branching choices, `canon` flags) | `data/dialogue/windrest.json`, `workshop.json`, `sky.json` | Imported into Unreal dialogue DataTables by a script; wording kept, and lines tagged canon stay word-for-word. Piko's lines stay vocalisations (D-12) |
| Quests: Morning Deliveries, The Hidden Workshop, Elias Was Here, Into the Clouds | `data/quests.json` | Same objectives and gating, rebuilt in the C++ quest system. Into the Clouds becomes Veilmist Q1 *The Impossible Route* (D-16) |
| Journal entries, items, speakers | `data/journal.json`, `items.json`, `speakers.json` | Seed data for journal, inventory and portraits |
| Windrest layout and named locations | `data/locations.json`, level layout, the Windrest map art | Greybox reference for the 3D island: relative positions of the Post House, Square, Tavern, Skywatch, Cloud Edge and the Bluff |
| Piko behaviours | Piko follow, emotes, sensing hidden currents | Behaviour spec for the 3D companion AI: spring follow, glowing markings near secrets, chirp reactions, revealing a hidden updraft |
| Lessons learned | `docs/DEVELOPMENT_LOG.md`, `AUDIT_REPORT.md`, `GAME_DESIGN_GUIDELINES.md` | Placeholders must look like placeholders; never redraw established characters; conflicts go to Adam; the first challenge teaches reading the wind; respawn at the last safe point with no other penalty; UI readable from a sofa with every action showing its button |
| Not reused | GDScript, `.tscn` scenes, 2D sprites, synthesised placeholder audio, the 2D movement numbers | Rebuilt in 3D; voice, music and sound come from ElevenLabs |
