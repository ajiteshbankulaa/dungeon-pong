# What Returns

A short desktop game poem for Week 2, *A Feeling*. Two people share an arcade machine on Tuesday night. Later, its recording remembers the other person's wrist. In daylight, the player serves into the empty half of the court.

## Play

On Windows, extract the complete release ZIP and open `WhatReturns/WhatReturns.exe`. Keep the accompanying `_internal` folder next to the executable. From source, install Python 3.11 or newer and run the following commands.

    python -m pip install -r requirements.txt
    python main.py

- Enter starts, advances a verse, and resumes after a pause. C on the title opens the saved passage.
- Walk with A/D or Left/Right. E uses the object in reach. At the arcade machine, move the paddle with W/S or Up/Down and serve with Space.
- At the end of the recording, walk left or hold Down/S to step away.
- In morning, aim with Up/Down and tap Space to send a single remembered shot. At the last invitation, E leaves the glass.
- On a controller, move with the left stick, use the south button to interact or serve, and the east button to leave the last invitation. Pull the stick back to step away from the machine.
- Escape or the controller Start button pauses. M toggles sound, R reduces motion, and Q quits from pause. Packaged saves live in `%LOCALAPPDATA%/WhatReturns`.

## Edit and verify

The fifteen passages and the alternate Morning Hold line are in `data/poem/text.json`. Interlude and coda text and passage timing live in `poem/runtime.py`. The hand, room, and court are drawn in `poem/app.py` and `poem/artwork.py`. Figures, window art, cup, and arcade machine are editable SVGs in `assets/poem`. The palettes live in `data/poem/palettes.json`.

The score runs through three movements, lasting 90, 96, and 87 seconds per loop. Each movement plays across passage boundaries. To rebuild the shipped music with NumPy and FFmpeg installed, run `python tools/build_soundtrack.py`. Sample attribution is in `assets/poem/AUDIO-CREDITS.txt`.

    python -m pytest -q
    python main.py --smoke
    python -m PyInstaller --noconfirm WhatReturns.spec

The tests include a complete playthrough and regression checks for missing shots, input during pause, the silent winter cut, withdrawal, both morning responses, the cup, and the final chord. Smoke renders the passage artwork using an isolated save. The historical design and audit documents describe earlier drafts.
