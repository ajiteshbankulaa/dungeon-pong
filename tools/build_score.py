"""Render the original two-movement score from one credited acoustic piano sample.

Edit PROGRESSION, MELODY and the voicings below, then run this file.
Requires numpy and ffmpeg for authoring. Runtime uses only pygame.
"""
from pathlib import Path
import math
import subprocess
import tempfile
import urllib.request
import wave
import numpy as np

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'assets/poem/audio'
RATE=24000
BEAT=60/72
BAR=BEAT*3
PROGRESSION=[
    [45,52,59,60], [41,48,57,64], [48,55,59,64], [43,50,57,59],
    [38,45,53,64], [45,52,59,60], [41,48,57,64], [43,50,57,62],
    [38,45,53,60], [40,47,55,62], [41,48,57,64], [45,52,59,64],
]
MELODY=[
    [76,72], [71,69], [67,71], [74,71],
    [72,69], [71,76], [72,71], [69,67],
    [65,69], [67,71], [72,76], [71,None],
]

def load_sample(folder):
    source=OUT/'piano-A3.mp3'
    if not source.exists():
        urllib.request.urlretrieve('https://tonejs.github.io/audio/salamander/A3.mp3',source)
    pcm=folder/'piano.wav'
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-ac','1','-ar',str(RATE),str(pcm)],check=True)
    with wave.open(str(pcm)) as f:
        data=np.frombuffer(f.readframes(f.getnframes()),dtype='<i2').astype(np.float64)/32768
    return data

def piano(sample,midi,seconds):
    step=2**((midi-57)/12)
    positions=np.arange(0,min(len(sample)-1,seconds*RATE*step),step)
    note=np.interp(positions,np.arange(len(sample)),sample)
    # A felt attack and natural decay; low-pass only removes the hard hammer edge.
    note=np.convolve(note,np.ones(7)/7,mode='same')
    fade=min(len(note),int(.12*RATE))
    note[:min(len(note),180)]*=np.linspace(0,1,min(len(note),180))
    note[-fade:]*=np.linspace(1,0,fade)
    return note

def render(sample,machine):
    bar=BAR/.85 if machine else BAR
    length=int((36*bar+5)*RATE)
    track=np.zeros((length,2))
    def add(midi,start,duration,gain,pan):
        if midi is None:return
        note=piano(sample,midi,duration)
        if machine:
            note=np.round(note*160)/160
            note*=np.exp(-np.arange(len(note))/RATE*.6)
        at=int(start*RATE)
        n=min(len(note),length-at)
        if n<=0:return
        track[at:at+n,0]+=note[:n]*gain*(1-pan)*1.4
        track[at:at+n,1]+=note[:n]*gain*pan*1.4
    for section in range(3):
        for bar_index,chord in enumerate(PROGRESSION):
            start=(section*12+bar_index)*bar
            intensity=(.68,.92,.58)[section]
            # Open voicings arrive softly out of unison, like two hands at one piano.
            for voice,midi in enumerate(chord):
                if machine and voice==2:continue
                add(midi,start+voice*.045,bar*1.8,.14*intensity,.3+voice*.13)
            tune=MELODY[bar_index]
            for j,midi in enumerate(tune):
                if machine and (bar_index+j)%4==3:continue
                offset=(.75+j*1.4)*(bar/3)
                add(midi,start+offset,bar*1.05,.19*intensity,.57)
            if section==1 and not machine and bar_index in (2,5,8):
                add(chord[-1]+12,start+bar*.82,bar,.065,.35)
    dry=track.copy()
    # A room with a long memory. Reconstruction is almost entirely dry.
    for delay,gain in ((.19,.17),(.37,.10),(.61,.065),(1.13,.035)):
        n=int(delay*RATE)
        track[n:]+=dry[:-n,::-1]*gain*(.18 if machine else 1)
    # Breathing boundaries avoid audible seams if a slow reader exceeds the movement.
    n=int(2*RATE)
    track[:n]*=np.linspace(0,1,n)[:,None]
    track[-n:]*=np.linspace(1,0,n)[:,None]
    peak=np.max(np.abs(track))
    if peak>.72:track*=.72/peak
    return np.clip(track,-1,1)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        folder=Path(td)
        sample=load_sample(folder)
        import json
        metadata=OUT/'loop-durations.json'
        durations=json.loads(metadata.read_text()) if metadata.exists() else {}
        for machine,name in ((False,'tuesday'),(True,'reconstruction')):
            track=render(sample,machine)
            overlap=5*RATE
            fade=np.linspace(0,1,overlap)[:,None]
            seam=track[-overlap:]*(1-fade)+track[:overlap]*fade
            track=np.concatenate([seam,track[overlap:-overlap]])
            durations[name]=len(track)/RATE
            filename='reconstruction-loop' if machine else name
            wav=folder/(name+'.wav')
            with wave.open(str(wav),'wb') as f:
                f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
                f.writeframes((track*32767).astype('<i2').tobytes())
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-af','loudnorm=I=-23:TP=-3:LRA=11','-c:a','libvorbis','-q:a','4',str(OUT/(filename+'.ogg'))],check=True)
            print(name,round(len(track)/RATE,1),'seconds')
        import json
        (OUT/'loop-durations.json').write_text(json.dumps(durations))
if __name__=='__main__':
    main()
