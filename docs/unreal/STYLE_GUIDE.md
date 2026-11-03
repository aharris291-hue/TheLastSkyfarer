# Style Guide (Phase 2 draft)

Status: draft for Adam's review, 2026-11-02. It follows Bible section 23 and the production brief. The look is whimsical, hand-painted storybook fantasy: original, stylized and painterly, the quality of a premium stylized 3D game, not photoreal and not a copy of any studio.

## 1. Reference: Adam's existing art is the design baseline

These existing sheets are the approved designs. 3D models must match them, and we never redesign an established character:
- Kieran Thorn: Turnaround Sheet, Emotions Sheet, Actions and Action frames, Kieran with Staff.
- Piko Turnaround. Skyfarer Staff Turnaround.
- Elias Thorn: Prime Years and Final Years turnarounds.
- Cassian Vale, Tessa Reed, Sage Alder, Elder Thalen, Forgemaster Rhea Vulkan, Kael Ashforge, Admiral Soren Tidecrest, Astronomer Lysette Vale, Bram Holloway, Elara Greenborough. There are also sheets for characters without roles yet.
- Aeolus, Tempest Ascendant (Option 3). Celestial Keeper, Horizon Breaker, Prime Guardian Sentinel, Prime Core of the Warden Network.
- Maps: Windrest Village, Brindle Isle Atlas (Elias's Journal), World Above the Clouds, Fantasy Atlas of Floating Realms.

**Missing designs:** Maren Holt, Rowan Finch, the Ancient Glider, the Brass Compass, the Wind Resonator, the Beacons, Seeker uniforms, and most creatures. Firefly prompts for these are in [FIREFLY_PROMPTS.md](FIREFLY_PROMPTS.md). New character designs need Adam's approval.

## 2. Shape language

| Subject | Shapes | Notes |
|---|---|---|
| Brindle Isle | Round, soft and warm. Rounded roofs, plump trees, bulging stone walls, curving paths | Nothing sharp in the village. Slight lean and wobble so it looks hand-made |
| Aerian ruins | Elegant, wind-carved geometry. Long tapering arcs, crescents, spirals, thin spires | Look carved by wind over centuries. Brass and pale stone. The wind-blade glyph repeats |
| Veilmist nature | Tall, organic and strange. Giant mushrooms, crystals, hanging moss | Mysterious, not threatening |
| Corruption | Jagged wisps and broken spirals, dark violet-grey | Always readable against the painterly world |
| Characters | Strong silhouettes, larger heads and hands (about 6.5 heads tall for Kieran) | Kieran's scarf, satchel, map tube and glider make his silhouette |

## 3. Colour

**Global palette** (from the outline): Kieran's jacket #5C6E4F, scarf #4B9FE1, shirt #E9E1CC, leather #8B5A2B, brass #C79A3B. Piko's fur #F5F4EF, accent #87C7FF, markings #ADEFFF, eyes #F4BC42. Aerian glow is sky blue #4BB3FF. Corruption is violet-grey #5A4E6E.

**Region colour scripts** (Bible 23.3, Adam's world map):
| Region | Key colours | Mood |
|---|---|---|
| Brindle Isle | Grass green, wheat gold, terracotta roofs, warm stone, sky blue | Home, golden hour |
| Mistreef and Veilmist | Teal, mist white, glowing cyan moss, violet shadows | Mysterious, soft |
| Verdant Reach | Bright greens, wildflower pinks and yellows | Lively, abundant |
| Ember Peaks | Basalt black, ember orange, brass | Dramatic heat |
| Azure Expanse | Turquoise, aqua, white water | Airy, aquatic |
| Shattered Sky | Desaturated stone, pale lavender | Unsettling |
| Starfall Basin | Indigo, violet, starlight gold | Contemplative |
| Lost Continent | Monumental white stone, brass, faded blue | Awe, melancholy |

**Act I colour script by story beat:**
1. Sunrise on the Upper Cliffs: peach and rose sky, long blue shadows.
2. Morning deliveries: clear warm daylight, saturated greens.
3. Letter of Inheritance: deep golden sunset, orange rim light.
4. The workshop at dusk and night: lamplight amber inside, cool blue moonlight outside, the compass glowing sky blue.
5. Dawn launch: pale gold horizon over a lilac cloud sea.
6. The fog crossing: low-contrast white and teal. The island appears as a dark silhouette.
7. Veilmist: teal mist, cyan bioluminescence, shafts of light.
8. Crystal Hollow: cool crystal blues with warm torch accents.
9. Silent Basin: still, slightly desaturated, eerie.
10. The Observatory: dark stone, starfield projection.
11. Beacon Awakened: night, then a pillar of saturated blue, and the island briefly bright above the clouds.

## 4. Lighting

- Golden-hour Windrest: warm low sun, soft sky fill, painterly bloom.
- Diffuse, mysterious Veilmist: heavy volumetric fog, light shafts, emissive moss and Glowwings.
- Soft-ramp (two to three band) diffuse shading on characters, with a subtle rim light for silhouette. Environments use Lumen with a painterly post-process (Kuwahara-style brush filter at low strength, edge darkening, colour grading per region).
- Clouds: stylized volumetric clouds with painted shapes and soft edges. The cloud sea below the islands is always visible and always moving.

## 5. Materials and textures

- Hand-painted look: baked light and shadow in albedo kept light, so Lumen still reads. Visible brush strokes at mid distance, simplified detail at a distance.
- **Texel density:** 512 px per metre for hero props and characters' near view, 256 px/m for environment kits, 128 px/m for distant terrain.
- **Master materials:** M_Painterly_Surface (stylized albedo, roughness ramp, painted normal at low strength), M_Painterly_Foliage (wind sway, translucency), M_Aerian_Brass (stylized metal with glowing glyph mask), M_CloudSea, M_Water_Stylized.
- **Quixel Megascans** must always go through the painterly master materials. Rules: simplified albedo (posterized and hand-tinted), normals reduced to about 40%, roughness flattened, colour graded to the region palette. Never placed unmodified next to stylized assets.
- Wind affects grass, trees, flowers, cloth, the scarf, banners, windmill sails and Piko's ears and tail.

## 6. UI style

Cartographer's ink, brass and parchment:
- Parchment panels with hand-drawn ink borders. Brass fittings for frames and the compass dial.
- Fonts (free): a hand-lettered serif for headings and a clean, readable serif or sans for body text at 1080p TV distance.
- Icons in ink line art with a light watercolour wash.
- Map: ink for known places, pencil and question marks for rumoured places, painted clouds for the unknown.
- The HUD stays minimal (GDD section 15).
