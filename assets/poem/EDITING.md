# Artwork and music

All landscape artwork is original SVG, editable in Inkscape, Figma or a text editor. Use a 1100 × 680 viewport with matching width/height because this pygame SVG renderer does not reliably scale mismatched viewports.

landscape-tuesday.svg contains broad peach dunes, a sage mountain, warm sun and dark teal foreground.
landscape-reconstruction.svg repeats the terrain in violet and breaks its framing architecture.
landscape-morning.svg leaves the same place open, pale and quiet.

Edit person.svg and other.svg for the faceless folded figures. Their identity colors continue into paddles and balls. reaches.svg supplies the two collision forms. The gameplay guide and collisions share geometry in poem/shots.py. Runtime staging is in poem/artwork.py and poem/app.py.

The full music source is tools/build_score.py. The progression and melody are written in MIDI note numbers and rendered from the credited A3 piano recording. It generates the Tuesday and reconstruction movements. Music does not restart between passages. Short sounds are mixed through poem/score.py; morning contains room tone and gesture sounds before the final recorded piano chord.
