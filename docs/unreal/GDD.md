# The Last Skyfarer: Game Design Document (Phase 1)

Status: draft for Adam's review, 2026-11-02. It implements the Bible and the approved decisions in [DECISION_LOG.md](DECISION_LOG.md); IDs such as D-6 refer to that log. All numbers are starting values to tune in Phase 3, not locked.

Engine conventions: C++ core systems in a `LastSkyfarer` runtime module, exposed to Blueprint. Enhanced Input for controls, Gameplay Ability System (GAS) for abilities and combat, Common UI for menus, MetaSounds for audio, data assets and DataTables for all content (dialogue, quests, journal, items), so writers never touch code.

---

## 1. Controls and movement

| Action | Keyboard and mouse | Gamepad |
|---|---|---|
| Move | WASD | Left stick |
| Camera | Mouse | Right stick |
| Walk / run toggle (run is default) | Ctrl | Left stick press |
| Sprint (short, no stamina) | Shift | Left stick press while running |
| Jump / climb up / deploy glider in air | Space | A |
| Interact / talk / pick up | E | X |
| Piko command (context) | Q | Y |
| Compass pulse | F | D-pad up |
| Staff attack (from Ch. 4) | Left mouse | RB |
| Staff heavy / hold | Right mouse | RT |
| Dodge | Alt | B |
| Lock-on | Middle mouse | Right stick press |
| Journal / map | J / M | View button, then tabs |
| Pause | Esc | Menu |

Every binding is remappable (Enhanced Input user settings), with a separate keyboard and gamepad profile.

