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
        self.objects={}
        assets=Path(__file__).resolve().parent.parent/'assets/poem'
        for name in ('cup','cabinet'):
            self.objects[name]=pygame.image.load(str(assets/(name+'.svg'))).convert_alpha()
        assets = Path(__file__).resolve().parent.parent / 'assets/poem'
        self.torsos = [pygame.image.load(str(assets / f'{name}.svg')) for name in ('person', 'other')]

    def background(self,surface,loop,t,reduced=False,loss=False):
        if loop not in self.backgrounds:
            names=('tuesday','reconstruction','morning')
            asset=Path(__file__).resolve().parent.parent/'assets/poem'/f'landscape-{names[loop]}.svg'
            image=pygame.image.load(str(asset)).convert()
            self.backgrounds[loop]=pygame.transform.smoothscale(image,(1100,680))
        p=PALETTES[loop]
        surface.fill(p['sky'])
        wall=(45,49,53) if loop==0 else (35,39,48) if loop==1 else (224,227,218)
        surface.fill(wall)
        window=pygame.transform.smoothscale(self.backgrounds[loop],(176,238))
        surface.blit(window,(236,152))
        trim=(103,103,94) if loop<2 else (161,173,164)
        pygame.draw.rect(surface,trim,(230,146,188,250),3)
        pygame.draw.line(surface,trim,(324,148),(324,394),3)
        pygame.draw.line(surface,trim,(232,280),(416,280),2)
        # The second cup has a stable place the hand can return to.
        shelf=(97,105,107) if loop<2 else (143,157,150)
        pygame.draw.line(surface,shelf,(505,395),(570,395),3)
        if loop==2:
            self.cup(surface,(535,374,27,22))
        floor=(34,39,43) if loop==0 else (28,32,42) if loop==1 else (193,205,198)
        pygame.draw.rect(surface,floor,(0,552,1100,128))
        beam=pygame.Surface((1100,680),pygame.SRCALPHA)
        color=(228,192,128,22) if loop==0 else (168,183,197,12) if loop==1 else (246,243,220,60)
        pygame.draw.polygon(beam,color,[(235,395),(414,395),(804,680),(292,680)])
        surface.blit(beam,(0,0))


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
        light_x,light_y=324,240
        spread=max(-170,min(220,(x-light_x)*.38))
        length=22+abs(x-light_x)*.035
        shadow=pygame.Surface((1100,680),pygame.SRCALPHA)
        width=12*scale+abs(stride)*3
        pygame.draw.polygon(shadow,(24,31,44,int(opacity*.20)),
                            [(x-width,y),(x+width,y),(x+spread+width*.6,y+length),(x+spread-width*1.5,y+length+5)])
        surface.blit(shadow,(0,0))
        surface.blit(image,image.get_rect(midbottom=(round(x),round(y+17*scale))))


    def cup(self,surface,rect):
        image=pygame.transform.smoothscale(self.objects['cup'],(rect[2],rect[3]))
        surface.blit(image,(rect[0],rect[1]))

    def cabinet(self,surface,rect,loop=0):
        image=pygame.transform.smoothscale(self.objects['cabinet'],(rect[2],rect[3]))
        surface.blit(image,(rect[0],rect[1]))
        if loop==2:
            pygame.draw.rect(surface,(147,160,157),(rect[0]+28,rect[1]+46,47,46),border_radius=3)

    def chamber(self,g,actors=True):
        c=g.canvas;p=PALETTES[g.loop]
        layer=pygame.Surface((1100,680),pygame.SRCALPHA)
        # A small inhabited terrace in a much larger remembered landscape.
        pygame.draw.polygon(c,(52,70,73) if g.loop==0 else (47,45,66),
                            [(180,551),(920,551),(864,584),(230,584)])
        pygame.draw.polygon(c,(35,53,60) if g.loop==0 else (35,34,54),
                            [(230,584),(864,584),(864,598),(230,598)])
        pygame.draw.line(c,p['court_accent'],(180,551),(920,551),1)
        # Shared folded silhouette, with one visible short support.
        rect=pygame.Rect(395,447,220,104)
        if g.loop<2:
            repairing=g.mode=='mend'
            progress=min(1,g.age/2.8) if repairing else 0
            tilt=0 if g.loop==1 or g.leveled else -1.5*(1-progress)
            self.table.draw(c,rect,0,ticket=False,outline=False)
            for i in range(2):
                self.cup(c,(455+i*48,426,40,30))
        self.cabinet(c,(690,340,110,211),g.loop)
        if g.loop==0:
            pygame.draw.ellipse(c,(196,177,131),(704,419,9,3))
        if g.loop==1:
            for i in range(7):
                xx=480+i*37
                pygame.draw.line(layer,(*p['shade'],40),(xx,465),(xx+10,489+i*4),1)
        c.blit(layer,(0,0))

        if actors and g.loop==0 and g.mode not in ('coda','ending'):
            opacity=235 if g.loop==0 else 100 if g.loop==1 else 165
            repairing=g.mode=='mend'
            ox=548 if repairing else 775
            reach=min(1,g.age/.8) if repairing else .65
            self.presence(c,ox,551,1,g.t,g.loop,opacity,reduced=g.reduced,facing=-1,reach=reach,lean=reach*.5)
        if actors:self.presence(c,495 if g.mode=='mend' else g.x,551,0,g.t,g.loop,moving=g.stride_weight,reduced=g.reduced,facing=g.facing,phase=g.walk,reach=min(1,g.age/.9) if g.mode=='mend' else 0,crouch=0)
