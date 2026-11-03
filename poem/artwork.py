"""Editable motion artwork: translucent folds, broken circles, architectural traces."""
import math
import pygame
from poem.table import PaperTable

from pathlib import Path
import json
PALETTES = json.loads((Path(__file__).resolve().parent.parent/'data/poem/palettes.json').read_text(encoding='utf-8'))

def mix(a,b,t):return tuple(round(x+(y-x)*t) for x,y in zip(a,b))

class Artwork:
    def __init__(self):
        self.backgrounds={}
        self.table=PaperTable()
        assets = Path(__file__).resolve().parent.parent / 'assets/poem'
        self.torsos = [pygame.image.load(str(assets / f'{name}.svg')) for name in ('person', 'other')]

    def background(self,surface,loop,t,reduced=False,loss=False):
        if loop not in self.backgrounds:
            names=('tuesday','reconstruction','morning')
            asset=Path(__file__).resolve().parent.parent/'assets/poem'/f'landscape-{names[loop]}.svg'
            image=pygame.image.load(str(asset)).convert()
            self.backgrounds[loop]=pygame.transform.smoothscale(image,(1100,680))
        surface.blit(self.backgrounds[loop],(0,0))

    def presence(self,surface,x,y,which,t,loop,opacity=255,moving=False,reduced=False,scale=.72,loss=0,facing=1,phase=0,reach=0,lean=0,crouch=0):
        p=PALETTES[loop]
        # The gait follows distance travelled, so pausing never advances a footstep.
        stride = math.sin(phase)*moving if not reduced else 0
        breath = 0 if reduced else math.sin(t * 1.5 + which * .8)
        body = pygame.Surface((180, 240), pygame.SRCALPHA)
        hip = (90, 153)
        for side in (-1, 1):
            foot_x = 90 + side * (10 + stride * 13)
            lift = max(0, -side * math.cos(phase)) * abs(stride) * 5
            foot = (foot_x, 223 - lift)
            knee = ((hip[0] + foot_x) / 2 + 3 + lift, 187 - lift)
            tone = mix((42,48,70), (142,178,200) if which==0 else (155,150,198), .55 if side < 0 else .82)
            pygame.draw.lines(body, tone, False, [(hip[0]+side*5,153+crouch*28), (knee[0]+crouch*10,knee[1]+crouch*8), foot], 8)
            pygame.draw.line(body, tone, foot, (foot_x+6,foot[1]), 5)
        torso = pygame.transform.rotozoom(self.torsos[which], breath*.35 + stride*1.2+lean*4, 1)
        body.blit(torso, torso.get_rect(midbottom=(90+stride*2,165+breath+crouch*28)))
        if reach:
            tone=(164,217,224) if which==0 else (209,206,245)
            elbow=(120,112-reach*14+crouch*75)
            hand=(126+reach*22,105-reach*7+crouch*100)
            pygame.draw.lines(body,tone,False,[(112,91+crouch*28),elbow,hand],5)
        image = pygame.transform.smoothscale(body,(round(180*scale),round(240*scale)))
        if facing < 0:
            image=pygame.transform.flip(image, True, False)
        image.set_alpha(round(opacity))
        surface.blit(image,image.get_rect(midbottom=(round(x),round(y+17*scale))))
        shadow=pygame.Surface((1100,680),pygame.SRCALPHA)
        pygame.draw.polygon(shadow,(*(30,32,57),int(opacity*.24)),[(x-11,y),(x+11,y),(x-70,y+24),(x-114,y+20)])
        surface.blit(shadow,(0,0))

    def chamber(self,g):
        c=g.canvas;p=PALETTES[g.loop]
        layer=pygame.Surface((1100,680),pygame.SRCALPHA)
        # A small inhabited terrace in a much larger remembered landscape.
        pygame.draw.polygon(c,(52,70,73) if g.loop==0 else (47,45,66),
                            [(180,551),(920,551),(864,584),(230,584)])
        pygame.draw.polygon(c,(35,53,60) if g.loop==0 else (35,34,54),
                            [(230,584),(864,584),(864,598),(230,598)])
        pygame.draw.line(c,p['court_accent'],(180,551),(920,551),1)
        # The doorway frames the same horizon in each act.
        for x in (257,407):
            pygame.draw.line(layer,(*p['ink'],105),(x,242),(x,551),3)
        pygame.draw.line(layer,(*p['ink'],105),(257,242),(407,242),3)
        # Shared folded silhouette, with one visible short support.
        rect=pygame.Rect(395,447,220,104)
        if g.loop<2:
            repairing=g.mode=='mend'
            progress=min(1,g.age/2.8) if repairing else 0
            tilt=0 if g.loop==1 or g.leveled else -1.5*(1-progress)
            self.table.draw(c,rect,tilt,ticket=g.leveled or progress>.6,outline=g.loop==1)
            for i in range(2):
                pygame.draw.arc(c,p['ink'],(464+i*44,433,16,14),0,math.pi,2)
        # Cabinet is a portal, not a literal arcade prop.
        pygame.draw.polygon(layer,(*p['shade'],100),[(710,550),(710,372),(763,365),(785,402),(785,550)])
        pygame.draw.rect(layer,(*p['sky'],240),(720,384,46,50),border_radius=3)
        pygame.draw.line(layer,(*p['light'],170),(722,443),(773,443),2)
        pygame.draw.line(layer,(*p['ink'],170),(760,462),(768,462),2)
        pygame.draw.line(layer,(*p['light'],150),(731,402),(757,402),2)
        if g.loop==1:
            for i in range(7):
                xx=480+i*37
                pygame.draw.line(layer,(*p['shade'],40),(xx,465),(xx+10,489+i*4),1)
        c.blit(layer,(0,0))

        if g.mode not in ('coda','ending'):
            opacity=235 if g.loop==0 else 100 if g.loop==1 else 165
            repairing=g.mode=='mend'
            ox=548 if repairing else 665
            reach=min(1,g.age/.8) if repairing else 0
            self.presence(c,ox,551,1,g.t,g.loop,opacity,reduced=g.reduced,facing=-1,reach=reach,lean=reach*.5)
            # One tenuous thread joins the presences, interrupted in loop 2.
            thread=pygame.Surface((1100,680),pygame.SRCALPHA)
            pts=[(g.x+(665-g.x)*i/40,506+math.sin(i/40*math.pi)*18) for i in range(41)]
            if g.loop==1:pts=pts[:12]
            pygame.draw.aalines(thread,(*p['light'],48),False,pts)
            c.blit(thread,(0,0))
        self.presence(c,495 if g.mode=='mend' else g.x,551,0,g.t,g.loop,moving=g.stride_weight,reduced=g.reduced,facing=g.facing,phase=g.walk,reach=min(1,g.age/.9) if g.mode=='mend' else 0,crouch=0)
