# Verification

Environment: Windows, Python 3.13.2, pygame 2.6.1. Tests use temporary saves and
SDL's dummy video/audio drivers. They do not alter the player's progress.

## Automated regression suite

`python -m unittest discover -s tests -v`

51 tests cover:

- New game, Continue, checkpoint restart, defeat, victory, pause/resume, menus and mouse input.
- Missing/corrupt/old/malformed save files, defaults, atomic write failures, read-only paths.
- Stats, cosmetic and power persistence, plus quitting before choosing an earned power.
- Fast paddle collisions, circular corner contacts, consistent movement at 30/60/144 FPS,
  velocity caps, and prevention of near-vertical endless rallies.
- Blink targeting/cooldown with projectiles; blocking without powers; Reflect against red and
  gold shots, paddles, and boss cores; Shock's third return; Ricochet and two-hit cover.
- Slime's exact two boosted bounces; Skeleton's return-persistent guard and telegraphed arrows;
  Wraith's partially visible ball phase and telegraphed paddle phase-step; slower AI read intervals;
  restoration of the larger 108px player paddle.
- Red projectile damage/dodging, simultaneous-hit recovery, telegraphs, safe channels,
  and the incoming-ball return corridor.
- Multiball with portals, simultaneous misses, moving walls, shrinking bounds,
  gravity, reverse play, individually destructible paddles, survival, and Breakout gating.
- Encounter-aware AI prediction through portals, gravity, and obstacles; the two-defender
  Twins encounter; level 10's aimed, fan, and alternating-lane phase progression.
- All phases of all four bosses; transition cleanup with an active projectile;
  pausing during an attack; core vulnerability; the final one-hit rally.
- Rendering every encounter, boss phase, menu, cosmetic style, and power choice.

## Longer diagnostic runs

`python tests/playtest.py`

A deterministic pilot runs each of 20 levels at seeds 3, 11, and 29. It has no
powers, moves at the normal 520px/s limit, and uses the same collision/damage
rules as a player. It predicts returns, aims with the paddle tips, and moves out
of nearby red lanes. No HP overrides, invulnerability cheats, forced damage, or
level skipping are used during these runs. Each run has a 240-second ceiling.

The latest sweep cleared **59/60 encounters**, with no invalid coordinates, excess
ball/projectile counts, or speed-cap violations. The one loss was Phantom Queen
level 10 after the new three-pattern escalation; the other two no-power seeds
cleared it. Most normal fights lasted roughly 15–80 seconds. Bosses ranged from
approximately 67–136 seconds. This is useful evidence
against hard power requirements and obvious softlocks, not proof of perfect
balance or human accessibility.

## Rendering / launch smoke

`python main.py --smoke --screenshots artifacts`

The actual launcher initializes pygame and simulates/renders all 20 levels.
The rendering tests additionally produce individual boss phase images, menu
screens, a 20-encounter contact sheet, and projectile telegraph/pattern scenes.
The menu, power choice, encounter contact sheet, and bullet telegraph were
visually inspected for contrast, clipping, and hierarchy. An overlapping dimmed
footer on modal screens was fixed.

## Human playtest still needed

Automated pilots have better trajectory information than a new player. Human
testing should evaluate whether early instruction timing is sufficient, whether
portal/multiball combinations are comfortable to read, whether the shorter
special encounters are satisfying, and whether the Bullet Saint needs longer
phases. This update deliberately avoids extending fights just by adding HP.

The project has not been manually played end-to-end on a physical keyboard in
this validation pass. Audio is not added; the original build had no sound system.
