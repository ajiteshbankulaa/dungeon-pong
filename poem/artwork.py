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
        p=PALETTES[loop]
        surface.fill(p['sky'])
        # A window drawn once: small imperfections belong to the room, never to a shake effect.
        light=((172,146,119),(98,115,135),(239,232,204))[loop]
        pygame.draw.polygon(surface,light,[(243,155),(406,158),(404,392),(245,394)])
        pygame.draw.aalines(surface,p['shade'],True,[(240,152),(409,156),(407,397),(241,396)])
        pygame.draw.line(surface,p['sky'],(325,157),(323,393),4)
        pygame.draw.line(surface,p['sky'],(245,273),(404,276),3)
        pygame.draw.rect(surface,p['floor'],(0,552,1100,128))
        pygame.draw.aalines(surface,p['shade'],False,[(170,552),(483,551),(804,553),(945,551)])
        pygame.draw.line(surface,p['shade'],(505,395),(570,395),2)
        if loop==2:self.cup(surface,(535,374,27,22))

    def court_background(self,surface,loop):
        key=('court',loop)
        if key not in self.backgrounds:
            asset=Path(__file__).resolve().parent.parent/'assets/poem'/f'court-{loop}.svg'
            self.backgrounds[key]=pygame.image.load(str(asset)).convert()
        surface.blit(self.backgrounds[key],(0,0))

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
            pygame.draw.lines(body, tone, False, [(hip[0]+side*5,153+crouch*28), (knee[0]+crouch*10,knee[1]+crouch*8), foot], 5)
            pygame.draw.line(body, tone, foot, (foot_x+6,foot[1]), 5)
        tone=(130,185,190) if which==0 else (181,166,199)
        # An open face and a single unwaisted coat suggest a person without portraiture.
        sway=0 if reduced else stride*2+lean*4
        head=pygame.Rect(76+round(sway),29+round(breath),28,33)
        pygame.draw.ellipse(body,tone,head,3)
        torso=pygame.Surface((180,240),pygame.SRCALPHA)
        pygame.draw.polygon(torso,tone,[(81,73),(100,73),(107,145),(73,145)])
        body.blit(torso,(round(sway),round(breath)))
        arm_swing=stride*9
        for side in (-1,1):
            shoulder=(90+side*10+sway,82+breath)
            elbow=(90+side*19+sway+side*arm_swing*.35,108+breath)
            wrist=(90+side*16+sway+side*arm_swing,130+breath)
            pygame.draw.lines(body,tone,False,[shoulder,elbow,wrist],5)
        if which==1:
            pygame.draw.line(body,(234,220,227),(102+sway-arm_swing,123+breath),
                             (110+sway-arm_swing,122+breath),3)
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
        pygame.draw.aaline(c,p['shade'],(210,551),(902,551))
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
