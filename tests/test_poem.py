"""Behavioral tests of the real score, including the aiming preview contract."""
import os
os.environ.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy')
import math
import pygame
import pytest
from poem.app import Poem,read_axes
from poem.runtime import PASSAGES,load_progress
from poem.shots import trajectory,shot_angle

def tap(g):
    if g.mode in ('pong','glass'):
        key=pygame.K_SPACE
    elif g.mode in ('cabinet','table','coin','coda'):
        key=pygame.K_e
    else:
        key=pygame.K_RETURN
    g.event(pygame.event.Event(pygame.KEYDOWN,key=key))

@pytest.fixture(scope='module',autouse=True)
def sdl():
    pygame.mixer.pre_init(44100,-16,2,512)
    pygame.init()
    pygame.display.set_mode((1100,680))
    yield
    pygame.quit()

@pytest.fixture
def g(tmp_path):
    return Poem(tmp_path/'save.json')

def until(g,predicate,seconds=30,move=lambda:0,back=False):
    for _ in range(round(seconds*120)):
        if predicate():return
        g.update(1/120,move(),back)
    assert predicate(),(g.index,g.mode,g.phase,g.target_count,g.count)

def aim(g,y):
    until(g,lambda:abs(g.py-y)<.6,move=lambda:max(-1,min(1,(y-g.py)/5)))

def approach(g,x):
    until(g,lambda:abs(g.x-x)<8,move=lambda:1 if g.x<x else -1)
    tap(g)

def shooting_lane(g):
    obstacles=g.art.table.colliders(g.table_rect) if g.kind in ('fold','diagram') else ()
    if g.kind=='measure':return 345+g.angle*141/.88
    for y in range(205,485):
        path=trajectory(y,shot_angle(y),obstacles)
        if path[-1][0]>=920 and abs(path[-1][1]-g.target_y)<18:
            return y
    raise AssertionError(('Unreachable opening',g.index,g.target_y))

def play(g):
    if g.mode=='text':tap(g)
    if g.mode=='cabinet':approach(g,745)
    if g.mode=='table':
        approach(g,470)
        until(g,lambda:g.mode=='pong')
    if g.kind in ('angle','measure','fold','diagram'):
        while g.mode=='pong':
            until(g,lambda:g.phase=='ready' or g.mode=='text')
            if g.mode=='text':break
            aim(g,shooting_lane(g));tap(g)
            until(g,lambda:g.phase!='playing')
    else:
        if g.kind=='voices':aim(g,275)
        tap(g)
        def follow():
            if g.phase=='ready':tap(g)
            if g.loop==2 or not g.balls:return 0
            return max(-1,min(1,(g.balls[0]['y']-g.py)/20))
        until(g,lambda:g.mode=='text',90,follow)
    assert g.lines==g.passage['closing']
    tap(g)

def test_entire_score(g):
    g.begin()
    for i in range(15):
        assert g.index==i
        play(g)
        if i==4:
            assert g.mode=='rupture'
            assert not pygame.mixer.get_busy()
            assert not pygame.mixer.music.get_busy()
            g.update(3.49);tap(g);assert g.mode=='rupture'
            g.update(.011);assert g.mode=='hooks'
            tap(g);approach(g,745)
            assert 'quarter' in g.lines
            tap(g);g.update(.01)
        elif i==9:
            assert g.mode=='withdraw'
            until(g,lambda:g.index==10,back=True)
    assert g.mode=='coda'
    approach(g,470);assert g.cup
    tap(g);approach(g,745);assert g.ticket
    tap(g)
    cues=[];g.cue=cues.append;g.update(.01);g.update(1)
    assert cues==['piano'] and g.mode=='ending'
    tap(g);g.begin()
    assert g.lines=='I remember you letting me serve first.'

def test_single_clock_and_unanswered_beat(g):
    g.index=13;g.enter();tap(g);tap(g)
    until(g,lambda:g.crossed)
    start=g.elapsed;y=g.py
    for _ in range(120):g.update(1/120,1)
    assert g.elapsed-start==pytest.approx(1)
    assert g.py!=y and g.mode=='glass'
    g.update(.51)
    assert g.mode=='text'
    assert g.lines=='I still waited for the return.'

def test_bus_once_and_no_hidden_wait(g):
    g.index=9;g.enter();g.mode_to('pong');g.count=3;g.serve()
    cues=[];g.cue=cues.append
    until(g,lambda:g.mode=='text')
    for _ in range(60):g.update(1/120)
    assert cues.count('bus')==1
    assert cues.count('bus')==1 and len(g.balls)==1

