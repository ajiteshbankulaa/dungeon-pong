# WHAT RETURNS — technical architecture

Status: original implementation proposal. The implemented initial runtime is consolidated in poem/app.py, uses editable SVG figures and procedural animation, and launches directly from main.py. Combat has been removed at user request. Module layout and legacy-launch sections below are historical proposals, not current behavior. Story and scene timings: POEM_DESIGN.md. Current executable remains Dungeon Pong. Target Python/pygame, 1100x680 logical canvas, 60 Hz presentation, 120 Hz fixed simulation.

## Integration strategy

Develop separate poem runtime launched with `python main.py --poem`. Keep existing behavior until the vertical slice is validated; later poem can become default with `--legacy` for combat. Keep game2.py separate. Do not drive the poem through Game.clear_level: its HP, damage, unlocks, and ending thresholds conflict with the design.

Reuse pygame initialization, geometry helpers, input-device patterns, fixed-step approach, and selected audio synthesis. Extract shared primitives only when both modes need them. Existing Ball.cap enforces horizontal speed >=220 px/s; do not inherit that restriction accidentally for slower cooperative scenes. Existing save data must remain independent.

## Proposed ownership

- poem/app.py: composition, main loop, pause, focus handling.
- poem/director.py: scene lifecycle, event queue, checkpoints, transitions.
- poem/model.py: typed specs, persistent and transient state.
- poem/input.py: semantic actions and per-mode mapping.
- poem/content.py: manifest loading/validation.
- poem/scenes/memory.py: horizontal movement, interaction anchors, staged figures.
- poem/scenes/pong.py: lean physics and short-match lifecycle.
- poem/scenes/text.py, loss.py, transition.py: safe reading, held poses, visual bridges.
- poem/objectives.py: event-driven completion policies.
- poem/opponent.py: generous/delayed/recorded/cooperative movement policies.
- poem/renderer.py, animation.py, audio.py: presentation and cue execution.
- poem/persistence.py: separate atomic checkpoint store.
- data/poem/sequence.json, text.json, sprites.json: stable authored IDs and assets.
- assets/poem/: sprite atlases, room layers, audio.

These are responsibility boundaries; avoid creating empty framework modules before the slice needs them.

## State and scene contracts

Persistent state: schema_version, content_version, checkpoint_id, completed, replay_count, settings. Transient state: scene_id, loop_index, room_id, elapsed, objective_progress, motif_recording, memory_flags, pending_events. Narrative text uses I/you; internal actor IDs player/other never appear on screen. No relationship metadata, moral score, perfection statistic, or rescue threshold.

SceneSpec fields: id, mode, loop, room, next_id, stage_preset, objective_spec, opponent_spec, text_cues, transition_out, checkpoint. Stable IDs such as l2_between_memory. Fifteen Pong rooms plus memory/text bridges, not fifteen separate environments.

Scene interface: enter(context), handle_actions(actions), fixed_update(dt), draw(surface, alpha), exit(). Scenes emit events. Director alone changes scene, after current fixed-step iteration completes. Completion is idempotent. Pause/text reset accumulator to prevent catch-up bursts. Consume transition-causing input so E/Space cannot also interact, serve, or skip in the next scene.

Ordinary graph: MEMORY -> TRANSITION -> PONG -> TEXT/MEMORY -> next room. Loss occurs once after l1_again; coda ends at title. Replay resets transient state and changes opening text. Checkpoints resume at safe scene entry, not in a live rally.

## Controls and movement

Memory: A/D or left/right horizontal, E/Enter interact. Pong: W/S or up/down vertical, Space serve. Controller: appropriate stick axis by mode; south button interact/serve. Escape pauses; window focus loss pauses. Map semantic actions before simulation and distinguish held movement from pressed edges. Show small mode-specific prompts at changes.

Memory baseline movement starts around 160 logical px/s; clamp x to room bounds. No platforming physics or navigation mesh. Anchors have stable ID, x position, eligibility, action, and approx. 48 px interaction radius. Nearest eligible anchor owns prompt; completed interactions disable. Mandatory anchor travel <=250 px. Other figure uses authored clips/waypoints.

## Physics and objective policies

Lean PoemBall/PoemPaddle models avoid combat flags. Start tuning at 280–360 px/s ball speed, player paddle 120 px tall, opponent 100–130 px; bounded angles and fixed room speed. Separate serve-wait from active-ball state. Resolve collision once per contact with positional separation. Goals emit exactly one event, then park ball. Reset trail and per-flight counters on serve.

