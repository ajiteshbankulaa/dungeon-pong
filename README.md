# What Returns

A game poem in fifteen passages. A Tuesday-night game, the arcade machine's reconstruction, and a last gesture on dusty glass.

Run with Python 3.11 or later:

    python -m pip install -r requirements.txt
    python main.py

Enter begins, C continues the saved passage. Walk with A/D or left/right. Approach the arcade machine or table and press E. Move the paddle with W/S or up/down and press Space to serve. Enter advances a line. A connected controller uses the left stick and south button. Pull the stick back or hold Down/S to withdraw from the machine.

Esc pauses. M toggles audio. F toggles the 15 kHz CRT tone. R reduces motion. Q quits from pause. The rupture holds for 3.5 seconds, then shows the coat-hook fragment. A completed shot reveals its poem immediately. Enter advances the visible poem. Each serve begins with Space.

The morning court is the reflection in a powered-off screen. Shots cross once. In the coda, approach the table to place the cup, then approach the arcade machine to leave the ticket.

## Editing

The fifteen passage definitions and their script live in data/poem/text.json. The coat-hook lines, restart and coda are in poem/runtime.py. Edit cut-paper figures in assets/poem and act palettes in data/poem/palettes.json. Audio credits are in assets/poem/AUDIO-CREDITS.txt. Older design documents are historical drafts.

## Checking the game

    python -m pytest -q
    python main.py --smoke

Smoke renders all fifteen passages using a temporary save. The test playthrough exercises all completion events, the rupture, controller/keyboard withdrawal, save continuation, and the unanswered morning beat. Around six minutes is a loose first-time target. Reading and interactions are self-paced. There are no per-room duration gates or automatic serves.

The continuous guide uses the live collision geometry. The Pong obstacle is a pair of reaching forms in assets/poem/reaches.svg. The domestic table remains a physical object in assets/poem/table.svg. Both are editable SVGs. Objective and progress indicators sit above the court. A missed shot returns to a ready ball, and completed returns remain earned.

## Art and score

The three landscapes are original editable SVG layers in assets/poem/landscape-tuesday.svg, landscape-reconstruction.svg and landscape-morning.svg. Their shared mountain, sun and terrain change across the emotional arc. Palette values, including court contrast colors, live in data/poem/palettes.json. The paddles are faceted ink strokes; ball color preserves identity.

The continuous score has two original movements, 95 seconds and 111 seconds, rather than a repeating four-note cue. The second develops the first movement with missing voices and a drier piano. Morning yields to room sound and the final acoustic chord. Playback continues across rooms and resumes after pause. The standalone listening version is assets/poem/audio/what-returns-suite.mp3.

To edit the composition, change the progression, melody and voicings in tools/build_score.py, then run it. The authoring script requires numpy and ffmpeg; the game still requires only pygame. Piano source credit and license are in assets/poem/AUDIO-CREDITS.txt.

## Revised morning and objects

Withdrawal uses the same room and cabinet. Hold left to step away, or Down/S to pull back. Morning has three playable gestures; the Angle/Between fragments now connect the first shot to the room rather than requiring two extra empty shots. The final ball may be sent with Space or left resting with E. Object labels indicate where to walk and which interaction is available.

The domestic cup and arcade cabinet are editable SVGs in assets/poem/cup.svg and cabinet.svg. Landscapes are confined to the window, with the room providing the setting.

Music playback uses circular five-second overlaps. The shipped looping tracks and lengths are recorded in assets/poem/audio/loop-durations.json. Reconstruction uses reconstruction-loop.ogg. The standalone suite remains the full listening arrangement. Restart an already open game to load the revised score and scenes.

## Current late-game staging

The loss is a quiet bedside scene in two held compositions, followed by the coat line. Withdrawal keeps the player in front of the arcade machine and offers replay or stepping away. After stepping away, a fragment marks the realization and daylight enters the same room. Morning has its own sparse piano reprise, authored in tools/build_morning.py, and a recognizable screen bezel.

Only Start and Resume are navigation buttons. Narrative text advances with Enter, serving with Space, and objects with E. Repeated Continue and control-list labels are removed. Shadows are projected from the window according to the figure's position, not mirrored with facing.


## Current interaction and sound revision

Text panels show Enter to continue in their bottom-right corner. Start and Resume work with Enter and with a click. The arcade machine is a foreground prop, not a walking barrier. Close-up memories render one pair of actors only.

Between is a cooperative placement exercise: send two returns within the purple paddle's reach. Angle is one familiar trick shot into the old corner. Their reconstruction versions revisit those habits. There are no block obstacles in Between.

The loss is implied through a brief wet-road/light image followed by one coat and an empty hanger. There is no explicit death declaration. Music now loads the three '-v3.ogg' movements, authored in tools/build_soundtrack.py. The repeating noise bed is disabled. The three movements share melody/harmony but use shared piano, mechanical plucks, and open morning voicings respectively. All have circular overlapping loop joins.
