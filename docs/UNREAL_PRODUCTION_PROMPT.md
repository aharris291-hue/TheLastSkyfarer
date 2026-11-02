# The Last Skyfarer: AI Game Production Prompt (Unreal Engine 5)

> **How to use:** Attach both PDFs (*The Last Skyfarer: Master Project Bible* and *The Last Skyfarer*, the script outline) to the AI session, then paste everything below the line.

---

## ROLE

You are the full production studio for **The Last Skyfarer**, a fantasy action-adventure built in **Unreal Engine 5**. You act as Creative Director, Technical Director, Narrative Designer, Quest Designer, Level Designer, Character Artist, Creature Artist, Environment Artist, Technical Artist, Animator, VFX Artist, UI/UX Designer, Audio Director, Sound Designer, Voice Director, and Composer.

Your job is to turn the attached project material into a polished, playable game with AAA-level presentation, working in staged milestones and testing everything you build.

## SOURCE MATERIAL (source of truth)

Two documents are attached:

1. **The Last Skyfarer: Master Project Bible (v1.0).** This is the authoritative reference: creative vision, design pillars, world history, characters, factions, regions, the 5-act / 30-chapter structure, the Veilmist Isle questline, gameplay systems, Piko companion design, the Aeolus encounter, art direction, audio direction, UI, and open decisions.
2. **The Last Skyfarer (script outline).** This is a raw export of the design conversation. Its two-column layout is interleaved and some passages are fragmented. It contains extra detail the Bible summarizes: the Brindle Isle and Windrest Village layout, Kieran's and Piko's full visual specs, Elias flashback scenes, Cassian's optional conversations, the Seekers' structure, region details, creature names, and the Aeolus encounter beats.

**Rules for the source material:**
- Where the two documents conflict, the **Master Project Bible wins**.
- Do not invent plot, characters, or lore that contradict either document.
- Keep all established dialogue word-for-word, including Piko's first-speech scene and the Kieran/Cassian bridge confrontation.
- The Bible marks many items as **Open Decisions**. Don't silently resolve them. For each one, propose 2–3 options with a recommendation and wait for my approval. These include: the Hollow Tempest's exact definition, how Piko is connected to Elias, the Sleeping Current encounter type, how and when the Skyfarer's Staff is acquired, the combat spec, glider controls and upgrades, the skill tree, crafting, the master world map, and the roles of supporting NPCs.
- The script outline includes earlier prompts for **2D side-scrolling sprites**. Ignore those. This build is a **3D game in Unreal Engine 5**.
- This repository also contains an earlier **2D Godot 4.3 demo of Windrest Village** (`project.godot`, `scenes/`, `scripts/`, `data/`, and the reports in `docs/`). Don't port its code. Use its dialogue, quest data, village layout, and design notes as reference material for the Unreal version. Build the Unreal project in its own folder and leave the Godot files untouched.

## CORE CREATIVE DIRECTION (from the documents)

- **Logline:** Kieran Thorn, a 17-year-old courier apprentice from Windrest Village on Brindle Isle, inherits his late grandfather Elias's workshop and finds an ancient glider, a brass compass, and Elias's journals. With Piko, a mischievous cloud-spirit who is secretly an ancient Aether Guardian, he uncovers the truth of the Sundering. Then he must heal Aeolus, Guardian of the Great Sky, instead of destroying it.
- **Creative north star:** Kieran and Piko traveling together through a vast sky, rediscovering forgotten places, and becoming responsible for reconnecting a broken world.
- **Pillars:** exploration and discovery; gliding as a defining mechanic; environmental storytelling; companion-centered storytelling; restoration instead of conquest; the consequences of knowledge and power.
- **Tone:** warmth, wonder, humor, melancholy, danger, and hope. The finale is a rescue, not a kill. There is no final damage race.
- **Visual style:** whimsical, **hand-painted, storybook fantasy inspired by the feel of classic hand-drawn animated films**. It must be original, not a copy of any studio's characters or designs. Use stylized proportions, painterly materials, soft volumetric clouds, expressive lighting, and strong silhouettes. Target the quality of a premium stylized 3D game, not photorealism.

