# Master Project Bible v1.0: Sections 26 to 32 (reconstructed)

**Provenance.** The Bible PDF on file stops mid-sentence in section 26. On 2026-11-02 Adam said there is no fuller copy and asked for these sections to be created from the existing material. They are reconstructed from Bible sections 1 to 25, the script outline (`docs/source/The Last Skyfarer.pdf`), the production brief and the approved decisions in [DECISION_LOG.md](DECISION_LOG.md). **They add no new lore.** Section headings follow the Bible's table of contents. The only text kept from the original section 26 is its first two paragraphs.

---

## 26. Narrative and Dialogue Standards

### 26.1 Dialogue Principles

Dialogue should be character-driven, emotionally clear, and consistent with the tone of the world.

Characters should not all explain the same information in the same way.

*(The original text breaks off here. The rest of this section is reconstructed.)*

A villager, a Seeker scholar, and Piko should describe the same discovery in three different ways: through rumor and weather, through evidence and theory, and through memory.

### 26.2 Character Voices

| Character | How they speak |
|---|---|
| Kieran | Curious, warm, quick humor, a little vulnerable. Asks questions. Grows steadier and more certain as the story progresses. |
| Piko | Non-verbal (chirps, trills, whistles, ear and tail language) until Chapter 16. Afterward: few words, dry, and older than he looks. Hints rather than explains ("Not everything."). |
| Elias | Gentle, wry, and wise. In journals, he records doubts as well as discoveries. |
| Cassian | Credible, intelligent, and warm at first. Speaks of choice and freedom. Never sounds like an obvious villain. His anger grows from conviction, not cruelty. |
| Maren Holt | Practical, stern but caring ("Don't tell me you've been staring at the horizon again."). |
| Tessa Reed | Clever, competitive, skeptical. Teases, then grudgingly respects ("I still think you're completely insane."). |
| Villagers | Everyday concerns: weather, work, rumors. Most adults treat the Skyfarers as fairy tales. |
| Aerian records | Formal, hopeful, and addressed to the future ("If you are standing here, then the future survived."). |

### 26.3 Established Lines

Established lines are kept word for word. They include Piko's first speech, the bridge confrontation, Elias's final journal entry, the First Skyfarer Message, Cassian's first appearance, and Aeolus's final words. The full list is in [CANON_SUMMARY.md](CANON_SUMMARY.md). In the dialogue data, these lines carry a `canon` flag and can't be edited without Adam's approval.

### 26.4 Exposition

- Show history through places and objects first. Use dialogue to react to discoveries rather than to explain them.
- No single character delivers the whole truth. Elias's story unfolds across journals and flashbacks.
- Piko never explains a mystery before the player has had the chance to discover it.
- The journal separates confirmed discoveries from open questions.

### 26.5 Tone

The world is warm, full of wonder, funny, melancholy, dangerous, and hopeful. Humor relieves tension but never undercuts grief. Darker moments, such as the Sundering's cost and the danger of the storm, serve the story and never aim to shock. The target rating is 16+, with no gore.

### 26.6 Script Formats

These formats come from the script outline.

- **Chapter document:** metadata (number, title, act, region, estimated playtime, main characters, story purpose), opening cinematic, gameplay segment, story scene, midpoint discovery, climactic sequence, chapter resolution.
- **Cutscene:** scene ID, location, characters present, camera, audio, dialogue, gameplay transition.
- **Dialogue:** the CHARACTER name in capitals, then the line. Stage directions go in italics or parentheses.
- **Gameplay trigger:** trigger, action, objective.

### 26.7 Companion Banter

Banter follows the triggers listed in section 20.3. It has cooldowns, never repeats, and never interrupts important dialogue.

## 27. Technical and Production Planning

- **Engine:** Unreal Engine 5.8 (project `Unreal/LastSkyfarer.uproject`). Core systems are written in C++ and exposed to Blueprint.
- **Rendering:** Lumen, Virtual Shadow Maps, and Nanite where it suits stylized assets. Painterly post-process, soft-ramp lighting, and stylized volumetric clouds.
- **World:** World Partition for islands and the sky. The cloud sea is a dedicated rendering layer.
- **Systems:** Enhanced Input, the Gameplay Ability System (abilities and combat), Common UI, Niagara (wind ribbons, Beacons, Glowwings), Control Rig, Sequencer (cinematics), and MetaSounds with Quartz (adaptive music).
- **Data:** all dialogue, quests, journal entries, items, and Beacons live in DataTables or data assets. Automated checks confirm that every reference resolves.
- **Saves:** atomic writes, 3 slots, autosave, and backup recovery.
- **Platform:** Windows PC. Target 60 FPS on a mid-range gaming PC, with scalable settings. Keyboard, mouse, and gamepad.
- **Version control:** Git with Git LFS for binary assets. Commit at every milestone and before any risky change.
- **Process:** work in phases, as set out in the production brief. Each phase ends with a report and Adam's approval.

## 28. Content and Asset Requirements

The asset categories come from section 23.5, scoped to the technology and the vertical slice.

| Category | Act I needs |
|---|---|
| Characters | Kieran, Piko, Elias (flashbacks), Maren, Tessa, Rowan Finch, Bram Holloway, Elara Greenborough, villagers, and Cassian (teaser) |
| Creatures | Glowwings, Mist Hoppers, Cloud Drifters, Cloud Koi, Puffbacks, Wind Sprites, Skybacks, and Mist Sprites (corrupted) |
| Environments | A Windrest village kit, windmills, orchards, cliffs, Aerian ruin and observatory kit, crystal caves, mushroom forest, and the cloud sea |
| Key props | Ancient Glider, Brass Compass, Skyfarer's Staff, Wind Resonator, Veilmist Beacon, and Elias's workshop set |
| Animation | Locomotion and traversal, the glider, Staff combat, interactions, Piko's floating idle and reactions, and cloth for the scarf, jacket, ears, and tail |
| VFX | Wind ribbons, updrafts, Beacon activation, Piko's markings, Resonator reveals, and the Sleeping Current |
| Audio | Voices (ElevenLabs Voice Design, one fixed voice per character), Piko's vocalizations, wind, foley, ambience, and an adaptive score |
| UI | Cartographer's ink, brass, and parchment: menus, HUD, map, journal, Great Sky Chart, and dialogue |

