"""Shared folded-paper table, used in the room, the court and the coda."""
from pathlib import Path
import pygame

ASSETS = Path(__file__).resolve().parent.parent / 'assets/poem'

class PaperTable:
    def __init__(self):
        self.image = pygame.image.load(str(ASSETS / 'table.svg'))
        self.court = pygame.image.load(str(ASSETS / 'reaches.svg'))
        self.ticket = pygame.image.load(str(ASSETS / 'ticket.svg'))

    def draw(self, surface, rect, tilt=0, ticket=False, outline=False, court=False):
        image = pygame.transform.smoothscale(self.court if court else self.image, rect.size)
        if outline:
            image.set_alpha(75)
        if tilt:
            image = pygame.transform.rotozoom(image, tilt, 1)
        surface.blit(image, image.get_rect(center=rect.center))
        if ticket:
            width = max(20, round(rect.width * .17))
            fold = pygame.transform.smoothscale(self.ticket, (width, max(10, width//3)))
            surface.blit(fold, (rect.left + rect.width*.13, rect.bottom-7))

    @staticmethod
    def colliders(rect):
        def box(x,y,w,h):
            return pygame.Rect(rect.x+x*rect.w, rect.y+y*rect.h, w*rect.w, h*rect.h)
        return [box(.225,.045,.15,.35),box(.63,.54,.15,.40)]