Events: serve_started; paddle_return(actor, ball_id, offset); wall_bank(ball_id); target_hit(target_id); ball_lost(side); interact(anchor_id); text_completed(cue_id); animation_cue(cue_id); sequence_elapsed.

Objectives:
- ReturnCount(3): counts only player paddle contacts.
- TargetHits(n): each active target counts once; visible progress.
- BankedTargets(n): >=1 wall bank since last paddle contact.
- SharedExchanges(n): ordered player/other contacts on same ball; reset incomplete half on goal, retain completed total.
- Maintenance(20 seconds): active simulation time, max two staggered balls; authored fade concludes independently of score.
- ReachableReturns(2): incoming shot reaches marked opponent band; exclude initial serve, no progress loss on miss.
- AnyPoint: either side ends room; identical narrative outcome.

After unsuccessful attempts, widen targets/reach or lower speed gradually. Expose a Continue option through pause if necessary; never fake a successful hit or grade affection. Set room-specific attempt budgets and playtest them. No room may trap players indefinitely.

Opponent policies: generous return lanes; delayed but telegraphed reaction; bounded replay motif; cooperative limited reach. Record normalized y/time from opening Serve; cap recording size. Supply deterministic authored fallback for checkpoint loads without prior recording. Signature gesture is anticipatory animation, never an unfair sudden hitbox change. Target rooms explicitly create reachable openings.

## Rendering and asset pipeline

Draw at logical resolution and letterbox. Order: background, room objects, character/game geometry, restrained lighting, text, prompts/overlays. Fading scenery does not lower essential gameplay contrast. Reading pauses simulation. Sprite manifest provides atlas path, rects, durations, feet origin, loop, cue markers. Validate paths/rectangles; developer placeholders are explicit and replaced before release. Keep feet anchored across clips.

Character-to-paddle bridge aligns centers over about 0.5 seconds and crossfades contour; enable physics afterward. Reduced motion uses dissolve. One room with layered object state plus bedside loss scene. Loss uses held poses, steady muted red, no flashing or medical mechanics. Skip retains factual death text and moves to replay-cabinet checkpoint.

Audio consumes gameplay events: impact remains readable separately from evolving music. Three-note motif has loop-dependent layers. Do not delete all feedback when representing absence. Cup sound at coda echoes impact without requiring literal reuse of identical waveform.

## Persistence and content checks

Use data/poem-save.json, never overwrite data/save.json. Atomic temp-write/replace; validate versions, settings, checkpoint IDs. Persist scene-boundary state only, no pygame objects/live physics. Unknown checkpoints recover to known safe scene with explicit Continue/New choice. New run clears memory flags. Opening alternate selected only by completed replay state.

Validate unique scene/text IDs, referenced assets, supported objective modes, all next edges, finite main path, intentional title replay edge, three-by-five room coverage, loss once, and coda reachable. Text cues fire once per scene entry. Input-triggered and elapsed-triggered exits cannot both transition.

## Production sequence

1. Opening Serve -> two-person bridge -> Angle -> table interaction -> Between. Temporary intentional silhouettes. Validate playable relationship, movement prompts, target affordance, continuity.
2. Finish loop 1, held-pose loss and skip, replay activation.
3. Data-driven loop 2 variants, maintenance sequence, visible window interrupt.
4. Cooperative loop 3, final score hold, coda, save/replay.
5. Final sprites, palette, motif mix, accessibility, pacing passes.

## Verification

Focused tests: event counting; same-ball exchange ordering; retained progress on miss; one completion per scene; input edges consumed at transitions; death scene once; either scorer same ending; replay alternate text; save isolation/recovery; fallback motif on resume.

Add --poem --smoke using deterministic scripted actions and temporary saves. Traverse and render every scene. Smoke checks lifecycle/rendering, not objective achievability; real-hit integration scenarios cover aiming and exchanges. Capture opening, human room, target, loss, fading loop, cooperative band, coda.

Manual playtests with new players: identify two people and death without coaching; understand reconstruction; discover mode controls; notice repeated detail; complete in 5–10 minutes median excluding optional reading holds. Check high contrast, reduced motion, readable text, muted audio, controller prompts, focus pause. Use local development timing/attempt logs if useful; no external telemetry required.

Scope: one memory room, one loss composition, two figures with pose variations, five court geometries in three rule passes, one ending. No platforming expansion, inventory, dialogue trees, full voice acting, or combat campaign production.
