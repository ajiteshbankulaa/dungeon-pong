"""Aiming and collision geometry shared by the live ball and its preview."""
import math
import pygame

def shot_angle(paddle_y):
    return (paddle_y-345)/141*.88

def reflect_table(ball,rectangles):
    for rect in rectangles:
        if rect.inflate(10,10).collidepoint(ball['x'],ball['y']):
            ball['x']=rect.left-7 if ball['vx']>0 else rect.right+7
            ball['vx']*=-1
            return True
    return False

def trajectory(y,angle,rectangles=()):
    ball=dict(x=158.,y=y,vx=425*math.cos(angle),vy=425*math.sin(angle))
    points=[(158,y)]
    for i in range(480):
        ball['x']+=ball['vx']/120
        ball['y']+=ball['vy']/120
        if ball['y']<154 or ball['y']>536:
            ball['y']=max(154,min(536,ball['y']))
            ball['vy']*=-1
        reflect_table(ball,rectangles)
        if i%3==0:points.append((ball['x'],ball['y']))
        if ball['x']>=920 or ball['x']<110:
            points.append((ball['x'],ball['y']))
            break
    return points
