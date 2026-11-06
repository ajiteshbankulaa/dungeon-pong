"""Playable score. Each passage owns one completion event."""
import json
import os
import sys
import math
from pathlib import Path
import pygame

from poem.artwork import Artwork, PALETTES
from poem.shots import shot_angle, trajectory
from poem.score import Score

ROOT=Path(__file__).resolve().parent.parent
STYLE=json.loads((ROOT/'data/poem/style.json').read_text())
PASSAGES=json.loads((ROOT/'data/poem/text.json').read_text(encoding='utf-8'))
HOOK='Winter. One coat by the door.\n\nThe empty hook beside it, still warm from your thumb.'
CODA='I set out one cup.\nMy hand went back for yours.\nThen I picked up mine.'
CARD='What Returns'
COIN='I fed the machine a quarter.\nIt gave me back Tuesday.'
W,H=1100,680

def load_progress(path):
    try:
        raw=json.loads(path.read_text())
        return dict(index=max(0,min(14,int(raw['index']))),completed=raw.get('completed') is True,
                    angle=max(-.88,min(.88,float(raw.get('angle',-.48)))),memories=raw.get('memories',{}))
    except (ValueError,TypeError,KeyError,OSError,AttributeError):
        return dict(index=0,completed=False,angle=-.48)

class Poem:
    def __init__(self,save_path=None):
        default_save=Path(os.environ.get('LOCALAPPDATA',str(Path.home())))/'WhatReturns'/'save.json' if getattr(sys,'frozen',False) else ROOT/'data/poem-save.json'
        self.path=save_path or default_save
        self.progress=load_progress(self.path)
        self.canvas=pygame.Surface((W,H)); self.art=Artwork(); self.score=Score()
        self.fonts={}; self.index=0; self.mode='title'; self.age=self.t=0.
        self.paused=self.muted=self.reduced=False; self.running=True
        self.x=450.;self.walk=0.;self.facing=1;self.stride_weight=0.;self.walking=False
        self.lines='';self.next_mode='';self.back=0.;self.angle=self.progress['angle']
        self.cup=False;self.cup_held=False
        self.memories={}
        for key,value in (self.progress.get('memories',{}) if isinstance(self.progress.get('memories',{}),dict) else {}).items():
            try:
                samples,returns=value
                if len(samples)>24000:continue
                clean=[(float(y),float(cuff)) for y,cuff in samples]
                speeds=[float(v) for v in returns]
                if all(math.isfinite(v) for sample in clean for v in sample) and all(math.isfinite(v) for v in speeds):
                    self.memories[int(key)]=(clean,speeds)
            except (ValueError,TypeError):
                continue
        self.reset()
    @property
    def loop(self):return self.index//5
    @property
    def room(self):return self.index%5
    @property
    def passage(self):return PASSAGES[self.index]
    @property
    def kind(self):return self.passage['action']
    @property
    def accent(self):return PALETTES[self.loop]['light']
    def reset(self):
        self.py=self.oy=345.;self.balls=[];self.count=0;self.attempts=0
        self.elapsed=self.impact=self.cuff=self.wait=self.back=0.
        self.dust_trail=[]
        self.finger_x=150.
        self.touching=False
        self.replay_time=0.
        self.recording=[]
        self.recorded_returns=[]
        self.return_index=0
        self.leveled=False;self.crossed=False;self.answered=False
        self.phase='ready'
        self.phase_age=0.
        self.feedback=''
        self.completed=False
        self.target_y=230.
        self.target_count=0
        self.machine_target=345.
        self.table_rect=pygame.Rect(470,300,160,132)
    def save(self,completed=False):
        self.progress.update(index=self.index,angle=self.angle,completed=completed or self.progress['completed'],memories=self.memories)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(self.progress));tmp.replace(self.path)
    def mode_to(self,name):
        self.mode=name;self.age=0
    def poem(self,line,following):
        self.lines=line;self.next_mode=following
        self.mode_to('text' if line else following)
    def begin(self,resume=False):
        self.index=self.progress['index'] if resume else 0
        self.enter()
    def enter(self):
        self.reset();self.save();self.score.enter(self.loop,self.muted)
        if self.index==12:self.x=745
        elif self.index==13:self.x=470
        elif self.loop<2:self.x=455
        opening=self.passage['opening']
        if self.index==0 and self.progress['completed']:opening='I remember you letting me serve first.'
        if self.loop==2:
            self.cup=self.index>12
            self.cup_held=False
            destination={12:'place_cup',13:'return_glass'}.get(self.index,'glass')
        elif self.room==0:
            destination='cabinet'
        else:
            destination='pong'
        self.poem(opening,destination)
    def finish(self):
        if self.completed:
            return
        if self.loop==0 and self.recording:
            self.memories[self.room]=(list(self.recording),list(self.recorded_returns))
        self.completed=True
        self.phase='complete'
        if self.passage['closing']:
            self.poem(self.passage['closing'],'resolved')
        else:
            self.resolve()

    def aftermath(self, seconds=.6):
        # A completed shot reveals its poem. Only the unanswered return holds.
        self.feedback=''
        if self.loop==2 and self.kind=='wait':
            self.phase='waiting'
            self.phase_age=0.
            self.aftermath_seconds=1.5
        else:
            self.finish()

    def retry(self, message):
        self.balls=[]
        self.phase='ready'
        self.feedback=message
        self.attempts+=1

    def resolve(self):
        if self.index==4:
            self.score.stop();pygame.event.clear([pygame.KEYDOWN,pygame.JOYBUTTONDOWN])
            self.mode_to('rupture')
        elif self.index==9:
            self.x=745;self.withdraw_start=745.;self.mode_to('withdraw')
        elif self.index==14:
            self.x=745;self.cup=True;self.cup_held=False;self.mode_to('coda')
        else:self.index+=1;self.enter()
    def cue(self,s):self.score.cue(s,self.muted)
    def action(self):
        if self.paused:
            return
        if self.mode=='rupture':
            if self.age>=3.5:
                self.mode_to('hooks')
            return
        if self.mode=='title':self.begin()
        elif self.mode=='text':
            if self.next_mode=='resolved':self.resolve()
            else:self.mode_to(self.next_mode)
        elif self.mode=='return_glass' and abs(self.x-745)<65:
            self.x=745
            self.mode_to('glass')
        elif self.mode=='place_cup' and abs(self.x-470)<65:
            self.mode_to('setting_cup')
        elif self.mode=='hooks':self.x=545;self.mode_to('coin')
        elif self.mode=='coin' and abs(self.x-745)<65:self.poem(COIN,'restart')
        elif self.mode=='restart':self.index=5;self.enter()
        elif self.mode=='cabinet' and abs(self.x-745)<65:self.mode_to('pong')
        elif self.mode=='table' and abs(self.x-470)<60:
            self.x=410;self.mode_to('mend')
        elif self.mode in ('pong','glass'):
            if self.mode=='glass' and self.phase=='playing':self.touching=True
            elif self.phase=='ready':self.serve()
        elif self.mode=='coda':
            if not self.cup and abs(self.x-470)<60:
                self.cup=True;self.cue('clink');self.poem('I set out one cup.\nMy hand went back for yours.','coda')
            elif self.cup and abs(self.x-470)<60:
                self.cup_held=True;self.poem('Then I picked up mine.\nIt was still warm.','final')
        elif self.mode=='withdraw':
            self.index=9;self.enter()
        elif self.mode=='ending':self.mode_to('title')
    def serve(self):
        if self.mode=='glass' and self.phase=='playing':
            self.lift_finger()
            return
        if self.phase!='ready' or self.balls:return
        self.phase='playing'
        self.feedback=''
        a=shot_angle(self.py) if self.kind in ('angle','measure','offer','footprint','fold','diagram') else 0
        if self.loop==2:
            self.touching=True
            self.trace_start=self.py
            self.trace_progress=0.
            if not self.dust_trail:self.dust_trail=[(self.finger_x,self.py)]
            self.cue('scuff')
            return
        if self.kind=='measure' and abs(a-self.angle)>.16:
            self.attempts+=1
            if abs(a-self.angle)>min(.75,.16+.07*self.attempts):
                self.phase='ready';self.feedback='Bring the white line onto the recorded line.';return
        self.replay_time=0.
        self.recording=[]
        self.recorded_returns=[]
        self.return_index=0
        self.launched_angle=a
        self.machine_target=345.
        self.balls=[dict(x=158.,y=self.py,vx=425*math.cos(a),vy=425*math.sin(a),voice=0,trail=[],banks=0)]
        if self.kind=='voices':
            self.balls[0].update(x=790.,y=275.,vx=-325.)
            self.balls.append(dict(x=320.,y=415.,vx=260.,vy=0.,voice=1,trail=[],banks=0))
            self.cue('note0');self.cue('hollow')
        elif self.loop==2:self.cue('scuff')
    def update(self,dt,move=0,back=False,horizontal=0):
        if self.paused:return
        self.t+=dt;self.age+=dt
        if self.mode=='rupture':
            if self.age>=3.5:self.mode_to('hooks')
            return
        if self.mode in ('hooks','title','ending'):return
        if self.mode=='dawn':
            if self.age>=3:self.poem(PASSAGES[10]['opening'],'glass')
            return
        if self.mode=='setting_cup':
            if self.age>=.7 and not self.cup:
                self.cup=True
                self.cue('clink')
            if self.age>=1.7:self.finish()
            return
        if self.mode=='mend':
            if self.age>=2.8:
                self.leveled=True
                self.cue('thud' if self.loop==0 else 'hollow')
                self.mode_to('pong')
            return
        if self.mode=='final':
            self.mode_to('ending');self.cue('piano');self.save(True);return
        if self.mode=='restart':self.index=5;self.enter();return
        if self.mode not in ('coin','restart') and not (self.mode=='text' and self.next_mode=='restart'):
            self.score.tick(dt,self.loop,self.muted)
        if self.mode in ('cabinet','table','coin','coda','place_cup','return_glass'):
            self.x=max(220,min(860,self.x+move*190*dt))
            if move:self.facing=1 if move>0 else -1
            self.walk+=abs(move)*dt*9
            self.stride_weight+=(abs(move)-self.stride_weight)*min(1,dt*12)
        if self.mode=='withdraw':
            retreat=max(0,-move)
            if back:retreat=1
            self.x=max(455,self.x-retreat*145*dt)
            self.facing=-1
            self.walk+=retreat*dt*9
            self.stride_weight+=(retreat-self.stride_weight)*min(1,dt*12)
            self.back=(745-self.x)/290
            if self.score.bank:
                pygame.mixer.music.set_volume(.38*(1-self.back))
            if self.back>=1:
                self.index=10
                self.reset();self.save();self.score.enter(2,self.muted)
                self.mode_to('dawn')
        if self.mode not in ('pong','glass'):return
        self.py=max(204,min(486,self.py+move*STYLE['paddle_speed']*dt))
        self.impact=max(0,self.impact-dt)
        self.elapsed+=dt
        self.phase_age+=dt
        if self.phase=='waiting':
            if self.phase_age>=1.5:self.finish()
            return
        if self.phase!='playing':
            return
        if self.mode=='glass':
            self.glass_step(dt,horizontal)
        else:
            self.court_step(dt)

    def lift_finger(self):
        self.touching=False
        if self.phase!='playing':
            return
        if self.finger_x>=900:
            self.crossed=True
            self.aftermath()
        else:
            self.phase='ready'
            self.feedback='Touch again and carry the line to the far edge.'

    def glass_step(self,dt,horizontal=0):
        if not self.touching:
            return
        self.finger_x=max(150.,min(950.,self.finger_x+horizontal*300*dt))
        point=(self.finger_x,self.py)
        if not self.dust_trail or math.dist(point,self.dust_trail[-1])>1:
            self.dust_trail.append(point)

    def advance_ball(self,b,dt):
        b['trail'].append((b['x'],b['y']));b['trail']=b['trail'][-32:]
        b['x']+=b['vx']*dt;b['y']+=b['vy']*dt
        if b['y']<154 or b['y']>536:
            b['vy']*=-1;b['y']=max(154,min(536,b['y']));b['banks']=b.get('banks',0)+1
    def court_step(self,dt):
        if not self.balls:return
        lead=self.balls[0]
        self.cuff=max(0,1-abs(lead['x']-890)/65) if lead['vx']>0 else 0
        self.replay_time+=dt
        memory=self.memories.get(self.room)
        if self.loop==1:
            if memory and memory[0]:
                samples=memory[0]
                sample=samples[min(len(samples)-1,int(self.replay_time*120))]
                self.oy=sample[0]
                self.cuff=sample[1]
            else:
                self.oy=345.
        elif self.kind=='fold':
            self.oy=345.
        else:
            destination=lead['y'] if self.kind!='angle' else 350
            self.oy+=max(-220*dt,min(220*dt,destination-self.oy))
        if self.loop==0:
            self.recording.append((self.oy,self.cuff))
        for b in list(self.balls):
            self.advance_ball(b,dt)
            if self.kind in ('repeat','cross') and self.count>=3 and b['vx']>0 and b['x']>=550:
                b.update(x=550.,vx=0.,vy=0.)
                if self.kind=='repeat':self.cue('bus')
                self.aftermath(.8);return
            if self.kind in ('angle','measure') and b['vx']>0 and b['x']>=920:
                if self.kind=='measure' or abs(b['y']-self.target_y)<min(90,42+self.attempts*7):
                    if self.kind=='angle':
                        self.angle=self.launched_angle
                    self.hit_target(b)
                    return
                self.retry('The ring is above the shot. Adjust the guide and serve again.' if b['y']>self.target_y else 'The ring is below the shot. Adjust the guide and serve again.')
                return
            if self.kind=='voices':
                if b['voice']==1 and b['x']>=980:self.balls.remove(b);self.crossed=True
                elif b['voice']==0 and b['x']<=150:
                    if abs(b['y']-self.py)<=66:self.answered=True;self.cue('hollow');self.balls.remove(b)
                    else:self.crossed=False;self.answered=False;self.retry('Catch the blue-green tone. Let the other pass.');return
                if self.answered and self.crossed:self.aftermath(.8)
                continue
            if b['vx']>0 and b['x']>=950 and abs(b['y']-self.oy)<66:
                return_y=(self.py+45-b['y'])*.47
                if self.loop==1:
                    returns=self.memories.get(self.room,([],[]))[1]
                    return_y=returns[self.return_index%len(returns)] if returns else 20.
                else:
                    self.recorded_returns.append(return_y)
                self.return_index+=1
                b.update(x=949.,vx=-425.,vy=return_y)
                self.impact=.24;self.cue('hollow' if self.loop==1 else 'note1')
                if self.kind in ('fold','diagram'):
                    self.target_count+=1
                    if self.target_count>=2:
                        self.finish()
                        return
            elif b['vx']<0 and b['x']<=152 and abs(b['y']-self.py)<66:
                self.count+=1;self.impact=.24
                if self.kind=='rally' and self.count==2:self.cue('bus')
                self.cue('hollow' if self.loop==1 else f'note{self.count%4}')
                if self.kind=='serve' and self.count>=3 or self.kind=='rally' and self.count>=4:
                    self.aftermath(.6);return
                angle=(b['y']-self.py)/66*.65
                b.update(x=153.,vx=425*math.cos(angle),vy=425*math.sin(angle))
            elif b['x']<110 or b['x']>990:
                self.retry('Another serve. Aim gently toward their paddle.');return


    def hit_target(self,ball):
        if self.kind in ('fold','diagram'):
            valid=abs(ball['y']-self.target_y)<min(90,45+self.attempts*7)
            if not valid:
                self.retry('Use the opening between the two reaches.')
                return
        self.target_count+=1
        self.cue('note2' if self.loop==0 else 'hollow')
        self.balls=[]
        if self.target_count>=1:
            self.aftermath(.7)
        else:
            self.target_y=440.
            self.phase='ready'
            self.phase_age=0
            self.feedback='One more. The opening has moved.'

    def table_collision(self,ball):
        from poem.table import PaperTable
        from poem.shots import reflect_table
        return reflect_table(ball,PaperTable.colliders(self.table_rect))
