# Original playtest audit

Baseline: commit `3eeeafb`, tag `original-playtest`. Published before edits.

## Preserve

- W/S and arrow movement, Space for a power; three HP.
- Paddle impact position controls the rebound angle; bounded ball speed.
- Enemy prediction includes an error and movement limit, rather than perfect tracking.
- Slime wall bounces, skeleton guard, wraith misdirection, necromancer obstacles.
- Black arena, white scoring ball, short impacts, two-choice power screens.

## Fix before expanding

- `pygame.Rect` truncates fractional paddle movement every frame. Use float positions.
- Discrete rectangle overlap can tunnel at low frame rates. Use a fixed 120 Hz simulation and bounded velocities, with circle/rectangle contacts and separation.
- Returns can exceed the nominal speed cap; normalize angles and cap every step.
- Damage functions disagree, hazards continue after defeat, and simultaneous hits consume multiple HP. Centralize damage and grant recovery time.
- Soul balls resemble hazards but punish misses and sometimes home into a paddle-sized target. Make all hostile projectiles dodgeable; outlined gold shots additionally permit blocking/reflection.
- Wraith hides the actual incoming ball, removing the information needed to return it. Keep the real ball solid and use outlined phantom copies.
- Necromancer wall teleports the ball through itself and applies a random kick. Use visible destructible geometry with ordinary reflections.
- AI reads immediately and teleport targets are perfect. Add reaction delay, frozen noisy prediction, and bounded teleports.
- Power selection samples two items even when fewer remain. Offer powers only at configured milestones and handle exhaustion.
- `shake` is unused; global display/font initialization makes imports open a window. Initialize presentation in the entry point.
- Restart always loses all progress. Add validated atomic JSON saves, checkpoint restarts, statistics, and cosmetic settings.
- Room-index branches couple rendering, abilities, and combat. Replace them with a short level table and explicit encounter rules, while keeping unique boss phases in code.

## Scope / validation

Twenty short encounters; bosses at 5/10/15/20. Four powers, three cosmetic styles, no inventory/economy or generic engine. New rules use ball/paddle/obstacle lists plus small configuration changes. Automated tests cover lifecycle, saves, collisions, phases, powers, and combinations; deterministic simulations exercise every encounter. Human pacing and fun judgments remain playtest targets, not claims established by unit tests.
