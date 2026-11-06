"""Author the winter bridge and curtain-opening continuation from the credited piano."""
from pathlib import Path
import tempfile, subprocess, wave
import numpy as np
from build_soundtrack import add
from build_score import RATE, OUT, load_sample

def write(sample,name,chords,melody,bar):
    length=len(chords)*bar
    track=np.zeros((int((length+6)*RATE),2))
    for i,chord in enumerate(chords):
        start=i*bar
        for voice,note in enumerate(chord):
            add(track,sample,start+voice*.13,note,bar+3,.13,.42+voice*.04)
        for beat,note in enumerate(melody[i%len(melody)]):
            if note:
                add(track,sample,start+.75+beat*bar/4,note,4,.17,.56)
    dry=track.copy()
    for delay,gain in ((.31,.12),(.73,.07),(1.4,.035)):
        n=int(delay*RATE);track[n:]+=dry[:-n,::-1]*gain
    tail=track[int(length*RATE):].copy()
    track=track[:int(length*RATE)]
    track[:len(tail)]+=tail*np.linspace(1,0,len(tail))[:,None]
    track*=min(.047/max(1e-9,np.sqrt(np.mean(track**2))),.65/max(1e-9,np.abs(track).max()))
    n=int(.008*RATE)
    track[:n]*=np.linspace(0,1,n)[:,None]
    track[-n:]*=np.linspace(1,0,n)[:,None]
    with tempfile.TemporaryDirectory() as td:
        wav=Path(td)/'score.wav'
        with wave.open(str(wav),'wb') as f:
            f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
            f.writeframes((track*32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','5',str(OUT/name)],check=True)

with tempfile.TemporaryDirectory() as td:
    sample=load_sample(Path(td))
    env=np.convolve(np.abs(sample),np.ones(240)/240,mode='same')
    sample*=np.clip(env/.0007,0,1)**2
    write(sample,'winter-v4.ogg',
          [[45,52,59,60],[41,48,55,59],[38,45,53,60],[40,47,55,59]]*2,
          [[72,None,71,None],[69,None,None,67],[65,None,64,None],[67,None,None,71]],4)
    # The opening A-minor voicing belongs to morning. F, C and G gradually open it.
    write(sample,'hope-v4.ogg',
          [[45,52,59,60],[41,48,55,64],[48,55,60,64],[43,50,57,62],
           [45,52,60,64],[41,48,57,65],[48,55,62,64],[43,50,59,62],
           [41,48,55,64],[48,55,60,67],[43,50,57,62],[45,52,59,60]],
          [[72,76,74,72],[69,72,76,None],[76,79,76,74],[74,71,67,None],
           [72,76,79,76],[77,76,72,None]],5)