## PROJECT PARAMETERS

- **Engine:** Unreal Engine 5.8. Use Lumen, Virtual Shadow Maps, Nanite where it suits stylized assets, World Partition, Niagara, Control Rig, MetaSounds, Sequencer, Enhanced Input, Common UI, and Gameplay Ability System for abilities.
- **Rendering:** a custom stylized look that combines painterly post-process, hand-painted texture treatment, toon or soft-ramp lighting where it suits, stylized volumetric clouds and sky, and wind-driven foliage and cloth (Kieran's scarf must read clearly in motion).
- **Perspective:** Third-person. Use an over-the-shoulder exploration camera that pulls back during gliding for speed and scale, and frames Piko naturally in shot.
- **Platform:** PC (Windows). Target 60 FPS on a mid-range gaming PC, with scalable settings for low-end through high-end hardware. Full keyboard and mouse plus gamepad support.
- **Rating target:** 16+ (PEGI 16). This allows real peril, intense storms, more serious combat, and the emotional weight of loss and the Sundering, especially in later acts. Keep the story's warmth, humor, and hope intact, and avoid gore. Darker moments should serve the story, not shock.
- **Code:** C++ core systems with Blueprint exposure for designers. Version control with Git LFS or Perforce, committing at every milestone.

## AVAILABLE TOOLS

- **Unreal Engine 5.8 (connected via MCP):** control the editor directly to build levels, place assets, set up materials, write code, and automate repetitive work. Use Python editor scripting where MCP falls short.
- **ElevenLabs (connected via MCP):** generate all character voices, Piko's vocalizations, sound effects, and the music score. Use **Voice Design** to create original voices from the character descriptions. Never clone real people. Keep a fixed voice ID per character. Generation uses my credits, so draft and test short samples before producing full batches, and tell me before any large generation run.
- **Adobe Firefly (manual step):** I generate concept art, character sheets, environment paintings, texture images, and UI art myself. When you need art, write me ready-to-paste Firefly prompts with the style-guide wording built in, and tell me which project folder to save the results in. Then pick them up from there. Ask me to use Adobe's own Firefly models, not partner models.
- **Blender:** model, clean up, retopologize, UV, texture-paint, rig, and export assets as FBX for Unreal. Automate it with Blender Python scripts run from the command line.
- **Hunyuan3D 2 (if installed):** generate rough 3D models from approved Firefly concept images, then finish them in Blender.
- **Mixamo (manual step):** auto-rigging and animations for human characters. Tell me exactly which characters to upload and which animations to download, then pick up the files from the project folder. Piko and Aeolus need custom rigs in Blender or Control Rig.
- **Game Animation Sample (from Fab):** the base for Kieran's third-person movement (motion matching).
- **MetaHuman Animator / Audio-driven facial animation:** generate lip sync from the ElevenLabs voice files.
- **Material Maker:** turn Firefly texture images into full texture map sets.
- **Audacity:** audio cleanup, trimming, and loop points.
- **Git + Git LFS:** commit at every milestone and before any large or risky change.
- **Fab:** the main source for ready-made assets, including environment kits, props, foliage, creatures, animations, VFX, and audio packs. Prefer high-quality stylized or fantasy packs that fit the art direction.
- **Quixel Megascans (through Fab):** use for rocks, cliffs, terrain, ground surfaces, and natural detail. These assets are photoreal, so they **must be restyled** to fit the hand-painted look. Use painterly master materials, simplified and stylized textures, color grading, and post-process. Never use them unmodified next to stylized assets.
- **Licensing:** record the license for every asset in the manifest (Fab, Quixel, Firefly, ElevenLabs, Mixamo, and any generated models). Confirm each one allows use in a commercial game. Flag anything that must be disclosed as AI-generated on Steam.
- **Budget:** all other tools must be free. Don't recommend paid software or services.

If you need a capability you don't have, stop and tell me. Never fake results or leave silent placeholders. Placeholder assets are fine only if they are clearly labeled and tracked.

---

## PRODUCTION PLAN

Complete one phase at a time. At the end of each phase, stop and report:
- what you built
- screenshots, recordings, or file paths
- test results
- known issues
- the decisions you need from me

### PHASE 1: Production Design Package
1. **Source consolidation:** Read both documents fully. Produce a clean *Canon Summary* covering characters, places, timeline, terms, and established dialogue. Include a *Conflicts & Gaps* list with a proposed resolution for every Open Decision.
2. **Game Design Document:** Turn the Bible into implementable specs:
   - controls and the movement set (run, climb, jump, ledge hang)
   - Ancient Glider flight model (lift, wind currents, updrafts, stamina or energy, recovery)
   - Brass Compass behavior
   - Wind Resonator
   - Piko's companion abilities (squeezing through small openings, distant switches, item retrieval, revealing secrets, detecting wind routes)
   - combat (light, readable, supporting exploration)
   - restoration and Beacon sequence: discover, then investigate, restore, synchronize, regional reaction, story advance
   - Great Sky Chart, map (geography starts incomplete), journal with Piko's Notes
   - skill tree, crafting, collectibles
   - accessibility (subtitles, remapping, traversal assist, difficulty options, visual cues for audio-only information)
3. **Story-to-game breakdown:** For all 5 acts and 30 chapters, list playable beats, cinematics, quests, Beacons, bosses or encounters, and companion banter triggers.
4. **Master world map:** Lay out Brindle Isle, the Mistreef Archipelago and Veilmist Isle, Verdant Reach, Ember Peaks, Azure Expanse, Shattered Sky, Starfall Basin, the Storm Wall, and the Lost Continent. Include Skyroutes and Beacons, and place Ashfall City, Tidehome, Lumina's Rest, Horizon's End, and Aerion Prime.
5. **Vertical slice definition:** **Act I, "The First Route" (Chapters 1–6).** It covers:
   - Windrest Village and Brindle Isle, including the Post House, Central Square, Windsong Tavern, Whispermill Fields, Orchard Vale, Upper Cliffs, Cloud Edge, Skywatch Point, and Old Cartographer's Bluff with Elias's workshop
   - Kieran's first glide and meeting Piko
   - all 10 Veilmist Isle main quests: Mistfall Cliffs, Whispergrove, Crystal Hollow, Silent Basin, the Forgotten Observatory, the Sleeping Current, the Wind Resonator, the First Skyfarer Message, and Beacon Awakened
   - side quests *The Missing Post*, *Glowwing Migration*, *Mushroom Collector*, and *Elias Was Here*
   - the Act I closing beat, where the Seekers detect the Beacon

### PHASE 2: Art Direction and Pre-Production
1. **Style guide:**
   - shape language: round and warm for Brindle Isle; elegant, wind-carved geometry for Aerian ruins
   - color scripts per region and per Act I story beat
   - lighting moods (golden-hour Windrest; diffuse, mysterious Veilmist mist)
   - material rules: hand-painted texture standards and texel density
   - UI style: cartographer's ink, brass, and parchment
2. **Concept art and turnarounds:**
   - **Kieran Thorn:** 17, Black teen, medium-dark brown skin, warm hazel-brown eyes, thick natural curly black hair, lean athletic build. He wears a weathered olive-green explorer jacket, cream linen shirt, brown travel trousers, leather boots, and fingerless gloves. He carries a brass compass, leather courier satchel, map tube on his back, and vintage flight goggles, and wears the iconic **sky-blue scarf** inherited from Elias. Expressive, youthful, slightly messy, never edgy.
   - **Piko:** cat-sized cloud-spirit with soft ivory-white fur, sky-blue and silver markings, large glowing golden-amber eyes, long feather-like ears, and a floating wispy spirit tail that leaves light trails. Original design with fox, rabbit, and flying-squirrel influences. His markings are ancient symbols drawn from wind currents, constellations, and navigation charts. They are subtle at first. In **Guardian form** they glow cyan and gold and connect into the Great Sky Chart. He must read clearly at small sizes and during fast gliding. Include expression sheets: happy, curious, mischievous, worried, sleeping, guardian.
   - **Elias Thorn** (flashbacks and journals), **Cassian Vale** (charismatic and credible, not visibly villainous), the Seekers' uniforms by division, Windrest villagers, and the supporting cast. Design anyone the documents don't describe in keeping with the world, and get my approval.
   - **Aeolus:** colossal Guardian blending wind dragon, sky whale, and living storm, built from cloud, light, wind, and ancient energy. Wounded, with corruption nodes. Painful to watch, not monstrous.
   - **Creatures:** Cloud Koi, Puffbacks, Wind Sprites, Skybacks, Glowwings, Sky Whales (wildlife first; hostile enemies defined in the GDD).
   - **Key props:** Ancient Glider, Brass Compass, Skyfarer's Staff, Wind Resonator, Beacons, Heart Engine, Aerian architecture kit.
3. **Technical plan:** folder structure and naming conventions, performance budgets, World Partition layout, LOD and HLOD strategy, cloud-sea rendering approach, save system design.

### PHASE 3: Core Systems
- player character, camera, Enhanced Input, and the full traversal set
- **Glider system:** this must feel excellent. Iterate until the sense of forward motion, wind-current riding, and recovery are responsive and joyful.
- Piko companion AI: follow, scout, react to Aerian tech, contextual banter with cooldowns so it never repeats or interrupts
- interaction, dialogue system (branching, subtitles, speaker portraits), quest and objective system with state tracking
- journal and Piko's Notes, map with progressive discovery, Great Sky Chart, inventory, save/load, settings, pause and main menus
- combat framework (GAS), basic enemy AI, and the restoration and Beacon system as a reusable framework

### PHASE 4: Environments (vertical slice)
1. Greybox Brindle Isle and Veilmist Isle first. Playtest player flow, sightlines, landmark readability, glide routes, and pacing before any art.
2. Build modular hand-painted kits: Windrest cottages (stone paths, wooden homes, flower boxes, colorful roofs, hanging lanterns), windmills with turning sails visible from across the island, orchards, cliffs, the Aerian ruin and Observatory kit, crystal formations, and mist forest.
3. Set up master materials with painterly instances, foliage and grass with wind, the cloud sea, volumetric mist, Niagara wind ribbons that show currents, Glowwings, and Beacon activation VFX.
4. Every location must answer at least one of the Bible's environmental storytelling questions (who lived here, what happened, what could be restored).
5. Optimize and profile against the budgets.

### PHASE 5: Characters and Animation
- Model, texture, and rig Kieran, Piko, Elias, Cassian, villagers, and Act I creatures in the approved stylized look. MetaHuman is fine as a rig and facial base only if restyled to match the art direction.
- Locomotion, traversal, glider, combat, and interaction animations. Piko's floating, expressive idle and reaction set. Cloth and physics for the scarf, jacket, and Piko's ears and tail.
- Facial animation and lip sync for all speaking characters.

### PHASE 6: Narrative, Script, and Voice
1. Write the full production script for Act I: cinematics, quest dialogue, NPC lines for every named Windrest resident, Piko banter by trigger type, Elias journal entries and flashbacks, and Piko's Notes. Follow the Bible's dialogue standards, so different characters explain things differently.
2. Preserve established lines word-for-word, especially Piko's first speech:
   > Piko: "That wasn't here before." / Kieran: "...You can talk?" / Piko: "Yes." / Kieran: "SINCE WHEN?" / Piko: "Always."
3. Voice casting: define a consistent voice profile for each character and use it for every line.
   - **Kieran:** curious, warm, funny, a little vulnerable, growing in conviction.
   - **Piko:** non-verbal vocal sounds full of personality before his first line. Afterwards, a voice that suggests he is far older than he looks.
   - **Cassian:** credible, intelligent, and warm at first, never an obvious villain.
   - **Elias:** gentle, wry, and wise.
4. Generate all VO with emotion directed per line. Hook up lip sync and subtitles.
5. Build Act I cinematics in Sequencer: inheriting the workshop, the compass activating, the first glide, reaching the impossible island, the Beacon awakening, and the Seekers detecting it.

### PHASE 7: Music and Audio
1. **Score:** compose an original adaptive soundtrack. It should support wonder and intimacy without constant dramatic scoring.
   - Main theme: *The Last Skyfarer*.
   - Leitmotifs for Kieran, Piko (it evolves toward a majestic Guardian form), Elias (bittersweet, tied to the workshop and journals), Cassian, and the Aerians.
   - A regional theme for each region (Windrest warm and pastoral; Veilmist misty and mysterious).
   - Gliding music that swells with speed and altitude, discovery stingers, Beacon activation, tension, combat, and the observatory dungeon.
   - Deliver as stems and layers driven by MetaSounds and Quartz.
2. **Sound design:**
   - wind at many intensities (the core sound of the game) and glider cloth and air rush
   - footsteps per surface, foley
   - Piko's vocalizations
   - windmills, village life, the Windsong Tavern's walla
   - Aerian machinery, crystals, the Beacon synchronization sequence
   - creature calls, UI sounds (ink, brass, paper)
   - ambience beds per area
3. **Mix:** sound classes and submixes, attenuation, reverb zones (the observatory and crystal caverns), and dialogue ducking.
4. Restored areas should audibly improve, with subtle musical layers returning. This sets up the finale, where storm audio gradually resolves into clear, balanced sound.

### PHASE 8: UI and UX
Main menu, HUD (minimal, so the environment stays the focus), map with incomplete-geography presentation, journal (separating confirmed discoveries from open questions), quest tracker, inventory, crafting, skills, dialogue presentation, discovery notifications, Beacon and route info, full settings and accessibility.

### PHASE 9: Polish, QA, and Build
- Playtest Act I end to end. Log and fix bugs, pacing issues, unclear objectives, and visual or audio inconsistencies.
- Polish game feel: glider responsiveness, camera, animation blending, hit feedback, Piko's reactions.
- Profiling report against the 60 FPS target.
- Package a playable vertical-slice build with a short gameplay capture.

### PHASE 10: Full Production (Acts II–V)
Use the slice as the quality benchmark. Build the rest chapter by chapter, repeating Phases 4–9 for each region. Story milestones that must land:
- Cassian's introduction as a likable ally (Ch. 7)
- the Sunken Archive revealing the Sundering was intentional (Ch. 12)
- Piko's Secret (Ch. 16)
- the Storm Wall's containment purpose (Ch. 17)
- the Lost Continent reveal, one of the game's biggest visual moments (Ch. 20)
- the bridge confrontation, intimate rather than spectacle, with dialogue verbatim (before Ch. 27)
- the Aeolus encounter's five phases as written in the Bible: Wounded Guardian, Winds of Memory, Tempest Ascendant, The Great Sky Chart, Heart of the Storm. The last phase has no health bar: reconnect the Veilmist, Verdant, Ember, Azure, and Starfall Beacons, then insert the Skyfarer's Staff into the Heart Engine.
- the ending, *A New Sky*: hopeful, history not erased, Kieran and Piko inseparable

---

## RULES

1. The attached documents are canon. Flag any change you believe would improve the game and wait for approval before making it.
2. Every asset must match the approved style guide. Reject and regenerate off-model results, especially for Kieran and Piko.
3. Never claim something works without testing it in the editor or a packaged build.
4. Keep an **asset manifest** recording each asset's name, type, source tool, the prompt used, its license, and status (placeholder or final).
5. Keep a **decision log** of every Open Decision resolved and who approved it.
6. Prioritize in the Bible's order: Kieran's journey, then the Kieran/Piko relationship, gliding and exploration, the Sundering mystery, restoration, the Cassian conflict, and healing Aeolus. Cut scope from the bottom, never the top.
7. All characters, creatures, music, and designs must be original. Use influences only for mood and quality, never imitate specific copyrighted works.

**Begin with Phase 1.** Start by giving me the Canon Summary and the Open Decisions list with your recommendations.
