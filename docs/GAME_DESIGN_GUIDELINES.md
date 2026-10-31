# Game Design Guidelines

## Tone

Warm, wondering, a little melancholy. Windrest is a small, kind place; the sky is the mystery. Kieran is curious and restless, not a chosen-one hero. Piko communicates through body language until the story gives him words.

## Lore rules

- The script and Master Project Bible are the source of truth. Quote them where possible and tag quoted lines `"canon": true` in dialogue data.
- Anything invented for gameplay (delivery parcels, signs, flavour lines) must fit existing facts and be listed in the audit or status docs.
- Conflicts go to Adam, never resolved silently.

## Characters

- Use the supplied turnarounds and sheets as the model sheet. Do not redraw or recolour established characters.
- Placeholders must look like placeholders (labelled silhouettes) so they are never mistaken for final art.

## Player movement (current values)

| Value | Setting | Why |
|---|---|---|
| Walk / run | 330 / 560 px/s | Village scale; running crosses a house in about a second |
| Jump | -1080 px/s, gravity 2600 | About 224 px apex, a bit more than one storey of a house |
| Coyote / buffer | 0.11 s / 0.13 s | Forgiving jumps |
| Short hop | Releasing jump multiplies upward speed by 0.45 | Control over height |
| Glide | Max fall 150 px/s, horizontal 560 px/s | Long and calm, sky travel should feel peaceful |
| Updraft | Lifts while gliding, weak lift when not | Rewards gliding into wind |

## Challenges

Challenges in this game teach reading the wind. Piko hints (glow, chirps) but does not solve. Falling off the island respawns at the last checkpoint with no other penalty.

## UI

Readable at 1080p from a sofa: body text at least 26 px, text scale option up to 1.5x, high contrast panels. Every action shows its current key or button.
