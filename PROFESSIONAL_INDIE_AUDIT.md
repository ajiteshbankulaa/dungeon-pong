# Dungeon Pong — professional-indie audit

## Verdict

The game is a credible combat prototype: responsive Pong, 25 encounters,
bosses, projectiles, powers, checkpoints, cosmetics, procedural SFX, saves,
and automated coverage. It is not yet a master-level indie game because those
systems are not joined by authored meaning, place, player choice, or replay
ritual. The goal is not to copy Undertale or Hollow Knight; it is to reach their
clarity of point of view and cohesion.

## What prevents that level now

| Gap | Current evidence | Player consequence | Priority |
| --- | --- | --- | --- |
| Narrative | Level data contains names, stats, and hints, but no scenes, cast, choices, or endings. | Fights have no emotional stake. | P0 |
| Dungeon structure | 25 sequential encounters, no room graph, map, shortcuts, keys, or side rooms. | A playlist rather than a journey. | P0 |
| Builds | Fixed power picks and a small permanent pool. | Little strategy or ownership between matches. | P0 |
| Identity | Three paddle styles and basic settings, but no complete art/theme modes. | Neither classic Pong nor a rich new world is fully expressed. | P0 |
| Music | SFX exist; no adaptive score or dungeon leitmotifs. | Reveals and wins do not become memories. | P0 |
| Onboarding/accessibility | No tutorial room, controller/remap support, UI scale, reduced flash, or difficulty assists. | New players may churn before learning the skill. | P1 |
| Sharing/replay | No seeded challenges, replay export, practice, achievements, or share cards. | Too little reason to return or talk about it. | P1 |
| Production | README/testing guide are deleted, builds are local artifacts, and UI still says `01 / 20` while data has 25 levels. | Harder collaboration and less trustworthy releases. | P1 |
| Authoring | Encounter behavior is concentrated in a large `encounters.py`. | Content and balancing will slow down. | P1 |

## Product pillars

1. Every point is a decision: skill, not hidden stat inflation, wins.
2. Readable chaos: each hazard telegraphs and always has a possible response.
3. Each dungeon has a visual material, enemy family, music motif, rule, and
   dramatic question.
4. Upgrades change expression, not competence; permanent damage/speed/paddle
   buffs are out.
5. Every run creates at least one striking, shareable moment.

## Campaign proposal: *The Cathedral of Return*

The paddle is the last Keeper of a cosmic arcade cathedral. Every ritual match
restores a memory; the Architect has preserved the world by looping it forever.
The finale asks whether to keep, break, or transform the loop.

| Dungeon | Rooms | Gameplay theme | Story beat | Boss |
| --- | ---: | --- | --- | --- |
| Silt Arcade | 12 | goo, cover, angle lessons | Meet the Slime; the cathedral is dying. | Bone King |
| Hunt Gallery | 14 | telegraphs, lanes, dual-ball routes | Free or recruit the Hunter. | Phantom Queen |
| Dream Engine | 16 | gravity, stasis, survival | Discover matches erase memory. | Bullet Saint |
| Broken Heavens | 16 | lightning, breakables, reversed court | Choose who receives memories. | Lord 666 / Angel |
| Infinite Court | 18 | portals, currents, mastery remixes | Confront the Architect. | branching finale |

Use 10–20 room maps: start -> 2–3 branches -> reward/story/shop -> elite gate
-> boss. Optional rooms grant lore, cosmetics, high-risk relics, and shortcuts.
The expanded production target is 100 authored rooms and 20–30 hours including
optional character routes, mastery rematches, and three endings; see
`NARRATIVE_BIBLE.md`. Room count must create emotional pacing, not filler.

## Progression, art, and sound

- **In-run relic draft:** after elites, choose one of three temporary relics;
  cap at 4–5. Examples: banked shots charge one parry; perfect center hits mark
  a weak point; manual curve gains precision but reduces paddle width.
- **Persistent mastery:** unlock sidegrades, palettes, codex, practice options,
  and challenge modifiers—not permanent power.
- **Paddle expression:** chassis, trail, impact glyph, and ability-slot
  cosmetics; mechanics remain in separately balanced pre-run loadouts.
- **Classic profile:** phosphor black, white geometry, restrained particles,
  competitive clarity. **Cathedral profile:** hand-drawn silhouettes,
  stained-glass glow, portraits, kinetic camera, themed materials.
- Add music/SFX/intensity sliders, screen-shake and reduced-flash settings,
  colorblind-safe shapes, subtitles, UI scale, and adaptive themed music.

## Implementation roadmap

### 0. Stabilize and define — 1–2 weeks

- Restore README, controls, attribution, build/testing instructions; fix every
  20/25 assumption.
- Add CI for tests and smoke mode, tagged release builds, and changelog.
- Write a style bible, narrative beat sheet, accessibility baseline, and
  telemetry schema.

**Exit:** a new contributor can clone, test, and package the game; all menus
report 25 levels correctly.

### 1. Vertical slice — 4–6 weeks

- Make Silt Arcade: a 10–12 room graph, map, tutorial-by-play, two NPCs, and
  Bone King.
- Refactor encounter data into room specs plus isolated behavior modules.
- Implement both presentation profiles, accessibility options, one adaptive
  music theme, and an intentional art pass.

**Exit:** 10 external players can finish, explain its premise, and voluntarily
replay a branch.

### 2. Replayable core — 4–6 weeks

- Add relic draft, sidegrade loadouts, practice, codex, and boss rematches.
- Add controller/remapping and difficulty assists that extend telegraphs rather
  than reduce enemy HP.
- Add deterministic daily seeds, replay recording, and a run-end share card.

**Exit:** different viable builds exist and a player can exactly reproduce a
shared run from seed and version.

### 3. Campaign production — 6–10 months for a small team

- Produce four further dungeons using reusable room/dialogue/music/VFX tools.
- Closed-playtest every two weeks; cut rooms that do not teach, escalate,
  reward, reveal, or delight.
- Prepare demo, trailer, store page, press kit, and creator challenge tools
  3–4 months before launch.

## First tasks

1. Repair documentation/release discipline and the 25-level display.
2. Write Silt Arcade's beat sheet and room graph.
3. Add a room-graph/map/save model, replacing level-index-only progression.
4. Convert levels 1–5 into the slice before adding new enemies.
5. Add presentation profiles, accessibility controls, and one polished theme.
6. Playtest and revise the first 20 minutes before dungeon two.

## Metrics to set before launch

- 80% tutorial completion; 60% reach first boss; 35% replay a slice/branch.
- Fewer than 10% of deaths called unfair in player feedback.
- Stable 60 FPS on minimum PC and zero save-loss failures in soak tests.
- Validate wishlist/demo conversion and creator clip uptake; virality is an
  outcome to measure, never a feature that can be guaranteed.
