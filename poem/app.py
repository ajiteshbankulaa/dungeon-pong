"""Desktop presentation and controls for What Returns."""
import argparse
import math
import os
import random
import tempfile
from pathlib import Path
import pygame
from poem.runtime import Poem as Simulation, ROOT, W, H, STYLE, HOOK, CARD, load_progress
from poem.artwork import PALETTES
from poem.shots import shot_angle, trajectory

class Poem(Simulation):
    def font(self,size,serif=False):
        key=(size,serif)
        if key not in self.fonts:self.fonts[key]=pygame.font.SysFont('georgia' if serif else 'segoeui',size)
        return self.fonts[key]

    def text(self,s,x,y,size=20,color=None,serif=False,center=True):
        for n,line in enumerate(s.split('\n')):
            im=self.font(size,serif).render(line,True,color or PALETTES[self.loop]['ink'])
            self.canvas.blit(im,im.get_rect(**({'midtop':(x,y+n*size*1.5)} if center else {'topleft':(x,y+n*size*1.5)})))

    def glow(self,pos,radius,color,alpha=35):
        surf=pygame.Surface((radius*2,radius*2),pygame.SRCALPHA)
        for r in range(radius,0,-8):
            a=int(alpha*(1-r/radius)**2)
            pygame.draw.circle(surf,(*color,a),(radius,radius),r)
        self.canvas.blit(surf,(pos[0]-radius,pos[1]-radius))

    def glass(self):
        c=self.canvas;self.art.background(c,2,self.t,self.reduced)
        # Reflection and dust are fixed to the glass, independently of the gesture.
        pygame.draw.polygon(c,(240,241,237),[(230,85),(402,85),(690,567),(452,567)])
        rng=random.Random(200)
        for _ in range(380):
            x,y=rng.randrange(100,1000),rng.randrange(130,552)
            c.set_at((x,y),(178,184,181))
        for i in range(9):
            pygame.draw.arc(c,(195+i,199+i,196+i),(216-i*2,299-i*2,54+i*4,88+i*4),.35,3.9)
        self.art.presence(c,265,520,0,self.t,2,65,reduced=self.reduced)
        if self.kind=='footprint':
            pygame.draw.rect(c,(248,248,240),(502,265,100,160))
        pygame.draw.rect(c,(183,187,181),(112,120,890,437),1,border_radius=24)
        pygame.draw.arc(c,(167,173,165),(119,132,867,416),3.4,5.8,1)
        pygame.draw.line(c,(198,199,187),(140,540),(982,540))
        pygame.draw.ellipse(c,(96,106,101),(137,self.py-18,17,36),1)
        if self.phase=='ready' and self.kind in ('offer','footprint'):
            points=trajectory(self.py,shot_angle(self.py))
            pygame.draw.aalines(c,(155,163,157),False,points)
        self.draw_balls()
        if self.crossed and self.wait<.3 and self.dust_trail:
            fade=self.wait/.3
            color=tuple(round(channel*(1-fade)+230*fade) for channel in self.accent)
            pygame.draw.aalines(c,color,False,self.dust_trail)

    def draw_balls(self):
        c=self.canvas
        if self.mode in ('pong','glass') and not self.balls and not self.crossed:
            center=(158,round(self.py))
            pygame.draw.circle(c,PALETTES[self.loop]['court_ink'],center,6)
        for b in self.balls:
            tone=self.accent if self.loop==2 else STYLE['presence_inks'][b['voice']]
            # Short paper-light wake, visually distinct from the continuous aim guide.
            trail=b['trail'][-16:]
            base=PALETTES[self.loop]['court'] if self.loop<2 else PALETTES[2]['sky']
            for j in range(0,len(trail),4):
                strength=(j+1)/max(1,len(trail))*.55
                tint=tuple(round(a+(z-a)*strength) for a,z in zip(base,tone))
                x,y=trail[j]
                pygame.draw.circle(c,tint,(round(x),round(y)),max(1,round(strength*4)))
            x,y=round(b['x']),round(b['y'])
            diamond=[(x,y-6),(x+6,y),(x,y+6),(x-6,y)]
            pygame.draw.polygon(c,tone,diamond,2 if b['voice']==1 else 0)
            pygame.draw.aalines(c,tone,True,diamond)

    def court(self):
        c=self.canvas;p=PALETTES[self.loop]
        self.art.background(c,self.loop,self.t,self.reduced)
        # A translucent, sharply readable playing plane floats in the landscape.
        field=pygame.Surface((W,H),pygame.SRCALPHA)
        pygame.draw.rect(field,(*p['court'],239),(112,145,878,402),border_radius=5)
        pygame.draw.polygon(field,(*p['court'],250),[(112,547),(990,547),(974,556),(128,556)])
        c.blit(field,(0,0))
        pygame.draw.line(c,p['court_accent'],(120,147),(982,147))
        pygame.draw.line(c,p['court_accent'],(120,543),(982,543))
        for y in range(155,536,19):pygame.draw.line(c,p['shade'],(550,y),(550,y+2))
        aiming=self.kind in ('angle','measure','fold','diagram')
        obstacles=self.art.table.colliders(self.table_rect) if self.kind in ('fold','diagram') else ()
        if self.kind in ('fold','diagram'):
            self.art.table.draw(c,self.table_rect,ticket=False,outline=self.loop==1,court=True)
        if aiming:
            height=min(90,42+self.attempts*7)
            if self.kind!='measure':
                pygame.draw.ellipse(c,p['court_accent'],(900,self.target_y-height,38,height*2),2)
                pygame.draw.circle(c,p['court_ink'],(919,round(self.target_y)),3)
                self.text('HERE',919,self.target_y-height-24,13,color=p['court_accent'])
            if self.phase=='ready':
                if self.kind=='measure':
                    recorded=trajectory(345+self.angle*141/.88,self.angle)
                    pygame.draw.aalines(c,STYLE['presence_inks'][1],False,recorded)
                points=trajectory(self.py,shot_angle(self.py),obstacles)
                pygame.draw.aalines(c,p['court_ink'],False,points)
                end=points[-1]
                pygame.draw.circle(c,p['court_ink'],(round(end[0]),round(end[1])),4,1)
        if self.kind=='voices':
            for y,col in zip((275,415),STYLE['presence_inks']):
                pygame.draw.line(c,col,(500,y),(550,y),1)
        pygame.draw.polygon(c,STYLE['presence_inks'][0],[(140,self.py-54),(145,self.py-58),(148,self.py-51),(148,self.py+54),(142,self.py+58),(140,self.py+51)])
        pygame.draw.line(c,(205,229,217),(141,self.py-48),(141,self.py+46))
        cy=self.oy-self.cuff*9
        pygame.draw.polygon(c,STYLE['presence_inks'][1],[(953,cy-54),(958,cy-58),(961,cy-51),(961,cy+54),(955,cy+58),(953,cy+51)])
        for dx in (0,5):
            pygame.draw.line(c,p['sky'],(953,self.oy-self.cuff*9+dx),(960,self.oy-self.cuff*9+dx-3),2)
        self.draw_balls()
    def chamber(self):
        self.art.background(self.canvas,self.loop,self.t,self.reduced)
        if self.loop==2:self.glass()
        elif self.mode=='coin':
            self.canvas.fill((8,11,18))
            self.art.presence(self.canvas,self.x,551,0,self.t,1,facing=self.facing)
            pygame.draw.rect(self.canvas,(102,252,241),(710,363,65,186),1)
        else:self.art.chamber(self)
    def cup_scene(self):
        c=self.canvas;self.art.background(c,2,self.t,self.reduced);ink=self.accent
        rock=math.sin(self.age*3)*2 if self.cup else 0
        self.art.table.draw(c,pygame.Rect(395,447,220,104),tilt=rock)
        pygame.draw.polygon(c,(139,147,148),[(711,550),(711,363),(761,356),(779,395),(779,550)])
        pygame.draw.rect(c,(191,197,190),(720,377,42,56))
        if self.cup:
            pygame.draw.arc(c,ink,(464,431-rock,22,17),0,math.pi,2)
            pygame.draw.ellipse(c,(205,208,194),(455,451-rock,43,4))
        if self.ticket:
            fold=pygame.transform.smoothscale(self.art.table.ticket,(40,13))
            c.blit(fold,(708,541))
        self.art.presence(c,self.x,551,0,self.t,2,facing=self.facing,phase=self.walk,moving=self.stride_weight)
        if self.mode=='coda':
            self.text('Set down the cup' if not self.cup else 'Leave the ticket under the machine',550,150,22,serif=True)
            self.text('← / →   move      E   reach',550,597,16)

    def draw(self):
        c=self.canvas;mode=self.mode;p=PALETTES[self.loop]
        if mode in ('rupture','hooks'):
            c.fill((0,0,0))
            if mode=='rupture':
                pygame.draw.line(c,(204,204,204),(144,self.py-58),(144,self.py+58),5)
                for x in range(550,985,24):pygame.draw.line(c,(63,63,63),(x,147),(x,543))
                for y in range(147,544,24):pygame.draw.line(c,(63,63,63),(550,y),(982,y))
                pygame.draw.circle(c,(204,204,204),(550,345),5)
                self.text('…',550,612,20,(120,120,120))
            else:
                ash=(204,204,204)
                pygame.draw.line(c,(86,86,86),(420,385),(680,385),2)
                for x in (480,620):
                    pygame.draw.lines(c,ash,False,[(x-4,384),(x,379),(x,368)],2)
                pygame.draw.polygon(c,(102,102,102),[(480,381),(505,396),(516,438),(506,441),(499,421),(501,481),(457,481),(462,421),(454,445),(444,440),(456,396)])
                self.text(HOOK,550,175,25,ash,True)
                self.text('ENTER   /   continue',550,612,14,ash)
        elif mode=='title':
            self.art.background(c,0,self.t,self.reduced)
            self.text('What Returns',550,268,54,serif=True)
            self.text('ENTER   begin       C   continue',550,433,17)
            self.text('A game poem about grief.',550,531,16)
        elif mode in ('coda','ending','final') or mode=='text' and self.next_mode in ('final','coda'):
            self.cup_scene()
            if mode=='ending':
                self.text(CARD,550,166,36,serif=True)
                self.text('ENTER   /   play again',550,600,15)
        elif mode=='withdraw':
            self.glass()
            factor=1-self.back if not self.reduced else float(self.back<.95)
            if factor>0:
                frame=pygame.Surface((860,390));frame.fill((8,11,18))
                phase=(self.age%3)/1.5
                travel=1-abs(phase-1)
                pygame.draw.line(frame,(90,160,155),(24,135),(24,240),6)
                pygame.draw.line(frame,(90,160,155),(835,135),(835,240),6)
                pygame.draw.circle(frame,(102,252,241),(round(30+800*travel),195),5)
                shrunk=pygame.transform.smoothscale(frame,(max(1,int(860*factor)),max(1,int(390*factor))))
                c.blit(shrunk,shrunk.get_rect(center=(550,345)))
            self.text('Hold ↓ or S to pull away',550,592,17,(74,78,77))
        elif mode in ('pong','glass') or mode=='text' and self.next_mode=='resolved':
            if self.loop==2:
                self.glass()
            elif mode=='text' and self.kind in ('serve','rally') and self.next_mode=='resolved':
                self.chamber()
                # Close sleeves in the lived scene, the same gesture separated in replay.
                shade=pygame.Surface((W,H),pygame.SRCALPHA)
                shade.fill((*p['sky'],170))
                c.blit(shade,(0,0))
                self.art.presence(c,495,551,0,self.t,self.loop,reach=.8,lean=.2)
                self.art.presence(c,548 if self.loop==0 else 690,551,1,self.t,self.loop,facing=-1,reach=.8,lean=.2)
            else:
                self.court()
            if mode in ('pong','glass'):
                self.instructions()
        else:
            self.chamber()
            if mode in ('table','coin','cabinet'):
                verb={'table':'Meet them halfway','coin':'Feed the quarter','cabinet':'Approach the cabinet'}[mode]
                self.text(verb+'     ·     ← / → move     E interact',550,594,16)
        if mode=='mend':
            self.text('Your hand. Their hand.',550,592,16)
        if mode=='text':
            # Keep the centered ball visible across the last Tuesday fragment.
            y=83 if self.next_mode=='resolved' and self.kind=='cross' else 194
            if y!=83:
                veil=pygame.Surface((W,H),pygame.SRCALPHA);veil.fill((*p['sky'],235));c.blit(veil,(0,0))
            self.text(self.lines,550,y,24,serif=self.loop!=1)
            self.text('ENTER   /   continue',550,612,14)
        if mode not in ('title','hooks','rupture','ending'):
            self.text(f'{self.loop+1:02}  /  {self.passage["name"]}',70,38,14,self.accent,center=False)
        if self.paused:
            c.fill(p['sky']);self.text('Paused',550,220,34,serif=True)
            self.text('Esc  resume    M  mute    R  reduce motion\nQ  save and quit',550,345,17)
        display=pygame.display.get_surface();w,h=display.get_size()
        scale=min(w/W,h/H)
        out=pygame.transform.smoothscale(c,(max(1,int(W*scale)),max(1,int(H*scale))))
        display.fill((0,0,0));display.blit(out,out.get_rect(center=(w//2,h//2)))

    def event(self,e):
        if e.type==pygame.QUIT:self.running=False;return
        if self.mode=='rupture' and self.age<3.5:return
        if e.type==pygame.WINDOWFOCUSLOST:self.paused=True;self.score.stop();return
        if e.type==pygame.JOYBUTTONDOWN and e.button==0:self.advance_text_or_act();return
        if e.type!=pygame.KEYDOWN or getattr(e,'repeat',False):return
        if e.key==pygame.K_ESCAPE:
            self.paused=not self.paused
            if self.paused:self.score.stop()
            elif self.mode not in ('hooks','coin','title'):self.score.enter(self.loop,self.muted)
        elif e.key==pygame.K_m:
            self.muted=not self.muted
            if self.muted:self.score.stop()
            elif not self.paused and self.mode not in ('hooks','coin','title'):self.score.enter(self.loop,False)
        elif e.key==pygame.K_f:
            self.score.flyback=not self.score.flyback
            if self.loop==1 and not self.paused:self.score.enter(1,self.muted)
        elif e.key==pygame.K_r:self.reduced=not self.reduced
        elif self.paused and e.key==pygame.K_q:self.running=False
        elif self.mode=='title' and e.key==pygame.K_c:self.begin(True)
        elif e.key==pygame.K_SPACE and self.mode in ('pong','glass'):
            self.action()
        elif e.key==pygame.K_e and self.mode in ('cabinet','table','coin','coda'):
            self.action()
        elif e.key==pygame.K_RETURN and self.mode in ('title','text','hooks','ending'):
            self.action()

    def advance_text_or_act(self):
        self.action()

    def instructions(self):
        targets=self.target_count
        objectives={
            'serve':('Find their rhythm',f'{min(self.count,3)} / 3 shared returns'),
            'angle':('Angle a shot into the ring',f'{targets} / 2 openings'),
            'fold':('Send the ball between the two reaches',f'{targets} / 2 openings'),
            'diagram':('The same space. The same return.',f'{targets} / 2 openings'),
            'measure':('Match your remembered shot',f'{targets} / 2 traces'),
            'rally':('Stay for another exchange',f'{min(self.count,8)} / 8 returns'),
            'cross':('One last rally',f'{min(self.count,3)} / 3 returns'),
            'repeat':('The machine repeats your evening',f'{min(self.count,3)} / 3 returns'),
            'voices':('Catch blue-green. Let periwinkle pass.','Two tones · one answer'),
            'trace':('Send it to the empty side',''),
            'offer':('Aim where their hand would be',''),
            'footprint':('Send a shot through the pale opening',''),
            'wait':('Send it. Stay for an answer.',''),
            'last':('One more?',''),
        }
        title,progress=objectives[self.kind]
        self.text(title,550,93,19,color=self.accent)
        if progress:self.text(progress,550,122,14,color=self.accent)
        if self.phase=='ready':
            self.text('↑ / ↓   move and aim     SPACE   serve',550,584,16)
        elif self.phase=='waiting':
            self.text('…',550,584,24)
        elif self.mode=='pong':
            self.text('↑ / ↓   return the ball',550,584,14)
        if self.feedback:
            self.text(self.feedback,550,620,14,color=self.accent)


def read_axes(keys,pads):
    vertical=int(keys[pygame.K_DOWN] or keys[pygame.K_s])-int(keys[pygame.K_UP] or keys[pygame.K_w])
    horizontal=int(keys[pygame.K_RIGHT] or keys[pygame.K_d])-int(keys[pygame.K_LEFT] or keys[pygame.K_a])
    if pads and pads[0].get_numaxes()>=2:
        x,y=pads[0].get_axis(0),pads[0].get_axis(1)
        if abs(x)>.2:horizontal=x
        if abs(y)>.2:vertical=y
    return horizontal,vertical

def run(smoke=False,screenshots=None):
    if smoke:
        os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
    pygame.mixer.pre_init(44100,-16,2,512);pygame.init()
    pygame.display.set_mode((W,H),pygame.RESIZABLE);pygame.display.set_caption('What Returns')
    with tempfile.TemporaryDirectory() as tmp:
        g=Poem(Path(tmp)/'save.json' if smoke else None)
        if smoke:
            dest=Path(screenshots or ROOT/'artifacts/poem-preview');dest.mkdir(parents=True,exist_ok=True)
            for i in range(15):
                g.index=i;g.enter();g.mode_to('glass' if g.loop==2 else 'pong');g.serve()
                for _ in range(90):g.update(1/120)
                g.draw();pygame.image.save(g.canvas,str(dest/f'room-{i:02}.png'))
            for mode,i in [('title',0),('cabinet',0),('rupture',4),('hooks',4),('coda',14),('ending',14)]:
                g.index=i;g.mode_to(mode);g.draw();pygame.image.save(g.canvas,str(dest/f'{mode}.png'))
            print('Rendered 15 passages and six scene compositions.')
        else:
            clock=pygame.time.Clock();acc=0.
            pads=[pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            while g.running:
                acc+=min(.1,clock.tick(60)/1000)
                for e in pygame.event.get():g.event(e)
                h,v=read_axes(pygame.key.get_pressed(),pads)
                while acc>=1/120:
                    g.update(1/120,v if g.mode in ('pong','glass') else h,v>.45);acc-=1/120
                g.draw();pygame.display.flip()
            if g.mode!='title':g.save()
    pygame.quit()