@pytest.mark.parametrize('index',[1,2,6,7])
def test_guide_matches_actual_shot(g,index):
    g.index=index;g.enter();g.mode_to('pong')
    lane=shooting_lane(g);aim(g,lane);g.serve()
    expected=trajectory(g.py,shot_angle(g.py),g.art.table.colliders(g.table_rect) if index in (2,7) else ())
    until(g,lambda:g.phase!='playing')
    assert g.target_count==1
    assert expected[-1][0]>=920
    if index!=6:assert abs(expected[-1][1]-230)<42

@pytest.mark.parametrize('index',[0,5,10])
def test_ready_ball_and_no_autoserve(g,index):
    g.index=index;g.enter();g.mode_to('glass' if index==10 else 'pong')
    g.update(1,1);g.draw()
    from poem.artwork import PALETTES
    assert tuple(g.canvas.get_at((158,round(g.py))))[:3]==tuple(PALETTES[g.loop]['court_ink'])
    assert not g.balls
    tap(g);assert g.balls
    g.retry('Try again')
    g.update(5)
    assert g.phase=='ready' and not g.balls

def test_text_input_reveal_then_advance(g):
    g.begin();g.advance_text_or_act()
    assert g.mode=='cabinet'

def test_miss_keeps_returns(g):
    g.index=3;g.enter();g.mode_to('pong');g.count=3;g.serve()
    g.py=480
    g.balls[0].update(x=111,y=190,vx=-425)
    g.update(1/120)
    assert g.count==3 and g.phase=='ready' and g.feedback

@pytest.mark.parametrize('key',[pygame.K_DOWN,pygame.K_s,None])
def test_withdraw_keyboard_and_controller(g,key):
    from collections import defaultdict
    class Pad:
        def get_numaxes(self):return 2
        def get_axis(self,i):return .8 if i==1 else 0
    keys=defaultdict(int)
    if key:keys[key]=1
    h,v=read_axes(keys,[Pad()] if key is None else [])
    g.index=9;g.mode_to('withdraw')
    until(g,lambda:g.index==10,back=v>.45)
    assert g.lines==PASSAGES[10]['opening']

def test_save_and_replay(g):
    g.index=10;g.save(True)
    g.progress=load_progress(g.path);g.begin(True)
    assert g.lines==PASSAGES[10]['opening']
    g.begin()
    assert g.lines=='I remember you letting me serve first.'


def test_completed_room_never_forces_scene(g):
    g.index=0;g.enter();g.mode_to('pong')
    g.aftermath(.5)
    assert g.mode=='text' and g.lines
    g.update(60)
    assert g.mode=='text'

def test_serve_cannot_repeat_itself(g):
    g.index=0;g.enter();g.mode_to('pong')
    tap(g)
    original=g.balls[0]
    for _ in range(10):tap(g)
    assert len(g.balls)==1 and g.balls[0] is original



def test_rupture_never_advances_without_input(g):
    g.index=4
    g.resolve()
    g.update(3.5)
    assert g.mode=='hooks'
    g.update(90)
    assert g.mode=='hooks'

def test_completion_is_idempotent(g):
    g.index=0;g.enter();g.mode_to('pong')
    g.finish()
    age=g.age
    g.update(.3);g.finish()
    assert g.mode=='text' and g.age>age



def test_enter_never_launches_ball(g):
    g.index=0;g.enter();g.mode_to('pong')
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    assert g.phase=='ready' and not g.balls
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_SPACE))
    assert g.phase=='playing' and len(g.balls)==1

def test_complete_rooms_reveal_text_without_input(g):
    for index in (0,1,2,3,4,5,6,7,8,9):
        g.index=index;g.enter();g.mode_to('pong')
        g.aftermath()
        assert g.mode=='text' and g.lines==g.passage['closing']
        g.draw()
        before=g.index
        g.update(10)
        assert g.index==before and g.mode=='text'



def test_landscape_covers_full_canvas(g):
    for loop in range(3):
        g.art.background(g.canvas,loop,0)
        for point in ((1090,10),(1090,670),(10,670)):
            assert tuple(g.canvas.get_at(point))[:3]!=(0,0,0)

def test_music_does_not_restart_at_room_boundary(g):
    g.index=0;g.enter()
    g.score.offset=5
    g.index=1;g.enter()
    assert g.score.offset==5 and g.score.playing
    g.index=10;g.enter()
    assert not g.score.playing

