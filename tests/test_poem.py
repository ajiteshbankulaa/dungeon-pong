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
    elif g.mode in ('cabinet','table','coin','coda','place_cup','return_glass'):
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

def trace(g):
    tap(g)
    for _ in range(330):
        g.update(1/120,horizontal=1)
    g.event(pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE))

def play(g):
    if g.mode=='text':tap(g)
    if g.mode=='cabinet':approach(g,745)
    if g.mode=='table':
        approach(g,470)
        until(g,lambda:g.mode=='pong')
    if g.mode=='return_glass':approach(g,745)
    if g.mode=='place_cup':
        approach(g,470)
        until(g,lambda:g.mode=='text')
        assert g.cup and g.lines==g.passage['closing']
        tap(g)
        return
    if g.mode=='glass':
        trace(g)
        if g.kind=='last':
            assert g.mode=='coda'
        else:
            until(g,lambda:g.mode=='text')
            closing='still_closing' if g.kind=='wait' else 'closing'
            assert g.lines==g.passage[closing]
            tap(g)
        return
    if g.kind in ('angle','measure'):
        while g.mode=='pong':
            until(g,lambda:g.phase=='ready' or g.mode=='text')
            if g.mode=='text':break
            aim(g,shooting_lane(g));tap(g)
            until(g,lambda:g.phase!='playing')
    else:
        if g.kind=='voices':aim(g,275)
        if g.kind in ('fold','diagram'):aim(g,345)
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
            assert g.mode=='dawn'
            tap(g);until(g,lambda:g.mode=='text')
            assert g.lines==PASSAGES[10]['opening']
    assert g.mode=='coda'
    assert g.cup
    approach(g,470)
    until(g,lambda:g.cup_held)
    tap(g)
    cues=[];g.cue=cues.append;g.update(.01);g.update(1)
    assert cues==['piano'] and g.mode=='ending'
    tap(g);g.begin()
    assert g.lines=='I remember you letting me serve first.'

def test_single_clock_and_unanswered_beat(g):
    g.index=13;g.enter();approach(g,745);trace(g)
    until(g,lambda:g.crossed)
    start=g.elapsed;y=g.py
    marks=list(g.dust_trail)
    for _ in range(120):g.update(1/120,1,horizontal=-1)
    assert g.finger_x<g.release_x-42 and marks==g.dust_trail
    assert g.elapsed-start==pytest.approx(1)
    assert g.py!=y and g.mode=='glass'
    g.update(.51)
    assert g.mode=='text'
    assert g.lines==PASSAGES[13]['closing']

def test_bus_once_and_no_hidden_wait(g):
    g.index=9;g.enter();g.mode_to('pong');g.count=3;g.serve()
    cues=[];g.cue=cues.append
    until(g,lambda:g.mode=='text')
    for _ in range(60):g.update(1/120)
    assert cues.count('bus')==1
    assert cues.count('bus')==1 and len(g.balls)==1

@pytest.mark.parametrize('index',[1,6])
def test_guide_matches_actual_shot(g,index):
    g.index=index;g.enter();g.mode_to('pong')
    lane=shooting_lane(g);aim(g,lane);g.serve()
    expected=trajectory(g.py,shot_angle(g.py),g.art.table.colliders(g.table_rect) if index in (2,7) else ())
    until(g,lambda:g.phase!='playing')
    assert g.target_count==1
    assert expected[-1][0]>=920
    if index!=6:assert abs(expected[-1][1]-230)<42

@pytest.mark.parametrize('index',[0,5])
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
    assert g.mode=='dawn'
    tap(g);until(g,lambda:g.mode=='text')
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
    assert g.score.playing and g.score.act==2



def test_last_invitation_can_rest(g):
    g.index=14;g.enter();tap(g)
    assert g.mode=='glass' and not g.balls
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_e))
    assert g.mode=='coda' and g.cup

def test_voice_assets_are_distinct(g):
    assert g.score.bank['note0'].get_raw()!=g.score.bank['hollow'].get_raw()

def test_withdrawal_moves_away_in_the_same_room(g):
    g.index=9;g.resolve()
    assert g.x==745
    g.update(.5,move=-1)
    assert 455<g.x<745 and g.facing==-1 and g.walk>0


def test_arcade_does_not_block_walking(g):
    for mode in ('cabinet','coin','coda'):
        g.mode_to(mode)
        g.x=640
        g.update(10,1)
        assert g.x==860

def test_start_and_resume_buttons(g):
    g.draw()
    g.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(550,445)))
    assert g.mode=='text'
    g.paused=True;g.draw()
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    assert not g.paused

def test_glass_trace_has_no_ball(g):
    g.index=11;g.enter();tap(g);tap(g);g.update(.4)
    assert g.dust_trail and not g.balls
    x=g.finger_x
    g.update(2)
    assert g.finger_x==x and g.mode=='glass'
    for _ in range(330):g.update(1/120,horizontal=1)
    g.event(pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE))
    until(g,lambda:g.mode=='text')
    tap(g);assert g.index==12 and g.mode=='place_cup'


