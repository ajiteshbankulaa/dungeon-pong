"""Playable score. Each passage owns one completion event."""
import json
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
CODA='The next morning I set out one cup.\n\nThe table rocked.\n\nI reached into my coat for Tuesday’s ticket—\n\nand left it under the machine.'
CARD='What Returns'
COIN='I fed the machine a quarter.\nIt gave me back Tuesday.'
W,H=1100,680

def load_progress(path):
    try:
        raw=json.loads(path.read_text())
        return dict(index=max(0,min(14,int(raw['index']))),completed=raw.get('completed') is True,
                    angle=max(-.88,min(.88,float(raw.get('angle',-.48)))))
    except (ValueError,TypeError,KeyError,OSError,AttributeError):
        return dict(index=0,completed=False,angle=-.48)

class Poem:
    def __init__(self,save_path=None):
        self.path=save_path or ROOT/'data/poem-save.json'
        self.progress=load_progress(self.path)
        self.canvas=pygame.Surface((W,H)); self.art=Artwork(); self.score=Score()
        self.fonts={}; self.index=0; self.mode='title'; self.age=self.t=0.
        self.paused=self.muted=self.reduced=False; self.running=True
        self.x=450.;self.walk=0.;self.facing=1;self.stride_weight=0.;self.walking=False
        self.lines='';self.next_mode='';self.back=0.;self.angle=self.progress['angle']
        self.cup=False;self.ticket=False
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
        self.progress.update(index=self.index,angle=self.angle,completed=completed or self.progress['completed'])
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
        self.x=455
        opening=self.passage['opening']
        if self.index==0 and self.progress['completed']:opening='I remember you letting me serve first.'
        if self.loop==2:
            destination='glass'
        elif self.kind in ('fold','diagram'):
            destination='table'
        elif self.room==0:
            destination='cabinet'
        else:
            destination='pong'
        self.poem(opening,destination)
    def finish(self):
        if self.completed:
            return
        self.completed=True
        self.phase='complete'
        self.poem(self.passage['closing'],'resolved')

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
        elif self.index==9:self.mode_to('withdraw')
        elif self.index==14:
            self.x=700;self.cup=self.ticket=False;self.mode_to('coda')
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
        elif self.mode=='hooks':self.x=545;self.mode_to('coin')
        elif self.mode=='coin' and abs(self.x-745)<65:self.poem(COIN,'restart')
        elif self.mode=='restart':self.index=5;self.enter()
        elif self.mode=='cabinet' and abs(self.x-745)<65:self.mode_to('pong')
        elif self.mode=='table' and abs(self.x-470)<60:
            self.x=410;self.mode_to('mend')
        elif self.mode in ('pong','glass'):
            if self.phase=='ready':self.serve()
        elif self.mode=='coda':
            if not self.cup and abs(self.x-470)<60:
                self.cup=True;self.cue('clink');self.poem('The next morning I set out one cup.\n\nThe table rocked.','coda')
            elif self.cup and abs(self.x-745)<60:
                self.ticket=True;self.poem('I reached into my coat for Tuesday’s ticket—\n\nand left it under the machine.','final')
        elif self.mode=='ending':self.mode_to('title')
    def serve(self):
        if self.phase!='ready' or self.balls:return
        self.phase='playing'
        self.feedback=''
        a=shot_angle(self.py) if self.kind in ('angle','measure','offer','footprint','fold','diagram') else 0
        if self.kind=='measure' and abs(a-self.angle)>.16:
            self.attempts+=1
            if abs(a-self.angle)>min(.75,.16+.07*self.attempts):
                self.phase='ready';self.feedback='Bring the white line onto the recorded line.';return
        self.launched_angle=a
        self.machine_target=345.
        self.balls=[dict(x=158.,y=self.py,vx=425*math.cos(a),vy=425*math.sin(a),voice=0,trail=[],banks=0)]
        if self.kind=='voices':
            self.balls[0].update(x=790.,y=275.,vx=-325.)
            self.balls.append(dict(x=320.,y=415.,vx=260.,vy=0.,voice=1,trail=[],banks=0))
            self.cue('note0');self.cue('hollow')
        elif self.loop==2:self.cue('scuff')
    def update(self,dt,move=0,back=False):
        if self.paused:return
        self.t+=dt;self.age+=dt
        if self.mode=='rupture':
            if self.age>=3.5:self.mode_to('hooks')
            return
        if self.mode in ('hooks','title','ending'):return
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
        if self.mode in ('cabinet','table','coin','coda'):
            self.x=max(220,min(860,self.x+move*190*dt))
            if move:self.facing=1 if move>0 else -1
            self.walk+=abs(move)*dt*9
            self.stride_weight+=(abs(move)-self.stride_weight)*min(1,dt*12)
        if self.mode=='withdraw':
            if int(self.age/3)!=int((self.age-dt)/3):self.cue('bus')
            self.back=min(1,max(0,self.back+dt*(1.6 if back else -1)))
            if self.back>=1:self.index=10;self.enter()
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
            self.glass_step(dt)
        else:
            self.court_step(dt)

    def glass_step(self,dt):
        for b in list(self.balls):
            self.advance_ball(b,dt)
            if self.kind=='footprint' and b['x']>=550 and not b.get('through'):
                if abs(b['y']-345)>80:
                    self.retry('The light is in the opening. Aim through it.')
                    return
                b['through']=True
            if b['x']>=982:
                self.dust_trail=list(b['trail'])
                self.crossed=True
                self.balls=[]
                self.wait=0
                self.aftermath(1.5 if self.kind=='wait' else .65)
                return

    def advance_ball(self,b,dt):
        b['trail'].append((b['x'],b['y']));b['trail']=b['trail'][-32:]
        b['x']+=b['vx']*dt;b['y']+=b['vy']*dt
        if b['y']<154 or b['y']>536:
            b['vy']*=-1;b['y']=max(154,min(536,b['y']));b['banks']=b.get('banks',0)+1
    def court_step(self,dt):
        if not self.balls:return
        lead=self.balls[0]
        self.cuff=max(0,1-abs(lead['x']-890)/65) if lead['vx']>0 else 0
        if self.loop==1:
            if lead['vx']>0:
                remaining=max(0,(950-lead['x'])/lead['vx'])
                unfolded=(lead['y']-154+lead['vy']*remaining)%764
                self.machine_target=154+min(unfolded,764-unfolded)
            self.oy+=max(-220*dt,min(220*dt,self.machine_target-self.oy))
        else:
            dest=lead['y'] if self.kind not in ('angle','measure') else 350
            self.oy+=max(-220*dt,min(220*dt,dest-self.oy))
        for b in list(self.balls):
            self.advance_ball(b,dt)
            if self.kind in ('repeat','cross') and self.count>=3 and b['vx']>0 and b['x']>=550:
                b.update(x=550.,vx=0.,vy=0.)
                if self.kind=='repeat':self.cue('bus')
                self.aftermath(.8);return
            if self.kind in ('fold','diagram'):
                if self.table_collision(b):
                    self.cue('thud' if self.loop==0 else 'hollow')
                if b['x']>=920 and b['vx']>0:
                    self.hit_target(b)
                    return
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
                b.update(x=949.,vx=-425.,vy=(self.py+45-b['y'])*.47)
                self.impact=.24;self.cue('hollow' if self.loop==1 else 'note1')
            elif b['vx']<0 and b['x']<=152 and abs(b['y']-self.py)<66:
                self.count+=1;self.impact=.24
                if self.kind=='rally' and self.count==2:self.cue('bus')
                self.cue('hollow' if self.loop==1 else f'note{self.count%4}')
                if self.kind=='serve' and self.count>=3 or self.kind=='rally' and self.count>=8:
                    self.aftermath(.6);return
                angle=(b['y']-self.py)/66*.65
                b.update(x=153.,vx=425*math.cos(angle),vy=425*math.sin(angle))
            elif b['x']<110 or b['x']>990:
                self.retry('Another serve. Your completed exchanges remain.');return


    def hit_target(self,ball):
        if self.kind in ('fold','diagram'):
            valid=abs(ball['y']-self.target_y)<min(90,45+self.attempts*7)
            if not valid:
                self.retry('Use the opening between the two reaches.')
                return
        self.target_count+=1
        self.cue('note2' if self.loop==0 else 'hollow')
        self.balls=[]
        if self.target_count>=2:
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