Every asset is recorded in the asset manifest with its source, licence, commercial-use confirmation, and an AI-generated disclosure flag for Steam. Placeholders must be clearly labelled and tracked.

## 29. Development Roadmap

1. **Phase 1, production design:** Canon Summary, decisions, GDD, chapter breakdown, world map, and slice definition. Drafted 2026-11-02.
2. **Phase 2, art direction and pre-production:** style guide, colour scripts, concept art and turnarounds, and the technical plan.
3. **Phase 3, core systems:** movement, glider, Piko, dialogue, quests, journal, map, saves, and the combat and restoration frameworks.
4. **Phase 4, environments:** greybox Brindle Isle and Veilmist Isle, then the hand-painted kits.
5. **Phase 5, characters and animation.**
6. **Phase 6, narrative, script, and voice.**
7. **Phase 7, music and audio.**
8. **Phase 8, UI and UX.**
9. **Phase 9, polish, QA, and build.**
10. **Phase 10, full production of Acts II to V,** using the vertical slice as the quality bar.

**Milestone A** (the Windrest 3D demo, Chapters 1 to 3) comes out of Phases 3 to 9 at Brindle Isle scope. **Milestone B** is the Act I vertical slice (Chapters 1 to 6). See [VERTICAL_SLICE.md](VERTICAL_SLICE.md).

If scope must be cut, follow the order in section 3.3 and cut from the bottom, never the top.

## 30. Continuity Notes and Open Decisions

- **Resolved decisions:** see [DECISION_LOG.md](DECISION_LOG.md). As of 2026-11-02 these are D-1 to D-19 and D-21, all approved by Adam.
- **Proposals and conflicts:** see [OPEN_DECISIONS.md](OPEN_DECISIONS.md) and the Conflicts & Gaps list in [CANON_SUMMARY.md](CANON_SUMMARY.md).
- **Key continuity rules:**
  - Piko does not speak before Chapter 16.
  - Kieran gets the Staff in Chapter 4, at Elias's camp.
  - The Hollow Tempest is Aeolus in his wounded, contained state.
  - Veilmist lies east of Brindle Isle, and its route points through the Storm Wall to the Lost Continent.
  - The Bible wins over the script outline.
- **Still open:**
  - The roles of the unassigned characters in Adam's art: Joren Coal, Arlen Voss, Doran Flint, Selka Furnacewind, Varek Flintgear, Verena Hallow, and Raxis Thornvein.
  - The candidate bosses for Acts II to IV named only in the outline: Rootwarden, Forgekeeper Leviathan, Horizon Breaker, Celestial Keeper, and the Warden Network.
  - Where the bridge confrontation falls: the end of Chapter 24 or the start of Chapter 27.

## 31. Glossary

| Term | Meaning |
|---|---|
| Aerians | The ancient civilization responsible for the Skyroute Network and the deliberate Sundering. |
| Aether Guardians | Guardian spirits responsible for preserving routes and keeping the sky in balance. Piko is one of them. |
| Aeolus | The Guardian of the Great Sky. He maintains the weather, routes, and migrations. The Hollow Tempest is his wounded, contained state. |
| Ancient Glider | Elias's Aerian glider, found in the workshop. Kieran's means of flight. |
| Beacon | A regional infrastructure node tied to world restoration: Veilmist, Verdant, Ember, Azure, and Starfall. |
| Brass Compass | Elias's compass. It activates in the workshop and points to hidden routes. |
| Great Sky Chart | The global route and restoration system. Piko's markings form the complete chart. |
| Heart Engine | The central Aerian mechanism, reached in the finale and restored with the Skyfarer's Staff. |
| Hollow Tempest | Aeolus in his wounded state, held inside the containment system. Not a monster. |
| Seekers | An organization devoted to recovering lost knowledge. It is led by Cassian Vale, the Grand Seeker. |
| Skyfarer | An explorer and route keeper of the Aerian era. Kieran becomes the first recognized Skyfarer in generations. |
| Skyfarer's Staff | An ancient explorer's tool that Kieran finds at Elias's camp on Veilmist. |
| Skyroute | An ancient route connecting islands, part of the Skyroute Network. |
| Sleeping Current | A failing Aerian wind engine beneath the Forgotten Observatory on Veilmist. |
| Storm Wall | The massive atmospheric barrier around the known world. It is part of the containment system. |
| Sundering | The ancient, deliberate fragmentation of the world into floating islands. |
| Wind Resonator | An Aerian device. Its portable core detects hidden currents, reveals paths, and powers Aerian technology. |
| Guardian creed | "Observe. Guide. Preserve. Endure." |

## 32. Project Vision Statement

The Last Skyfarer is about an ordinary young courier who discovers that the world is larger, older, and more connected than anyone believes. It is a story about reconnecting a broken world.

Kieran and Piko travel together across a vast sky. They find forgotten places, read the wind, and restore what was lost. The adventure grows from a village mystery into a world-spanning conflict, but it never loses the friendship at its centre.

The game ends in healing, not conquest. Restoring the world doesn't erase its history. It creates the conditions for a different future, where a new generation of Skyfarers can keep the world's people connected.
