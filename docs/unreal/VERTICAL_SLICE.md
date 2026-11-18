# Vertical Slice and Milestone A Definition (Phase 1 draft)

Two playable milestones, each approved by Adam before the next starts.

## Milestone A: Windrest 3D Demo (Chapters 1 to 3)

Same story scope as the Godot demo, rebuilt in 3D.

**Places (Brindle Isle):** Windrest Village (Central Square with fountain, bulletin board and market; Post House; Windsong Tavern; village homes), Whispermill Fields (windmills visible across the island), Orchard Vale (new: apples, pears, skyberries), Upper Cliffs, Skywatch Point, Cloud Edge, and Old Cartographer's Bluff with Elias's workshop and the observation tower. The layout follows Adam's Windrest Village map: the Bluff on the east edge, Skywatch to the north, Whispermill to the north-west, Orchard Vale to the west.

**Story beats:**
1. Sunrise on the Upper Cliffs: "There has to be more out there than this."
2. Morning Deliveries: Post House, Windsong Tavern, Skywatch Point, Cloud Edge.
3. Letter of Inheritance at sunset.
4. The Hidden Workshop: search, the compartment, the glider, the final journal entry, the compass awakens.
5. Into the Clouds: dawn at the Bluff, Piko sitting on the glider, the first glide along the impossible current, Piko revealing a hidden updraft, the island in the fog. The demo ends on that view.

**Quests:** Morning Deliveries, The Hidden Workshop, Elias Was Here (part 1: Elias's notes around Brindle), Into the Clouds.

**Systems:** third-person movement (run, climb, jump, ledge hang, mantle), the glider (D-6), the compass pulse, Piko follow and current sensing, dialogue with voice and subtitles, quests and journal (including Piko's Notes as written by Kieran), the incomplete map, saving, settings and accessibility basics, story-driven morning, sunset and night (D-21).

**Characters on screen:** Kieran, Piko, Maren Holt, Tessa Reed, Rowan Finch, Bram Holloway (tavern keeper), Elara Greenborough (Orchard Vale), villagers, and Elias in his portrait and journals.

**Audio:** ElevenLabs voices for Kieran, Maren, Tessa, Rowan, Bram, Elara and villagers, designed with Voice Design and tested on short samples before any batch. Piko's chirps and trills, wind, the windmills, village life, the Windrest theme and a first gliding cue.

**Not in Milestone A:** the Staff and combat (D-4), Veilmist gameplay, crafting and perks (the bench is visible but closed).

**Done means:** playable from New Game to the end view with no blockers. Automated checks pass for every dialogue line, quest step and trigger. A 60 FPS target on a mid-range PC at High. A packaged Windows build delivered as a .zip, with screenshots and a short gameplay capture.

## Milestone B: Act I vertical slice (Chapters 1 to 6)

Everything in Milestone A, polished to the slice quality bar, plus:

**Veilmist Isle:** Mistfall Cliffs, Whispergrove, Crystal Hollow, Silent Basin, the Forgotten Observatory, Elias's hidden camp and the Beacon.

**Main quests (Bible's 10, D-16):**
| # | Quest | Content |
|---|---|---|
| 1 | The Impossible Route | Ch. 3 glide and arrival (Milestone A's Into the Clouds) |
| 2 | Mistfall Cliffs | Traversal; three Aerian markers open the way into Whispergrove |
| 3 | Whispergrove | Giant mushroom forest, secret tunnels, first combat (Mist Sprites), key fragment 1/3; Elias's camp and the Staff |
| 4 | Crystal Hollow | Dungeon with crystal reflection puzzles and moving platforms, fragment 2/3 |
| 5 | Silent Basin | Dead air; Piko finds the hidden passage before it appears, fragment 3/3 |
| 6 | The Forgotten Observatory | Restore Wind Engines Alpha, Beta and Gamma |
| 7 | The Sleeping Current | Three-beat restoration encounter (D-3) |
| 8 | The Wind Resonator | Repair it and carry its core (D-17) |
| 9 | The First Skyfarer Message | "To those who find this place... the routes are failing."; the route through the Storm Wall |
| 10 | Beacon Awakened | The Beacon sequence; the Great Sky Chart unlocks |

**Side quests:** The Missing Post (lost courier parcels, satchel upgrade), Glowwing Migration (guide the swarm home, a rare crafting material), Mushroom Collector (catalogue fungi for a researcher on Brindle Isle, expanded codex), Elias Was Here part 2 (his camp, Flashback I, new journal pages).

**Closing beat:** the Beacon's light, Piko staring as if remembering, and far away Cassian: "Interesting. Someone found it before we did." Fade to black.

**Added systems:** Staff combat (D-5), the Wind Resonator, the restoration and Beacon framework, the Great Sky Chart, light crafting (D-8), the perk tree (about 6 points in the slice, D-7), the bestiary and relics.

**Done means:** Act I playable end to end, a profiling report against 60 FPS, the asset manifest with licences and AI-disclosure flags complete, and a packaged build with a gameplay capture.