**Movement set** (built on the Game Animation Sample's motion matching):
- Walk 1.8 m/s, run 4.5 m/s, sprint 6.5 m/s. Sprint has no meter; it ends after 4 s and needs 2 s before it can start again, which stops sprint-spamming without a bar on screen.
- Jump: 1.3 m high, with 0.12 s coyote time and a 0.15 s input buffer.
- Mantle and vault: automatic on obstacles 0.5 to 1.8 m high while moving forward.
- Climb: only on readable climbable surfaces (painted rock with handholds, vines, Aerian rungs), marked with a consistent pale-ochre wear. 1.2 m/s, no stamina. Jump while climbing hops 1.5 m in the stick direction.
- Ledge hang and shimmy: grab ledges automatically when falling past them. Drop with Ctrl/B.
- Slide: down steep slopes automatically; jump out at any time.
- Swim: shallow water only in Act I (no diving).
- Fall damage: none. Falling off an island into the cloud sea triggers recovery (section 2.5).

**Camera:** over-the-shoulder exploration camera at 3.2 m, offset right 0.45 m. It pulls back to 6 m and widens FOV from 80 to 95 degrees as glide speed rises. Piko is framed by a soft "keep in shot" weight. In dialogue it uses authored two-shot rigs.

## 2. Ancient Glider (D-6: energy model)

The glider is the heart of the game. It is deployed by pressing Jump in the air once the player owns it (Ch. 3).

### 2.1 Flight model
- State: airspeed (m/s) and altitude. No stamina bar.
- Neutral glide: the glider sinks 1.6 m/s at a trim speed of 14 m/s.
- Pitch down (stick forward) trades height for speed: up to 32 m/s in a dive.
- Pitch up trades speed for height: about 70% of the kinetic energy converts back, so a dive and pull-up never gains net height.
- Tuning (D-24): gentle drag and a 90°/s pitch response. A full dive from trim and pull-up regains about 22 m of the 42 m lost; drag and the turn out of the dive take the rest.
- Below 7 m/s the glider stalls: it noses down until speed returns. There is no crash.
- Turning: bank with left/right. Turn rate falls as speed rises, so tight turns need slow flight.
- Air brake (Ctrl/B held): lose 6 m/s per second, for precision landings.
- Landing: touching ground below 18 m/s folds the glider into a run. Above that, a roll landing with a brief stagger.

### 2.2 Wind
- **Wind currents:** ribbon-shaped volumes (a spline plus a radius). Inside, they push the glider along the spline at 8 to 20 m/s and hold altitude. Visible as Niagara wind ribbons, plus audio.
- **Updrafts:** vertical columns that add 4 to 9 m/s of lift. Visible as rising leaves, petals or mist.
- **Gusts and crosswinds:** sideways push areas used as hazards, telegraphed by streaked clouds 1.5 s ahead.
- **Hidden currents:** invisible and silent until Piko senses them (section 5) or the Wind Resonator reveals them (section 4).
- **Dead air:** the Silent Basin. No wind, so no updrafts and the glider sinks at double rate.

### 2.3 Upgrades (crafted at the workshop bench, section 10)
1. Handling: faster banking.
2. Current catch: a larger radius for entering wind currents.
3. Air brake: stronger, plus a short hover.
4. Resonator boost (after Ch. 6): spend a charge collected from currents for a 2 s burst of speed.

### 2.4 Assist mode (accessibility)
Holds altitude automatically, slows the turn rate and highlights the next current. It can be switched on at any time in Settings with no penalty.

### 2.5 Recovery
Falling into the cloud sea: the screen washes white, a wind gust "returns" Kieran to the last safe ledge he stood on (sampled every 2 s on stable ground), and Piko gives an alarmed squeak. No other penalty, no lost progress.

## 3. Brass Compass

- A narrative object first. It activates in Elias's workshop (Ch. 2).
- **Compass pulse (F):** the needle and a faint sky-blue ribbon point toward the current story objective or a tracked marker. Cooldown 3 s.
- **Impossible routes:** the needle swings to hidden Skyroutes and currents within 150 m that no map shows. This is how Kieran finds the route to Veilmist.
- The compass and Piko's markings react to each other near Aerian sites. Both are fragments of the same Skyfarer system, which pays off in the Great Sky Chart.
- In the HUD it appears only as a small brass dial at the top of the screen while pulsing, never a permanent minimap.

## 4. Wind Resonator (D-17)

- Bible quest 8 on Veilmist: Kieran repairs the Observatory's Resonator, then carries its portable core.
- **Uses:** hold Q (Piko command) near an Aerian device or hold F to "sing" the Resonator.
  - Detect: hidden currents within 60 m become visible for 20 s.
  - Reveal: invisible Aerian paths (light bridges, wind stairs) appear while held.
  - Activate: powers Aerian mechanisms (doors, lifts, wind engines) and the Beacon consoles.
- In Q9 the core is placed in the archive console to play the First Skyfarer Message, then returned to Kieran.
- Upgrades later: range, duration, Resonator boost for the glider.

## 5. Piko (companion)

**Follow:** a soft spring that keeps Piko 1.5 to 3 m behind Kieran's shoulder, floating 0.4 to 1.2 m above the ground. He perches on Kieran's shoulder when idle in town, rides the glider's crossbar in flight, and sleeps in the satchel during long dialogue.

**Abilities** (all from the Bible; Piko never solves a puzzle by himself):
| Ability | Trigger | Rule |
|---|---|---|
| Squeeze through small openings | Q at a small gap | Piko goes through and opens the other side (a latch or a rope). |
| Distant switches | Q while aiming at a switch within 25 m | Piko flies over and nudges it. Only works on switches marked with the wind-blade glyph. |
| Item retrieval | Q at an out-of-reach item | Brings back small items (keys, letters, fruit). |
| Reveal secrets | Passive | Within 12 m of a secret, his ears lift and his markings glow faintly. He looks at it but does not fly to it. |
| Detect wind routes | Passive, and Q in the air | Senses hidden currents within 40 m. His markings glow and the current becomes visible. |
| React to Aerian tech | Passive | Stares, goes still or acts nervous near markers before they are revealed (Veilmist). |

**Communication:** chirps, trills, whistles, ear and tail language through Acts I and II (D-12). His first speech is in Ch. 16.

**Banter system:** triggers from the Bible's list (entering a region, a landmark, an ancient record, a finished side quest, a Beacon, dangerous weather, revisiting, story milestones). Rules: a global cooldown of 90 s, no banter during quest dialogue or combat, each line plays once (revisit variants unlock after story flags), and a priority system so story lines win over ambient lines.

**Mischief (Act I flavour):** steals a shiny object from a market stall once, sits on Maren's ledger, chases floating seeds. Short and scripted, never blocking the player.

## 6. Combat (D-5)

- Available from Ch. 4, when Kieran gets the Skyfarer's Staff (D-4). **Milestone A has no combat.**
- **Moves:** a 3-hit light combo, a heavy strike (hold for a wind push that knocks enemies back), a dodge with 0.25 s of invulnerability, a parry (block just before a hit lands staggers the attacker), and soft lock-on.
- **Enemies are corrupted wind creatures.** A beaten enemy is cleansed: the dark wisps leave it and it flies off or curls up, never dies on screen. No blood or gore (PEGI 16 peril only).
- **Telegraphs:** every attack has a glowing wind-up of at least 0.5 s on Story difficulty and 0.35 s on Normal, plus an audio cue.
- **Health:** Kieran has 5 wind-feather pips. Lost pips regenerate out of combat after 6 s. At 0 he is knocked down and recovers at the last safe point, with nothing lost.
- **Difficulty:** Story, Normal, Challenging. Changes enemy damage, telegraph length and aggression. Can be changed at any time.
- Act I enemies: Mist Sprites (Whispergrove, dive and wind-burst attacks), corrupted Crystal Mites (Crystal Hollow). The Sleeping Current is an encounter, not an enemy (section 7).
- Combat is rare: about 6 to 10 short fights in the whole slice.

## 7. Encounters: the Sleeping Current (D-3)

A broken Aerian wind engine beneath the Observatory. It has no mind and no health bar; it has a **stability meter** that fills.
1. **Redirect:** rotate three wind vanes so the engine's streams flow into its intake again (puzzle).
2. **Ride:** glide and dodge energy surges up the engine shaft, using the restored streams (traversal).
3. **Stabilise:** strike four exposed power nodes with the Staff while avoiding telegraphed surges. Each node struck fills the meter by a quarter (light combat).
Reward: the engine settles, the routes around Veilmist stop shifting, and Kieran gets the Wind Resonator core.

## 8. Restoration and the Beacon sequence

A reusable framework (data asset per Beacon or restorable system) with six stages, each with a story flag:
1. **Discover:** the Beacon or system is seen from afar (a dark silhouette) and logged on the map.
2. **Investigate:** find what is broken (journal entries, Piko reactions, compass pulses).
3. **Restore:** the local challenge (puzzle, dungeon, encounter).
4. **Synchronize:** a short interactive sequence: Kieran aligns the Beacon's rings to the compass while Piko's markings pulse. 3 rings, each turned until its glyph matches; no fail state.
5. **Regional reaction:** a cinematic. A pillar of blue light, the island rises out of the clouds for a moment, new routes draw themselves across the sky, the music adds a layer, and NPCs and wildlife change (for example, Glowwings return).
6. **Story advance:** chapter flag set, new Skyroute on the Great Sky Chart, fast travel point unlocked.

## 9. Great Sky Chart, map and journal

**Map (geography starts incomplete):**
- Drawn in cartographer's ink on parchment. Only places Kieran has seen are inked. Places only heard about are pencilled with a question mark. Undiscovered areas stay blank or are covered in drawn cloud.
- Elias's old annotations appear on his map pages, some marked "wrong" when the player proves otherwise.
- Markers: quests, discovered landmarks, fast travel Beacons, and up to 3 player pins.

**Great Sky Chart** (unlocks in Ch. 6): the world-level view. It shows islands, restored Skyroutes (glowing lines), active Beacons and Skyfarer landmarks. Each Beacon restored adds a constellation-like segment. Its full form in Act V matches Piko's connected markings.

**Journal**, four tabs:
1. Quests: active and finished, with the current objective.
2. Discoveries: confirmed facts and "open questions" kept separate, as the Bible asks.
3. Elias's Journal: entries found in the world, in his handwriting.
4. Piko's Notes: written by Kieran about Piko until Ch. 16 (D-13), in Piko's own voice afterwards, when early notes gain Piko's replies.

## 10. Progression: skills, crafting, collectibles

**Story abilities (fixed, D-7):** glider (Ch. 3), compass pulse (Ch. 2), Staff (Ch. 4), Wind Resonator (Ch. 5), Resonator boost (Ch. 6).

**Perk tree (about 15 perks, D-7):** three branches, Traversal, Explorer and Piko, Staff. Points come from discoveries and restorations: each Beacon gives 2, each Skyfarer marker set gives 1, each side quest gives 1. Never from defeating enemies. The Act I slice offers about 6 points.

Example Act I perks: Sure Footing (climb 20% faster), Long Glide (sink rate -10%), Keen Ears (Piko's secret radius +50%), Wind Reader (gusts telegraphed earlier), Steady Staff (parry window +0.05 s), Courier's Satchel (carry more materials).

**Crafting (D-8):** light. Materials gathered while exploring (Skysilk, Aerian brass, crystal shards, Glowwing dust, wind-cured timber) upgrade the glider, Staff and satchel at Elias's workbench. Each upgrade has 3 tiers and a fixed recipe. No consumables, no durability, no inventory juggling: materials have no weight and a generous cap.

**Collectibles** (each one says something about the world):
- Elias's notes and journal pages (Elias Was Here).
- Skyfarer markers (sets of three that reveal a route or a secret).
- Aerian relics with a short codex entry (children's toys, tools, letters).
- Creature sightings for the Mushroom Collector and a bestiary.
- Vistas: hidden viewpoints that ink a large part of the map.

## 11. Dialogue and quests

- **Dialogue:** branching conversations from DataTables (imported from the Godot demo's 35 conversations, D-reuse). Lines carry speaker, emotion, voice file, subtitle text and a `canon` flag; canon lines may not be edited. Choices change tone and small rewards only, never canon outcomes.
- **Presentation:** subtitles with speaker names and colours, optional speaker portraits, and camera two-shots for key scenes.
- **Quests:** data assets with objectives, triggers, rewards and state (inactive, active, done, failed where relevant), dependencies, and the Bible's quest fields (purpose, start, initiator, objective, mechanics, clues, completion, reward, consequences, optional finds, required dialogue).
- **Automated checks:** every dialogue line, quest step, trigger and journal key must resolve (a commandlet test run in CI), carrying over the Godot demo's data integrity tests.

## 12. Save system

- 3 manual slots plus an autosave, written atomically (write to a temp file, then swap) with a .bak copy, as in the Godot demo.
- Saves quest states, flags, inventory, map ink, journal, perks, Piko's banter history, position and time of day.
- Autosave at every quest step, chapter change and Beacon.

## 13. Time of day (D-21)

Driven by story beats in Act I: morning for deliveries, sunset for the deed, night after the compass awakens, dawn launch. Between beats, the sun and clouds drift slowly so the world never looks frozen. Lighting presets per beat are authored, so every scene matches its colour script.

## 14. Accessibility

- Subtitles on by default, with size (4 steps), background opacity and speaker names. Captions for important sounds (wind gusts, Piko's chirps, approaching enemies).
- Full remapping for keyboard, mouse and gamepad. Toggle or hold for every hold action.
- Camera sensitivity, invert axes, motion blur and camera shake off, FOV slider.
- Traversal assist: glider assist mode, auto-climb, longer ledge grab windows.
- Difficulty: Story, Normal, Challenging, changeable any time. Combat skip option for story encounters (the Sleeping Current's combat beat can be auto-completed).
- Visual cues for every audio-only signal: hidden currents shimmer, Piko's reactions show an icon, off-screen threats show a direction marker.
- Colour-blind-safe UI colours and a high-contrast option for key interactables.
- Text size for UI, and a UI scale slider for TV distance.

## 15. HUD

Minimal so the world stays the focus. Default visible: nothing except prompts when needed. Health pips appear only in combat. Compass dial appears while pulsing. Quest objective appears for 6 s on change, then fades (always available in the journal or with a tap of the D-pad).
