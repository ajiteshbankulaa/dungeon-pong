"""Render the sparse morning reprise from the same credited piano sample."""
from pathlib import Path
import json
import subprocess
import tempfile
import wave
import numpy as np
from build_score import OUT, RATE, load_sample, piano

def main():
    with tempfile.TemporaryDirectory() as td:
        sample=load_sample(Path(td))
        track=np.zeros((72*RATE,2))
        events=[
            (0,45,5,.19),(1.2,64,4,.23),(5,60,5,.18),(12,57,5,.20),
            (20,48,5,.17),(21,67,5,.19),(28,64,6,.18),(38,53,7,.18),
            (40,69,6,.21),(48,64,5,.14),(56,60,5,.14),(63,57,7,.15)]
        for start,midi,duration,gain in events:
            note=piano(sample,midi,duration)
            for delay,attenuation in ((0,1),(.29,.16),(.53,.07)):
                at=int((start+delay)*RATE)
                n=min(len(note),len(track)-at)
                track[at:at+n,0]+=note[:n]*gain*attenuation*.9
                track[at:at+n,1]+=note[:n]*gain*attenuation
        overlap=5*RATE
        fade=np.linspace(0,1,overlap)[:,None]
        track=np.concatenate([track[-overlap:]*(1-fade)+track[:overlap]*fade,track[overlap:-overlap]])
        output=Path(td)/'morning.wav'
        with wave.open(str(output),'wb') as f:
            f.setnchannels(2);f.setsampwidth(2);f.setframerate(RATE)
            f.writeframes(np.clip(track*32767,-32768,32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(output),'-af','loudnorm=I=-27:TP=-6:LRA=12',
                        '-c:a','libvorbis','-q:a','4',str(OUT/'morning.ogg')],check=True)
        metadata=OUT/'loop-durations.json'
        durations=json.loads(metadata.read_text()) if metadata.exists() else {}
        durations['morning']=len(track)/RATE
        metadata.write_text(json.dumps(durations))
if __name__=='__main__':
    main()
