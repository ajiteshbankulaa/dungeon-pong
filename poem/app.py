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

    def loss_scene(self,after):
        c=self.canvas
        self.art.background(c,1,self.t,True)
        darkness=pygame.Surface((W,H),pygame.SRCALPHA)
        darkness.fill((12,20,29,165))
        c.blit(darkness,(0,0))
        if not after:
            # A side-on street, with a stable curb and recognizable crossing.
            # No room/window layer: this is a different place, not a road indoors.
            c.fill((19,25,34))
            pygame.draw.rect(c,(30,37,47),(0,305,W,144))
            for x,width,height in ((85,150,170),(260,210,110),(725,170,155),(920,180,195)):
                pygame.draw.rect(c,(26,33,43),(x,449-height,width,height))
            pygame.draw.rect(c,(49,57,65),(0,449,W,49))
            pygame.draw.line(c,(133,142,144),(0,498),(W,498),3)
            pygame.draw.rect(c,(27,34,43),(0,501,W,179))
            for x in range(410,800,70):
                pygame.draw.polygon(c,(99,106,108),[(x,523),(x+39,523),(x+12,648),(x-32,648)])
            # The same two inks establish whose ordinary walk this is.
            self.art.presence(c,365,490,0,0,0,reduced=True,scale=.52,facing=1)
            self.art.presence(c,438,490,1,0,0,reduced=True,scale=.52,facing=1)
            pygame.draw.line(c,(98,108,110),(240,258),(240,449),4)
            pygame.draw.line(c,(98,108,110),(240,258),(301,258),4)
            pygame.draw.ellipse(c,(228,211,167),(287,254,31,8))
            # One vehicle passes in the foreground. Its form remains readable;
            # the scene cuts before any collision could be shown.
            u=max(0,min(1,(self.age-.65)/2.6))
            x=round(1180-610*u)
            light=pygame.Surface((W,H),pygame.SRCALPHA)
            pygame.draw.polygon(light,(238,224,187,32),[(x-7,557),(x-7,580),(x-360,617),(x-360,514)])
            c.blit(light,(0,0))
            if u>.65:
                pygame.draw.line(c,(227,220,183),(444,438),(449,434),3)
            pygame.draw.polygon(c,(65,75,86),[(x,586),(x,553),(x+43,542),(x+79,510),(x+169,510),(x+208,544),(x+238,553),(x+238,586)])
            pygame.draw.polygon(c,(136,153,159),[(x+61,542),(x+87,519),(x+123,519),(x+123,542)])
            pygame.draw.polygon(c,(109,127,138),[(x+133,519),(x+163,519),(x+189,542),(x+133,542)])
            for wheel in (x+49,x+190):
                pygame.draw.circle(c,(15,21,29),(wheel,585),20)
                pygame.draw.circle(c,(82,91,101),(wheel,585),9)
            pygame.draw.rect(c,(243,232,196),(x,554,10,13),border_radius=2)
            pygame.draw.rect(c,(158,96,91),(x+228,555,9,10),border_radius=2)
            self.text('That winter, at the curb,\nyour cuff caught the light.',550,155,25,(236,229,211),True)
        else:
            ink=(202,203,193)
            pygame.draw.line(c,(103,113,122),(408,351),(702,351),3)
            for x in (477,545):
                pygame.draw.lines(c,ink,False,[(x-10,355),(x,365),(x+10,355)],2)
            coat=[(477,363),(500,383),(516,441),(505,446),(493,416),(498,513),(454,513),(459,416),(447,446),(435,441),(452,383)]
            swing=0 if self.reduced else .35*math.sin(self.age*3)*math.exp(-self.age*.7)
            pygame.draw.polygon(c,(91,137,148),[(round(x+(y-363)*swing),y) for x,y in coat])
            self.poem_panel('I hung mine up.\nIt swung into the space yours left.',157,1)

    def poem_panel(self,content,y,loop=None,advance=True):
        loop=self.loop if loop is None else loop
        tone=PALETTES[loop]['ink']
        font=self.font(24,True)
        lines=content.split('\n')
        width=min(960,max(font.size(line)[0] for line in lines)+70)
        panel=pygame.Surface((width,int(len(lines)*36+58)),pygame.SRCALPHA)
        panel.fill((*((30,35,40) if loop<2 else (224,227,218)),225))
        self.canvas.blit(panel,(550-width/2,y-16))
        self.text(content,550,y,24,tone,True)
        if advance:
            cue=self.font(13).render('Enter to continue',True,tone)
            self.canvas.blit(cue,(550+width/2-cue.get_width()-16,y+len(lines)*36+6))

    def glass(self):
        c=self.canvas
        self.art.background(c,2,self.t,self.reduced)
        # Same machine, seen close enough that the frame identifies the surface.
        pygame.draw.rect(c,(100,115,117),(101,137,899,419),border_radius=16)
        pygame.draw.rect(c,(52,66,69),(112,145,878,402),border_radius=9)
        pygame.draw.rect(c,(48,59,62),(120,153,862,384),border_radius=5)
        pygame.draw.polygon(c,(70,81,82),[(120,153),(365,153),(679,537),(458,537)])
        pygame.draw.polygon(c,(151,166,164),[(101,558),(1000,558),(1032,594),(74,594)])
        pygame.draw.circle(c,(148,119,115),(880,579),9)
        pygame.draw.line(c,(77,94,97),(237,578),(233,558),4)
        pygame.draw.circle(c,(98,117,122),(233,555),7)
        self.art.presence(c,250,532,0,self.t,2,48,reduced=True)
        if len(self.dust_trail)>1:
            pygame.draw.lines(c,(132,149,145),False,self.dust_trail,5)
            pygame.draw.aalines(c,(186,193,179),False,self.dust_trail)
        point=(self.finger_x,self.py) if self.phase in ('playing','ready') else (150,self.py)
        x,y=round(point[0]),round(point[1])
        # A tapered wrist and bent thumb make contact legible at this scale.
        pygame.draw.polygon(c,(96,135,145),[(x-8,y+91),(x+29,y+91),(x+28,y+66),(x+43,y+42),(x+41,y+27),(x+31,y+23),(x+27,y+33),(x+21,y+18),(x+11,y+16),(x+7,y+24),(x-7,y+23),(x-16,y+40),(x-10,y+65)])
        pygame.draw.lines(c,(146,178,182),False,[(x+29,y+52),(x+31,y+34),(x+37,y+30)],2)
        pygame.draw.line(c,(160,193,196),(x+2,y+38),(x,y+4),14)
        pygame.draw.circle(c,(177,204,202),(x,y+3),7)
        if self.touching:pygame.draw.circle(c,(218,221,204),(x,y),10,1)

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
        if self.kind in ('rally','repeat') and self.phase!='ready':
            # Light belongs to the window outside the court.
            progress=min(1,self.elapsed/5)
            pygame.draw.rect(c,(161,147,115),(238+int(146*progress),152,15,42))
        # A translucent, sharply readable playing plane floats in the landscape.
        field=pygame.Surface((W,H),pygame.SRCALPHA)
        pygame.draw.rect(field,(*p['court'],239),(112,145,878,402),border_radius=5)
        pygame.draw.polygon(field,(*p['court'],250),[(112,547),(990,547),(974,556),(128,556)])
        c.blit(field,(0,0))
        pygame.draw.line(c,p['court_accent'],(120,147),(982,147))
        pygame.draw.line(c,p['court_accent'],(120,543),(982,543))
        for y in range(155,536,19):pygame.draw.line(c,p['shade'],(550,y),(550,y+2))
        aiming=self.kind in ('angle','measure','fold','diagram')
        obstacles=()
        if self.kind in ('fold','diagram'):
            band=pygame.Surface((W,H),pygame.SRCALPHA)
            pygame.draw.rect(band,(*STYLE['presence_inks'][1],26),(904,279,66,132),border_radius=10)
            c.blit(band,(0,0))
            self.text('their reach',928,252,13,color=p['court_accent'])
        if aiming:
            height=min(90,42+self.attempts*7)
            if self.kind=='angle':
                pygame.draw.ellipse(c,p['court_accent'],(900,self.target_y-height,38,height*2),2)
                pygame.draw.circle(c,p['court_ink'],(919,round(self.target_y)),3)
                self.text('that corner',919,self.target_y-height-24,13,color=p['court_accent'])
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
    def chamber(self,actors=True):
        self.art.background(self.canvas,self.loop,self.t,self.reduced)
        if self.loop==2:self.glass()
        elif self.mode=='coin':
            self.art.background(self.canvas,1,self.t,True)
            self.art.cabinet(self.canvas,(690,340,110,211),1)
            self.art.presence(self.canvas,self.x,551,0,self.t,1,facing=self.facing)
        else:self.art.chamber(self,actors=actors)
    def cup_scene(self):
        c=self.canvas;self.art.background(c,2,self.t,self.reduced);ink=self.accent
        self.art.table.draw(c,pygame.Rect(395,447,220,104),tilt=0)
        self.art.cabinet(c,(690,340,110,211),2)
        # The old cup ring stays: caring for oneself does not erase the other.
        pygame.draw.ellipse(c,(128,145,137),(520,453,30,5),1)
        if self.cup and not self.cup_held:
            self.art.cup(c,(455,426,40,30))
        reaching=self.cup_held or (self.kind=='place_cup' and self.cup)
        self.art.presence(c,self.x,551,0,self.t,2,facing=self.facing,phase=self.walk,moving=self.stride_weight,reach=.75 if self.cup_held else 0)
        if reaching and not self.cup_held:
            phase=min(1,max(0,(self.age-.7)/.7)) if self.mode=='setting_cup' else max(0,1-self.age)
            reach=math.sin(phase*math.pi/2)
            pygame.draw.lines(c,(157,195,199),False,[(self.x+7,469),(self.x+28,452-22*reach),(self.x+40+18*reach,450-45*reach)],5)
        if self.mode in ('place_cup','setting_cup') and not self.cup:
            u=min(1,self.age/.7) if self.mode=='setting_cup' else 0
            hand_x=self.x+12
            self.art.cup(c,(round(hand_x+(455-hand_x)*u),round(447-21*u),29+round(11*u),23+round(7*u)))
        if self.cup_held:
            offset=23 if self.facing>0 else -52
            self.art.cup(c,(round(self.x+offset),445,29,23))
        if self.mode in ('coda','place_cup'):
            self.text('Set down one cup' if not self.cup else 'Pick up your cup',550,150,22,serif=True)

    def draw(self):
        c=self.canvas;mode=self.mode;p=PALETTES[self.loop]
        if mode in ('rupture','hooks'):
            self.loss_scene(mode=='hooks')
        elif mode=='title':
            self.art.background(c,0,self.t,self.reduced)
            self.text('What Returns',550,268,54,serif=True)
            if self.progress['index']>0:self.text('C  ·  continue saved poem',550,494,16)
            self.draw_button('Start',pygame.Rect(450,427,200,48))
            
        elif mode in ('place_cup','setting_cup','return_glass','coda','ending','final') or mode=='text' and self.kind=='place_cup' or mode=='text' and self.next_mode in ('final','coda'):
            self.cup_scene()
            if mode=='ending':
                self.text(CARD,550,166,36,serif=True)
                
        elif mode=='withdraw':
            self.chamber()
            self.text('E  replay the point     ← / S  step away.',550,592,18)
        elif mode=='dawn':
            old=pygame.Surface((W,H))
            self.art.background(old,1,self.t,True)
            self.art.background(c,2,self.t,True)
            old.set_alpha(round(255*(1-min(1,self.age/3))))
            c.blit(old,(0,0))
            self.art.cabinet(c,(690,340,110,211),2)
            self.art.presence(c,455,551,0,self.t,2)
        elif mode in ('pong','glass') or mode=='text' and self.next_mode=='resolved':
            if self.loop==2:
                self.glass()
            elif mode=='text' and self.kind in ('serve','rally') and self.next_mode=='resolved':
                self.chamber(actors=False)
                # Close sleeves in the lived scene, the same gesture separated in replay.
                self.art.presence(c,495,551,0,self.t,self.loop,reach=.8,lean=.2)
                if self.loop==0:self.art.presence(c,548,551,1,self.t,self.loop,facing=-1,reach=.8,lean=.2)
            else:
                self.court()
            if mode in ('pong','glass'):
                self.instructions()
        else:
            self.chamber()
            if mode in ('table','coin','cabinet'):
                self.object_prompt()
        if mode in ('place_cup','return_glass','coda'):self.object_prompt()
        if mode=='text':
            self.poem_panel(self.lines,174)
        if mode not in ('title','hooks','rupture','ending'):
            self.text(f'{self.loop+1:02}  /  {self.passage["name"]}',70,38,14,self.accent,center=False)
        if self.paused:
            veil=pygame.Surface((W,H),pygame.SRCALPHA);veil.fill((20,27,32,225));c.blit(veil,(0,0))
            self.text('Paused',550,235,34,(236,231,213),True)
            self.draw_button('Resume',pygame.Rect(450,335,200,48))
        display=pygame.display.get_surface();w,h=display.get_size()
        scale=min(w/W,h/H)
        out=pygame.transform.smoothscale(c,(max(1,int(W*scale)),max(1,int(H*scale))))
        display.fill((0,0,0));display.blit(out,out.get_rect(center=(w//2,h//2)))

    def object_prompt(self):
        if self.mode=='return_glass':
            target=745
            label='touch the glass'
        elif self.mode in ('coda','place_cup'):
            target=470
            label='place the cup' if not self.cup else 'pick up your cup'
        else:
            target=470 if self.mode=='table' else 745
            label={'table':'meet their hand','coin':'insert a quarter','cabinet':'play at the arcade machine'}[self.mode]
        near=abs(self.x-target)<65
        tone=PALETTES[self.loop]['ink']
        anchor_y=337 if target==470 else 321
        self.text(('E  ·  '+label) if near else ('←  ' if self.x>target else '→  ')+label,target,anchor_y,16,color=tone)
        pygame.draw.circle(self.canvas,tone,(target,anchor_y+29),3)
        

    def draw_button(self,label,rect):
        tone=(236,231,213) if self.paused else PALETTES[self.loop]['ink']
        pygame.draw.line(self.canvas,tone,rect.bottomleft,rect.bottomright,1)
        self.text(label,rect.centerx,rect.y,24,color=tone,serif=True)

    def event(self,e):
        if e.type==pygame.KEYUP and e.key==pygame.K_SPACE and self.mode=='glass':
            self.lift_finger()
            return
        if e.type==pygame.JOYBUTTONUP and e.button==0 and self.mode=='glass':
            self.lift_finger()
            return
        if e.type==pygame.JOYBUTTONDOWN:
            if e.button==7:
                self.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_ESCAPE))
                return
            if e.button==1 and self.mode=='glass' and self.kind=='last':
                self.finish()
                return
            if e.button==0 and self.paused:
                self.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
                return
        if e.type==pygame.QUIT:self.running=False;return
        if e.type==pygame.MOUSEBUTTONDOWN and e.button==1 and (self.mode=='title' or self.paused):
            display=pygame.display.get_surface()
            scale=min(display.get_width()/W,display.get_height()/H)
            x=(e.pos[0]-(display.get_width()-W*scale)/2)/scale
            y=(e.pos[1]-(display.get_height()-H*scale)/2)/scale
            rect=pygame.Rect(450,335 if self.paused else 427,200,48)
            if rect.collidepoint(x,y):
                if self.paused:
                    self.paused=False;self.score.enter(self.loop,self.muted)
                else:self.begin()
            return
        if e.type==pygame.KEYDOWN and self.paused and e.key==pygame.K_RETURN:
            self.paused=False;self.score.enter(self.loop,self.muted);return
        if self.mode=='rupture' and self.age<3.5:return
        if e.type==pygame.WINDOWFOCUSLOST:self.touching=False;self.paused=True;self.score.stop();return
        if e.type==pygame.JOYBUTTONDOWN and e.button==0:self.advance_text_or_act();return
        if e.type!=pygame.KEYDOWN or getattr(e,'repeat',False):return
        if e.key==pygame.K_ESCAPE:
            self.touching=False
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
        elif e.key==pygame.K_e and self.mode=='glass' and self.kind=='last' and self.phase=='ready':
            self.finish()
        elif e.key==pygame.K_e and self.mode in ('cabinet','table','coin','coda','place_cup','return_glass','withdraw'):
            self.action()
        elif e.key==pygame.K_RETURN and self.mode in ('title','text','hooks','ending','morning_room'):
            self.action()

    def advance_text_or_act(self):
        self.action()

    def instructions(self):
        targets=self.target_count
        objectives={
            'serve':('Find their rhythm',f'{min(self.count,3)} / 3 shared returns'),
            'angle':('Aim into the corner.',f'{targets} / 1 corner shot'),
            'fold':('Send it within their reach',''),
            'diagram':('The machine repeats the receiving position.',''),
            'measure':('Repeat the shot from Tuesday',f'{targets} / 1 remembered shot'),
            'rally':('Stay for another exchange',f'{min(self.count,4)} / 4 returns'),
            'cross':('One last rally',f'{min(self.count,3)} / 3 returns'),
            'repeat':('The machine repeats your evening',f'{min(self.count,3)} / 3 returns'),
            'voices':('Catch blue-green. Let purple pass.','Two tones · one answer'),
            'trace':('Draw across the glass',''),
            'offer':('Trace the corner shot',''),
            'footprint':('Send a shot through the pale opening',''),
            'wait':('Draw the return',''),
            'last':('One more?',''),
        }
        title,progress=objectives[self.kind]
        self.text(title,550,93,19,color=self.accent)
        
        if self.loop==2:
            self.text('Arrows move hand · hold SPACE to touch · release to lift · E leave' if self.kind=='last' else 'Arrows move hand · hold SPACE to touch · release at far edge',550,620,16)
        else:
            self.text('↑ / ↓ or W / S move     SPACE serve',550,590,16)
        if self.phase=='waiting':
            self.text('…',550,584,24)
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
                g.index=i;g.enter()
                if i!=12:
                    g.mode_to('glass' if g.loop==2 else 'pong');g.serve()
                for _ in range(90):g.update(1/120,horizontal=1 if g.loop==2 else 0)
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
                    g.update(1/120,v if g.mode in ('pong','glass') else h,v>.45,h);acc-=1/120
                g.draw();pygame.display.flip()
            if g.mode!='title':g.save()
    pygame.quit()