def test_memory_scene_draws_exactly_two_figures(g,monkeypatch):
    for index in (0,5):
        g.index=index;g.enter();g.finish()
        figures=[]
        monkeypatch.setattr(g.art,'presence',lambda *args,**kwargs:figures.append(args[3]))
        g.draw()
        assert figures==([0,1] if index==0 else [0])

def test_between_is_considerate_placement(g):
    g.index=2;g.enter();tap(g)
    until(g,lambda:g.mode=='pong')
    aim(g,345);tap(g)
    until(g,lambda:g.mode=='text',30,lambda:max(-1,min(1,(g.balls[0]['y']-g.py)/20)) if g.balls else 0)
    assert g.target_count==2
    assert g.lines==g.passage['closing']

def test_foreground_actor_drawn_after_machine(g,monkeypatch):
    g.index=0;g.mode_to('cabinet');g.x=745
    order=[]
    monkeypatch.setattr(g.art,'cabinet',lambda *a,**kw:order.append('machine'))
    monkeypatch.setattr(g.art,'presence',lambda *a,**kw:order.append('actor'))
    g.draw()
    assert order[-1]=='actor' and order.index('machine')<len(order)-1

def test_start_and_resume_accept_enter(g):
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    assert g.mode=='text'
    g.paused=True
    g.event(pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN))
    assert not g.paused



def test_recorded_opponent_ignores_new_ball_position(g):
    g.memories[0]=([(310.,.5)]*600,[17.])
    g.index=5;g.enter();g.mode_to('pong');g.serve()
    g.balls[0]['y']=470
    g.update(.1)
    assert g.oy==310 and g.cuff==.5

def test_controller_can_resume_and_leave_last_trace(g):
    g.paused=True
    g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=0))
    assert not g.paused
    g.index=14;g.enter();tap(g)
    g.event(pygame.event.Event(pygame.JOYBUTTONDOWN,button=1))
    assert g.mode=='coda'


def test_recorded_motion_survives_checkpoint(g):
    g.memories[0]=([(320.,.4),(325.,.5)],[18.])
    g.index=5
    g.save()
    resumed=Poem(g.path)
    assert resumed.memories[0]==g.memories[0]


def test_lifting_early_keeps_trace_recoverable(g):
    g.index=10;g.enter();tap(g);tap(g)
    g.update(.5,horizontal=1)
    g.event(pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE))
    assert g.phase=='ready' and g.mode=='glass'
    previous=g.finger_x
    g.update(2,horizontal=1)
    assert g.finger_x==previous
    trace(g)
    assert g.mode=='text'

def test_paused_glass_needs_fresh_contact(g):
    g.index=14;g.enter();tap(g);tap(g)
    for _ in range(320):g.update(1/120,horizontal=1)
    g.event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
    for event in (pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE),
                  pygame.event.Event(pygame.JOYBUTTONDOWN,button=1)):
        g.event(event)
    assert g.paused and g.mode=='glass' and g.phase=='playing'
    tap_resume=pygame.event.Event(pygame.KEYDOWN,key=pygame.K_RETURN)
    g.event(tap_resume)
    x=g.finger_x
    g.update(.3,horizontal=-1)
    assert g.finger_x==x and not g.touching
    tap(g);g.event(pygame.event.Event(pygame.KEYUP,key=pygame.K_SPACE))
    assert g.mode=='coda'

def test_still_hand_waits_without_drawing(g):
    g.index=13;g.enter();approach(g,745);trace(g)
    x=g.finger_x
    marks=list(g.dust_trail)
    g.update(1.49)
    assert g.phase=='waiting' and g.finger_x==x and g.dust_trail==marks
    g.update(.02)
    assert g.lines==g.passage['still_closing']

def test_silent_hooks_survive_resume(g):
    g.index=4;g.enter();g.resolve();g.update(3.51)
    for key in (pygame.K_ESCAPE,pygame.K_RETURN):
        g.event(pygame.event.Event(pygame.KEYDOWN,key=key))
    assert g.mode=='hooks' and not pygame.mixer.music.get_busy()

def test_replay_is_one_exchange_back_to_choice(g):
    g.index=9;g.enter();g.resolve();g.update(.4,move=-1);g.action()
    assert g.mode=='pong' and not g.balls and g.replaying
    tap(g)
    until(g,lambda:g.mode=='withdraw',12)
    assert g.count==1 and g.x==745

def test_two_tones_sound_at_their_own_contacts(g):
    g.index=8;g.enter();tap(g);aim(g,275)
    cues=[];g.cue=cues.append;tap(g)
    assert not cues
    until(g,lambda:g.answered)
    assert cues==['note0'] and not g.crossed
    until(g,lambda:g.mode=='text')
    assert cues==['note0','hollow']
