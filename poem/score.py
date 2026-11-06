"""Continuous story score with short, responsive acoustic cues."""
import array
import math
import random
import json
from functools import lru_cache
from pathlib import Path
import pygame

AUDIO=Path(__file__).resolve().parent.parent/'assets/poem/audio'

@lru_cache(maxsize=2)
def library(rate,channels):
    rng=random.Random(74)
    sounds={}
    for name,length in [('room',4),('bus',1.6),('scuff',.35),('thud',.45),('clink',1),('whine',.2),('hollow',.5)]+[(f'note{i}',1.3) for i in range(4)]:
        samples=array.array('h')
        low=0.
        for i in range(int(rate*length)):
            t=i/rate
            noise=rng.uniform(-1,1)
            low=.992*low+.008*noise
            wave=lambda f:math.sin(math.tau*f*t)
            if name=='room':
                value=low*.035
            elif name=='bus':
                value=(wave(77)*.012+wave(113)*.004)*math.sin(math.pi*t/length)**2
            elif name=='scuff':
                value=low*.018*math.exp(-t*18)
            elif name=='thud':
                value=wave(83)*.045*math.exp(-t*15)
            elif name=='clink':
                value=(wave(1480)+wave(2317)*.25)*.025*math.exp(-t*7)
            elif name=='whine':
                value=0.
            elif name=='hollow':
                value=wave(220)*.018*math.exp(-t*9)
            else:
                frequency=(220,261.63,329.63,293.66)[int(name[-1])]
                value=(wave(frequency)+wave(frequency*2)*.14)*.032*math.exp(-t*4)
            envelope=min(1,t/.014,(length-t)/.05)
            samples.extend([int(value*max(0,envelope)*32767)]*channels)
        sounds[name]=pygame.mixer.Sound(buffer=samples)
    sounds['piano']=pygame.mixer.Sound(str(AUDIO.parent/'final-piano.ogg'))
    return sounds

@lru_cache(maxsize=48)
def harmonic_note(midi,rate,channels):
    frequency=440*2**((midi-69)/12)
    samples=array.array('h')
    for i in range(int(rate*.7)):
        t=i/rate
        envelope=min(1,t/.012)*math.exp(-t*7)
        value=(math.sin(math.tau*frequency*t)+.12*math.sin(math.tau*frequency*2*t))
        samples.extend([int(value*envelope*750)]*channels)
    return pygame.mixer.Sound(buffer=samples)

TUESDAY_CHORDS=((45,52,59,60),(41,48,57,64),(48,55,59,64),(43,50,57,59),
                (38,45,53,64),(45,52,59,60),(41,48,57,64),(43,50,57,62),
                (38,45,53,60),(40,47,55,62),(41,48,57,64),(45,52,59,64))

class Score:
    def __init__(self):
        fmt=pygame.mixer.get_init()
        self.bank=library(fmt[0],fmt[2]) if fmt else {}
        self.flyback=False
        self.act=None
        self.playing=False
        self.offset=0.
        self.phrase=0
    def stop(self):
        if not self.bank:return
        if self.playing:
            position=pygame.mixer.music.get_pos()
            if position>=0:self.offset+=position/1000
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        self.playing=False
    def enter(self,act,mute):
        if not self.bank:return
        if act!=self.act:
            self.stop()
            self.act=act
            self.offset=0.
            self.phrase=0
        if mute:return
        pygame.mixer.Channel(0).stop()
        if self.playing:return
        name=('tuesday','reconstruction','morning')[act]
        pygame.mixer.music.load(str(AUDIO/(name+'-v3.ogg')))
        pygame.mixer.music.set_volume((.48,.38,.35)[act])
        duration=json.loads((AUDIO/'loop-durations.json').read_text())[name]
        pygame.mixer.music.play(loops=-1,start=self.offset%duration,fade_ms=900)
        self.playing=True
    def cue(self,name,mute=False):
        if not self.bank or mute:return
        sound=self.bank.get(name)
        if name.startswith('note') and self.act==0:
            seconds=(self.offset+max(0,pygame.mixer.music.get_pos())/1000)%90
            chord=TUESDAY_CHORDS[int(seconds/2.5)%12]
            midi=chord[1+self.phrase%3]+12
            self.phrase+=1
            rate,_,channels=pygame.mixer.get_init()
            sound=harmonic_note(midi,rate,channels)
        elif name.startswith('note'):
            name=f'note{self.phrase%4}'
            self.phrase+=1
            sound=self.bank[name]
        if sound:
            channel=pygame.mixer.find_channel()
            if channel:channel.play(sound)
    def tick(self,dt,act,mute):
        # The recorded movement continues across rooms. Actions add its responses.
        pass
