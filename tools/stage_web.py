"""Stage the desktop poem for pygbag. Run from the project root before packing."""
from pathlib import Path
import os, shutil, wave
os.environ.update(SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy')
import pygame, matplotlib
root=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(root))
from poem.score import library
out=root/'build'/'itch'/'whatreturns'
out.mkdir(parents=True,exist_ok=True)
shutil.copytree(root/'poem',out/'poem',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(root/'data/poem',out/'data/poem',dirs_exist_ok=True)
assets=out/'assets/poem'
audio=assets/'audio'
audio.mkdir(parents=True,exist_ok=True)
src=root/'assets/poem'
pygame.mixer.pre_init(44100,-16,2,512);pygame.init();pygame.display.set_mode((1,1))
for f in src.glob('*.svg'):
    pygame.image.save(pygame.image.load(str(f)),str(assets/(f.stem+'.png')))
for name in ('artwork','table'):
    p=out/'poem'/(name+'.py');p.write_text(p.read_text(encoding='utf8').replace('.svg','.png'),encoding='utf8')
for pattern in ('*-v3.ogg','*-v4.ogg','loop-durations.json'):
    for f in (src/'audio').glob(pattern):shutil.copy2(f,audio)
for name in ('final-piano.ogg','AUDIO-CREDITS.txt'):shutil.copy2(src/name,assets)
shutil.copy2(root/'LICENSE',out)
fonts=Path(matplotlib.get_data_path())/'fonts'/'ttf'
for name in ('DejaVuSerif.ttf','DejaVuSans.ttf','LICENSE_DEJAVU'):shutil.copy2(fonts/name,assets)
for name,sound in library(44100,2).items():
    if name=='piano':continue
    with wave.open(str(audio/(name+'.wav')),'wb') as w:
        w.setparams((2,2,44100,0,'NONE',''));w.writeframes(sound.get_raw())
p=out/'poem/score.py';s=p.read_text();a=s.index('    rng=');b=s.index("    sounds['piano']",a)
s=s[:a]+"""    sounds={f.stem:pygame.mixer.Sound(str(f)) for f in AUDIO.glob('*.wav')}
"""+s[b:];p.write_text(s)
p=out/'poem/app.py';s=p.read_text(encoding='utf8').replace("pygame.font.SysFont('georgia' if serif else 'segoeui',size)","pygame.font.Font(str(ROOT/'assets/poem'/('DejaVuSerif.ttf' if serif else 'DejaVuSans.ttf')),size)")
p.write_text(s,encoding='utf8')
shutil.copy2(root/'tools/web_main.py',out/'main.py')
pygame.quit()
print(out)
