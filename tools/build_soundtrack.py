"""Three distinct movements: shared piano, mechanical ostinato, open morning."""
from pathlib import Path
import json,subprocess,tempfile,wave
import numpy as np
from build_score import RATE,OUT,load_sample,piano,render

def add(track,sample,start,midi,duration,gain,pan=.5,plucked=False):
    note=piano(sample,midi,duration)
    if plucked:
        note*=np.exp(-np.arange(len(note))/RATE*7)
    at=int(start*RATE)
    n=min(len(note),len(track)-at)
    track[at:at+n,0]+=note[:n]*gain*(1-pan)*1.5
    track[at:at+n,1]+=note[:n]*gain*pan*1.5

def compose(sample,act):
    if act==0:
        return render(sample,False)
    seconds=101 if act==1 else 92
    track=np.zeros((seconds*RATE,2))
    if act==1:
        motif=[69,72,76,72,71,64,69,72]
        for bar in range(32):
            root=[45,41,48,43][(bar//4)%4]
            for step in range(6):
                if (bar+step)%9==0:continue
                start=bar*3+step*.5
                note=motif[(bar*2+step)%len(motif)]
                add(track,sample,start,note,.8,.18,.3 if step%2 else .7,True)
            add(track,sample,bar*3,root,2.7,.15)
        return track
    # A slower, spacious reply to the opening, with different harmony and register.
    chords=[[48,55,62,64],[41,48,57,64],[38,45,53,60],[43,50,57,62]]
    for bar in range(14):
        start=bar*6
        chord=chords[(bar//2)%4]
        for voice,note in enumerate(chord):
            add(track,sample,start+voice*.18,note,7,.14)
        if bar%2==0:
            for offset,note in zip((2.5,4.2),(76,72) if bar<7 else (74,69)):
                add(track,sample,start+offset,note,5,.20,.58)
    dry=track.copy()
    for delay,gain in ((.27,.15),(.67,.08),(1.3,.04)):
        n=int(delay*RATE)
        track[n:]+=dry[:-n,::-1]*gain
    return track

def main():
    OUT.mkdir(exist_ok=True)
    durations={}
    with tempfile.TemporaryDirectory() as td:
        sample=load_sample(Path(td))
        # Suppress the original recording's low-level room floor smoothly.
        envelope=np.convolve(np.abs(sample),np.ones(240)/240,mode='same')
        sample*=np.clip(envelope/.0007,0,1)**2
        for act,name in enumerate(('tuesday','reconstruction','morning')):
            track=compose(sample,act)
            n=5*RATE;fade=np.linspace(0,1,n)[:,None]
            track=np.concatenate([track[-n:]*(1-fade)+track[:n]*fade,track[n:-n]])
            durations[name]=len(track)/RATE
            wav=Path(td)/(name+'.wav')
            with wave.open(str(wav),'wb') as f:
                f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
                f.writeframes(np.clip(track*32767,-32768,32767).astype('<i2').tobytes())
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-af',
                            'loudnorm=I=-25:TP=-4:LRA=12','-ar','24000','-c:a','libvorbis','-q:a','4',str(OUT/(name+'-v3.ogg'))],check=True)
            print(name,durations[name])
    (OUT/'loop-durations.json').write_text(json.dumps(durations))
if __name__=='__main__':main()
